import json
from collections import Counter

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeyEvent, QHideEvent, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from database import registry
from engines.camera import camera_selection_engine
from engines.camera.link_manager import intelligent_camera_link_manager
from engines.camera.link_states import CameraLinkMode
from observation.geo_context import geo_context
from debug.obs_freeze_trace import (
    schedule_traced_single_shot,
    trace_block,
    trace_enter,
    trace_event,
    trace_exit,
    trace_timer_callback,
)
from gui.vesselcard import vessel_card_layout_manager
from gui.mapcontroller import MapController
from gui.map_core import PickMode
from gui.widgets.camera_link_panel import CameraLinkPanel
from gui.widgets.camerapreviewpanel import CameraPreviewPanel
from gui.widgets.vessel_details_panel import VesselDetailsPanel
from gui.widgets.vessel_timeline_panel import (
    VesselTimelinePanel,
    sync_panel_from_engine,
)
from i18n import language_manager, tr
from vessel_statistics.statistics_manager import statistics_manager
from timeline.timeline_manager import timeline_manager
from timeline.vessel_playback import PlaybackMode, vessel_playback_engine
from logbook import logbook_manager
from vessels.flags.flag_manager import flag_manager
from vessels.photo_manager import photo_manager


_MAP_SHIPS_INTERVAL_MS = 200  # SAVE-106: max 5 Hz marker updates
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


def _marker_fingerprint(ship) -> tuple:

    return (
        ship.mmsi,
        round(float(ship.lat or 0.0), 5),
        round(float(ship.lon or 0.0), 5),
        round(float(ship.speed or 0.0), 1),
        round(float(ship.course or 0.0), 0),
        round(float(ship.heading or 0.0), 0),
        str(ship.name or ""),
    )


def _full_fingerprint(ship) -> tuple:

    return _marker_fingerprint(ship) + (
        str(ship.callsign or ""),
        str(ship.ship_type or ""),
        str(ship.destination or ""),
        str(ship.eta or ""),
        str(ship.source or ""),
        bool(ship.ais_visible),
        bool(ship.rtl_visible),
        round(float(ship.distance_km or 0.0), 2),
        str(ship.direction or ""),
        str(ship.text_heading or ""),
    )


def _timeline_fields(mmsi: int) -> tuple[list[dict], str]:

    trace_enter(f"MapPage._timeline_fields mmsi={mmsi}")
    records = timeline_manager.history(mmsi)
    trace_exit(f"MapPage._timeline_fields mmsi={mmsi}")

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


def _apply_reference_observation_fields(ship, payload: dict) -> None:

    observation = geo_context.ship_observation_fields(ship.lat, ship.lon)
    distance_km = observation.get("distance_km")

    if distance_km is not None:
        payload["distance_km"] = distance_km

    payload["reference_bearing_deg"] = observation.get("reference_bearing_deg")


def _display_camera_for_ship(ship):

    match = camera_selection_engine.get_best_camera(ship)

    if match is not None:
        return match.camera, match.distance_km

    return None, None


