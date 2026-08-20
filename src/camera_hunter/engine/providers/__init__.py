"""Discovery-side provider filters. Playback stays on MediaEngine / IMediaAdapter."""

from __future__ import annotations

from camera_hunter.engine.providers.earthcam import applies as earthcam_applies

__all__ = ["earthcam_applies", "provider_id"]


def provider_id(url: str | None, page_url: str | None = None) -> str | None:
    if earthcam_applies(url) or earthcam_applies(page_url):
        return "earthcam"
    return None
