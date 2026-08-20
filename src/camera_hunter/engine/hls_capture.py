"""Fetch a Hunter-discovered HLS URL, download a live segment, extract a JPEG frame."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from camera_hunter.models import CameraSource, SourceType

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MAX_PLAYLIST_BYTES = 2 * 1024 * 1024
MAX_SEGMENT_BYTES = 20 * 1024 * 1024
DEFAULT_TIMEOUT = 20


@dataclass
class HlsCaptureResult:
    hls_url: str
    hls_fetch: bool = False
    segment: bool = False
    video_frame: bool = False
    frame_file: str | None = None
    segment_url: str | None = None
    headers_used: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def report(self) -> str:
        lines = [
            f"HLS FETCH: {'OK' if self.hls_fetch else 'FAIL'}",
            f"SEGMENT: {'OK' if self.segment else 'FAIL'}",
            f"VIDEO FRAME: {'OK' if self.video_frame else 'FAIL'}",
        ]
        if self.frame_file:
            lines.append(f"FRAME FILE: {self.frame_file}")
        return "\n".join(lines)


def normalize_discovered_hls_url(url: str) -> str:
    """Keep the discovered token; map Skyline's page-relative live.m3u8 to hd-auth."""
    raw = (url or "").strip()
    if not raw:
        return raw
    raw = raw.replace("livee.m3u8", "live.m3u8")
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if host in {"www.skylinewebcams.com", "skylinewebcams.com"} and "live.m3u8" in (
        parsed.path or ""
    ).lower():
        return parsed._replace(netloc="hd-auth.skylinewebcams.com").geturl()
    return raw


_AUTH_HEADER_CANON = {
    "user-agent": "User-Agent",
    "referer": "Referer",
    "origin": "Origin",
    "cookie": "Cookie",
    "accept": "Accept",
    "accept-language": "Accept-Language",
    "authorization": "Authorization",
}


def hls_playback_headers(page_url: str | None) -> dict[str, str]:
    """Referer/UA for ffmpeg live read — same header set capture_hls tries first."""
    attempts = _header_attempts(page_url, None)
    return dict(attempts[0]) if attempts else {"User-Agent": BROWSER_UA}


def canonical_request_headers(raw: dict | None) -> dict[str, str]:
    """Copy auth-relevant headers from a real WebEngine/CDP request. Do not invent values."""
    out: dict[str, str] = {}
    if not raw:
        return out
    for key, value in raw.items():
        name = _header_key(key)
        canon = _AUTH_HEADER_CANON.get(name.lower())
        if canon is None:
            continue
        text = _header_value(value)
        if text:
            out[canon] = text
    return out


def merge_hls_headers(*parts: dict[str, str] | None) -> dict[str, str]:
    """Later dicts override earlier ones. Empty values do not wipe a previous value."""
    merged: dict[str, str] = {}
    for part in parts:
        if not part:
            continue
        for key, value in canonical_request_headers(part).items():
            if value:
                merged[key] = value
    return merged


def cookie_names_from_header(header: str | None) -> list[str]:
    names: list[str] = []
    for part in (header or "").split(";"):
        name = part.split("=", 1)[0].strip()
        if name:
            names.append(name)
    return names


def cookie_header_from_associated(cookies: list | None) -> str:
    """Build a Cookie header from CDP Network associatedCookies. No synthetic tokens."""
    parts: list[str] = []
    for item in cookies or []:
        if not isinstance(item, dict):
            continue
        if item.get("blockedReasons"):
            continue
        cookie = item.get("cookie") if isinstance(item.get("cookie"), dict) else item
        name = str((cookie or {}).get("name") or "").strip()
        value = (cookie or {}).get("value")
        if not name or value is None:
            continue
        parts.append(f"{name}={value}")
    return "; ".join(parts)


def _header_key(key: object) -> str:
    if isinstance(key, bytes):
        return key.decode("utf-8", errors="replace")
    return str(key)


def _header_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None:
        return ""
    return str(value)