def _enrich_camera_fields(ship, payload: dict) -> None:

    camera, camera_distance_km = _display_camera_for_ship(ship)

    if camera is None:
        payload["camera_name"] = None
        payload["camera_distance_km"] = None
        payload["camera_bearing_deg"] = None
        return

    payload["camera_name"] = camera.name
    payload["camera_distance_km"] = round(camera_distance_km, 2)
    payload["camera_bearing_deg"] = camera.bearing_deg_to(
        ship.lat,
        ship.lon,
    )


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

    trace_enter(f"MapPage._serialize_ship mmsi={ship.mmsi}")

    try:
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
        _apply_reference_observation_fields(ship, payload)
        _enrich_camera_fields(ship, payload)
        _enrich_statistics_fields(ship.mmsi, payload)
        payload["timeline_events"] = _timeline_events(ship.mmsi)
        payload["timeline_summary"] = _timeline_summary(ship.mmsi)
        payload["statistics_summary"] = _statistics_summary(ship.mmsi)
        payload["has_logbook"] = logbook_manager.has_logbook(ship)
        trace_enter(f"MapPage._serialize_ship.render mmsi={ship.mmsi}")
        payload["popup_html"] = vessel_card_layout_manager.render(payload)
        trace_exit(f"MapPage._serialize_ship.render mmsi={ship.mmsi}")

        return payload
    finally:
        trace_exit(f"MapPage._serialize_ship mmsi={ship.mmsi}")


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

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.vessel_details = VesselDetailsPanel()
        right_layout.addWidget(self.vessel_details, 1)

        self.vessel_timeline = VesselTimelinePanel()
        right_layout.addWidget(self.vessel_timeline, 0)

        self.camera_link = CameraLinkPanel()
        right_layout.addWidget(self.camera_link, 0)

        self.camera_preview = CameraPreviewPanel()
        right_layout.addWidget(self.camera_preview, 0)

        layout.addWidget(right_column)

        self._selected_mmsi = None
        self._camera_link = intelligent_camera_link_manager
        self._ships_update_busy = False
        self._ships_update_pending = None  # serializer waiting while busy
        self._markers_dirty = True
        self._ship_refresh_generation = 0
        self._marker_fingerprints: dict[int, tuple] = {}
        self._full_fingerprints: dict[int, tuple] = {}
        self._force_map_full_sync = True
        self._playback = vessel_playback_engine

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
        self._connect_timeline_playback()
        self.camera_link.refreshRequested.connect(self._on_camera_link_refresh)
        self.camera_link.coverageToggled.connect(self._on_camera_coverage_toggled)
        try:
            from cameras import camera_manager as _camera_manager

            _camera_manager.load()
        except Exception:
            pass
        self.apply_personalization()
        self._map_controller.refresh_observation_points()

        self._marker_timer = QTimer(self)
        self._marker_timer.timeout.connect(
            trace_timer_callback(
                "MapPage._marker_timer",
                self._update_ship_markers,
            )
        )

        self._popup_timer = QTimer(self)
        self._popup_timer.timeout.connect(
            trace_timer_callback(
                "MapPage._popup_timer",
                self._update_ships_full,
            )
        )

    def _map_page_is_current(self) -> bool:

        window = self.window()
        pages = getattr(window, "pages", None)

        if pages is not None:
            return pages.currentWidget() is self

        return self.isVisible()

    def _map_updates_enabled(self) -> bool:

        with trace_block("MapPage._map_updates_enabled"):
            trace_enter("MapPage._map_updates_enabled._map_page_is_current")
            page_current = self._map_page_is_current()
            trace_exit(
                f"MapPage._map_updates_enabled._map_page_is_current "
                f"result={page_current}"
            )

            trace_enter("MapPage._map_updates_enabled.isVisible")
            visible = self.isVisible()
            trace_exit(f"MapPage._map_updates_enabled.isVisible result={visible}")

            trace_enter("MapPage._map_updates_enabled.pick_mode")
            pick_mode = self._map_controller.pick_mode()
            trace_exit(f"MapPage._map_updates_enabled.pick_mode result={pick_mode}")

            return (
                page_current
                and visible
                and pick_mode == PickMode.NONE
            )

    def _schedule_ships_full(self, label: str) -> None:

        trace_enter(f"MapPage._schedule_ships_full label={label}")
        generation = self._ship_refresh_generation

        def _run() -> None:

            trace_enter(
                f"MapPage._schedule_ships_full.callback label={label} "
                f"generation={generation}"
            )

            try:
                if generation != self._ship_refresh_generation:
                    trace_event(
                        f"MapPage._schedule_ships_full skipped stale "
                        f"generation={generation} label={label}"
                    )
                    return

                self._update_ships_full()
            finally:
                trace_exit(
                    f"MapPage._schedule_ships_full.callback label={label} "
                    f"generation={generation}"
                )

        schedule_traced_single_shot(0, label, _run)
        trace_exit(f"MapPage._schedule_ships_full label={label}")

    def _on_map_ready(self) -> None:

        with trace_block("MapPage._on_map_ready"):
            self.apply_personalization()
            self._map_controller.refresh_observation_points()

    def refresh_observation_point(self) -> None:

        with trace_block("MapPage.refresh_observation_point"):
            self._map_controller.refresh_observation_points()

    def on_observation_changed(self) -> None:

        with trace_block("MapPage.on_observation_changed"):
            with trace_block("MapPage.on_observation_changed.refresh_observation_point"):
                self.refresh_observation_point()

            with trace_block("MapPage.on_observation_changed.maybe_prompt_reference_selection"):
                self._map_controller.maybe_prompt_reference_selection()

            updates_enabled = self._map_updates_enabled()

            if updates_enabled:
                self._schedule_ships_full(
                    "MapPage.on_observation_changed->_update_ships_full"
                )
            else:
                trace_event(
                    "MapPage.on_observation_changed skip _update_ships_full "
                    f"(visible={self.isVisible()} "
                    f"pick={self._map_controller.pick_mode()})"
                )

    def apply_personalization(self, layout: str | None = None) -> None:

        from preferences import preferences_manager

        preferences = preferences_manager.get()
        selected_layout = layout or preferences.vessel_card_layout

        if selected_layout == "media":
            self.camera_preview.setMinimumWidth(400)
            self.camera_preview.setMaximumWidth(480)
            self.camera_link.setMinimumWidth(400)
            self.camera_link.setMaximumWidth(480)
            self.vessel_details.setMinimumWidth(400)
            self.vessel_details.setMaximumWidth(480)
            self.vessel_timeline.setMinimumWidth(400)
            self.vessel_timeline.setMaximumWidth(480)
        else:
            self.camera_preview.setMinimumWidth(300)
            self.camera_preview.setMaximumWidth(360)
            self.camera_link.setMinimumWidth(300)
            self.camera_link.setMaximumWidth(360)
            self.vessel_details.setMinimumWidth(320)
            self.vessel_details.setMaximumWidth(400)
            self.vessel_timeline.setMinimumWidth(320)
            self.vessel_timeline.setMaximumWidth(400)

        if self._map_updates_enabled():
            self._schedule_ships_full(
                "MapPage.apply_personalization->_update_ships_full"
            )

    def _start_ship_timers(self) -> None:

        with trace_block("MapPage._start_ship_timers"):
            if not self._map_updates_enabled():
                trace_event("MapPage._start_ship_timers skipped")
                return

            if not self._marker_timer.isActive():
                self._marker_timer.start(_MAP_SHIPS_INTERVAL_MS)

            if not self._popup_timer.isActive():
                self._popup_timer.start(_MAP_POPUP_REFRESH_INTERVAL_MS)

    def _stop_ship_timers(self) -> None:

        with trace_block("MapPage._stop_ship_timers"):
            self._marker_timer.stop()
            self._popup_timer.stop()

    def _on_pick_mode_changed(self, mode: PickMode) -> None:

        with trace_block(f"MapPage._on_pick_mode_changed mode={mode}"):
            if mode == PickMode.LOCATION:
                self._stop_ship_timers()
                return

            self._start_ship_timers()
            self._markers_dirty = True
            self._update_ship_markers()
            self._schedule_ships_full(
                "MapPage._on_pick_mode_changed->NONE"
            )

    def on_ship_updated(self) -> None:

        with trace_block("MapPage.on_ship_updated"):
            if not self._map_updates_enabled():
                trace_event("MapPage.on_ship_updated skipped")
                return

            # SAVE-106: mark dirty; 5 Hz timer merges requests (no immediate JS).
            self._markers_dirty = True

            if not self._marker_timer.isActive():
                self._start_ship_timers()

            self._append_selected_playback_sample()

    def select_vessel(self, mmsi: int):

        self._selected_mmsi = int(mmsi)
        self.vessel_details.set_mmsi(self._selected_mmsi)
        self._bind_timeline_vessel(self._selected_mmsi)
        self._camera_link.select_vessel(self._selected_mmsi)
        self._refresh_camera_preview()

    def _open_logbook(self, mmsi: int) -> None:

        logbook_manager.open_logbook(int(mmsi))

    def _on_camera_link_refresh(self) -> None:

        self._refresh_camera_preview()

    def _on_camera_coverage_toggled(self, _visible: bool) -> None:

        self._apply_camera_link_overlays()

    def _refresh_camera_preview(self):

        if self._selected_mmsi is None:
            self._camera_link.select_vessel(None)
            self.camera_link.apply_snapshot(self._camera_link.last_snapshot)
            self.camera_preview.show_empty()
            self.vessel_details.clear()
            self._bind_timeline_vessel(None)
            self._apply_camera_link_overlays()
            return

        ship = registry.get(self._selected_mmsi)
        snapshot = self._camera_link.evaluate()
        self.camera_link.apply_snapshot(snapshot)

        # Preserve Camera Preview auto path when Auto mode; manual uses explicit match.
        if (
            snapshot.mode == CameraLinkMode.MANUAL
            and snapshot.active is not None
            and ship is not None
        ):
            self.camera_preview.show_for_match(ship, snapshot.active.match)
        else:
            self.camera_preview.show_for_ship(ship)

        self.vessel_details.set_mmsi(self._selected_mmsi)
        self._apply_camera_link_overlays()

    def _apply_camera_link_overlays(self) -> None:

        snapshot = self._camera_link.last_snapshot
        if snapshot.coverage_visible:
            zones = [
                sector.to_map_dict()
                for sector in self._camera_link.coverage_sectors()
            ]
            self.map.set_camera_coverage_zones(zones)
        else:
            self.map.clear_camera_coverage_zones()

        link = self._camera_link.link_overlay_payload()
        self.map.set_camera_link(link)

    def _connect_timeline_playback(self) -> None:

        panel = self.vessel_timeline
        engine = self._playback

        panel.playPauseRequested.connect(self._on_timeline_play_pause)
        panel.liveRequested.connect(self._on_timeline_live)
        panel.rateChanged.connect(engine.set_rate)
        panel.seekFractionChanged.connect(self._on_timeline_seek)

        engine.mode_changed.connect(self._on_playback_mode_changed)
        engine.samples_changed.connect(self._on_playback_samples_changed)
        engine.index_changed.connect(self._on_playback_index_changed)
        engine.position_changed.connect(self._on_playback_position_changed)
        engine.rate_changed.connect(lambda _rate: sync_panel_from_engine(panel, engine))

        panel.set_enabled_for_vessel(False)

    def _bind_timeline_vessel(self, mmsi: int | None) -> None:

        ship = registry.get(mmsi) if mmsi is not None else None
        self._playback.bind_vessel(mmsi, ship)
        sync_panel_from_engine(self.vessel_timeline, self._playback)
        self.vessel_timeline.set_enabled_for_vessel(mmsi is not None)

        if mmsi is None or self._playback.is_live():
            self._map_controller.clear_playback()
        else:
            self._apply_playback_overlay()

    def _append_selected_playback_sample(self) -> None:

        if self._selected_mmsi is None:
            return

        ship = registry.get(self._selected_mmsi)
        if ship is None:
            return

        self._playback.append_live_ship(ship)
        if self._playback.is_live():
            sync_panel_from_engine(self.vessel_timeline, self._playback)

    def _on_timeline_play_pause(self) -> None:

        if self._selected_mmsi is None:
            return
        self._playback.toggle_play_pause()

    def _on_timeline_live(self) -> None:

        self._playback.go_live()
        self._map_controller.clear_playback()
        self._markers_dirty = True
        self._force_map_full_sync = True
        self._update_ship_markers()
        sync_panel_from_engine(self.vessel_timeline, self._playback)

    def _on_timeline_seek(self, fraction: float) -> None:

        self._playback.seek_fraction(fraction)

    def _on_playback_mode_changed(self, mode: str) -> None:

        sync_panel_from_engine(self.vessel_timeline, self._playback)
        if mode == PlaybackMode.LIVE.value:
            self._map_controller.clear_playback()
            self._markers_dirty = True
            self._force_map_full_sync = True
            if self._map_updates_enabled():
                self._update_ship_markers()
            return

        self._apply_playback_overlay()

    def _on_playback_samples_changed(self) -> None:

        sync_panel_from_engine(self.vessel_timeline, self._playback)
        if self._playback.is_playback_active():
            self._map_controller.set_playback_trail(self._playback.trail_points())

    def _on_playback_index_changed(self, _index: int, _total: int) -> None:

        sync_panel_from_engine(self.vessel_timeline, self._playback)

    def _on_playback_position_changed(self, sample) -> None:

        if self._playback.is_live() or sample is None:
            return
        self._apply_playback_overlay(sample)

    def _apply_playback_overlay(self, sample=None) -> None:

        if self._selected_mmsi is None:
            self._map_controller.clear_playback()
            return

        current = sample or self._playback.current_sample()
        points = self._playback.trail_points()
        self._map_controller.set_playback_active(self._selected_mmsi)
        self._map_controller.set_playback_trail(points)

        if current is None:
            self._map_controller.set_playback_cursor(None, None)
            return

        heading = current.heading if current.heading is not None else current.course
        self._map_controller.set_playback_cursor(
            current.latitude,
            current.longitude,
            heading,
        )

    def update_ships(self) -> None:

        with trace_block("MapPage.update_ships"):
            self._update_ships_full()

    def _update_ship_markers(self) -> None:

        with trace_block("MapPage._update_ship_markers"):
            if not self._map_updates_enabled():
                trace_event("MapPage._update_ship_markers skipped")
                return

            if not self._markers_dirty:
                trace_event("MapPage._update_ship_markers skipped clean")
                return

            self._markers_dirty = False
            self._publish_ships(_serialize_ship_marker)

    def _update_ships_full(self) -> None:

        with trace_block("MapPage._update_ships_full"):
            if not self._map_updates_enabled():
                trace_event("MapPage._update_ships_full skipped")
                return

            self._markers_dirty = False
            self._publish_ships(_serialize_ship)

    def _publish_ships(self, serializer) -> None:

        if self._ships_update_busy:
            # Prefer a pending full refresh over a marker-only one.
            pending = self._ships_update_pending
            if pending is None or serializer is _serialize_ship:
                self._ships_update_pending = serializer
            trace_event(
                f"MapPage._publish_ships merged busy "
                f"serializer={getattr(serializer, '__name__', serializer)}"
            )
            return

        self._ships_update_busy = True

        try:
            with trace_block(
                f"MapPage._publish_ships serializer="
                f"{getattr(serializer, '__name__', serializer)}"
            ):
                trace_enter("MapPage._publish_ships.registry.all")
                ships = [
                    ship
                    for ship in registry.all()
                    if geo_context.is_within_coverage(ship.lat, ship.lon)
                ]
                trace_exit(
                    f"MapPage._publish_ships.registry.all count={len(ships)}"
                )

                is_full = serializer is _serialize_ship
                fingerprints = (
                    self._full_fingerprints if is_full else self._marker_fingerprints
                )
                fingerprint_fn = (
                    _full_fingerprint if is_full else _marker_fingerprint
                )
                force_full = self._force_map_full_sync and is_full

                current_mmsis = {int(ship.mmsi) for ship in ships}
                remove = [
                    mmsi for mmsi in list(fingerprints) if mmsi not in current_mmsis
                ]
                for mmsi in remove:
                    fingerprints.pop(mmsi, None)

                upsert = []
                trace_enter("MapPage._publish_ships.serialize_loop")
                for ship in ships:
                    mmsi = int(ship.mmsi)
                    fingerprint = fingerprint_fn(ship)
                    if force_full or fingerprints.get(mmsi) != fingerprint:
                        upsert.append(serializer(ship))
                        fingerprints[mmsi] = fingerprint
                trace_exit(
                    f"MapPage._publish_ships.serialize_loop "
                    f"upsert={len(upsert)} remove={len(remove)}"
                )

                if not upsert and not remove and not force_full:
                    trace_event("MapPage._publish_ships skipped unchanged")
                    return

                if force_full:
                    payload_obj = {"mode": "full", "ships": upsert}
                    self._force_map_full_sync = False
                else:
                    payload_obj = {
                        "mode": "patch",
                        "upsert": upsert,
                        "remove": remove,
                    }

                trace_enter("MapPage._publish_ships.json_dumps")
                payload = json.dumps(payload_obj)
                trace_exit(
                    f"MapPage._publish_ships.json_dumps bytes={len(payload)}"
                )

                trace_enter("MapPage._publish_ships.update_ships")
                self._map_controller.update_ships(payload)
                trace_exit("MapPage._publish_ships.update_ships")

                if self._selected_mmsi is not None:
                    trace_enter("MapPage._publish_ships._refresh_camera_preview")
                    self._refresh_camera_preview()
                    trace_exit("MapPage._publish_ships._refresh_camera_preview")
        finally:
            self._ships_update_busy = False
            pending = self._ships_update_pending
            self._ships_update_pending = None

            if pending is not None:
                schedule_traced_single_shot(
                    0,
                    "MapPage._publish_ships.pending",
                    lambda: self._publish_ships(pending),
                )

    def showEvent(self, event: QShowEvent) -> None:

        with trace_block("MapPage.showEvent"):
            super().showEvent(event)
            self._map_controller.on_map_page_visible()
        self._force_map_full_sync = True
        self._start_ship_timers()
        self._update_ship_markers()
        self._schedule_ships_full("MapPage.showEvent->_update_ships_full")

    def hideEvent(self, event: QHideEvent) -> None:

        with trace_block("MapPage.hideEvent"):
            self._ship_refresh_generation += 1
            self._stop_ship_timers()
            super().hideEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:

        if (
            event.key() == Qt.Key.Key_Escape
            and MapController.instance().pick_mode() != PickMode.NONE
        ):
            MapController.instance().cancel_pick_mode()
            event.accept()
            return

        super().keyPressEvent(event)
