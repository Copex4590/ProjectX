from pathlib import Path

import json

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class MapWidget(QWebEngineView):

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

        html = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "resources"
            / "map"
            / "map.html"
        )

        self.load(QUrl.fromLocalFile(str(html)))

    def focus_ship(self, mmsi: int):

        self.page().runJavaScript(
            f"focusShip({int(mmsi)});"
        )

    def update_ships(self, payload: str):

        self.page().runJavaScript(
            f"updateShips({payload});"
        )

    def set_vessel_card_layout(self, layout: str) -> None:

        encoded = json.dumps(str(layout or "standard"))
        self.page().runJavaScript(
            f"setVesselCardLayout({encoded});"
        )

    def set_translations(self, translations: dict) -> None:

        payload = json.dumps(translations or {})
        self.page().runJavaScript(
            f"setTranslations({payload});"
        )