def select_hls_url(sources: list[CameraSource]) -> str | None:
    """Return the HLS URL Hunter actually found. Do not invent a replacement."""
    hls = [
        s
        for s in sources
        if s.source_type == SourceType.HLS and s.is_camera_hit() and s.url
    ]
    if not hls:
        return None
    hls.sort(
        key=lambda s: (
            0 if "hd-auth.skylinewebcams.com" in s.url else 1,
            0 if s.discovery_source == "NETWORK RESPONSE" else 1,
            0 if ".m3u8" in s.url.lower() else 1,
            -s.confidence,
        )
    )
    return normalize_discovered_hls_url(hls[0].url)


def capture_hls(
    hls_url: str,
    *,
    page_url: str | None = None,
    cookie: str | None = None,
    output_dir: str | Path | None = None,
    print_report: bool = True,
) -> HlsCaptureResult:
    """Download playlist + current segment from a discovered m3u8, then extract a JPEG."""
    result = HlsCaptureResult(hls_url=hls_url or "")
    if not hls_url or not hls_url.startswith(("http://", "https://")):
        result.error = "Nincs HLS URL."
        return _finish(result, print_report)

    attempts = _header_attempts(page_url, cookie)
    body, used, fetch_error = _fetch_playlist(hls_url, attempts)
    result.headers_used = used
    if body is None:
        result.error = fetch_error or "HLS playlist letöltése sikertelen."
        return _finish(result, print_report)

    text = body.decode("utf-8", errors="replace")
    if "#EXTM3U" not in text:
        result.error = "A válasz nem HLS playlist (#EXTM3U hiányzik)."
        return _finish(result, print_report)
    result.hls_fetch = True

    try:
        _media_playlist_url, segment_url = _resolve_current_segment(
            text, hls_url, used or (attempts[0] if attempts else {})
        )
    except Exception as exc:
        result.error = f"Playlist feloldás sikertelen: {exc}"
        return _finish(result, print_report)
    if not segment_url:
        result.error = "A playlistben nincs media szegmens."
        return _finish(result, print_report)
    result.segment_url = segment_url

    work = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "camera_hunter"
    work.mkdir(parents=True, exist_ok=True)
    seg_path = work / "segment.bin"
    frame_path = work / "frame.jpg"

    seg_bytes, _, seg_error = _http_get(segment_url, used or attempts[-1], MAX_SEGMENT_BYTES)
    if not seg_bytes:
        result.error = seg_error or f"Szegmens letöltése sikertelen: {segment_url}"
        return _finish(result, print_report)
    seg_path.write_bytes(seg_bytes)
    result.segment = True

    if not _has_video_stream(seg_path):
        result.error = "ffprobe: a szegmensben nincs videó stream."
        return _finish(result, print_report)

    if not _extract_jpeg(seg_path, frame_path):
        result.error = "ffmpeg: JPEG képkocka kinyerése sikertelen."
        return _finish(result, print_report)
    if not _is_jpeg(frame_path):
        result.error = "A kimeneti fájl nem érvényes JPEG."
        return _finish(result, print_report)

    result.video_frame = True
    result.frame_file = str(frame_path.resolve())
    return _finish(result, print_report)


def hls_stream_alive(
    hls_url: str,
    *,
    page_url: str | None = None,
    last_segment_url: str | None = None,
) -> tuple[bool, str | None]:
    """Health check: playlist + current segment without reloading the page."""
    if not hls_url or not hls_url.startswith(("http://", "https://")):
        return False, None
    if is_ad_hls_url(hls_url):
        return False, None
    attempts = _header_attempts(page_url, None)
    body, used, _err = _fetch_playlist(hls_url, attempts)
    if not body:
        return False, None
    text = body.decode("utf-8", errors="replace")
    try:
        _playlist, segment = _resolve_current_segment(
            text, hls_url, used or (attempts[0] if attempts else {})
        )
    except Exception:
        return False, None
    if not segment:
        return False, None
    data, _, _ = _http_get(segment, used or {}, min(MAX_SEGMENT_BYTES, 256 * 1024))
    if not data:
        return False, None
    return True, segment


def is_ad_hls_url(url: str) -> bool:
    from camera_hunter.engine.classifier import is_ad_or_tracking

    return is_ad_or_tracking(url)


def _finish(result: HlsCaptureResult, print_report: bool) -> HlsCaptureResult:
    if print_report:
        print(result.report(), flush=True)
    return result


