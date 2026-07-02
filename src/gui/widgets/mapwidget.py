from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings
from pathlib import Path


class MapWidget(QWebEngineView):

    def __init__(self):
        super().__init__()

        settings = self.settings()
        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.JavascriptEnabled,
            True,
        )

        html_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "resources"
            / "map"
            / "map.html"
        )

        self.load(QUrl.fromLocalFile(str(html_path)))

    def focus_ship(self, mmsi):

        self.page().runJavaScript(
            f"focusShip({int(mmsi)});"
        )
