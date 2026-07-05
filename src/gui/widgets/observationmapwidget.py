from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class _ObservationMapBridge(QObject):

    locationSelected = Signal(float, float)

    @Slot(float, float)
    def reportLocation(self, latitude: float, longitude: float):

        self.locationSelected.emit(latitude, longitude)


class ObservationMapWidget(QWebEngineView):

    locationSelected = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

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

        self._bridge = _ObservationMapBridge()
        self._bridge.locationSelected.connect(self.locationSelected)

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        html = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "resources"
            / "map"
            / "observation_map.html"
        )

        self.load(QUrl.fromLocalFile(str(html)))
        self.loadFinished.connect(self._on_load_finished)

        self._pending_lat: float | None = None
        self._pending_lon: float | None = None
        self._pick_enabled = False

    def set_observation_point(self, latitude: float, longitude: float) -> None:

        self._pending_lat = latitude
        self._pending_lon = longitude
        self._apply_observation_point()

    def enable_pick_mode(self, enabled: bool) -> None:

        self._pick_enabled = bool(enabled)
        self.page().runJavaScript(
            f"enablePickMode({'true' if self._pick_enabled else 'false'});"
        )

    def _on_load_finished(self, ok: bool) -> None:

        if not ok:
            return

        self.enable_pick_mode(self._pick_enabled)
        self._apply_observation_point()

    def _apply_observation_point(self) -> None:

        if self._pending_lat is None or self._pending_lon is None:
            return

        lat = self._pending_lat
        lon = self._pending_lon
        self.page().runJavaScript(
            f"setObservationPoint({lat}, {lon});"
        )
