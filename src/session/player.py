# ============================================================================
# Project X
# Session Player (SAVE-219)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from events import eventbus
from models.ship import Ship
from session.models import (
    EVENT_SESSION_REPLAY_ALERTS,
    EVENT_SESSION_REPLAY_FRAME,
    EVENT_SESSION_STATE,
    PLAYBACK_RATES,
    RecordedEvent,
    SessionManifest,
    SessionState,
)
from session.storage import SessionStorage, session_storage

logger = logging.getLogger(__name__)

_TICK_MS = 100


class SessionPlayer(QObject):
    """Replay a recorded .pxsession with Play / Pause / Seek / rate control."""

    state_changed = Signal(str)
    progress_changed = Signal(float, float)  # elapsed_s, duration_s
    finished = Signal()

    def __init__(self, storage: SessionStorage | None = None, parent=None):
        super().__init__(parent)

        self._storage = storage or session_storage
        self._manifest: SessionManifest | None = None
        self._events: list[RecordedEvent] = []
        self._path: Path | None = None
        self._state = SessionState.IDLE
        self._rate = 1
        self._cursor_index = 0
        self._elapsed = 0.0
        self._duration = 0.0
        self._origin: datetime | None = None
        self._ships: dict[int, dict] = {}
        self._alerts: list[dict] = []
        self._camera_snapshot: dict | None = None
        self._focus_mmsi: int | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    @property
    def is_active(self) -> bool:

        return self._state in (SessionState.REPLAYING, SessionState.PAUSED)

    @property
    def is_playing(self) -> bool:

        return self._state == SessionState.REPLAYING

    @property
    def state(self) -> SessionState:

        return self._state

    @property
    def rate(self) -> int:

        return self._rate

    @property
    def duration_seconds(self) -> float:

        return self._duration

    @property
    def elapsed_seconds(self) -> float:

        return self._elapsed

    @property
    def manifest(self) -> SessionManifest | None:

        return self._manifest

    def load(self, path: Path) -> SessionManifest:

        self.stop()
        manifest, events = self._storage.load_events(Path(path))
        self._path = Path(path)
        self._manifest = manifest
        self._events = sorted(events, key=lambda item: item.timestamp)
        self._origin = self._events[0].timestamp if self._events else manifest.started_at
        if self._events:
            self._duration = max(
                0.001,
                (self._events[-1].timestamp - self._origin).total_seconds(),
            )
        else:
            self._duration = max(0.001, manifest.duration_seconds)
        self._cursor_index = 0
        self._elapsed = 0.0
        self._ships = {}
        self._alerts = []
        self._camera_snapshot = None
        self._focus_mmsi = None
        self._set_state(SessionState.PAUSED)
        self._emit_progress()
        return manifest

    def play(self) -> None:

        if not self._events and self._manifest is None:
            return
        if self._elapsed >= self._duration - 0.0001:
            self.seek(0.0)
        self._set_state(SessionState.REPLAYING)
        self._timer.start()

    def pause(self) -> None:

        if not self.is_active:
            return
        self._timer.stop()
        self._set_state(SessionState.PAUSED)

    def stop(self) -> None:

        self._timer.stop()
        was_active = self.is_active
        self._cursor_index = 0
        self._elapsed = 0.0
        self._ships = {}
        self._alerts = []
        self._camera_snapshot = None
        self._set_state(SessionState.IDLE)
        if was_active:
            eventbus.publish(
                EVENT_SESSION_REPLAY_ALERTS,
                alerts=[],
                replay=True,
            )
            eventbus.publish(
                EVENT_SESSION_STATE,
                state=SessionState.IDLE.value,
                replay=True,
            )
        self._emit_progress()

    def set_rate(self, rate: int) -> None:

        value = int(rate)
        if value not in PLAYBACK_RATES:
            value = 1
        self._rate = value

    def seek(self, elapsed_seconds: float) -> None:

        if self._origin is None:
            return
        self._elapsed = max(0.0, min(float(elapsed_seconds), self._duration))
        self._rebuild_state_to_elapsed()
        self._publish_frame()
        self._emit_progress()

    def seek_fraction(self, fraction: float) -> None:

        self.seek(max(0.0, min(1.0, float(fraction))) * self._duration)

    def _on_tick(self) -> None:

        if self._state != SessionState.REPLAYING:
            return
        self._elapsed = min(
            self._duration,
            self._elapsed + (_TICK_MS / 1000.0) * self._rate,
        )
        self._advance_events()
        self._publish_frame()
        self._emit_progress()
        if self._elapsed >= self._duration:
            self._timer.stop()
            self._set_state(SessionState.PAUSED)
            self.finished.emit()

    def _advance_events(self) -> None:

        if self._origin is None:
            return
        target = self._origin + timedelta(seconds=self._elapsed)
        while self._cursor_index < len(self._events):
            event = self._events[self._cursor_index]
            if event.timestamp > target:
                break
            self._apply_event(event)
            self._cursor_index += 1

    def _rebuild_state_to_elapsed(self) -> None:

        self._ships = {}
        self._alerts = []
        self._camera_snapshot = None
        self._focus_mmsi = None
        self._cursor_index = 0
        if self._origin is None:
            return
        target = self._origin + timedelta(seconds=self._elapsed)
        while self._cursor_index < len(self._events):
            event = self._events[self._cursor_index]
            if event.timestamp > target:
                break
            self._apply_event(event)
            self._cursor_index += 1

    def _apply_event(self, event: RecordedEvent) -> None:

        name = event.name
        payload = event.payload

        if name == "ships.snapshot":
            for item in payload.get("ships") or []:
                mmsi = int(item.get("mmsi") or 0)
                if mmsi:
                    self._ships[mmsi] = dict(item)
                    self._focus_mmsi = mmsi
            return

        if name == "ship.updated":
            ship = payload.get("ship") or {}
            mmsi = int(ship.get("mmsi") or 0)
            if mmsi:
                self._ships[mmsi] = dict(ship)
                self._focus_mmsi = mmsi
            return

        if name == "alerts.fired":
            alert = dict(payload.get("event") or {})
            if alert:
                alert["acknowledged"] = False
                self._alerts.append(alert)
            return

        if name == "alerts.acknowledged":
            alert = payload.get("event") or {}
            alert_id = alert.get("id")
            for item in self._alerts:
                if alert_id is not None and item.get("id") == alert_id:
                    item["acknowledged"] = True
                    item["acknowledged_at"] = alert.get("acknowledged_at")
            return

        if name == "alerts.cleared":
            if payload.get("acknowledged_only"):
                self._alerts = [
                    item for item in self._alerts if not item.get("acknowledged")
                ]
            else:
                self._alerts = []
            return

        if name == "camera.link.changed":
            self._camera_snapshot = dict(payload.get("snapshot") or {})
            mmsi = self._camera_snapshot.get("mmsi")
            if mmsi is not None:
                self._focus_mmsi = int(mmsi)
            return

        if name == "vessel.playback.position":
            mmsi = int(payload.get("mmsi") or 0)
            if mmsi and mmsi in self._ships:
                ship = dict(self._ships[mmsi])
                if payload.get("latitude") is not None:
                    ship["lat"] = float(payload["latitude"])
                if payload.get("longitude") is not None:
                    ship["lon"] = float(payload["longitude"])
                self._ships[mmsi] = ship
                self._focus_mmsi = mmsi

    def _publish_frame(self) -> None:

        eventbus.publish(
            EVENT_SESSION_REPLAY_FRAME,
            ships=list(self._ships.values()),
            camera_snapshot=self._camera_snapshot,
            focus_mmsi=self._focus_mmsi,
            elapsed=self._elapsed,
            duration=self._duration,
            replay=True,
        )
        eventbus.publish(
            EVENT_SESSION_REPLAY_ALERTS,
            alerts=list(self._alerts),
            replay=True,
        )

    def _set_state(self, state: SessionState) -> None:

        self._state = state
        self.state_changed.emit(state.value)
        eventbus.publish(
            EVENT_SESSION_STATE,
            state=state.value,
            replay=True,
            session_id=self._manifest.session_id if self._manifest else "",
        )

    def _emit_progress(self) -> None:

        self.progress_changed.emit(self._elapsed, self._duration)

    def apply_ships_to_registry(self) -> list[Ship]:
        """Materialize current replay ships into Ship models (for map/details)."""

        ships: list[Ship] = []
        for data in self._ships.values():
            mmsi = int(data.get("mmsi") or 0)
            if not mmsi:
                continue
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
            ships.append(ship)
        return ships


session_player = SessionPlayer()
