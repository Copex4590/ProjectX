from pathlib import Path

from PySide6.QtCore import QUrl, Signal, Slot
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class MapWidget(QWebEngineView):

    addShipSignal = Signal(object)
    updateShipSignal = Signal(object)
    removeShipSignal = Signal(int)

    def __init__(self):
        super().__init__()

        self._loaded = False

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls,
            True
        )

        self.addShipSignal.connect(self._add_ship_gui)
        self.updateShipSignal.connect(self._update_ship_gui)
        self.removeShipSignal.connect(self._remove_ship_gui)

        self.loadFinished.connect(self.loaded)

        html = (
            Path(__file__).resolve().parents[2]
            / "resources"
            / "map"
            / "map.html"
        )

        self.load(QUrl.fromLocalFile(str(html)))

    def loaded(self, ok):
        self._loaded = ok
        print("Map loaded:", ok)

    def add_ship(self, ship):
        self.addShipSignal.emit(ship)

    def update_ship(self, ship):
        self.updateShipSignal.emit(ship)

    def remove_ship(self, mmsi):
        self.removeShipSignal.emit(mmsi)

    @Slot(object)
    def _add_ship_gui(self, ship):

        if not self._loaded:
            return

        name = (ship.name or "").replace('"', '\\"')

        heading = ship.heading
        if heading is None or heading < 0:
            heading = ship.course if ship.course is not None else 0

        js = f"""
        addShip(
            {ship.mmsi},
            "{name}",
            {ship.lat},
            {ship.lon},
            {heading}
        );
        """

        self.page().runJavaScript(js)

    @Slot(object)
    def _update_ship_gui(self, ship):

        if not self._loaded:
            return

        heading = ship.heading
        if heading is None or heading < 0:
            heading = ship.course if ship.course is not None else 0

        js = f"""
        updateShip(
            {ship.mmsi},
            {ship.lat},
            {ship.lon},
            {heading}
        );
        """

        self.page().runJavaScript(js)

    @Slot(int)
    def _remove_ship_gui(self, mmsi):

        if not self._loaded:
            return

        self.page().runJavaScript(
            f"removeShip({mmsi});"
        )
