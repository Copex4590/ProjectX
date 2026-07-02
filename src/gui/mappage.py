from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from gui.widgets.mapwidget import MapWidget
from database import registry
import json


class MapPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.map = MapWidget()
        layout.addWidget(self.map)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ships)
        self.timer.start(1000)

    def update_ships(self):

        ships = []

        for ship in registry.all():

            ships.append({
                "mmsi": ship.mmsi,
                "lat": ship.lat,
                "lon": ship.lon,
                "heading": ship.heading or 0,
                "speed": ship.speed,
                "course": ship.course,
                "name": ship.name,
            })

        payload = json.dumps(ships)

        self.map.page().runJavaScript(
            f"updateShips({payload});"
        )
