# ============================================================================
# Project X
# Vessel Statistics Records
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GlobalStatistics:

    total_vessels: int = 0
    active_vessels: int = 0
    arrivals_today: int = 0
    departures_today: int = 0
    position_updates_today: int = 0
    average_vessel_speed: float | None = None
    most_common_ship_type: str = ""
    most_common_flag: str = ""
    computed_at: datetime = field(default_factory=datetime.now)


@dataclass
class VesselStatistics:

    mmsi: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    total_observations: int = 0
    total_arrivals: int = 0
    total_departures: int = 0
    total_distance: float | None = None
    average_speed: float | None = None
    maximum_speed: float | None = None
    computed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ActiveVesselEntry:

    mmsi: int
    name: str
    activity_count: int


@dataclass
class DashboardStatistics:

    global_stats: GlobalStatistics = field(default_factory=GlobalStatistics)
    top_ship_types: list[tuple[str, int]] = field(default_factory=list)
    top_flags: list[tuple[str, int]] = field(default_factory=list)
    top_active_vessels: list[ActiveVesselEntry] = field(default_factory=list)
    arrivals_by_hour: list[int] = field(default_factory=lambda: [0] * 24)
    departures_by_hour: list[int] = field(default_factory=lambda: [0] * 24)
    activity_last_24_hours: list[int] = field(default_factory=lambda: [0] * 24)
