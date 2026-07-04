import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from database import registry
from gui.widgets.mapwidget import MapWidget


def _serialize_ship(ship):
    payload = {
        "mmsi": ship.mmsi,
        "name": ship.name,
        "lat": ship.lat,
        "lon": ship.lon,
        "heading": ship.heading or 0,
        "course": ship.course,
        "speed": ship.speed,
        "callsign": ship.callsign,
        "ship_type": ship.ship_type,
        "destination": ship.destination,
        "eta": ship.eta,
        "distance_km": ship.distance_km,
        "direction": ship.direction,
        "text_heading": ship.text_heading,
        "source": ship.source,
        "last_seen": ship.last_seen.isoformat() if ship.last_seen else None,
        "ais_visible": ship.ais_visible,
        "rtl_visible": ship.rtl_visible,
        "camera_visible": ship.camera_visible,
    }

    for field_name in ("imo", "length", "width", "draft", "flag"):
        if hasattr(ship, field_name):
            payload[field_name] = getattr(ship, field_name)

    return payload


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
            _serialize_ship(ship)
            for ship in registry.all()
        ])

        self.map.update_ships(payload)
