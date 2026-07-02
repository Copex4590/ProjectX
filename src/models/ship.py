# ============================================================================
# Project X
# Ship Model
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


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

    # Utolsó 100 pozíció
    history: deque = field(
        default_factory=lambda: deque(maxlen=100),
        repr=False
    )

    def add_history(self):

        if not self.history:
            self.history.append((self.lat, self.lon))
            return

        last_lat, last_lon = self.history[-1]

        if (
            abs(last_lat - self.lat) > 0.00001
            or
            abs(last_lon - self.lon) > 0.00001
        ):
            self.history.append((self.lat, self.lon))
