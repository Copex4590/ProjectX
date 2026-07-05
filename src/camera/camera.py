# ============================================================================
# Project X
# Camera Model
# ============================================================================

from __future__ import annotations

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
}

SUPPORTED_CAMERA_TYPES = ("hls", "rtsp", "mjpeg", "http")
FUTURE_CAMERA_TYPES = ("local", "youtube")


def _utc_now() -> datetime:

    return datetime.now(timezone.utc)


def _normalize_camera_type(value: str) -> str:

    normalized = str(value or "").strip().lower()

    if normalized in CAMERA_TYPES:
        return normalized

    return "hls"


@dataclass
class Camera:

    name: str
    observation_point_id: str
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    type: str = "hls"
    stream_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    heading: float = 0.0
    field_of_view: float = 90.0
    max_distance: float = 0.0
    description: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "type": self.type,
            "stream_url": self.stream_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "heading": self.heading,
            "field_of_view": self.field_of_view,
            "max_distance": self.max_distance,
            "description": self.description,
            "observation_point_id": self.observation_point_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Camera:

        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data.get("name") or "").strip() or "Camera",
            enabled=bool(data.get("enabled", True)),
            type=_normalize_camera_type(data.get("type", "hls")),
            stream_url=str(data.get("stream_url") or "").strip(),
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            heading=float(data.get("heading", 0.0)),
            field_of_view=float(data.get("field_of_view", 90.0)),
            max_distance=float(data.get("max_distance", 0.0)),
            description=str(data.get("description") or "").strip(),
            observation_point_id=str(
                data.get("observation_point_id") or ""
            ).strip(),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )


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
