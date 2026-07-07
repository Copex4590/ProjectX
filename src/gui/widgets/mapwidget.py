from __future__ import annotations

import json

from app.paths import resource_path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class _MapBridge(QObject):

    openLogbookRequested = Signal(int)
    observationActionRequested = Signal(str, str)
    mapEmptyActionRequested = Signal(str, float, float)
    locationSelected = Signal(float, float)
    observationMoved = Signal(str, float, float)

    @Slot(int)
    def openLogbook(self, mmsi: int):

        self.openLogbookRequested.emit(int(mmsi))

    @Slot(str, str)
    def observationAction(self, point_id: str, action: str):

        self.observationActionRequested.emit(str(point_id), str(action))

    @Slot(str, float, float)
    def mapEmptyAction(self, action: str, latitude: float, longitude: float):

        self.mapEmptyActionRequested.emit(
            str(action),
            float(latitude),
            float(longitude),
        )

    @Slot(float, float)
    def reportLocation(self, latitude: float, longitude: float):

        self.locationSelected.emit(float(latitude), float(longitude))

    @Slot(str, float, float)
    def observationMoved(self, point_id: str, latitude: float, longitude: float):

        self.observationMoved.emit(
            str(point_id),
            float(latitude),
            float(longitude),
        )


class MapWidget(QWebEngineView):

    openLogbookRequested = Signal(int)
    observationActionRequested = Signal(str, str)
    mapEmptyActionRequested = Signal(str, float, float)
    locationSelected = Signal(float, float)
    observationMoved = Signal(str, float, float)

    def __init__(self):
        super().__init__()

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
        self._bridge.observationActionRequested.connect(
            self.observationActionRequested
        )
        self._bridge.mapEmptyActionRequested.connect(
            self.mapEmptyActionRequested
        )
        self._bridge.locationSelected.connect(self.locationSelected)
        self._bridge.observationMoved.connect(self.observationMoved)

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        html = resource_path("map", "map.html")

        self.load(QUrl.fromLocalFile(str(html)))
        self.loadFinished.connect(self._on_load_finished)

        self._pending_points: list[dict] | None = None
        self._empty_message = ""
        self._pick_enabled = False
        self._move_point_id: str | None = None
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

    def enable_move_mode(self, point_id: str | None) -> None:

        self._move_point_id = str(point_id).strip() if point_id else None
        value = json.dumps(self._move_point_id)
        self._run_js(f"enableMoveMode({value});")

    def _on_load_finished(self, ok: bool) -> None:

        if not ok:
            return

        self._page_ready = True
        self.enable_pick_mode(self._pick_enabled)
        self.enable_move_mode(self._move_point_id)

        if not self._pending_points:
            self._apply_empty_state()
        else:
            self._apply_observation_points()

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

        message = json.dumps(self._empty_message)
        self._run_js(f"clearObservationPoints({message});")

    def focus_ship(self, mmsi: int):

        self._run_js(f"focusShip({int(mmsi)});")

    def update_ships(self, payload: str):

        self._run_js(f"updateShips({payload});")

    def _run_js(self, script: str) -> None:

        self.page().runJavaScript(script)
