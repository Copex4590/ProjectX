from __future__ import annotations

import json

from app.paths import resource_path

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
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

    def set_observation_points(self, points: list[dict]) -> None:

        self._pending_points = list(points)
        self._apply_observation_points()

    def clear_observation_points(self, message: str = "") -> None:

        self._pending_points = []
        self._empty_message = message
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

        self._run_js(
            f"setPickMarker({float(latitude)}, {float(longitude)});"
        )

    def clear_pick_marker(self) -> None:

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

    def _apply_location_pick(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._run_js(f"beginLocationPick({message});")

    def _apply_observation_points(self) -> None:

        if not self._page_ready:
            return

        if not self._pending_points:
            self._apply_empty_state()
            return

        payload = json.dumps(self._pending_points)
        self._run_js(f"updateObservationPoints({payload});")

    def _apply_empty_state(self) -> None:

        if not self._page_ready:
            return

        if self._pick_overlay_message:
            return

        message = json.dumps(self._empty_message)
        self._run_js(f"clearObservationPoints({message});")

    def _apply_pick_overlay(self) -> None:

        if not self._page_ready:
            return

        message = json.dumps(self._pick_overlay_message)
        self._run_js(f"setPickOverlay({message});")

    def focus_ship(self, mmsi: int):

        self._run_js(f"focusShip({int(mmsi)});")

    def update_ships(self, payload: str):

        if not self._page_ready:
            return

        self._run_js(f"updateShips({payload});")

    def _run_js(self, script: str) -> None:

        self.page().runJavaScript(script)
