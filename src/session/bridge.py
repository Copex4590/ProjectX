# ============================================================================
# Project X
# Session Replay GUI bridge (SAVE-219)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from alerts.alert_event import AlertEvent
from database import registry
from events import eventbus
from models.ship import Ship
from session.models import (
    EVENT_SESSION_REPLAY_ALERTS,
    EVENT_SESSION_REPLAY_FRAME,
    EVENT_SESSION_STATE,
)
from session.player import session_player

logger = logging.getLogger(__name__)


class SessionReplayBridge(QObject):
    """Applies replay frames onto Map / Details / Camera Link / Alert Center."""

    frame_applied = Signal()
    alerts_updated = Signal(object)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)

        self._window = main_window
        self._replay_alerts: list[AlertEvent] = []
        self._gui = _GuiProxy()
        self._gui.apply_frame.connect(self._apply_frame)
        self._gui.apply_alerts.connect(self._apply_alerts)

        eventbus.subscribe(EVENT_SESSION_REPLAY_FRAME, self._on_frame)
        eventbus.subscribe(EVENT_SESSION_REPLAY_ALERTS, self._on_alerts)
        eventbus.subscribe(EVENT_SESSION_STATE, self._on_state)

    def shutdown(self) -> None:

        eventbus.unsubscribe(EVENT_SESSION_REPLAY_FRAME, self._on_frame)
        eventbus.unsubscribe(EVENT_SESSION_REPLAY_ALERTS, self._on_alerts)
        eventbus.unsubscribe(EVENT_SESSION_STATE, self._on_state)

    @property
    def replay_alerts(self) -> list[AlertEvent]:

        return list(self._replay_alerts)

    def _on_frame(self, **kwargs) -> None:

        if not kwargs.get("replay"):
            return
        self._gui.apply_frame.emit(dict(kwargs))

    def _on_alerts(self, **kwargs) -> None:

        if not kwargs.get("replay"):
            return
        self._gui.apply_alerts.emit(list(kwargs.get("alerts") or []))

    def _on_state(self, **kwargs) -> None:

        state = str(kwargs.get("state") or "")
        if state == "idle" and kwargs.get("replay"):
            self._replay_alerts = []
            page = getattr(self._window, "alert_center_page", None)
            apply = getattr(page, "apply_session_replay_alerts", None)
            if callable(apply):
                apply(None)
            map_page = getattr(self._window, "map_page", None)
            clear = getattr(getattr(map_page, "_map_controller", None), "clear_playback", None)
            if callable(clear):
                clear()
            self.alerts_updated.emit([])

    def _apply_frame(self, payload: dict) -> None:

        window = self._window
        map_page = getattr(window, "map_page", None)
        if map_page is None:
            return

        ships_data = list(payload.get("ships") or [])
        ships = [_ship_from_dict(item) for item in ships_data]
        ships = [ship for ship in ships if ship is not None]

        # Update registry in-place for details/timeline consumers.
        for ship in ships:
            existing = registry.get(ship.mmsi)
            if existing is None:
                registry.add(ship)
            else:
                existing.lat = ship.lat
                existing.lon = ship.lon
                existing.speed = ship.speed
                existing.course = ship.course
                existing.heading = ship.heading
                existing.name = ship.name or existing.name
                existing.last_seen = ship.last_seen
                existing.ais_visible = ship.ais_visible
                existing.rtl_visible = ship.rtl_visible
                existing.camera_visible = ship.camera_visible

        focus = payload.get("focus_mmsi")
        if focus is not None:
            try:
                map_page.select_vessel(int(focus))
            except Exception:
                logger.debug("Replay vessel select failed", exc_info=True)

        apply = getattr(map_page, "apply_session_replay_ships", None)
        if callable(apply):
            apply(ships, focus_mmsi=focus)

        camera_snapshot = payload.get("camera_snapshot")
        apply_cam = getattr(map_page, "apply_session_replay_camera", None)
        if callable(apply_cam):
            apply_cam(camera_snapshot)

        self.frame_applied.emit()

    def _apply_alerts(self, alerts: list) -> None:

        reconstructed: list[AlertEvent] = []
        for item in alerts:
            try:
                reconstructed.append(_alert_from_dict(item))
            except Exception:
                logger.debug("Replay alert decode failed", exc_info=True)
        self._replay_alerts = reconstructed
        self.alerts_updated.emit(reconstructed)

        page = getattr(self._window, "alert_center_page", None)
        apply = getattr(page, "apply_session_replay_alerts", None)
        if callable(apply):
            apply(reconstructed)


class _GuiProxy(QObject):
    apply_frame = Signal(dict)
    apply_alerts = Signal(object)


def _ship_from_dict(data: dict) -> Ship | None:

    mmsi = int(data.get("mmsi") or 0)
    if not mmsi:
        return None
    ship = Ship(
        mmsi=mmsi,
        name=str(data.get("name") or ""),
        callsign=str(data.get("callsign") or ""),
        ship_type=str(data.get("ship_type") or ""),
        lat=float(data.get("lat") or 0.0),
        lon=float(data.get("lon") or 0.0),
        speed=float(data.get("speed") or 0.0),
        course=float(data.get("course") or 0.0),
        heading=float(data.get("heading") or 0.0),
        destination=str(data.get("destination") or ""),
        eta=str(data.get("eta") or ""),
        source=str(data.get("source") or "replay"),
        distance_km=float(data.get("distance_km") or 0.0),
        direction=str(data.get("direction") or ""),
        text_heading=str(data.get("text_heading") or ""),
        ais_visible=bool(data.get("ais_visible", True)),
        rtl_visible=bool(data.get("rtl_visible", False)),
        camera_visible=bool(data.get("camera_visible", False)),
    )
    last_seen = data.get("last_seen")
    if last_seen:
        try:
            ship.last_seen = datetime.fromisoformat(str(last_seen))
        except ValueError:
            ship.last_seen = datetime.now()
    else:
        ship.last_seen = datetime.now()
    return ship


def _alert_from_dict(data: dict) -> AlertEvent:

    timestamp = datetime.now()
    raw_ts = data.get("timestamp")
    if raw_ts:
        try:
            timestamp = datetime.fromisoformat(str(raw_ts))
        except ValueError:
            pass
    ack_at = None
    raw_ack = data.get("acknowledged_at")
    if raw_ack:
        try:
            ack_at = datetime.fromisoformat(str(raw_ack))
        except ValueError:
            ack_at = None
    return AlertEvent(
        id=data.get("id"),
        rule_id=int(data.get("rule_id") or 0),
        mmsi=int(data.get("mmsi") or 0),
        event_type=str(data.get("event_type") or ""),
        timestamp=timestamp,
        severity=str(data.get("severity") or "info"),
        message=str(data.get("message") or ""),
        metadata=dict(data.get("metadata") or {}),
        acknowledged=bool(data.get("acknowledged", False)),
        acknowledged_at=ack_at,
    )


def is_session_replaying() -> bool:

    return session_player.is_active
