# ============================================================================
# Project X
# Vessel Timeline Recorder
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Lock, Thread
import logging
import time

from models.ship import Ship
from timeline.timeline_manager import TimelineManager, timeline_manager
from timeline.timeline_record import TimelineRecord

logger = logging.getLogger(__name__)

EVENT_POSITION_UPDATE = "POSITION_UPDATE"
POSITION_EPSILON = 0.00001
_STOP = object()
_BATCH_FLUSH_S = 0.5
_BATCH_MAX = 64


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


def _position_changed(
    previous_lat: float | None,
    previous_lon: float | None,
    latitude: float,
    longitude: float,
) -> bool:

    if previous_lat is None or previous_lon is None:
        return True

    return (
        abs(previous_lat - latitude) > POSITION_EPSILON
        or abs(previous_lon - longitude) > POSITION_EPSILON
    )


@dataclass(frozen=True)
class TimelineObservation:

    mmsi: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    course: float
    heading: float
    source: str


def _observation_from_ship(ship: Ship) -> TimelineObservation | None:

    normalized_mmsi = _normalize_mmsi(ship.mmsi)

    if normalized_mmsi is None:
        return None

    return TimelineObservation(
        mmsi=normalized_mmsi,
        timestamp=_normalize_timestamp(ship.last_seen),
        latitude=float(ship.lat),
        longitude=float(ship.lon),
        speed=float(ship.speed or 0.0),
        course=float(ship.course or 0.0),
        heading=float(ship.heading or 0.0),
        source=_safe_text(ship.source),
    )


class TimelineRecorder:

    def __init__(self, manager: TimelineManager | None = None):

        self._manager = manager or timeline_manager
        self._queue: Queue[TimelineObservation | object] = Queue()
        self._worker_lock = Lock()
        self._worker: Thread | None = None
        self._last_positions: dict[int, tuple[float, float]] = {}
        self._position_lock = Lock()
        self._stop_requested = False

    def enqueue(self, ship: Ship | None) -> None:

        if self._stop_requested:
            return

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return

        if not self._should_record(observation):
            return

        self._ensure_worker()
        self._queue.put(observation)

    def stop(self, timeout: float = 5.0) -> None:

        self._stop_requested = True

        with self._worker_lock:
            worker = self._worker
            if worker is not None and worker.is_alive():
                self._queue.put(_STOP)

        if worker is not None and worker.is_alive():
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning(
                    "TimelineRecorder worker did not stop within %.1fs",
                    timeout,
                )

    def record_now(self, ship: Ship | None) -> TimelineRecord | None:

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return None

        return self._apply_observation(observation)

    def _should_record(self, observation: TimelineObservation) -> bool:

        with self._position_lock:
            last_position = self._last_positions.get(observation.mmsi)

        if last_position is None:
            return True

        last_lat, last_lon = last_position

        return _position_changed(
            last_lat,
            last_lon,
            observation.latitude,
            observation.longitude,
        )

    def _remember_position(
        self,
        mmsi: int,
        latitude: float,
        longitude: float,
    ) -> None:

        with self._position_lock:
            self._last_positions[mmsi] = (latitude, longitude)

    def _ensure_worker(self) -> None:

        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._stop_requested = False
            self._worker = Thread(
                target=self._worker_loop,
                name="TimelineRecorderWorker",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:

        pending: list[TimelineObservation] = []
        last_flush = time.monotonic()

        while True:
            timeout = max(0.05, _BATCH_FLUSH_S - (time.monotonic() - last_flush))
            try:
                observation = self._queue.get(timeout=timeout)
            except Empty:
                observation = None

            try:
                if observation is _STOP:
                    if pending:
                        self._flush_pending(pending)
                        pending.clear()
                    self._queue.task_done()
                    return

                if observation is not None:
                    pending.append(observation)
                    self._queue.task_done()

                due = pending and (
                    len(pending) >= _BATCH_MAX
                    or (time.monotonic() - last_flush) >= _BATCH_FLUSH_S
                )
                if due:
                    self._flush_pending(pending)
                    pending.clear()
                    last_flush = time.monotonic()

                if observation is None and self._stop_requested and not pending:
                    return
            except Exception:
                logger.exception("TimelineRecorder failed to apply observation batch")
                pending.clear()
                last_flush = time.monotonic()

    def _flush_pending(self, pending: list[TimelineObservation]) -> None:

        records: list[TimelineRecord] = []
        for observation in pending:
            if not self._should_record(observation):
                continue
            records.append(
                TimelineRecord(
                    mmsi=observation.mmsi,
                    timestamp=observation.timestamp,
                    event_type=EVENT_POSITION_UPDATE,
                    latitude=observation.latitude,
                    longitude=observation.longitude,
                    speed=observation.speed,
                    course=observation.course,
                    heading=observation.heading,
                    source=observation.source,
                )
            )
            self._remember_position(
                observation.mmsi,
                observation.latitude,
                observation.longitude,
            )

        if records:
            self._manager.append_many(records)

    def _apply_observation(
        self,
        observation: TimelineObservation,
    ) -> TimelineRecord | None:

        if not self._should_record(observation):
            return None

        record = TimelineRecord(
            mmsi=observation.mmsi,
            timestamp=observation.timestamp,
            event_type=EVENT_POSITION_UPDATE,
            latitude=observation.latitude,
            longitude=observation.longitude,
            speed=observation.speed,
            course=observation.course,
            heading=observation.heading,
            source=observation.source,
        )

        saved = self._manager.append(record)
        self._remember_position(
            observation.mmsi,
            observation.latitude,
            observation.longitude,
        )

        return saved


timeline_recorder = TimelineRecorder()
