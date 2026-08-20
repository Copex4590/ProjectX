from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SourceType(str, Enum):
    IMAGE = "image"
    REFRESH_IMAGE = "refresh_image"
    VIDEO = "video"
    HLS = "hls"
    DASH = "dash"
    MJPEG = "mjpeg"
    WEBSOCKET = "websocket"
    MEDIA_SOURCE = "media_source"
    IFRAME = "iframe"
    UNKNOWN_MEDIA = "unknown_media"


class SourceRole(str, Enum):
    CAMERA_SOURCE = "camera_source"
    CAMERA_THUMBNAIL = "camera_thumbnail"


@dataclass(frozen=True)
class CameraSource:
    url: str
    source_type: SourceType
    mime_type: str | None = None
    confidence: float = 0.5
    source_page: str | None = None
    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    hit_count: int = 1
    notes: str | None = None
    discovery_source: str = "NETWORK RESPONSE"
    role: SourceRole = SourceRole.CAMERA_SOURCE
    found_after: str | None = None
    navigation_index: int = 0

    def kind_label(self) -> str:
        mapping = {
            SourceType.IMAGE: "IMAGE",
            SourceType.REFRESH_IMAGE: "IMAGE",
            SourceType.VIDEO: "VIDEO",
            SourceType.HLS: "HLS",
            SourceType.DASH: "DASH",
            SourceType.MJPEG: "MJPEG",
            SourceType.WEBSOCKET: "WEBSOCKET",
            SourceType.MEDIA_SOURCE: "MEDIA_SOURCE",
            SourceType.IFRAME: "IFRAME",
            SourceType.UNKNOWN_MEDIA: "MEDIA",
        }
        return mapping.get(self.source_type, self.source_type.value.upper())

    def label_hu(self) -> str:
        mapping = {
            SourceType.IMAGE: "Állókép",
            SourceType.REFRESH_IMAGE: "Frissülő kép",
            SourceType.VIDEO: "Videó",
            SourceType.HLS: "HLS",
            SourceType.DASH: "DASH",
            SourceType.MJPEG: "MJPEG",
            SourceType.WEBSOCKET: "WebSocket",
            SourceType.MEDIA_SOURCE: "MediaSource",
            SourceType.IFRAME: "Iframe",
            SourceType.UNKNOWN_MEDIA: "Ismeretlen média",
        }
        return mapping.get(self.source_type, self.source_type.value)

    def is_thumbnail(self) -> bool:
        return self.role == SourceRole.CAMERA_THUMBNAIL

    def is_stream(self) -> bool:
        return self.source_type in {
            SourceType.VIDEO,
            SourceType.HLS,
            SourceType.DASH,
            SourceType.MJPEG,
        }

    def is_camera_hit(self) -> bool:
        return self.role == SourceRole.CAMERA_SOURCE and (
            self.is_stream()
            or self.source_type in {SourceType.IMAGE, SourceType.REFRESH_IMAGE}
        )

    def is_direct_camera(self) -> bool:
        if self.is_thumbnail():
            return False
        return self.source_type in {
            SourceType.IMAGE,
            SourceType.REFRESH_IMAGE,
            SourceType.VIDEO,
            SourceType.HLS,
            SourceType.DASH,
            SourceType.MJPEG,
        }

    def navigation_label(self) -> str:
        if not self.found_after:
            return ""
        idx = self.navigation_index or 1
        return f"{idx}. {self.found_after}"
