# ============================================================================
# Project X
# Unified Camera Model (SAVE-231)
# ============================================================================

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

CAMERA_TYPES = {
    "hls": "HLS (.m3u8)",
    "rtsp": "RTSP",
    "mjpeg": "MJPEG",
    "http": "HTTP Stream",
    "local": "Local video",
    "youtube": "YouTube",
    "snapshot": "Snapshot",
}

SUPPORTED_CAMERA_TYPES = ("hls", "rtsp", "mjpeg", "http")
FUTURE_CAMERA_TYPES = ("local", "youtube")

SOURCE_CATALOG = "catalog"
SOURCE_PACK = "pack"
SOURCE_USER = "user"


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


def normalize_camera_type(value: str | None) -> str:

    normalized = str(value or "").strip().lower()

    if normalized in CAMERA_TYPES:
        return normalized

    return "hls"


def _parse_datetime(value) -> datetime:

    if isinstance(value, datetime):
        return value

    text = str(value or "").strip()

    if not text:
        return _utc_now()

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _utc_now()

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


@dataclass
class Camera:
    """Single camera record for catalog packs and user/OP-bound cameras."""

    id: str
    name: str
    country: str = ""

    lat: float = 0.0
    lon: float = 0.0

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

    observation_point_id: str = ""
    source: str = SOURCE_CATALOG
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    # --- Wizard / legacy aliases (Stack A field names) ---

    @property
    def type(self) -> str:

        return self.provider_type or "hls"

    @type.setter
    def type(self, value: str) -> None:

        self.provider_type = normalize_camera_type(value)

    @property
    def latitude(self) -> float:

        return self.lat

    @latitude.setter
    def latitude(self, value: float) -> None:

        self.lat = float(value)

    @property
    def longitude(self) -> float:

        return self.lon

    @longitude.setter
    def longitude(self, value: float) -> None:

        self.lon = float(value)

    @property
    def heading(self) -> float:

        return self.direction_deg

    @heading.setter
    def heading(self, value: float) -> None:

        self.direction_deg = float(value)

    @property
    def field_of_view(self) -> float:

        return self.fov_deg

    @field_of_view.setter
    def field_of_view(self, value: float) -> None:

        self.fov_deg = float(value)

    @property
    def max_distance(self) -> float:

        return self.visibility_radius_km

    @max_distance.setter
    def max_distance(self, value: float) -> None:

        self.visibility_radius_km = float(value)

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

    def to_user_dict(self) -> dict:
        """Persist user/OP cameras (legacy + canonical keys)."""

        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "type": self.provider_type or "hls",
            "provider_type": self.provider_type or "hls",
            "stream_url": self.stream_url,
            "latitude": self.lat,
            "longitude": self.lon,
            "lat": self.lat,
            "lon": self.lon,
            "heading": self.direction_deg,
            "direction_deg": self.direction_deg,
            "field_of_view": self.fov_deg,
            "fov_deg": self.fov_deg,
            "max_distance": self.visibility_radius_km,
            "visibility_radius_km": self.visibility_radius_km,
            "description": self.description,
            "observation_point_id": self.observation_point_id,
            "country": self.country,
            "source": SOURCE_USER,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_user_dict(cls, data: dict) -> Camera:
        """Load user camera JSON (legacy Stack A or unified keys)."""

        provider_type = normalize_camera_type(
            data.get("provider_type") or data.get("type") or "hls"
        )
        lat = float(data.get("lat", data.get("latitude", 0.0)) or 0.0)
        lon = float(data.get("lon", data.get("longitude", 0.0)) or 0.0)
        direction = float(
            data.get("direction_deg", data.get("heading", 0.0)) or 0.0
        )
        fov = float(data.get("fov_deg", data.get("field_of_view", 90.0)) or 90.0)
        radius = float(
            data.get(
                "visibility_radius_km",
                data.get("max_distance", 0.0),
            )
            or 0.0
        )

        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data.get("name") or "").strip() or "Camera",
            country=str(data.get("country") or "").strip().upper(),
            lat=lat,
            lon=lon,
            direction_deg=direction,
            visibility_radius_km=radius,
            fov_deg=fov,
            enabled=bool(data.get("enabled", True)),
            description=str(data.get("description") or "").strip(),
            provider_type=provider_type,
            stream_url=str(data.get("stream_url") or "").strip(),
            observation_point_id=str(
                data.get("observation_point_id") or ""
            ).strip(),
            source=SOURCE_USER,
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )

    @classmethod
    def new_user_camera(
        cls,
        *,
        name: str,
        observation_point_id: str,
        enabled: bool = True,
        camera_type: str = "hls",
        stream_url: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
        heading: float = 0.0,
        field_of_view: float = 90.0,
        max_distance: float = 0.0,
        description: str = "",
        country: str = "",
    ) -> Camera:

        now = _utc_now()
        return cls(
            id=uuid4().hex,
            name=str(name).strip() or "Camera",
            country=str(country or "").strip().upper(),
            lat=float(latitude),
            lon=float(longitude),
            direction_deg=float(heading),
            visibility_radius_km=float(max_distance),
            fov_deg=float(field_of_view),
            enabled=bool(enabled),
            description=str(description).strip(),
            provider_type=normalize_camera_type(camera_type),
            stream_url=str(stream_url).strip(),
            observation_point_id=str(observation_point_id).strip(),
            source=SOURCE_USER,
            created_at=now,
            updated_at=now,
        )
