# ============================================================================
# Project X
# Lightweight camera stream reachability probe (SAVE-235)
# ============================================================================

from __future__ import annotations

import socket
from urllib.parse import urlparse

from models.camera import Camera


def camera_stream_url(camera: Camera) -> str:

    return str(
        getattr(camera, "playback_stream_url", None)
        or getattr(camera, "stream_url", "")
        or ""
    ).strip()


def probe_url_host_reachable(url: str, *, timeout_s: float = 2.0) -> bool:
    """Return True if the stream URL's host:port accepts a TCP connection."""

    text = str(url or "").strip()
    if not text:
        return False

    parsed = urlparse(text)
    host = parsed.hostname
    if not host:
        return False

    scheme = (parsed.scheme or "").lower()
    if parsed.port:
        port = int(parsed.port)
    elif scheme in {"https", "rtsps"}:
        port = 443
    elif scheme in {"rtsp"}:
        port = 554
    elif scheme in {"http"}:
        port = 80
    else:
        port = 80

    try:
        with socket.create_connection((host, port), timeout=max(0.2, float(timeout_s))):
            return True
    except OSError:
        return False


def is_camera_reachable(camera: Camera, *, timeout_s: float = 2.0) -> bool:
    """Enabled camera with a stream URL whose host is reachable."""

    if not bool(getattr(camera, "enabled", False)):
        return False

    url = camera_stream_url(camera)
    if not url:
        return False

    return probe_url_host_reachable(url, timeout_s=timeout_s)


def any_reachable_camera(
    cameras: list[Camera],
    *,
    timeout_s: float = 2.0,
) -> bool:

    for camera in cameras:
        if is_camera_reachable(camera, timeout_s=timeout_s):
            return True
    return False
