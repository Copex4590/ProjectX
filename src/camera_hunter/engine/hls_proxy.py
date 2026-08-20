"""Local HLS reverse proxy so QMediaPlayer can play tokenized M3U8 with headers.

QMediaPlayer/FFmpeg cannot set Referer/User-Agent. This process binds 127.0.0.1,
fetches playlists and segments with the headers that already work in capture_hls,
and rewrites playlist URIs to localhost so the player never talks to the CDN.
"""

from __future__ import annotations

import errno
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from camera_hunter.engine.hls_diag import diag, diag_exc

MAX_PLAYLIST_BYTES = 2 * 1024 * 1024
MAX_SEGMENT_BYTES = 20 * 1024 * 1024
FETCH_TIMEOUT = 20
_URI_RE = re.compile(r'URI="([^"]+)"', re.IGNORECASE)
_FILE_SUFFIX_RE = re.compile(r"/file(\.[A-Za-z0-9]+)?$")
_PROXY_EXTS = (".m3u8", ".m3u", ".ts", ".m4s", ".mp4", ".aac", ".key")


def rewrite_playlist_body(text: str, base_url: str, proxy_root: str) -> str:
    """Rewrite media, variant and EXT-X-MAP URIs to pass through the local proxy."""
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append(raw)
            continue
        if stripped.startswith("#"):
            lines.append(_URI_RE.sub(lambda m: _rewrite_uri_attr(m, base_url, proxy_root), raw))
            continue
        abs_url = urljoin(base_url, stripped)
        lines.append(_proxied(proxy_root, abs_url))
    return "\n".join(lines) + "\n"


def select_variant_url(text: str, base_url: str) -> str | None:
    """Last #EXT-X-STREAM-INF URI, or None when this is already a media playlist."""
    last: str | None = None
    pending = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-STREAM-INF"):
            pending = True
            continue
        if pending and line and not line.startswith("#"):
            last = urljoin(base_url, line)
            pending = False
    return last


def decode_proxy_target(path: str) -> str:
    """Recover the upstream URL from a local /u/.../file.ext proxy path."""
    parsed = urlparse(path)
    rest = parsed.path or path
    if rest.startswith("/u/"):
        rest = rest[3:]
    rest = _FILE_SUFFIX_RE.sub("", rest)
    return unquote(rest)


def _rewrite_uri_attr(match: re.Match[str], base_url: str, proxy_root: str) -> str:
    abs_url = urljoin(base_url, match.group(1))
    return f'URI="{_proxied(proxy_root, abs_url)}"'


def _proxy_ext(abs_url: str) -> str:
    path = (urlparse(abs_url).path or "").lower()
    for ext in _PROXY_EXTS:
        if path.endswith(ext):
            return ext
    return ".bin"


def _proxied(proxy_root: str, abs_url: str) -> str:
    # /file.ext is the last path component so QMediaPlayer/FFmpeg does not
    # probe EarthCam's /15041.flv/... URLs as FLV.
    return f"{proxy_root.rstrip('/')}/u/{quote(abs_url, safe='')}/file{_proxy_ext(abs_url)}"


def _http_get(url: str, headers: dict[str, str], max_bytes: int) -> tuple[bytes | None, str, str | None]:
    if not url.startswith(("http://", "https://")):
        diag("proxy_fetch_skip", url=url, reason="unsupported url")
        return None, "", "unsupported url"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            status = getattr(resp, "status", 200)
            ctype = str(resp.headers.get("Content-Type") or "")
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                diag("proxy_fetch_too_large", url=url, http_status=status, content_type=ctype)
                return None, ctype, "too large"
            diag(
                "proxy_fetch_ok",
                url=url,
                http_status=status,
                content_type=ctype,
                bytes=len(data),
                extm3u=b"#EXTM3U" in data[:64],
            )
            return data, ctype, None
    except HTTPError as exc:
        diag("proxy_fetch_http_error", url=url, http_status=exc.code)
        return None, "", f"HTTP {exc.code}"
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc) or exc)
        diag("proxy_fetch_url_error", url=url, error=reason)
        return None, "", reason
    except Exception as exc:
        diag("proxy_fetch_error", url=url, error=str(exc))
        return None, "", str(exc)


