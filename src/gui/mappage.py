import json

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from database import registry
from gui.widgets.camerapreviewpanel import CameraPreviewPanel
from gui.widgets.mapwidget import MapWidget
from i18n import language_manager
from vessels.flags.flag_manager import flag_manager
from vessels.photo_manager import photo_manager


def _serialize_flag(country_code: str | None) -> dict:

    flag_value = str(country_code or "").strip()
    flag_record = flag_manager.get_flag(flag_value)
    flag_path = flag_manager.get_flag_file(flag_value)
    default_path = flag_manager.get_flag_file("ZZ")

    flag_url = None
    flag_fallback_url = None

    if flag_path is not None:
        flag_url = QUrl.fromLocalFile(str(flag_path.resolve())).toString()

    if default_path is not None:
        flag_fallback_url = QUrl.fromLocalFile(str(default_path.resolve())).toString()

    return {
        "flag_code": flag_record.normalized_country_code(),
        "flag_url": flag_url,
        "flag_fallback_url": flag_fallback_url,
    }


def _serialize_photo(mmsi: int) -> dict:

    if not photo_manager.has_photo(mmsi):
        return {
            "has_photo": False,
            "photo_url": None,
        }

    photo_path = photo_manager.get_photo_file(mmsi)

    if photo_path is None:
        return {
            "has_photo": True,
            "photo_url": None,
        }

    return {
        "has_photo": True,
        "photo_url": QUrl.fromLocalFile(str(photo_path.resolve())).toString(),
    }


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

    payload.update(_serialize_flag(payload.get("flag", "")))
    payload.update(_serialize_photo(ship.mmsi))

    return payload


class MapPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)

        self.map = MapWidget()
        map_layout.addWidget(self.map)

        layout.addWidget(map_container, 1)

        self.camera_preview = CameraPreviewPanel()
        layout.addWidget(self.camera_preview)

        self._selected_mmsi = None

        language_manager.language_changed.connect(
            lambda _code: self.apply_personalization()
        )
        self.map.loadFinished.connect(
            lambda _ok: self.apply_personalization()
        )
        self.apply_personalization()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ships)

        # 5 FPS frissítés – alap a smooth mozgáshoz
        self.timer.start(200)

    def apply_personalization(self, layout: str | None = None) -> None:

        from preferences import preferences_manager

        preferences = preferences_manager.get()
        selected_layout = layout or preferences.vessel_card_layout

        self.map.set_vessel_card_layout(selected_layout)
        self.map.set_translations(language_manager.translations())

        if selected_layout == "media":
            self.camera_preview.setMinimumWidth(400)
            self.camera_preview.setMaximumWidth(480)
        else:
            self.camera_preview.setMinimumWidth(300)
            self.camera_preview.setMaximumWidth(360)

    def select_vessel(self, mmsi: int):

        self._selected_mmsi = int(mmsi)
        self._refresh_camera_preview()

    def _refresh_camera_preview(self):

        if self._selected_mmsi is None:
            self.camera_preview.show_empty()
            return

        ship = registry.get(self._selected_mmsi)
        self.camera_preview.show_for_ship(ship)

    def update_ships(self):

        payload = json.dumps([
            _serialize_ship(ship)
            for ship in registry.all()
        ])

        self.map.update_ships(payload)

        if self._selected_mmsi is not None:
            self._refresh_camera_preview()
