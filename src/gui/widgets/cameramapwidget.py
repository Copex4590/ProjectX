from app.paths import resource_path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class _CameraMapBridge(QObject):

    positionSelected = Signal(float, float)
    headingSelected = Signal(float)

    @Slot(float, float)
    def reportPosition(self, latitude: float, longitude: float):

        self.positionSelected.emit(latitude, longitude)

    @Slot(float)
    def reportHeading(self, heading: float):

        self.headingSelected.emit(heading)


class CameraMapWidget(QWebEngineView):

    positionSelected = Signal(float, float)
    headingSelected = Signal(float)

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

        self._bridge = _CameraMapBridge()
        self._bridge.positionSelected.connect(self.positionSelected)
        self._bridge.headingSelected.connect(self.headingSelected)

        channel = QWebChannel(self.page())
        channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(channel)

        html = resource_path("map", "camera_map.html")

        self.load(QUrl.fromLocalFile(str(html)))
        self.loadFinished.connect(self._on_load_finished)

        self._pending_lat: float | None = None
        self._pending_lon: float | None = None
        self._pending_heading: float = 0.0
        self._position_pick = False
        self._heading_pick = False

    def set_camera(self, latitude: float, longitude: float, heading: float) -> None:

        self._pending_lat = latitude
        self._pending_lon = longitude
        self._pending_heading = heading
        self._apply_camera()

    def set_heading(self, heading: float) -> None:

        self._pending_heading = heading
        self.page().runJavaScript(
            f"setHeading({float(heading)});"
        )

    def enable_position_pick(self, enabled: bool) -> None:

        self._position_pick = bool(enabled)
        self.page().runJavaScript(
            f"enablePositionPick({'true' if self._position_pick else 'false'});"
        )

        if self._position_pick:
            self.enable_heading_pick(False)

    def enable_heading_pick(self, enabled: bool) -> None:

        self._heading_pick = bool(enabled)
        self.page().runJavaScript(
            f"enableHeadingPick({'true' if self._heading_pick else 'false'});"
        )

        if self._heading_pick:
            self.enable_position_pick(False)

    def _on_load_finished(self, ok: bool) -> None:

        if not ok:
            return

        self.enable_position_pick(self._position_pick)
        self.enable_heading_pick(self._heading_pick)
        self._apply_camera()

    def _apply_camera(self) -> None:

        if self._pending_lat is None or self._pending_lon is None:
            return

        lat = self._pending_lat
        lon = self._pending_lon
        heading = self._pending_heading
        self.page().runJavaScript(
            f"setCamera({lat}, {lon}, {heading});"
        )
