from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class _MapBridge(QObject):

    openLogbookRequested = Signal(int)

    @Slot(int)
    def openLogbook(self, mmsi: int):

        self.openLogbookRequested.emit(int(mmsi))


class MapWidget(QWebEngineView):

    openLogbookRequested = Signal(int)

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

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        html = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "resources"
            / "map"
            / "map.html"
        )

        self.load(QUrl.fromLocalFile(str(html)))
        self.loadFinished.connect(self._on_load_finished)

        self._pending_lat: float | None = None
        self._pending_lon: float | None = None

    def set_observation_point(self, latitude: float, longitude: float) -> None:

        self._pending_lat = latitude
        self._pending_lon = longitude
        self._apply_observation_point()

    def _on_load_finished(self, ok: bool) -> None:

        if not ok:
            return

        self._apply_observation_point()

    def _apply_observation_point(self) -> None:

        if self._pending_lat is None or self._pending_lon is None:
            return

        lat = self._pending_lat
        lon = self._pending_lon
        self.page().runJavaScript(
            f"setObservationPoint({lat}, {lon});"
        )

    def focus_ship(self, mmsi: int):

        self.page().runJavaScript(
            f"focusShip({int(mmsi)});"
        )

    def update_ships(self, payload: str):

        self.page().runJavaScript(
            f"updateShips({payload});"
        )
