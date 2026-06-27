# ============================================================================
# Project X
# Ship Model
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Ship:

    mmsi: int

    name: str = ""

    callsign: str = ""

    ship_type: str = ""

    lat: float = 0.0

    lon: float = 0.0

    speed: float = 0.0

    course: float = 0.0

    heading: float = 0.0

    destination: str = ""

    eta: str = ""

    source: str = ""

    last_seen: datetime = field(default_factory=datetime.now)

    ais_visible: bool = False

    rtl_visible: bool = False

    camera_visible: bool = False
