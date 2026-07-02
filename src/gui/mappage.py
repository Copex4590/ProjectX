import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from database import registry
from gui.widgets.mapwidget import MapWidget


class MapPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.map = MapWidget()
        layout.addWidget(self.map)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ships)

        # 5 FPS frissítés – alap a smooth mozgáshoz
        self.timer.start(200)

    def update_ships(self):

        payload = json.dumps([
            {
                "mmsi": ship.mmsi,
                "lat": ship.lat,
                "lon": ship.lon,
                "heading": ship.heading or 0,
                "course": ship.course,
                "speed": ship.speed,
                "name": ship.name,
            }
            for ship in registry.all()
        ])

        self.map.update_ships(payload)
