# ============================================================================
# Project X
# Session Recorder (SAVE-219)
# ============================================================================

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock

from database import registry
from events import eventbus
from session.models import (
    EVENT_SESSION_STATE,
    RECORDABLE_EVENTS,
    RecordedEvent,
    SessionManifest,
    SessionState,
)
from session.serialize import serialize_event_payload, serialize_ship
from session.storage import SessionStorage, session_storage
from version import PROJECT_VERSION

logger = logging.getLogger(__name__)

# Coalesce high-frequency ship.updated writes.
_SHIP_COALESCE_SECONDS = 0.5


class SessionRecorder:
    """Capture EventBus traffic into an in-memory buffer, then finalize to .pxsession."""

    def __init__(self, storage: SessionStorage | None = None):

        self._storage = storage or session_storage
        self._lock = Lock()
        self._recording = False
        self._session_id = ""
        self._started_at: datetime | None = None
        self._events: list[RecordedEvent] = []
        self._last_ship_ts: dict[int, float] = {}
        self._handlers: dict[str, object] = {}

    @property
    def is_recording(self) -> bool:

        return self._recording

    @property
    def event_count(self) -> int:

        with self._lock:
            return len(self._events)

    def start(self, *, label: str = "") -> SessionManifest:

        with self._lock:
            if self._recording:
                raise RuntimeError("A session is already recording")

            now = datetime.now()
            self._session_id = now.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
            self._started_at = now
            self._events = []
            self._last_ship_ts = {}
            self._recording = True
            manifest = SessionManifest(
                session_id=self._session_id,
                created_at=now,
                started_at=now,
                app_version=PROJECT_VERSION,
                label=label or f"Session {now.strftime('%Y-%m-%d %H:%M:%S')}",
            )

        self._subscribe()
        # Seed current fleet snapshot so replay has immediate vessels.
        self._capture_registry_snapshot()
        eventbus.publish(
            EVENT_SESSION_STATE,
            state=SessionState.RECORDING.value,
            session_id=self._session_id,
        )
        logger.info("Session recording started: %s", self._session_id)
        return manifest

    def stop(self) -> Path | None:

        with self._lock:
            if not self._recording:
                return None
            self._recording = False
            events = list(self._events)
            started = self._started_at or datetime.now()
            session_id = self._session_id
            self._events = []
            self._last_ship_ts = {}
            self._session_id = ""
            self._started_at = None

        self._unsubscribe()
        ended = datetime.now()
        manifest = SessionManifest(
            session_id=session_id,
            created_at=started,
            started_at=started,
            ended_at=ended,
            event_count=len(events),
            app_version=PROJECT_VERSION,
            label=f"Session {started.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        path = self._storage.write_session(manifest=manifest, events=events)
        eventbus.publish(
            EVENT_SESSION_STATE,
            state=SessionState.IDLE.value,
            session_id=session_id,
            path=str(path),
        )
        logger.info(
            "Session recording stopped: %s (%s events) → %s",
            session_id,
            len(events),
            path,
        )
        return Path(path)

    def _subscribe(self) -> None:

        for name in RECORDABLE_EVENTS:
            handler = self._make_handler(name)
            self._handlers[name] = handler
            eventbus.subscribe(name, handler)

    def _unsubscribe(self) -> None:

        for name, handler in list(self._handlers.items()):
            eventbus.unsubscribe(name, handler)
        self._handlers.clear()

    def _make_handler(self, event_name: str):

        def _handler(*args, **kwargs) -> None:

            # Ignore synthetic replay traffic.
            if kwargs.get("replay") or kwargs.get("session_replay"):
                return
            self._on_event(event_name, args, kwargs)

        _handler.__name__ = f"session_record_{event_name.replace('.', '_')}"
        return _handler

    def _on_event(self, event_name: str, args: tuple, kwargs: dict) -> None:

        with self._lock:
            if not self._recording:
                return

            now = datetime.now()
            if event_name == "ship.updated":
                ship = kwargs.get("ship")
                if ship is None and args:
                    ship = args[0]
                if ship is not None:
                    mmsi = int(getattr(ship, "mmsi", 0) or 0)
                    last = self._last_ship_ts.get(mmsi, 0.0)
                    if (now.timestamp() - last) < _SHIP_COALESCE_SECONDS:
                        return
                    self._last_ship_ts[mmsi] = now.timestamp()

            payload = serialize_event_payload(event_name, args, kwargs)
            if event_name == "ship.updated" and payload.get("registry_hint"):
                # Expand to full fleet snapshot when publisher omitted ship=.
                payload = {
                    "ships": [
                        serialize_ship(ship) for ship in registry.all()
                    ]
                }
                event_name = "ships.snapshot"

            self._events.append(
                RecordedEvent(
                    timestamp=now,
                    name=event_name,
                    payload=payload,
                )
            )

    def _capture_registry_snapshot(self) -> None:

        with self._lock:
            if not self._recording:
                return
            ships = [serialize_ship(ship) for ship in registry.all()]
            self._events.append(
                RecordedEvent(
                    timestamp=datetime.now(),
                    name="ships.snapshot",
                    payload={"ships": ships},
                )
            )


session_recorder = SessionRecorder()
