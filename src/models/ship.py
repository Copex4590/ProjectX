# ============================================================================
# Project X
# Ship Model
# ============================================================================

from collections import deque
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


    # --- Hybrid Monitor migration fields ---
    distance_km: float = 0.0
    direction: str = ""
    text_heading: str = ""

    last_seen: datetime = field(default_factory=datetime.now)

    ais_visible: bool = False
    rtl_visible: bool = False
    camera_visible: bool = False

    history: deque = field(
        default_factory=lambda: deque(maxlen=100),
        repr=False,
    )

    previous_lat: float = 0.0
    previous_lon: float = 0.0

    target_lat: float = 0.0
    target_lon: float = 0.0

    def add_history(self):

        if self.target_lat == 0.0 and self.target_lon == 0.0:
            self.target_lat = self.lat
            self.target_lon = self.lon

        self.previous_lat = self.target_lat
        self.previous_lon = self.target_lon

        self.target_lat = self.lat
        self.target_lon = self.lon

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
