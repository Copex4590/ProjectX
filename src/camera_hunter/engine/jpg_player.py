"""Continuous JPEG camera viewer. Independent of the HLS QMediaPlayer path.

Polls a discovered JPEG URL, hashes bodies, and only treats a changed
image as a new frame. Interval follows observed change timing.
"""

from __future__ import annotations

import hashlib
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from camera_hunter.engine.hls_diag import diag as hls_diag

MIN_POLL_S = 0.5
MAX_POLL_S = 8.0
DEFAULT_POLL_S = 1.0
FETCH_TIMEOUT_S = 15.0
JPEG_MAGIC = b"\xff\xd8"


def jpg_diag(step: str, **fields: object) -> None:
    extra = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    line = f"[{step}]"
    if extra:
        line = f"{line} {extra}"
    print(line, flush=True)
    hls_diag(step, **fields)


def looks_like_jpeg_feed(url: str) -> bool:
    """True for a URL that is itself a JPEG camera resource, not a page."""
    raw = (url or "").strip()
    if not raw.lower().startswith(("http://", "https://")):
        return False
    path = urlparse(raw).path.lower()
    if path.endswith((".jpg", ".jpeg")):
        return True
    return "/jpeg/" in path or "/jpg/" in path


def is_jpeg_payload(body: bytes) -> bool:
    return bool(body) and body[:2] == JPEG_MAGIC


def jpeg_body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def format_refresh_hu(seconds: float) -> str:
    return f"{seconds:.1f}".replace(".", ",")


