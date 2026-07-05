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
