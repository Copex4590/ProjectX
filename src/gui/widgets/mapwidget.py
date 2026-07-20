from __future__ import annotations

import json
import logging

from app.paths import resource_path
from config.maptiler import maptiler_api_key
from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit, trace_event
from gui.map_engine import (
    BRIDGE_ENTRY_POINTS,
    BridgeVersionError,
    RenderCapabilities,
    RendererDiagnostics,
    default_capabilities,
    parse_bridge_info,
    parse_renderer_diagnostics,
    resolve_map_engine_kind,
    verify_bridge_info,
)

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


logger = logging.getLogger(__name__)


class _MapBridge(QObject):

    openLogbookRequested = Signal(int)
    locationSelected = Signal(float, float)
    headingSelected = Signal(float)

    @Slot(int)
    def openLogbook(self, mmsi: int):

        self.openLogbookRequested.emit(int(mmsi))

    @Slot(float, float)
    def reportLocation(self, latitude: float, longitude: float):

        self.locationSelected.emit(float(latitude), float(longitude))

    @Slot(float)
    def reportHeading(self, heading: float):

        self.headingSelected.emit(float(heading))


class MapWidget(QWebEngineView):

    openLogbookRequested = Signal(int)
    locationSelected = Signal(float, float)
    headingSelected = Signal(float)
    bridge_failed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        settings = self.settings()
        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.JavascriptEnabled,
            True,
        )

        self._bridge = _MapBridge()
        self._bridge.openLogbookRequested.connect(self.openLogbookRequested)
        self._bridge.locationSelected.connect(self.locationSelected)
        self._bridge.headingSelected.connect(self.headingSelected)

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        self._install_maptiler_api_key_script()

        self._engine_kind = resolve_map_engine_kind()
        self._capabilities = default_capabilities(self._engine_kind)

        html = resource_path("map", "map.html")
        url = QUrl.fromLocalFile(str(html))
        url.setQuery(f"engine={self._engine_kind.value}")

        self.load(url)
        self.loadFinished.connect(self._on_load_finished)

        self._pending_points: list[dict] | None = None
        self._empty_message = ""
        self._pick_overlay_message = ""
        self._pick_enabled = False
        self._page_ready = False
        self._bridge_verified = False
        self._bridge_error = ""
        self._pending_ships_payload: str | None = None
        self._renderer_diagnostics = RendererDiagnostics()

    def _install_maptiler_api_key_script(self) -> None:

        script = QWebEngineScript()
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setSourceCode(
            "window.__PROJECTX_MAPTILER_API_KEY__ = "
            f"{json.dumps(maptiler_api_key())};"
        )
        self.page().scripts().insert(script)

    @property
    def renderer_diagnostics(self) -> RendererDiagnostics:

        return self._renderer_diagnostics

    def fetch_renderer_diagnostics(self, callback=None) -> None:

        if not self._bridge_verified:
            if callback is not None:
                callback(self._renderer_diagnostics)
            return

        def _handle_payload(payload: str | None) -> None:

            if not payload:
                if callback is not None:
                    callback(self._renderer_diagnostics)
                return

            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                if callback is not None:
                    callback(self._renderer_diagnostics)
                return

            if not isinstance(data, dict):
                if callback is not None:
                    callback(self._renderer_diagnostics)
                return

            self._renderer_diagnostics = parse_renderer_diagnostics(data)

            if callback is not None:
                callback(self._renderer_diagnostics)

        self.page().runJavaScript(
            "JSON.stringify("
            "typeof getRendererDiagnostics === 'function'"
            " ? getRendererDiagnostics()"
            " : null"
            ")",
            _handle_payload,
        )

    @property
    def bridge_ready(self) -> bool:

        return self._bridge_verified

    @property
    def bridge_error(self) -> str:

        return self._bridge_error

    @property
    def render_capabilities(self) -> RenderCapabilities:

        return self._capabilities

    def set_observation_points(self, points: list[dict]) -> None:

        with trace_block(
            f"MapWidget.set_observation_points count={len(points)}"
        ):
            self._pending_points = list(points)
            self._apply_observation_points()

    def clear_observation_points(self, message: str = "") -> None:

        with trace_block("MapWidget.clear_observation_points"):
            self._pending_points = []
            self._empty_message = message
            self._pick_overlay_message = ""
            self._pick_enabled = False
            self._apply_empty_state()

    def set_observation_point(self, latitude: float, longitude: float) -> None:

        self.set_observation_points([
            {
                "id": "__legacy__",
                "name": "",
                "lat": latitude,
                "lon": longitude,
                "active": True,
            }
        ])

    def clear_observation_point(self, message: str = "") -> None:

        self.clear_observation_points(message)

    def enable_pick_mode(self, enabled: bool) -> None:

        self._pick_enabled = bool(enabled)
        enabled_js = "true" if self._pick_enabled else "false"
        self._invoke_bridge("setPickMode", enabled_js)

        if not self._pick_enabled:
            self.clear_pick_marker()

    def begin_location_pick(self, message: str) -> None:

        self._pick_enabled = True
        self._pick_overlay_message = str(message)
        self._apply_location_pick()

    def end_location_pick(self) -> None:

        self._pick_enabled = False
        self._pick_overlay_message = ""

        if not self._page_ready:
            return

        self._invoke_bridge("endLocationPick")

    def begin_heading_pick(self, message: str, latitude: float, longitude: float) -> None:

        self._pick_overlay_message = str(message)
        self._apply_heading_pick(latitude, longitude)

    def end_heading_pick(self) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("endHeadingPick")

    def set_cameras(self, cameras: list[dict]) -> None:

        if not self._page_ready:
            return

        payload = json.dumps(cameras)
        self._invoke_bridge("updateCameras", payload)

    def clear_cameras(self) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("clearCameras")

    def set_camera_preview(self, camera: dict) -> None:

        if not self._page_ready:
            return

        payload = json.dumps(camera)
        self._invoke_bridge("setCameraPreview", payload)

    def reset_world_view(self) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("resetMapToWorldView")

    def refresh_location_pick_view(self) -> None:

        if not self._page_ready:
            return

        if not self._pick_enabled or not self._pick_overlay_message:
            self.reset_world_view()
            return

        message = json.dumps(self._pick_overlay_message)
        self._invoke_bridge("refreshLocationPickView", message)

    def set_pick_overlay(self, message: str) -> None:

        self._pick_overlay_message = str(message)
        self._apply_pick_overlay()

    def clear_pick_overlay(self) -> None:

        self._pick_overlay_message = ""
        self._apply_pick_overlay()

    def set_pick_marker(self, latitude: float, longitude: float) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge(
            "setPickMarker",
            str(float(latitude)),
            str(float(longitude)),
        )

    def clear_pick_marker(self) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("clearPickMarker")

    def remove_ship(self, mmsi: int) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("removeShip", str(int(mmsi)))

    def clear_ships(self) -> None:

        if not self._page_ready:
            return

        self._invoke_bridge("clearShips")

    def mousePressEvent(self, event: QMouseEvent) -> None:

        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:

        if event.key() == Qt.Key.Key_Escape and (
            self._pick_enabled or self._pick_overlay_message
        ):
            from gui.mapcontroller import MapController

            MapController.instance().cancel_pick_mode()
            event.accept()
            return

        super().keyPressEvent(event)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            self._fail_bridge("Map page failed to load.")
            return

        self.page().runJavaScript(
            "JSON.stringify(typeof getBridgeInfo === 'function' ? getBridgeInfo() : null)",
            self._on_bridge_info,
        )

    def _on_bridge_info(self, payload: str | None) -> None:

        if not payload:
            self._fail_bridge(
                "Map bridge handshake failed: getBridgeInfo() returned no data."
            )
            return

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self._fail_bridge(
                "Map bridge handshake failed: bridge info is not valid JSON."
            )
            return

        if not isinstance(data, dict):
            self._fail_bridge(
                "Map bridge handshake failed: bridge info is not an object."
            )
            return

        try:
            bridge_info = parse_bridge_info(data)
            verify_bridge_info(
                bridge_info,
                expected_engine=self._engine_kind,
            )
        except BridgeVersionError as exc:
            self._fail_bridge(str(exc))
            return

        self._capabilities = bridge_info.capabilities
        self._bridge_verified = True
        self._page_ready = True
        self._bridge_error = ""

        if self._pick_enabled and self._pick_overlay_message:
            self._apply_location_pick()
        else:
            self.enable_pick_mode(self._pick_enabled)
            self._apply_pick_overlay()

        if not self._pending_points:
            self._apply_empty_state()
        else:
            self._apply_observation_points()

        self._flush_pending_ships()

    def _fail_bridge(self, message: str) -> None:

        logger.error("MapWidget bridge verification failed: %s", message)
        self._page_ready = False
        self._bridge_verified = False
        self._bridge_error = message
        self.bridge_failed.emit(message)

        escaped = json.dumps(message)
        self.page().runJavaScript(
            "(function(message) {"
            "const overlay = document.getElementById('empty-state');"
            "if (!overlay) return;"
            "overlay.textContent = message;"
            "overlay.hidden = false;"
            "overlay.classList.remove('map-empty-state--top');"
            f"}})({escaped});"
        )

    def _apply_heading_pick(self, latitude: float, longitude: float) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._invoke_bridge(
            "beginHeadingPick",
            message,
            str(float(latitude)),
            str(float(longitude)),
        )

    def _apply_location_pick(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._invoke_bridge("beginLocationPick", message)

    def _apply_observation_points(self) -> None:

        with trace_block("MapWidget._apply_observation_points"):
            if not self._page_ready:
                return

            if not self._pending_points:
                self._apply_empty_state()
                return

            trace_enter("MapWidget._apply_observation_points.json.dumps")
            payload = json.dumps(self._pending_points)
            trace_exit("MapWidget._apply_observation_points.json.dumps")

            trace_enter("MapWidget._apply_observation_points.runJavaScript")
            self._invoke_bridge("updateObservationPoints", payload)
            trace_exit("MapWidget._apply_observation_points.runJavaScript")

    def _apply_empty_state(self) -> None:

        with trace_block("MapWidget._apply_empty_state"):
            if not self._page_ready:
                return

            if self._pick_overlay_message:
                trace_event("MapWidget._apply_empty_state skipped pick_overlay")
                return

            trace_enter("MapWidget._apply_empty_state.json.dumps")
            message = json.dumps(self._empty_message)
            trace_exit("MapWidget._apply_empty_state.json.dumps")

            trace_enter("MapWidget._apply_empty_state.runJavaScript")
            self._invoke_bridge("clearObservationPoints", message)
            trace_exit("MapWidget._apply_empty_state.runJavaScript")

    def _apply_pick_overlay(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._invoke_bridge("setPickOverlay", message)

    def focus_ship(self, mmsi: int):

        self._invoke_bridge("focusShip", str(int(mmsi)))

    def update_ships(self, payload: str):

        with trace_block(f"MapWidget.update_ships bytes={len(payload)}"):
            self._pending_ships_payload = payload

            if not self._page_ready:
                trace_event("MapWidget.update_ships deferred page_not_ready")
                return

            self._flush_pending_ships()

    def _flush_pending_ships(self) -> None:

        if not self._page_ready or self._pending_ships_payload is None:
            return

        payload = self._pending_ships_payload

        trace_enter("MapWidget.update_ships.runJavaScript")
        self._invoke_bridge("updateShips", payload)
        trace_exit("MapWidget.update_ships.runJavaScript")

    def _invoke_bridge(self, method: str, *args: str) -> None:

        if not self._bridge_verified:
            trace_event(
                f"MapWidget._invoke_bridge skipped bridge_not_verified method={method}"
            )
            return

        if method not in BRIDGE_ENTRY_POINTS:
            raise ValueError(f"Unknown bridge entry point: {method}")

        arg_list = ", ".join(args)
        script = f"{method}({arg_list});" if arg_list else f"{method}();"
        self._run_js(script)

    def _run_js(self, script: str) -> None:

        trace_enter(f"MapWidget._run_js len={len(script)}")
        self.page().runJavaScript(script)
        trace_exit(f"MapWidget._run_js len={len(script)}")
