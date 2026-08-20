"""Structured CAMERA RESULT — API-ready snapshot of a discovered camera source.

Does not replace CameraSource; it is built from actually found sources only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

from camera_hunter.models.camera_source import CameraSource, SourceType


class CameraResultType(str, Enum):
    STILL_IMAGE = "still_image"
    REFRESHING_IMAGE = "refreshing_image"
    MJPEG = "mjpeg"
    HLS = "hls"
    DASH = "dash"
    MP4 = "mp4"
    WEBM = "webm"
    UNKNOWN = "unknown"


_SOURCE_PRIORITY = (
    SourceType.HLS,
    SourceType.DASH,
    SourceType.MJPEG,
    SourceType.VIDEO,
    SourceType.REFRESH_IMAGE,
    SourceType.IMAGE,
)


@dataclass(frozen=True)
class CameraResult:
    source_page: str | None
    final_page: str | None
    camera_source_url: str | None
    source_type: CameraResultType
    content_type: str | None
    is_live: bool
    extraction_method: str | None
    referer: str | None
    user_agent: str | None
    discovered_at: datetime | None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        if isinstance(self.discovered_at, datetime):
            data["discovered_at"] = self.discovered_at.isoformat()
        return data


def result_type_from_source(src: CameraSource) -> CameraResultType:
    st = src.source_type
    if st == SourceType.HLS:
        return CameraResultType.HLS
    if st == SourceType.DASH:
        return CameraResultType.DASH
    if st == SourceType.MJPEG:
        return CameraResultType.MJPEG
    if st == SourceType.REFRESH_IMAGE:
        return CameraResultType.REFRESHING_IMAGE
    if st == SourceType.IMAGE:
        return CameraResultType.STILL_IMAGE
    if st == SourceType.VIDEO:
        return _video_result_type(src)
    return CameraResultType.UNKNOWN


def _video_result_type(src: CameraSource) -> CameraResultType:
    mime = (src.mime_type or "").split(";")[0].strip().lower()
    url = (src.url or "").lower()
    if mime == "video/webm" or url.endswith(".webm") or ".webm?" in url:
        return CameraResultType.WEBM
    if mime == "video/mp4" or url.endswith(".mp4") or ".mp4?" in url:
        return CameraResultType.MP4
    return CameraResultType.UNKNOWN


def select_camera_source(sources: list[CameraSource]) -> CameraSource | None:
    """Pick the best *actually found* camera source. Thumbnails and ads are skipped."""
    hits = [s for s in sources if s.is_camera_hit() and not s.is_thumbnail() and s.url]
    if not hits:
        return None
    ranked: list[CameraSource] = []
    for wanted in _SOURCE_PRIORITY:
        group = [s for s in hits if s.source_type == wanted]
        if wanted == SourceType.HLS:
            group.sort(
                key=lambda s: (
                    0 if s.discovery_source == "NETWORK RESPONSE" else 1,
                    0 if ".m3u8" in s.url.lower() else 1,
                    -s.confidence,
                )
            )
        else:
            group.sort(key=lambda s: -s.confidence)
        ranked.extend(group)
    return ranked[0] if ranked else None


def camera_result_from_source(
    src: CameraSource,
    *,
    source_page: str | None = None,
    final_page: str | None = None,
    user_agent: str | None = None,
    referer: str | None = None,
) -> CameraResult:
    rtype = result_type_from_source(src)
    page = source_page or src.source_page
    final = final_page or src.found_after or src.source_page
    used_referer = referer or src.found_after or src.source_page
    return CameraResult(
        source_page=page,
        final_page=final,
        camera_source_url=src.url,
        source_type=rtype,
        content_type=src.mime_type,
        is_live=rtype == CameraResultType.HLS,
        extraction_method=src.discovery_source or None,
        referer=used_referer,
        user_agent=user_agent,
        discovered_at=src.discovered_at,
    )


def camera_result_from_sources(
    sources: list[CameraSource],
    *,
    source_page: str | None = None,
    final_page: str | None = None,
    user_agent: str | None = None,
    referer: str | None = None,
) -> CameraResult | None:
    src = select_camera_source(sources)
    if src is None:
        return None
    return camera_result_from_source(
        src,
        source_page=source_page,
        final_page=final_page,
        user_agent=user_agent,
        referer=referer,
    )
