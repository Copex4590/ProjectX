import json
from collections import Counter

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from cameras import camera_manager
from database import registry
from engines.camera import camera_selection_engine
from observation.coords import (
    bearing_deg_from_origin,
    distance_km_from_origin,
    fallback_coordinates,
)
from gui.vesselcard import vessel_card_layout_manager
from gui.widgets.camerapreviewpanel import CameraPreviewPanel
from gui.widgets.mapwidget import MapWidget
from i18n import language_manager, tr
from statistics.statistics_manager import statistics_manager
from timeline.timeline_manager import timeline_manager
from logbook import logbook_manager
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


def _timeline_summary(mmsi: int) -> str:

    records = timeline_manager.history(mmsi)

    if not records:
        return "—"

    counts = Counter(record.event_type for record in records)
    latest = max(records, key=lambda record: record.timestamp)
    parts = [
        f"{count} {tr(event_type)}"
        for event_type, count in sorted(counts.items())
    ]

    return (
        f"{len(records)} {tr('events')} ({', '.join(parts)}); "
        f"{tr('latest')} {tr(latest.event_type)} "
        f"{latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _statistics_summary(mmsi: int) -> str:

    stats = statistics_manager.vessel_statistics(mmsi)

    if stats is None:
        return "—"

    parts = [
        f"{tr('observations')} {stats.total_observations}",
        f"{tr('arrivals')} {stats.total_arrivals}",
        f"{tr('departures')} {stats.total_departures}",
    ]

    if stats.average_speed is not None:
        parts.append(
            f"{tr('avg speed')} {stats.average_speed:.1f} kn"
        )

    if stats.maximum_speed is not None:
        parts.append(
            f"{tr('max speed')} {stats.maximum_speed:.1f} kn"
        )

    return "; ".join(parts)


def _timeline_events(mmsi: int, limit: int = 3) -> list[dict]:

    records = timeline_manager.history(mmsi)

    if not records:
        return []

    latest = sorted(records, key=lambda record: record.timestamp, reverse=True)

    return [
        {
            "event_type": record.event_type,
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for record in latest[:limit]
    ]


def _display_camera_for_ship(ship):

    match = camera_selection_engine.get_best_camera(ship)

    if match is not None:
        return match.camera, match.distance_km

    cameras = camera_manager.enabled()

    if cameras:
        camera = min(
            cameras,
            key=lambda item: item.distance_km_to(ship.lat, ship.lon),
        )
        return camera, camera.distance_km_to(ship.lat, ship.lon)

    return None, None


def _enrich_camera_fields(ship, payload: dict) -> None:

    camera, distance_km = _display_camera_for_ship(ship)

    if camera is not None:
        payload["camera_name"] = camera.name
        payload["camera_distance_km"] = round(distance_km, 2)
        payload["camera_bearing_deg"] = camera.bearing_deg_to(
            ship.lat,
            ship.lon,
        )
        return

    payload["camera_name"] = None

    if ship.lat is not None and ship.lon is not None:
        origin_lat, origin_lon = fallback_coordinates()
        payload["camera_bearing_deg"] = bearing_deg_from_origin(
            ship.lat,
            ship.lon,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )
        payload["camera_distance_km"] = round(
            distance_km_from_origin(
                ship.lat,
                ship.lon,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            ),
            2,
        )
        return

    payload["camera_distance_km"] = None
    payload["camera_bearing_deg"] = None


def _enrich_statistics_fields(mmsi: int, payload: dict) -> None:

    stats = statistics_manager.vessel_statistics(mmsi)

    if stats is None:
        payload["stats_first_seen"] = None
        payload["stats_last_seen"] = None
        payload["stats_observation_count"] = None
        return

    payload["stats_first_seen"] = (
        stats.first_seen.isoformat() if stats.first_seen else None
    )
    payload["stats_last_seen"] = (
        stats.last_seen.isoformat() if stats.last_seen else None
    )
    payload["stats_observation_count"] = stats.total_observations


def _serialize_ship(ship) -> dict:

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
    _enrich_camera_fields(ship, payload)
    _enrich_statistics_fields(ship.mmsi, payload)
    payload["timeline_events"] = _timeline_events(ship.mmsi)
    payload["timeline_summary"] = _timeline_summary(ship.mmsi)
    payload["statistics_summary"] = _statistics_summary(ship.mmsi)
    payload["has_logbook"] = logbook_manager.has_logbook(ship)
    payload["popup_html"] = vessel_card_layout_manager.render(payload)

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
            lambda _ok: self._on_map_ready()
        )
        self.map.openLogbookRequested.connect(self._open_logbook)
        self.apply_personalization()
        self.refresh_observation_point()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ships)

        self.timer.start(200)

    def _on_map_ready(self) -> None:

        self.apply_personalization()
        self.refresh_observation_point()

    def refresh_observation_point(self) -> None:

        origin_lat, origin_lon = fallback_coordinates()
        self.map.set_observation_point(origin_lat, origin_lon)

    def on_observation_changed(self) -> None:

        self.refresh_observation_point()
        self.update_ships()

    def apply_personalization(self, layout: str | None = None) -> None:

        from preferences import preferences_manager

        preferences = preferences_manager.get()
        selected_layout = layout or preferences.vessel_card_layout

        if selected_layout == "media":
            self.camera_preview.setMinimumWidth(400)
            self.camera_preview.setMaximumWidth(480)
        else:
            self.camera_preview.setMinimumWidth(300)
            self.camera_preview.setMaximumWidth(360)

        self.update_ships()

    def select_vessel(self, mmsi: int):

        self._selected_mmsi = int(mmsi)
        self._refresh_camera_preview()

    def _open_logbook(self, mmsi: int) -> None:

        logbook_manager.open_logbook(int(mmsi))

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