class HlsProxy:
    """One 127.0.0.1 server. Upstream URL/headers can be replaced without a restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._upstream = ""
        self._headers: dict[str, str] = {}
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def playlist_url(self) -> str:
        httpd = self._httpd
        if httpd is None:
            return ""
        host, port = httpd.server_address[:2]
        return f"http://{host}:{port}/live.m3u8"

    def start(self) -> str:
        if self._httpd is not None:
            return self.playlist_url
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _HlsProxyHandler)
        httpd.proxy = self  # type: ignore[attr-defined]
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, name="hls-proxy", daemon=True)
        self._thread.start()
        diag("proxy_started", playlist_url=self.playlist_url)
        return self.playlist_url

    def stop(self) -> None:
        httpd = self._httpd
        self._httpd = None
        if httpd is not None:
            httpd.shutdown()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=3)
        with self._lock:
            self._upstream = ""
            self._headers = {}

    def set_upstream(self, url: str, headers: dict[str, str] | None = None) -> str:
        with self._lock:
            self._upstream = (url or "").strip()
            self._headers = dict(headers or {})
        if self._httpd is None:
            self.start()
        diag(
            "proxy_upstream",
            upstream=self._upstream,
            playlist_url=self.playlist_url,
            header_keys=sorted(self._headers),
            referer=self._headers.get("Referer"),
        )
        return self.playlist_url

    def fetch(self, url: str, *, resolve_master: bool = False) -> tuple[bytes, str]:
        with self._lock:
            headers = dict(self._headers)
            upstream = self._upstream
        target = url or upstream
        if not target:
            raise RuntimeError("no upstream")
        parsed = urlparse(target)
        path = (parsed.path or "").lower()
        is_playlist = path.endswith(".m3u8") or target.rstrip("/").endswith("live.m3u8")
        limit = MAX_PLAYLIST_BYTES if is_playlist else MAX_SEGMENT_BYTES
        body, ctype, err = _http_get(target, headers, limit)
        if body is None:
            diag("proxy_fetch_failed", url=target, error=err)
            raise RuntimeError(err or "fetch failed")
        if body.lstrip().startswith(b"#EXTM3U"):
            text = body.decode("utf-8", errors="replace")
            if resolve_master:
                variant = select_variant_url(text, target)
                if variant:
                    diag("proxy_flatten_master", master=target, variant=variant)
                    return self.fetch(variant, resolve_master=False)
            rewritten = rewrite_playlist_body(text, target, self._root())
            return rewritten.encode("utf-8"), "application/vnd.apple.mpegurl"
        return body, ctype or "application/octet-stream"

    def fetch_live_playlist(self) -> tuple[bytes, str]:
        with self._lock:
            upstream = self._upstream
        return self.fetch(upstream, resolve_master=True)

    def _root(self) -> str:
        httpd = self._httpd
        if httpd is None:
            return ""
        host, port = httpd.server_address[:2]
        return f"http://{host}:{port}"


class _HlsProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        proxy: HlsProxy = self.server.proxy  # type: ignore[attr-defined]
        try:
            path = urlparse(self.path).path
            if path in {"/live.m3u8", "/", "/live.m3u8/"}:
                diag("proxy_request_playlist", path=path, client=self.client_address[0])
                body, ctype = proxy.fetch_live_playlist()
            elif path.startswith("/u/"):
                target = decode_proxy_target(path)
                diag("proxy_request_upstream", path=path[:80], target=target)
                body, ctype = proxy.fetch(target)
            else:
                diag("proxy_request_404", path=path)
                self.send_error(404)
                return
        except Exception as exc:
            diag_exc("proxy_request_502", path=self.path, error=str(exc))
            self.send_error(502)
            return
        diag("proxy_response_200", path=urlparse(self.path).path, content_type=ctype, bytes=len(body))
        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError) as exc:
            diag(
                "proxy_client_disconnected",
                path=urlparse(self.path).path,
                error=type(exc).__name__,
            )
        except OSError as exc:
            if getattr(exc, "errno", None) in (
                errno.EPIPE,
                errno.ECONNRESET,
                errno.ECONNABORTED,
            ):
                diag(
                    "proxy_client_disconnected",
                    path=urlparse(self.path).path,
                    error=str(exc),
                )
            else:
                diag_exc("proxy_response_write_failed", path=self.path, error=str(exc))
