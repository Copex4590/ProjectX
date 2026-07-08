import json
from collections import Counter

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeyEvent, QShowEvent
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
from gui.mapcontroller import MapController
from gui.map_core import PickMode
from gui.widgets.camerapreviewpanel import CameraPreviewPanel
from i18n import language_manager, tr
from vessel_statistics.statistics_manager import statistics_manager
from timeline.timeline_manager import timeline_manager
from logbook import logbook_manager
from vessels.flags.flag_manager import flag_manager
from vessels.photo_manager import photo_manager


_MAP_SHIPS_INTERVAL_MS = 500
_MAP_POPUP_REFRESH_INTERVAL_MS = 2000


def _serialize_ship_marker(ship) -> dict:

    return {
        "mmsi": ship.mmsi,
        "name": ship.name,
        "lat": ship.lat,
        "lon": ship.lon,
        "heading": ship.heading or 0,
        "course": ship.course,
        "speed": ship.speed,
    }


def _timeline_fields(mmsi: int) -> tuple[list[dict], str]:

    records = timeline_manager.history(mmsi)

    if not records:
        return [], "—"

    counts = Counter(record.event_type for record in records)
    latest = max(records, key=lambda record: record.timestamp)
    parts = [
        f"{count} {tr(event_type)}"
        for event_type, count in sorted(counts.items())
    ]
    summary = (
        f"{len(records)} {tr('events')} ({', '.join(parts)}); "
        f"{tr('latest')} {tr(latest.event_type)} "
        f"{latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    latest_records = sorted(
        records,
        key=lambda record: record.timestamp,
        reverse=True,
    )
    events = [
        {
            "event_type": record.event_type,
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for record in latest_records[:3]
    ]

    return events, summary


def _timeline_summary(mmsi: int) -> str:

    _events, summary = _timeline_fields(mmsi)
    return summary


def _timeline_events(mmsi: int, limit: int = 3) -> list[dict]:

    events, _summary = _timeline_fields(mmsi)
    return events[:limit]


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


def _statistics_summary(mmsi: int) -> str:

    stats = statistics_manager.vessel_statistics(mmsi)

    if stats is None:
        return "—"

    parts = [
        f"{tr('observations')} {stats.total_observations}",
        f"{tr('Arrivals')} {stats.total_arrivals}",
        f"{tr('Departures')} {stats.total_departures}",
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
        origin = fallback_coordinates()

        if origin is None:
            payload["camera_bearing_deg"] = None
            payload["camera_distance_km"] = None
            return

        origin_lat, origin_lon = origin
        payload["camera_bearing_deg"] = bearing_deg_from_origin(
            ship.lat,
            ship.lon,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )
        distance_km = distance_km_from_origin(
            ship.lat,
            ship.lon,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )
        payload["camera_distance_km"] = (
            round(distance_km, 2) if distance_km is not None else None
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

        self._map_controller = MapController.instance()
        self.map = self._map_controller.widget()
        map_layout.addWidget(self.map)

        layout.addWidget(map_container, 1)

        self.camera_preview = CameraPreviewPanel()
        layout.addWidget(self.camera_preview)

        self._selected_mmsi = None
        self._ships_update_busy = False

        language_manager.language_changed.connect(
            lambda _code: self.apply_personalization()
        )
        self.map.loadFinished.connect(
            lambda _ok: self._on_map_ready()
        )
        self.map.openLogbookRequested.connect(self._open_logbook)
        self._map_controller.pick_mode_changed.connect(
            self._on_pick_mode_changed
        )
        self.apply_personalization()
        self._map_controller.refresh_observation_points()

        self._marker_timer = QTimer(self)
        self._marker_timer.timeout.connect(self._update_ship_markers)

        self._popup_timer = QTimer(self)
        self._popup_timer.timeout.connect(self._update_ships_full)

        self._start_ship_timers()

    def _on_map_ready(self) -> None:

        self.apply_personalization()
        self._map_controller.refresh_observation_points()

    def refresh_observation_point(self) -> None:

        self._map_controller.refresh_observation_points()

    def on_observation_changed(self) -> None:

        self.refresh_observation_point()
        self._map_controller.maybe_prompt_reference_selection()
        self._update_ships_full()

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

        self._update_ships_full()

    def _start_ship_timers(self) -> None:

        if self._map_controller.pick_mode() == PickMode.LOCATION:
            return

        if not self._marker_timer.isActive():
            self._marker_timer.start(_MAP_SHIPS_INTERVAL_MS)

        if not self._popup_timer.isActive():
            self._popup_timer.start(_MAP_POPUP_REFRESH_INTERVAL_MS)

    def _stop_ship_timers(self) -> None:

        self._marker_timer.stop()
        self._popup_timer.stop()

    def _on_pick_mode_changed(self, mode: PickMode) -> None:

        if mode == PickMode.LOCATION:
            self._stop_ship_timers()
            return

        self._start_ship_timers()

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

    def update_ships(self) -> None:

        self._update_ships_full()

    def _update_ship_markers(self) -> None:

        if self._map_controller.pick_mode() == PickMode.LOCATION:
            return

        self._publish_ships(_serialize_ship_marker)

    def _update_ships_full(self) -> None:

        if self._map_controller.pick_mode() == PickMode.LOCATION:
            return

        self._publish_ships(_serialize_ship)

    def _publish_ships(self, serializer) -> None:

        if self._ships_update_busy:
            return

        self._ships_update_busy = True

        try:
            payload = json.dumps([
                serializer(ship)
                for ship in registry.all()
            ])
            self._map_controller.update_ships(payload)

            if self._selected_mmsi is not None:
                self._refresh_camera_preview()
        finally:
            self._ships_update_busy = False

    def showEvent(self, event: QShowEvent) -> None:

        super().showEvent(event)
        self._map_controller.on_map_page_visible()

    def keyPressEvent(self, event: QKeyEvent) -> None:

        if (
            event.key() == Qt.Key.Key_Escape
            and MapController.instance().pick_mode() != PickMode.NONE
        ):
            MapController.instance().cancel_pick_mode()
            event.accept()
            return

        super().keyPressEvent(event)
