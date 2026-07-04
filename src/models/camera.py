# ============================================================================
# Project X
# Camera Model
# ============================================================================

import math
from dataclasses import dataclass


@dataclass
class Camera:

    id: str
    name: str
    country: str

    lat: float
    lon: float

    direction_deg: float = 0.0
    visibility_radius_km: float = 0.0
    fov_deg: float = 90.0

    enabled: bool = True
    description: str = ""

    def distance_km_to(self, lat: float, lon: float) -> float:

        radius = 6371.0
        lat1 = math.radians(self.lat)
        lon1 = math.radians(self.lon)
        lat2 = math.radians(lat)
        lon2 = math.radians(lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )

        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def bearing_deg_to(self, lat: float, lon: float) -> float:

        lat1 = math.radians(self.lat)
        lat2 = math.radians(lat)
        dlon = math.radians(lon - self.lon)

        x = math.sin(dlon) * math.cos(lat2)
        y = (
            math.cos(lat1) * math.sin(lat2)
            - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        )

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360.0) % 360.0

    def is_within_radius(self, lat: float, lon: float) -> bool:

        if self.visibility_radius_km <= 0.0:
            return False

        return self.distance_km_to(lat, lon) <= self.visibility_radius_km

    def is_within_direction(self, lat: float, lon: float) -> bool:

        target_bearing = self.bearing_deg_to(lat, lon)
        half_fov = self.fov_deg / 2.0
        delta = abs(target_bearing - self.direction_deg)

        if delta > 180.0:
            delta = 360.0 - delta

        return delta <= half_fov

    def can_observe(self, lat: float, lon: float) -> bool:

        if not self.enabled:
            return False

        return self.is_within_radius(lat, lon) and self.is_within_direction(lat, lon)