def _header_attempts(page_url: str | None, cookie: str | None) -> list[dict[str, str]]:
    origin = ""
    referer = (page_url or "").strip()
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if not referer.endswith("/"):
                referer = referer
    attempts: list[dict[str, str]] = []
    if referer:
        headers = {
            "User-Agent": BROWSER_UA,
            "Accept": "*/*",
            "Referer": referer,
        }
        if origin:
            headers["Origin"] = origin
        if cookie:
            headers["Cookie"] = cookie
        attempts.append(headers)
    ua = {"User-Agent": BROWSER_UA, "Accept": "*/*"}
    if cookie:
        ua["Cookie"] = cookie
    attempts.append(ua)
    attempts.append({})
    return attempts


def _fetch_playlist(
    url: str, attempts: list[dict[str, str]]
) -> tuple[bytes | None, dict[str, str], str | None]:
    errors: list[str] = []
    for headers in attempts:
        body, status, err = _http_get(url, headers, MAX_PLAYLIST_BYTES)
        if body and b"#EXTM3U" in body:
            return body, dict(headers), None
        label = ",".join(sorted(headers)) or "no-headers"
        errors.append(f"{label} -> HTTP {status or '-'} {err or ''}".strip())
    return None, {}, "HLS playlist nem kérhető le. Próbált headerek: " + "; ".join(errors)


def _http_get(
    url: str, headers: dict[str, str], max_bytes: int
) -> tuple[bytes | None, int | None, str | None]:
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            status = getattr(resp, "status", 200)
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None, status, f"túl nagy válasz (>{max_bytes} byte)"
            return data, status, None
    except HTTPError as exc:
        snippet = b""
        try:
            snippet = exc.read(200)
        except Exception:
            pass
        return None, exc.code, f"HTTP {exc.code} {snippet[:80]!r}"
    except URLError as exc:
        return None, None, str(exc.reason if getattr(exc, "reason", None) else exc)
    except Exception as exc:
        return None, None, str(exc)


def _resolve_current_segment(
    playlist_text: str,
    playlist_url: str,
    headers: dict[str, str],
) -> tuple[str, str | None]:
    variants, media = _parse_playlist(playlist_text, playlist_url)
    current_url = playlist_url
    if variants and not media:
        variant_url = variants[-1]
        body, _, err = _http_get(variant_url, headers, MAX_PLAYLIST_BYTES)
        if not body:
            raise RuntimeError(f"variant playlist hiba: {err}")
        current_url = variant_url
        current_text = body.decode("utf-8", errors="replace")
        variants, media = _parse_playlist(current_text, current_url)
    if not media:
        return current_url, None
    return current_url, media[-1]


def _parse_playlist(text: str, base_url: str) -> tuple[list[str], list[str]]:
    variants: list[str] = []
    media: list[str] = []
    pending_variant = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-STREAM-INF"):
            pending_variant = True
            continue
        map_uri = _ext_x_map_uri(line)
        if map_uri:
            media.append(urljoin(base_url, map_uri))
            continue
        if line.startswith("#"):
            continue
        abs_url = urljoin(base_url, line)
        if pending_variant:
            variants.append(abs_url)
            pending_variant = False
        else:
            media.append(abs_url)
    return variants, media


def _ext_x_map_uri(line: str) -> str | None:
    if not line.startswith("#EXT-X-MAP"):
        return None
    match = re.search(r'URI="([^"]+)"', line, re.IGNORECASE)
    return match.group(1) if match else None


def _ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def _ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def _has_video_stream(path: Path) -> bool:
    probe = _ffprobe_bin()
    if not probe:
        return False
    cmd = [
        probe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_type,codec_name,width,height",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return False
    streams = data.get("streams") or []
    return any(s.get("codec_type") == "video" for s in streams)


def _extract_jpeg(segment_path: Path, frame_path: Path) -> bool:
    ffmpeg = _ffmpeg_bin()
    if not ffmpeg:
        return False
    if frame_path.exists():
        frame_path.unlink()
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(segment_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(frame_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and frame_path.is_file() and frame_path.stat().st_size > 0


def _is_jpeg(path: Path) -> bool:
    try:
        data = path.read_bytes()[:3]
    except OSError:
        return False
    return data == b"\xff\xd8\xff"
