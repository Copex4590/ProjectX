# ============================================================================
# Project X
# Camera Stream Connection Test
# ============================================================================

from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from camera.camera import CAMERA_TYPES, _normalize_camera_type


@dataclass(frozen=True)
class StreamTestResult:

    success: bool
    message: str
    stream_type: str = ""
    resolution: str = ""


def validate_stream_url(camera_type: str, stream_url: str) -> tuple[bool, str]:

    normalized_type = _normalize_camera_type(camera_type)
    url = str(stream_url or "").strip()

    if not url:
        return False, "Stream URL cannot be empty."

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if normalized_type == "rtsp":
        if scheme not in {"rtsp", "rtsps"}:
            return False, "RTSP URL must start with rtsp:// or rtsps://."

    elif normalized_type in {"hls", "mjpeg", "http"}:
        if scheme not in {"http", "https"}:
            return False, "URL must start with http:// or https://."

    else:
        return False, "Unsupported camera type."

    if not parsed.netloc:
        return False, "URL must include a host."

    return True, ""


def test_stream(camera_type: str, stream_url: str) -> StreamTestResult:

    normalized_type = _normalize_camera_type(camera_type)
    stream_label = CAMERA_TYPES.get(normalized_type, normalized_type)

    valid, error = validate_stream_url(normalized_type, stream_url)

    if not valid:
        return StreamTestResult(
            success=False,
            message=error,
            stream_type=stream_label,
        )

    url = str(stream_url).strip()

    if normalized_type == "rtsp":
        return _test_rtsp(url, stream_label)

    return _test_http_stream(url, normalized_type, stream_label)


def _test_rtsp(url: str, stream_label: str) -> StreamTestResult:

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (554 if parsed.scheme == "rtsp" else 322)

    if not host:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )

    try:
        with socket.create_connection((host, port), timeout=5.0):
            pass
    except OSError:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )

    return StreamTestResult(
        success=True,
        message="Connection successful",
        stream_type=stream_label,
    )


def _test_http_stream(
    url: str,
    camera_type: str,
    stream_label: str,
) -> StreamTestResult:

    request = Request(
        url,
        headers={"User-Agent": "ProjectX/1.0"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=8.0) as response:
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            body_prefix = response.read(4096)
    except HTTPError as error:
        if error.code in {401, 403}:
            return StreamTestResult(
                success=True,
                message="Connection successful",
                stream_type=stream_label,
                resolution=_resolution_from_headers(error.headers),
            )

        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )
    except URLError:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )
    except TimeoutError:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )

    if status >= 400:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )

    resolution = _resolution_from_body(camera_type, content_type, body_prefix)

    if camera_type == "hls" and b"#EXTM3U" not in body_prefix:
        return StreamTestResult(
            success=False,
            message="Unable to connect",
            stream_type=stream_label,
        )

    return StreamTestResult(
        success=True,
        message="Connection successful",
        stream_type=stream_label,
        resolution=resolution,
    )


def _resolution_from_headers(headers) -> str:

    if headers is None:
        return ""

    for key in ("X-Resolution", "X-Video-Resolution"):
        value = headers.get(key)

        if value:
            return str(value).strip()

    return ""


def _resolution_from_body(
    camera_type: str,
    content_type: str,
    body: bytes,
) -> str:

    lowered = content_type.lower()

    if "jpeg" in lowered or "jpg" in lowered:
        return _jpeg_resolution(body)

    if camera_type == "mjpeg" and (
        "multipart" in lowered or "image" in lowered
    ):
        return _jpeg_resolution(body)

    return ""


def _jpeg_resolution(body: bytes) -> str:

    start = body.find(b"\xff\xd8")

    if start < 0:
        return ""

    segment = body[start:start + 512]
    index = 2

    while index + 9 < len(segment):
        if segment[index] != 0xFF:
            break

        marker = segment[index + 1]

        if marker in {0xC0, 0xC1, 0xC2}:
            height = int.from_bytes(segment[index + 5:index + 7], "big")
            width = int.from_bytes(segment[index + 7:index + 9], "big")
            return f"{width}x{height}"

        if index + 3 >= len(segment):
            break

        length = int.from_bytes(segment[index + 2:index + 4], "big")

        if length < 2:
            break

        index += length + 2

    return ""
