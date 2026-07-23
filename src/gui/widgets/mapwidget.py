from __future__ import annotations

import json

from app.paths import resource_path
from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit, trace_event

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class _MapBridge(QObject):

    openLogbookRequested = Signal(int)
    locationSelected = Signal(float, float)

    @Slot(int)
    def openLogbook(self, mmsi: int):

        self.openLogbookRequested.emit(int(mmsi))

    @Slot(float, float)
    def reportLocation(self, latitude: float, longitude: float):

        self.locationSelected.emit(float(latitude), float(longitude))


class MapWidget(QWebEngineView):

    openLogbookRequested = Signal(int)
    locationSelected = Signal(float, float)

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

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        html = resource_path("map", "map.html")

        self.load(QUrl.fromLocalFile(str(html)))
        self.loadFinished.connect(self._on_load_finished)

        self._pending_points: list[dict] | None = None
        self._empty_message = ""
        self._pick_overlay_message = ""
        self._pick_enabled = False
        self._page_ready = False
        self._pending_ships_payload: str | None = None
        self._ships_flush_scheduled = False
        self._pending_playback: dict | None = None

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
        self._run_js(f"enablePickMode({'true' if self._pick_enabled else 'false'});")

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

        self._run_js("endLocationPick();")

    def reset_world_view(self) -> None:

        if not self._page_ready:
            return

        self._run_js("resetMapToWorldView();")

    def refresh_location_pick_view(self) -> None:

        if not self._page_ready:
            return

        if not self._pick_enabled or not self._pick_overlay_message:
            self.reset_world_view()
            return

        message = json.dumps(self._pick_overlay_message)
        self._run_js(f"refreshLocationPickView({message});")

    def set_pick_overlay(self, message: str) -> None:

        self._pick_overlay_message = str(message)
        self._apply_pick_overlay()

    def clear_pick_overlay(self) -> None:

        self._pick_overlay_message = ""
        self._apply_pick_overlay()

    def set_pick_marker(self, latitude: float, longitude: float) -> None:

        if not self._page_ready:
            return

        self._run_js(
            f"setPickMarker({float(latitude)}, {float(longitude)});"
        )

    def clear_pick_marker(self) -> None:

        if not self._page_ready:
            return

        self._run_js("clearPickMarker();")

    def mousePressEvent(self, event: QMouseEvent) -> None:

        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:

        if event.key() == Qt.Key.Key_Escape and self._pick_enabled:
            from gui.mapcontroller import MapController

            MapController.instance().cancel_pick_mode()
            event.accept()
            return

        super().keyPressEvent(event)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            return

        self._page_ready = True

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
        self._flush_pending_playback()

    def _apply_location_pick(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._run_js(f"beginLocationPick({message});")

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
            self._run_js(f"updateObservationPoints({payload});")
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
            self._run_js(f"clearObservationPoints({message});")
            trace_exit("MapWidget._apply_empty_state.runJavaScript")

    def _apply_pick_overlay(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._run_js(f"setPickOverlay({message});")

    def focus_ship(self, mmsi: int):

        self._run_js(f"focusShip({int(mmsi)});")

    def set_playback_active(self, mmsi: int | None) -> None:

        state = self._pending_playback if self._pending_playback is not None else {}
        state = dict(state)
        state["active_mmsi"] = None if mmsi is None else int(mmsi)
        self._pending_playback = state
        self._flush_pending_playback()

    def set_playback_trail(self, points: list[tuple[float, float]]) -> None:

        state = self._pending_playback if self._pending_playback is not None else {}
        state = dict(state)
        state["trail"] = [[float(lat), float(lon)] for lat, lon in points]
        self._pending_playback = state
        self._flush_pending_playback()

    def set_playback_cursor(
        self,
        lat: float | None,
        lon: float | None,
        heading: float | None = None,
    ) -> None:

        state = self._pending_playback if self._pending_playback is not None else {}
        state = dict(state)
        if lat is None or lon is None:
            state["cursor"] = None
        else:
            state["cursor"] = {
                "lat": float(lat),
                "lon": float(lon),
                "heading": float(heading or 0.0),
            }
        self._pending_playback = state
        self._flush_pending_playback()

    def clear_playback(self) -> None:

        self._pending_playback = {"clear": True}
        self._flush_pending_playback()

    def _flush_pending_playback(self) -> None:

        if not self._page_ready or self._pending_playback is None:
            return

        state = self._pending_playback
        self._pending_playback = None

        if state.get("clear"):
            self._run_js("clearPlayback();")
            return

        if "active_mmsi" in state:
            mmsi = state["active_mmsi"]
            if mmsi is None:
                self._run_js("setPlaybackActive(null);")
            else:
                self._run_js(f"setPlaybackActive({int(mmsi)});")

        if "trail" in state:
            payload = json.dumps(state["trail"])
            self._run_js(f"setPlaybackTrail({payload});")

        if "cursor" in state:
            cursor = state["cursor"]
            if cursor is None:
                self._run_js("setPlaybackCursor(null, null, 0);")
            else:
                self._run_js(
                    "setPlaybackCursor("
                    f"{cursor['lat']}, {cursor['lon']}, {cursor['heading']});"
                )

    def update_ships(self, payload: str):

        with trace_block(f"MapWidget.update_ships bytes={len(payload)}"):
            # SAVE-106: keep latest payload only; coalesce duplicate JS flushes.
            self._pending_ships_payload = payload

            if not self._page_ready:
                trace_event("MapWidget.update_ships deferred page_not_ready")
                return

            if self._ships_flush_scheduled:
                trace_event("MapWidget.update_ships merged pending flush")
                return

            self._ships_flush_scheduled = True
            QTimer.singleShot(0, self._flush_pending_ships)

    def _flush_pending_ships(self) -> None:

        self._ships_flush_scheduled = False

        if not self._page_ready or self._pending_ships_payload is None:
            return

        payload = self._pending_ships_payload

        trace_enter("MapWidget.update_ships.runJavaScript")
        self._run_js(f"updateShips({payload});")
        trace_exit("MapWidget.update_ships.runJavaScript")

    def _run_js(self, script: str) -> None:

        trace_enter(f"MapWidget._run_js len={len(script)}")
        self.page().runJavaScript(script)
        trace_exit(f"MapWidget._run_js len={len(script)}")