def next_poll_interval_s(
    *,
    change_intervals: list[float],
    unchanged_streak: int,
    last_fetch_duration: float,
    failed: bool = False,
    previous: float = DEFAULT_POLL_S,
) -> float:
    """Adaptive poll: follow real change cadence, backoff on identical/failed frames."""
    if failed:
        return min(MAX_POLL_S, max(previous * 1.5, 2.0))
    if change_intervals:
        ordered = sorted(change_intervals)
        base = ordered[len(ordered) // 2]
    else:
        base = DEFAULT_POLL_S
    if unchanged_streak > 0:
        base = min(MAX_POLL_S, base * (1.0 + 0.25 * min(unchanged_streak, 8)))
    floor = max(MIN_POLL_S, last_fetch_duration + 0.05)
    return min(MAX_POLL_S, max(base, floor))


def median_change_interval_s(change_intervals: list[float]) -> float | None:
    if not change_intervals:
        return None
    ordered = sorted(change_intervals)
    return ordered[len(ordered) // 2]


def jpeg_status_text(refresh_s: float | None = None, *, live_label: str = "🟢 ÉLŐ — JPEG") -> str:
    if refresh_s is None:
        return live_label
    return f"{live_label}  ·  Frissítés: {format_refresh_hu(refresh_s)} s"


def _http_get_jpeg(url: str, headers: dict[str, str]) -> tuple[int, bytes, str]:
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
            return int(resp.status), bytes(resp.read(8_000_000) or b""), ""
    except HTTPError as exc:
        body = b""
        try:
            body = bytes(exc.read(4096) or b"")
        except Exception:
            pass
        return int(exc.code), body, str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        return 0, b"", str(exc)


class _JpegBridge(QObject):
    fetched = Signal(object)


class JpegLivePlayer(QObject):
    """Fetch a JPEG URL on a timer and paint it on a QLabel. Never blocks the GUI."""

    live_started = Signal()
    frame_changed = Signal(bytes, float)
    frame_unchanged = Signal()
    fetch_failed = Signal(str)
    reconnecting = Signal()
    refresh_interval = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel()
        self._label.setObjectName("jpegLiveView")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setScaledContents(False)
        self._label.setStyleSheet("background-color: #0a0e16;")
        self._label.hide()
        self._url = ""
        self._headers: dict[str, str] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)
        self._bridge = _JpegBridge(self)
        self._bridge.fetched.connect(self._on_fetched)
        self._inflight = False
        self._generation = 0
        self._hash = ""
        self._started = False
        self._fail_streak = 0
        self._unchanged_streak = 0
        self._change_intervals: list[float] = []
        self._last_change_at: float | None = None
        self._last_success_at: float = 0.0
        self._last_fetch_duration = 0.0
        self._poll_s = DEFAULT_POLL_S
        self._last_reconnect_at = 0.0
        self._play_started_at = 0.0

    @property
    def widget(self) -> QWidget:
        return self._label

    @property
    def url(self) -> str:
        return self._url

    @property
    def has_image(self) -> bool:
        return self._started

    @property
    def last_success_at(self) -> float:
        return self._last_success_at

    @property
    def poll_interval_s(self) -> float:
        return self._poll_s

    def observed_refresh_s(self) -> float | None:
        return median_change_interval_s(self._change_intervals)

    def is_healthy(self) -> bool:
        if not self._url:
            return False
        now = time.monotonic()
        if self._last_success_at > 0:
            return (now - self._last_success_at) < 25.0
        if self._play_started_at <= 0:
            return False
        return (now - self._play_started_at) < 25.0

    def play(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.stop()
        self._url = (url or "").strip()
        self._headers = dict(headers or {})
        self._headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        self._generation += 1
        self._hash = ""
        self._started = False
        self._fail_streak = 0
        self._unchanged_streak = 0
        self._change_intervals = []
        self._last_change_at = None
        self._last_success_at = 0.0
        self._poll_s = DEFAULT_POLL_S
        self._play_started_at = time.monotonic()
        jpg_diag("jpg_player_started", url=self._url[:160])
        self._timer.start(0)

    def stop(self) -> None:
        self._generation += 1
        self._timer.stop()
        self._url = ""
        self._inflight = False
        self._started = False
        self._hash = ""

    @Slot()
    def _tick(self) -> None:
        if not self._url or self._inflight:
            return
        self._inflight = True
        gen = self._generation
        url = self._url
        headers = dict(self._headers)
        threading.Thread(
            target=self._fetch_thread,
            args=(gen, url, headers),
            daemon=True,
        ).start()

    def _fetch_thread(self, gen: int, url: str, headers: dict[str, str]) -> None:
        t0 = time.monotonic()
        status, body, err = _http_get_jpeg(url, headers)
        duration = time.monotonic() - t0
        self._bridge.fetched.emit(
            {
                "gen": gen,
                "status": status,
                "body": body,
                "err": err,
                "duration": duration,
            }
        )

    @Slot(object)
    def _on_fetched(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        self._inflight = False
        if int(data.get("gen") or 0) != self._generation or not self._url:
            return
        status = int(data.get("status") or 0)
        body = data.get("body") if isinstance(data.get("body"), bytes) else b""
        err = str(data.get("err") or "")
        self._last_fetch_duration = float(data.get("duration") or 0.0)
        now = time.monotonic()

        if status != 200 or not is_jpeg_payload(body):
            self._fail_streak += 1
            reason = err or f"http_{status}" or "not_jpeg"
            jpg_diag("jpg_frame_failed", status=status, reason=reason[:80], fail=self._fail_streak)
            self.fetch_failed.emit(reason)
            if (now - self._last_reconnect_at) > 0.2:
                self._last_reconnect_at = now
                jpg_diag("jpg_reconnect", fail=self._fail_streak)
                self.reconnecting.emit()
            self._poll_s = next_poll_interval_s(
                change_intervals=self._change_intervals,
                unchanged_streak=self._unchanged_streak,
                last_fetch_duration=self._last_fetch_duration,
                failed=True,
                previous=self._poll_s,
            )
            self._timer.start(int(self._poll_s * 1000))
            return

        digest = jpeg_body_hash(body)
        self._last_success_at = now
        jpg_diag("jpg_frame_received", bytes=len(body), hash=digest[:12])
        if digest == self._hash:
            self._unchanged_streak += 1
            jpg_diag("jpg_frame_unchanged", streak=self._unchanged_streak, hash=digest[:12])
            self.frame_unchanged.emit()
            self._poll_s = next_poll_interval_s(
                change_intervals=self._change_intervals,
                unchanged_streak=self._unchanged_streak,
                last_fetch_duration=self._last_fetch_duration,
                previous=self._poll_s,
            )
            self._timer.start(int(self._poll_s * 1000))
            return

        if self._last_change_at is not None:
            dt = now - self._last_change_at
            if dt >= 0.05:
                self._change_intervals.append(dt)
                self._change_intervals = self._change_intervals[-8:]
                observed = median_change_interval_s(self._change_intervals)
                if observed is not None:
                    self.refresh_interval.emit(observed)
        self._last_change_at = now
        self._hash = digest
        self._unchanged_streak = 0
        self._fail_streak = 0
        jpg_diag("jpg_frame_changed", bytes=len(body), hash=digest[:12])
        self._paint(body)
        self.frame_changed.emit(body, self._poll_s)
        if not self._started:
            self._started = True
            self.live_started.emit()
        self._poll_s = next_poll_interval_s(
            change_intervals=self._change_intervals,
            unchanged_streak=0,
            last_fetch_duration=self._last_fetch_duration,
            previous=self._poll_s,
        )
        self._timer.start(int(self._poll_s * 1000))

    def _paint(self, body: bytes) -> None:
        image = QImage.fromData(body, "JPEG")
        if image.isNull():
            return
        pix = QPixmap.fromImage(image)
        if pix.isNull():
            return
        size = self._label.size()
        if size.width() > 2 and size.height() > 2:
            pix = pix.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._label.setPixmap(pix)
