# ============================================================================
# Project X
# Camera Model
# ============================================================================

import math
from dataclasses import dataclass, field


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

    provider_type: str = ""
    stream_url: str = ""
    snapshot_url: str = ""
    web_url: str = ""
    provider_name: str = ""
    city: str = ""
    river: str = ""
    timezone: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def safe_text(self, value: str) -> str:

        if value is None:
            return ""

        return str(value).strip()

    @property
    def playback_provider_type(self) -> str:

        return self.safe_text(self.provider_type)

    @property
    def playback_stream_url(self) -> str:

        return self.safe_text(self.stream_url)

    @property
    def playback_snapshot_url(self) -> str:

        return self.safe_text(self.snapshot_url)

    @property
    def playback_web_url(self) -> str:

        return self.safe_text(self.web_url)

    @property
    def location_city(self) -> str:

        return self.safe_text(self.city)

    @property
    def location_river(self) -> str:

        return self.safe_text(self.river)

    @property
    def location_timezone(self) -> str:

        return self.safe_text(self.timezone)

    @property
    def camera_tags(self) -> tuple[str, ...]:

        if not self.tags:
            return ()

        return tuple(
            tag
            for tag in (self.safe_text(item) for item in self.tags)
            if tag
        )

    def has_playback_metadata(self) -> bool:

        return bool(
            self.playback_provider_type
            or self.playback_stream_url
            or self.playback_snapshot_url
            or self.playback_web_url
        )

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
