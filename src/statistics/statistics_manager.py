# ============================================================================
# Project X
# Vessel Statistics Manager
# ============================================================================

import os
from collections import Counter
from datetime import datetime, timedelta
from threading import Lock

from database.vessel_database import VesselDatabase, vessel_database
from engines.timeline.arrival_departure_engine import (
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
)
from models.vessel_record import VesselRecord
from statistics.statistics_record import GlobalStatistics, VesselStatistics
from timeline.timeline_manager import TimelineManager, timeline_manager
from timeline.timeline_recorder import EVENT_POSITION_UPDATE
from timeline.timeline_record import TimelineRecord

DEFAULT_REFRESH_INTERVAL_SECONDS = float(
    os.environ.get("PROJECTX_STATISTICS_REFRESH_INTERVAL_SECONDS", "30")
)

ACTIVE_VESSEL_HOURS = 24


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


def _most_common(values: list[str]) -> str:

    counter = Counter(
        value.strip()
        for value in values
        if str(value or "").strip()
    )

    if not counter:
        return ""

    return counter.most_common(1)[0][0]


def _average_speed(records: list[TimelineRecord]) -> float | None:

    speeds = [
        float(record.speed)
        for record in records
        if record.speed is not None
    ]

    if not speeds:
        return None

    return sum(speeds) / len(speeds)


def _maximum_speed(records: list[TimelineRecord]) -> float | None:

    speeds = [
        float(record.speed)
        for record in records
        if record.speed is not None
    ]

    if not speeds:
        return None

    return max(speeds)


class StatisticsManager:

    def __init__(
        self,
        database: VesselDatabase | None = None,
        timeline: TimelineManager | None = None,
        refresh_interval_seconds: float | None = None,
    ):

        self._vessel_database = database or vessel_database
        self._timeline_manager = timeline or timeline_manager
        self._refresh_interval = timedelta(
            seconds=refresh_interval_seconds or DEFAULT_REFRESH_INTERVAL_SECONDS
        )
        self._lock = Lock()
        self._global_cache: GlobalStatistics | None = None
        self._vessel_cache: dict[int, VesselStatistics] = {}
        self._timeline_by_mmsi: dict[int, list[TimelineRecord]] = {}
        self._vessels_by_mmsi: dict[int, VesselRecord] = {}
        self._cache_timestamp: datetime | None = None

    @property
    def refresh_interval(self) -> timedelta:

        return self._refresh_interval

    def global_statistics(self) -> GlobalStatistics:

        with self._lock:
            if not self._cache_is_fresh():
                self._rebuild_cache_locked()

            if self._global_cache is None:
                return GlobalStatistics()

            return self._global_cache

    def vessel_statistics(self, mmsi: int | str) -> VesselStatistics | None:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return None

        with self._lock:
            if not self._cache_is_fresh():
                self._rebuild_cache_locked()

            cached = self._vessel_cache.get(normalized_mmsi)

            if cached is not None:
                return cached

            return self._compute_vessel_statistics_locked(
                normalized_mmsi,
                self._vessels_by_mmsi.get(normalized_mmsi),
                self._timeline_by_mmsi.get(normalized_mmsi, []),
            )

    def refresh(self) -> GlobalStatistics:

        with self._lock:
            self._rebuild_cache_locked()

            if self._global_cache is None:
                return GlobalStatistics()

            return self._global_cache

    def _cache_is_fresh(self) -> bool:

        if self._cache_timestamp is None:
            return False

        return datetime.now() - self._cache_timestamp < self._refresh_interval

    def _rebuild_cache_locked(self) -> None:

        vessels = self._vessel_database.all()
        timeline_records = self._timeline_manager.all()
        now = datetime.now()
        today = now.date()

        self._vessels_by_mmsi = {
            vessel.mmsi: vessel
            for vessel in vessels
        }
        self._timeline_by_mmsi = {}

        for record in timeline_records:
            self._timeline_by_mmsi.setdefault(record.mmsi, []).append(record)

        active_threshold = now - timedelta(hours=ACTIVE_VESSEL_HOURS)
        position_records = [
            record
            for record in timeline_records
            if record.event_type == EVENT_POSITION_UPDATE
        ]

        self._global_cache = GlobalStatistics(
            total_vessels=len(vessels),
            active_vessels=sum(
                1
                for vessel in vessels
                if vessel.last_seen >= active_threshold
            ),
            arrivals_today=sum(
                1
                for record in timeline_records
                if record.event_type == EVENT_ARRIVAL
                and record.timestamp.date() == today
            ),
            departures_today=sum(
                1
                for record in timeline_records
                if record.event_type == EVENT_DEPARTURE
                and record.timestamp.date() == today
            ),
            position_updates_today=sum(
                1
                for record in timeline_records
                if record.event_type == EVENT_POSITION_UPDATE
                and record.timestamp.date() == today
            ),
            average_vessel_speed=_average_speed(position_records),
            most_common_ship_type=_most_common([
                vessel.ship_type
                for vessel in vessels
            ]),
            most_common_flag=_most_common([
                vessel.flag
                for vessel in vessels
            ]),
            computed_at=now,
        )

        self._vessel_cache = {
            mmsi: self._compute_vessel_statistics_locked(
                mmsi,
                vessel,
                self._timeline_by_mmsi.get(mmsi, []),
            )
            for mmsi, vessel in self._vessels_by_mmsi.items()
        }

        for mmsi, records in self._timeline_by_mmsi.items():
            if mmsi in self._vessel_cache:
                continue

            self._vessel_cache[mmsi] = self._compute_vessel_statistics_locked(
                mmsi,
                None,
                records,
            )

        self._cache_timestamp = now

    def _compute_vessel_statistics_locked(
        self,
        mmsi: int,
        vessel: VesselRecord | None,
        timeline_records: list[TimelineRecord],
    ) -> VesselStatistics:

        position_records = [
            record
            for record in timeline_records
            if record.event_type == EVENT_POSITION_UPDATE
        ]

        first_seen = vessel.first_seen if vessel is not None else None
        last_seen = vessel.last_seen if vessel is not None else None

        if first_seen is None and timeline_records:
            first_seen = min(record.timestamp for record in timeline_records)

        if last_seen is None and timeline_records:
            last_seen = max(record.timestamp for record in timeline_records)

        return VesselStatistics(
            mmsi=mmsi,
            first_seen=first_seen,
            last_seen=last_seen,
            total_observations=len(position_records),
            total_arrivals=sum(
                1
                for record in timeline_records
                if record.event_type == EVENT_ARRIVAL
            ),
            total_departures=sum(
                1
                for record in timeline_records
                if record.event_type == EVENT_DEPARTURE
            ),
            total_distance=None,
            average_speed=_average_speed(position_records),
            maximum_speed=_maximum_speed(position_records),
            computed_at=datetime.now(),
        )


statistics_manager = StatisticsManager()
