# ============================================================================
# Project X
# Arrival / Departure Detection Engine
# ============================================================================

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import Empty, Queue
from threading import Lock, Thread

from models.ship import Ship
from timeline.timeline_manager import TimelineManager, timeline_manager
from timeline.timeline_record import TimelineRecord

EVENT_ARRIVAL = "ARRIVAL"
EVENT_DEPARTURE = "DEPARTURE"

DEFAULT_ABSENCE_TIMEOUT_SECONDS = float(
    os.environ.get("PROJECTX_ARRIVAL_DEPARTURE_TIMEOUT_SECONDS", "300")
)


def _normalize_mmsi(mmsi: int | str | None) -> int | None:

    if mmsi is None:
        return None

    try:
        normalized = int(mmsi)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None

    return normalized


def _normalize_timestamp(value: datetime | None) -> datetime:

    if value is None:
        value = datetime.now()

    return value.replace(microsecond=0)


def _safe_text(value) -> str:

    if value is None:
        return ""

    return str(value).strip()


@dataclass(frozen=True)
class PresenceObservation:

    mmsi: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    course: float
    heading: float
    source: str


@dataclass
class VesselPresence:

    status: str
    last_seen: datetime


def _observation_from_ship(ship: Ship) -> PresenceObservation | None:

    normalized_mmsi = _normalize_mmsi(ship.mmsi)

    if normalized_mmsi is None:
        return None

    return PresenceObservation(
        mmsi=normalized_mmsi,
        timestamp=_normalize_timestamp(ship.last_seen),
        latitude=float(ship.lat),
        longitude=float(ship.lon),
        speed=float(ship.speed or 0.0),
        course=float(ship.course or 0.0),
        heading=float(ship.heading or 0.0),
        source=_safe_text(ship.source),
    )


class ArrivalDepartureEngine:

    def __init__(
        self,
        manager: TimelineManager | None = None,
        absence_timeout_seconds: float | None = None,
    ):

        self._manager = manager or timeline_manager
        self._absence_timeout = timedelta(
            seconds=absence_timeout_seconds or DEFAULT_ABSENCE_TIMEOUT_SECONDS
        )
        self._presence: dict[int, VesselPresence] = {}
        self._state_lock = Lock()
        self._queue: Queue[PresenceObservation] = Queue()
        self._worker_lock = Lock()
        self._worker: Thread | None = None

    @property
    def absence_timeout(self) -> timedelta:

        return self._absence_timeout

    def notify(self, ship: Ship | None) -> None:

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return

        self._ensure_worker()
        self._queue.put(observation)

    def observe_now(self, ship: Ship | None) -> TimelineRecord | None:

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return None

        return self._handle_observation(observation)

    def scan_departures_now(self) -> list[TimelineRecord]:

        return self._scan_departures(datetime.now())

    def _registry(self):

        from database import registry

        return registry

    def _ensure_worker(self) -> None:

        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._worker = Thread(
                target=self._worker_loop,
                name="ArrivalDepartureEngineWorker",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:

        while True:
            try:
                observation = self._queue.get(timeout=1.0)
            except Empty:
                observation = None

            try:
                if observation is not None:
                    self._handle_observation(observation)

                self._scan_departures(datetime.now())
            except Exception:
                pass
            finally:
                if observation is not None:
                    self._queue.task_done()

    def _handle_observation(
        self,
        observation: PresenceObservation,
    ) -> TimelineRecord | None:

        should_arrive = False

        with self._state_lock:
            presence = self._presence.get(observation.mmsi)

            if presence is None or presence.status == "departed":
                self._presence[observation.mmsi] = VesselPresence(
                    status="present",
                    last_seen=observation.timestamp,
                )
                should_arrive = True
            else:
                presence.last_seen = observation.timestamp

        if not should_arrive:
            return None

        return self._append_event(observation, EVENT_ARRIVAL)

    def _scan_departures(self, now: datetime) -> list[TimelineRecord]:

        departure_mmsis: list[int] = []

        with self._state_lock:
            for mmsi, presence in self._presence.items():
                if presence.status != "present":
                    continue

                if now - presence.last_seen < self._absence_timeout:
                    continue

                presence.status = "departed"
                departure_mmsis.append(mmsi)

        saved_records: list[TimelineRecord] = []

        for mmsi in departure_mmsis:
            ship = self._registry().get(mmsi)
            record = self._append_departure(mmsi, ship, now)

            if record is not None:
                saved_records.append(record)

        return saved_records

    def _append_departure(
        self,
        mmsi: int,
        ship: Ship | None,
        timestamp: datetime,
    ) -> TimelineRecord | None:

        if ship is None:
            return self._append_event(
                PresenceObservation(
                    mmsi=mmsi,
                    timestamp=_normalize_timestamp(timestamp),
                    latitude=0.0,
                    longitude=0.0,
                    speed=0.0,
                    course=0.0,
                    heading=0.0,
                    source="",
                ),
                EVENT_DEPARTURE,
            )

        observation = _observation_from_ship(ship)

        if observation is None:
            return None

        return self._append_event(
            PresenceObservation(
                mmsi=observation.mmsi,
                timestamp=_normalize_timestamp(timestamp),
                latitude=observation.latitude,
                longitude=observation.longitude,
                speed=observation.speed,
                course=observation.course,
                heading=observation.heading,
                source=observation.source,
            ),
            EVENT_DEPARTURE,
        )

    def _append_event(
        self,
        observation: PresenceObservation,
        event_type: str,
    ) -> TimelineRecord:

        record = TimelineRecord(
            mmsi=observation.mmsi,
            timestamp=observation.timestamp,
            event_type=event_type,
            latitude=observation.latitude,
            longitude=observation.longitude,
            speed=observation.speed,
            course=observation.course,
            heading=observation.heading,
            source=observation.source,
        )

        return self._manager.append(record)


arrival_departure_engine = ArrivalDepartureEngine()
