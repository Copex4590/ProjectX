# ============================================================================
# Project X
# Vessel Sync
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Lock, Thread

from database.vessel_database import VesselDatabase
from models.ship import Ship
from models.vessel_record import VesselRecord
from storage.lazy_singleton import LazySingleton, lazy_module_getattr

_TEXT_FIELDS = ("imo", "name", "callsign", "ship_type", "flag")
_FLOAT_FIELDS = ("length", "width", "draft")


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


@dataclass(frozen=True)
class VesselObservation:

    mmsi: int
    imo: str
    name: str
    callsign: str
    ship_type: str
    flag: str
    length: float | None
    width: float | None
    draft: float | None
    last_seen: datetime


def _safe_text(value) -> str:

    if value is None:
        return ""

    return str(value).strip()


def _optional_float(ship: Ship, *field_names: str) -> float | None:

    for field_name in field_names:
        if not hasattr(ship, field_name):
            continue

        value = getattr(ship, field_name)

        if value is None or value == "":
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return None


def _normalize_timestamp(value: datetime | None) -> datetime:

    if value is None:
        value = datetime.now()

    return value.replace(microsecond=0)


def _observation_from_ship(ship: Ship) -> VesselObservation | None:

    normalized_mmsi = _normalize_mmsi(ship.mmsi)

    if normalized_mmsi is None:
        return None

    return VesselObservation(
        mmsi=normalized_mmsi,
        imo=_safe_text(getattr(ship, "imo", "")),
        name=_safe_text(ship.name),
        callsign=_safe_text(ship.callsign),
        ship_type=_safe_text(ship.ship_type),
        flag=_safe_text(getattr(ship, "flag", "")),
        length=_optional_float(ship, "length"),
        width=_optional_float(ship, "width"),
        draft=_optional_float(ship, "draft", "draught"),
        last_seen=_normalize_timestamp(ship.last_seen),
    )


def _merge_observation(
    existing: VesselRecord,
    observation: VesselObservation,
) -> tuple[VesselRecord, bool]:

    now = _normalize_timestamp(datetime.now())
    changed = False

    merged = VesselRecord(
        mmsi=existing.mmsi,
        imo=existing.imo,
        name=existing.name,
        callsign=existing.callsign,
        ship_type=existing.ship_type,
        flag=existing.flag,
        length=existing.length,
        width=existing.width,
        draft=existing.draft,
        first_seen=existing.first_seen,
        last_seen=existing.last_seen,
        created_at=existing.created_at,
        updated_at=existing.updated_at,
    )

    for field_name in _TEXT_FIELDS:
        new_value = getattr(observation, field_name)
        old_value = getattr(merged, field_name)

        if new_value != old_value:
            setattr(merged, field_name, new_value)
            changed = True

    for field_name in _FLOAT_FIELDS:
        new_value = getattr(observation, field_name)

        if new_value is None:
            continue

        old_value = getattr(merged, field_name)

        if old_value != new_value:
            setattr(merged, field_name, new_value)
            changed = True

    if merged.last_seen != observation.last_seen:
        merged.last_seen = observation.last_seen
        changed = True

    if changed:
        merged.updated_at = now

    return merged, changed


class VesselSync:

    def __init__(self, database: VesselDatabase | None = None):

        self._database = database
        self._queue: Queue[VesselObservation] = Queue()
        self._worker_lock = Lock()
        self._worker: Thread | None = None

    def _database_instance(self) -> VesselDatabase:

        if self._database is None:
            from database.vessel_database import get_vessel_database

            self._database = get_vessel_database()

        return self._database

    def enqueue(self, ship: Ship | None) -> None:

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return

        self._ensure_worker()
        self._queue.put(observation)

    def sync_now(self, ship: Ship | None) -> VesselRecord | None:

        observation = _observation_from_ship(ship) if ship is not None else None

        if observation is None:
            return None

        return self._apply_observation(observation)

    def _ensure_worker(self) -> None:

        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return

            self._worker = Thread(
                target=self._worker_loop,
                name="VesselSyncWorker",
                daemon=True,
            )
            self._worker.start()

    def _worker_loop(self) -> None:

        while True:
            try:
                observation = self._queue.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._apply_observation(observation)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def _apply_observation(
        self,
        observation: VesselObservation,
    ) -> VesselRecord | None:

        database = self._database_instance()
        existing = database.get(observation.mmsi)

        if existing is None:
            now = _normalize_timestamp(datetime.now())
            record = VesselRecord(
                mmsi=observation.mmsi,
                imo=observation.imo,
                name=observation.name,
                callsign=observation.callsign,
                ship_type=observation.ship_type,
                flag=observation.flag,
                length=observation.length,
                width=observation.width,
                draft=observation.draft,
                first_seen=observation.last_seen,
                last_seen=observation.last_seen,
                created_at=now,
                updated_at=now,
            )
            return database.upsert(record)

        merged, changed = _merge_observation(existing, observation)

        if not changed:
            return existing

        return database.upsert(merged)


get_vessel_sync = LazySingleton(VesselSync)


def __getattr__(name: str):
    return lazy_module_getattr(
        name,
        module_name=__name__,
        export_name="vessel_sync",
        getter=get_vessel_sync,
    )
