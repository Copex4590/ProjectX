from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, replace

from urllib.parse import urlparse

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from camera_hunter.engine.cdp_monitor import CdpNetworkMonitor
from camera_hunter.engine.classifier import (
    ObservedRequest,
    _strip_cache_bust,
    classify_url,
    is_ad_or_tracking,
    is_listing_page,
    jpeg_camera_feed_score,
    merge_observations,
    should_classify_network_event,
    should_replace_jpeg_candidate,
)
from camera_hunter.engine.earthcam_consent import EARTHCAM_CONSENT_JS, install_consent_script
from camera_hunter.engine.providers.earthcam import (
    EarthCamExpiryGuard,
    applies as earthcam_applies,
    filter_hls_candidate,
    is_ectv_player_hint,
    safe_log_fields,
)
from camera_hunter.engine.hls_capture import (
    HlsCaptureResult,
    capture_hls,
    canonical_request_headers,
    cookie_names_from_header,
    hls_playback_headers,
    merge_hls_headers,
    normalize_discovered_hls_url,
)
from camera_hunter.engine.hls_diag import diag
from camera_hunter.engine.hls_player import HlsPlayer
from camera_hunter.engine.jpg_player import (
    JpegLivePlayer,
    jpeg_status_text,
    jpg_diag,
    looks_like_jpeg_feed,
)
from camera_hunter.engine.session import (
    HEALTH_CHECK_INTERVAL_MS,
    STATUS_CHOOSE_CAMERA,
    STATUS_LOADING,
    STATUS_RECONNECTING,
    HunterSession,
    HunterState,
    is_promo_or_filler_page,
    is_redirect_navigation,
    looks_like_camera_page,
    normalize_session_url,
    visible_navigation_action,
)
from camera_hunter.models import CameraSource, SourceType
from camera_hunter.models.camera_result import CameraResult, CameraResultType, camera_result_from_sources

# Wait after loadFinished for late media / XHR / HLS playlists.
DEFAULT_SETTLE_MS = 4500
MAX_LOAD_MS = 25000
INTERACTIVE_MAX_MS = 15 * 60 * 1000


class _CaptureBridge(QObject):
    finished = Signal(object, object, int)  # CameraSource, HlsCaptureResult, generation


def _collect_page_media_urls_js(*, prefetch: bool) -> str:
    """JS: gather img/srcset/icon/og:image/video URLs; optionally force Chromium to fetch them."""
    prefetch_block = (
        """
  urls.forEach((u) => {
    try { const img = new Image(); img.src = u; } catch (e) {}
  });
"""
        if prefetch
        else ""
    )
    return f"""
(function () {{
  const urls = [];
  const seen = {{}};
  const add = (u) => {{
    if (!u) return;
    try {{
      const abs = new URL(String(u), document.baseURI).href;
      if ((abs.startsWith("http://") || abs.startsWith("https://")) && !seen[abs]) {{
        seen[abs] = true;
        urls.push(abs);
      }}
    }} catch (e) {{}}
  }};
  const addSrcset = (ss) => {{
    if (!ss) return;
    String(ss).split(",").forEach((part) => add(part.trim().split(/\\s+/)[0]));
  }};
  try {{
    document.querySelectorAll("img").forEach((el) => {{
      add(el.currentSrc); add(el.src); addSrcset(el.srcset);
    }});
  }} catch (e) {{}}
  try {{
    document.querySelectorAll("source").forEach((el) => {{
      add(el.src); addSrcset(el.srcset);
    }});
  }} catch (e) {{}}
  try {{
    document.querySelectorAll("video, audio").forEach((el) => {{
      add(el.currentSrc); add(el.src);
    }});
  }} catch (e) {{}}
  try {{
    document.querySelectorAll("link[rel]").forEach((el) => {{
      const rel = String(el.rel || "").toLowerCase();
      const as = String(el.as || "").toLowerCase();
      if (rel.includes("icon") || rel === "image_src" || (rel === "preload" && as === "image")) {{
        add(el.href);
      }}
    }});
  }} catch (e) {{}}
  try {{
    document.querySelectorAll("meta[property], meta[name]").forEach((el) => {{
      const key = String(el.getAttribute("property") || el.getAttribute("name") || "").toLowerCase();
      if (key === "og:image" || key === "og:image:url" || key === "twitter:image") {{
        add(el.getAttribute("content"));
      }}
    }});
  }} catch (e) {{}}
  {prefetch_block}
  return urls;
}})();
"""


_PREFETCH_JS = _collect_page_media_urls_js(prefetch=True)

_STREAM_PROBE_JS = r"""
(function () {
  const urls = new Set();
  const add = (u) => {
    if (!u) return;
    try {
      const abs = String(u).trim();
      if (!abs) return;
      if (!/^https?:/i.test(abs)) return;
      if (/\.(ts|m4s|cmfv|cmfa)(\?|$)/i.test(abs)) return;
      urls.add(abs);
    } catch (e) {}
  };
  const addM3u8 = (raw) => {
    if (!raw) return;
    let s = String(raw).trim().replace(/^['"]|['"]$/g, "");
    s = s.replace("livee.", "live.");
    add(s);
    try { add(new URL(s, document.baseURI).href); } catch (e) {}
    if (!/^https?:/i.test(s)) {
      add("https://hd-auth.skylinewebcams.com/" + s.replace(/^\/+/, ""));
    }
  };
  try {
    if (typeof json_base !== "undefined" && json_base && json_base.cam) {
      Object.keys(json_base.cam).forEach((k) => {
        const c = json_base.cam[k] || {};
        const domain = c.html5_streamingdomain || c.streamingdomain || "";
        const path = c.html5_streampath || c.streampath || "";
        if (domain && path) add(domain + path);
        if (c.liveimage) add(c.liveimage);
      });
    }
  } catch (e) {}
  try {
    if (typeof player !== "undefined" && player && player.options) {
      addM3u8(player.options.source);
      (player.options.sources || []).forEach((x) => addM3u8((x && x.source) || x));
    }
  } catch (e) {}
  try {
    const html = document.documentElement.innerHTML;
    const reAbs = /https?:[^"'\\\s<>]+?\.m3u8(?:\?[^"'\\\s<>]*)?/gi;
    let m;
    while ((m = reAbs.exec(html))) add(m[0]);
    const reSrc = /source\s*:\s*['"]([^'"]+\.m3u8[^'"]*)['"]/gi;
    while ((m = reSrc.exec(html))) addM3u8(m[1]);
    const reLive = /livee?\.m3u8\?[^"'\\\s<>]+/gi;
    while ((m = reLive.exec(html))) addM3u8(m[0]);
  } catch (e) {}
  try {
    document.querySelectorAll("video, source").forEach((v) => {
      add(v.currentSrc || ""); add(v.src || "");
    });
  } catch (e) {}
  try {
    performance.getEntriesByType("resource").forEach((e) => {
      if (e && e.name && /\.m3u8/i.test(e.name)) add(e.name);
    });
  } catch (e) {}
  urls.forEach((u) => {
    try {
      fetch(u, {method: "GET", mode: "cors", credentials: "omit", cache: "no-store"})
        .catch(function () {
          try { fetch(u, {mode: "no-cors", cache: "no-store"}).catch(function () {}); } catch (e2) {}
        });
    } catch (e) {}
  });
  return Array.from(urls);
})();
"""

_SCAN_JS = r"""
(function () {
  const out = {
    images: [],
    videos: [],
    sources: [],
    iframes: [],
    performance: [],
    mediaSource: false,
    websockets: []
  };

  try {
    document.querySelectorAll("img").forEach((el) => {
      if (el.currentSrc) out.images.push(el.currentSrc);
      if (el.src) out.images.push(el.src);
      if (el.srcset) {
        el.srcset.split(",").forEach((part) => {
          const u = part.trim().split(/\s+/)[0];
          if (u) out.images.push(new URL(u, document.baseURI).href);
        });
      }
    });
  } catch (e) {}

  try {
    document.querySelectorAll("video").forEach((v) => {
      if (v.currentSrc) out.videos.push(v.currentSrc);
      if (v.src) out.videos.push(v.src);
      v.querySelectorAll("source[src]").forEach((s) => {
        out.sources.push({url: s.src, type: s.type || null});
      });
    });
  } catch (e) {}

  try {
    document.querySelectorAll("source[src]").forEach((s) => {
      out.sources.push({url: s.src, type: s.type || null});
    });
  } catch (e) {}

  try {
    document.querySelectorAll("link[rel]").forEach((el) => {
      const rel = String(el.rel || "").toLowerCase();
      if (rel.includes("icon") || rel === "image_src") {
        if (el.href) out.images.push(el.href);
      }
    });
  } catch (e) {}

  try {
    document.querySelectorAll("meta[property], meta[name]").forEach((el) => {
      const key = String(el.getAttribute("property") || el.getAttribute("name") || "").toLowerCase();
      if (key === "og:image" || key === "og:image:url" || key === "twitter:image") {
        const u = el.getAttribute("content");
        if (u) out.images.push(u);
      }
    });
  } catch (e) {}

  try {
    document.querySelectorAll("iframe[src]").forEach((f) => {
      out.iframes.push(f.src);
    });
  } catch (e) {}

  try {
    if (window.performance && performance.getEntriesByType) {
      performance.getEntriesByType("resource").forEach((e) => {
        out.performance.push({
          name: e.name,
          initiatorType: e.initiatorType || null
        });
      });
    }
  } catch (e) {}

  try {
    out.mediaSource = typeof MediaSource !== "undefined";
  } catch (e) {}

  return JSON.stringify(out);
})();
"""



_CAMERA_LOCKED_STATES = {
    HunterState.CAMERA_LOADING,
    HunterState.DISCOVERY_ACTIVE,
    HunterState.VALIDATING_HLS,
    HunterState.RECONNECTING,
    HunterState.LIVE,
}


def _bytes_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    data = getattr(value, "data", None)
    if callable(data):
        try:
            return bytes(data()).decode("utf-8", errors="replace")
        except Exception:
            pass
    return str(value)


def _info_request_headers(info: QWebEngineUrlRequestInfo) -> dict[str, str]:
    raw: dict[str, str] = {}
    try:
        headers = info.httpHeaders()
    except Exception:
        return raw
    for key, value in headers.items():
        raw[_bytes_text(key)] = _bytes_text(value)
    return canonical_request_headers(raw)


def _cookie_key(cookie: QNetworkCookie) -> tuple[str, str, str]:
    return (
        str(cookie.domain() or ""),
        str(cookie.path() or "/"),
        _bytes_text(cookie.name()),
    )


class _NetworkInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, engine: DiscoveryEngine) -> None:
        super().__init__()
        self._engine = engine

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:  # noqa: N802
        try:
            if not self._engine.is_busy:
                return
            url = bytes(info.requestUrl().toEncoded()).decode("utf-8", errors="replace")
            rtype = (
                str(info.resourceType().name)
                if hasattr(info.resourceType(), "name")
                else str(info.resourceType())
            )
            gen = int(self._engine.session_id)
            if not should_classify_network_event(
                discovery_enabled=self._engine.discovery_enabled,
                url=url,
                mime_type=None,
                session_id=gen,
                current_generation=gen,
            ):
                return
            headers_json = ""
            first_party = ""
            lower = url.lower()
            if ".m3u8" in lower or "mpegurl" in lower or ".mpd" in lower:
                headers_json = json.dumps(_info_request_headers(info))
                first_party = info.firstPartyUrl().toString()
            QMetaObject.invokeMethod(
                self._engine,
                "_on_network_request",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, url),
                Q_ARG(str, rtype or ""),
                Q_ARG(int, gen),
                Q_ARG(str, headers_json),
                Q_ARG(str, first_party),
            )
        except Exception:
            pass


class _HunterPage(QWebEnginePage):
    """Keep popups/ads/player windows in-process so CDP can follow them."""

    def __init__(self, profile: QWebEngineProfile, engine: DiscoveryEngine) -> None:
        super().__init__(profile, engine)
        self._engine = engine

    def createWindow(self, _type):  # noqa: N802
        return self._engine._create_popup_page()

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):  # noqa: N802
        if not is_main_frame:
            return True
        return self._engine._allow_page_navigation(self, url.toString(), nav_type)


@dataclass
class DiscoveryResult:
    page_url: str
    sources: list[CameraSource] = field(default_factory=list)
    error: str | None = None
    timed_out: bool = False
    navigation_chain: list[str] = field(default_factory=list)
    interactive: bool = False
    camera_result: CameraResult | None = None

    @property
    def direct_sources(self) -> list[CameraSource]:
        return [s for s in self.sources if s.is_direct_camera()]

    @property
    def thumbnails(self) -> list[CameraSource]:
        return [s for s in self.sources if s.is_thumbnail()]

    @property
    def camera_hits(self) -> list[CameraSource]:
        return [s for s in self.sources if s.is_camera_hit()]


class DiscoveryEngine(QObject):
    """Chromium loader + network discovery. Interactive mode follows clicks."""

    finished = Signal(object)  # DiscoveryResult
    status = Signal(str)
    source_found = Signal(object)  # CameraSource
    navigation = Signal(str, int)  # url, index
    state_changed = Signal(str)
    overlay_changed = Signal(bool, str)  # visible, message
    live_ready = Signal(object)  # CameraResult
    live_frame = Signal(str)  # JPEG path from optional capture_hls snapshot

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        settle_ms: int = DEFAULT_SETTLE_MS,
        max_load_ms: int = MAX_LOAD_MS,
        show_browser: bool = False,
        headless: bool = False,
    ) -> None:
        super().__init__(parent)
        self._settle_ms = settle_ms
        self._max_load_ms = max_load_ms
        self._show_browser = show_browser
        self._headless = bool(headless)
        self._busy = False
        self._interactive = False
        self._page_url = ""
        self._current_url = ""
        self._nav_chain: list[str] = []
        self._observations: list[ObservedRequest] = []
        self._live_sources: dict[tuple[str, SourceType], CameraSource] = {}
        self._popup_views: list[QWebEngineView] = []
        self._worker_view: QWebEngineView | None = None
        self._session = HunterSession()
        self._url_session: dict[str, int] = {}
        self._validated: CameraResult | None = None
        self._live_frame_path: str | None = None
        self._live_hls_url: str | None = None
        self._live_jpeg_url: str | None = None
        self._live_headers: dict[str, str] = {}
        self._hls_request_headers: dict[str, dict[str, str]] = {}
        self._cookie_jar: dict[tuple[str, str, str], QNetworkCookie] = {}
        self._live_player: HlsPlayer | None = None
        self._jpeg_player: JpegLivePlayer | None = None
        self._pending_live_src: CameraSource | None = None
        self._pending_jpeg_src: CameraSource | None = None
        self._jpeg_score: int | None = None
        self._jpeg_request_hits: dict[str, int] = {}
        self._hls_failed_urls: set[str] = set()
        self._capture_inflight = False
        self._earthcam_expiry = EarthCamExpiryGuard()
        self._capture_bridge = _CaptureBridge(self)
        self._capture_bridge.finished.connect(
            self._on_hls_capture_finished, Qt.ConnectionType.QueuedConnection
        )

        self._profile = QWebEngineProfile(f"camera-hunter-{id(self)}", self)
        self._profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self._interceptor = _NetworkInterceptor(self)
        self._profile.setUrlRequestInterceptor(self._interceptor)
        install_consent_script(self._profile)
        store = self._profile.cookieStore()
        store.cookieAdded.connect(self._on_cookie_added)
        store.cookieRemoved.connect(self._on_cookie_removed)
        store.loadAllCookies()

        self._host = QWidget()
        self._host.resize(1280, 720)
        self._host.setWindowTitle("Camera Hunter — kamera kiválasztása")
        self._view = QWebEngineView(self._host)
        self._view.resize(1280, 720)
        page = _HunterPage(self._profile, self)
        self._view.setPage(page)
        self._apply_page_settings(page)
        self._wire_page(page)
        self._present_engine_host()

        self._cdp = CdpNetworkMonitor(self)
        self._cdp.response_captured.connect(self._on_cdp_response)
        self._cdp_wait_tries = 0
        QTimer.singleShot(150, self._cdp.start)

        self._settle_timer = QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.timeout.connect(self._on_settle)

        self._probe_timer = QTimer(self)
        self._probe_timer.setInterval(2000)
        self._probe_timer.timeout.connect(self._run_stream_probe)

        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog)

        self._health_timer = QTimer(self)
        self._health_timer.setInterval(HEALTH_CHECK_INTERVAL_MS)
        self._health_timer.timeout.connect(self._on_health_check)

    @property
    def headless(self) -> bool:
        return self._headless

    @property
    def is_busy(self) -> bool:
        return self._busy

    @property
    def is_interactive(self) -> bool:
        return self._interactive and self._busy

    @property
    def view(self) -> QWebEngineView:
        return self._view

    @property
    def state(self) -> HunterState:
        return self._session.state

    @property
    def session_id(self) -> int:
        return self._session.generation

    @property
    def discovery_enabled(self) -> bool:
        return self._session.discovery_enabled

    @property
    def live_frame_path(self) -> str | None:
        return self._live_frame_path

    def set_live_player(self, player: HlsPlayer | None) -> None:
        if self._live_player is not None:
            try:
                self._live_player.video_started.disconnect(self._on_player_video_started)
            except (RuntimeError, TypeError):
                pass
            failed = getattr(self._live_player, "playback_failed", None)
            if failed is not None:
                try:
                    failed.disconnect(self._on_player_playback_failed)
                except (RuntimeError, TypeError):
                    pass
        self._live_player = player
        if player is not None:
            player.video_started.connect(self._on_player_video_started)
            failed = getattr(player, "playback_failed", None)
            if failed is not None:
                failed.connect(self._on_player_playback_failed)
        diag("player_attached", attached=player is not None)

    def set_jpeg_player(self, player: JpegLivePlayer | None) -> None:
        if self._jpeg_player is not None:
            try:
                self._jpeg_player.live_started.disconnect(self._on_jpeg_live_started)
            except (RuntimeError, TypeError):
                pass
            try:
                self._jpeg_player.refresh_interval.disconnect(self._on_jpeg_refresh_interval)
            except (RuntimeError, TypeError):
                pass
        self._jpeg_player = player
        if player is not None:
            player.live_started.connect(self._on_jpeg_live_started)
            player.refresh_interval.connect(self._on_jpeg_refresh_interval)
        diag("jpeg_player_attached", attached=player is not None)

    def open_camera_in_background(self, url: str) -> None:
        """Load a camera page off the listing view so the user never sees the site."""
        self._open_camera_in_background(url)

    def embed_view(self, parent: QWidget) -> QWebEngineView:
        """Reparent the WebEngine into the GUI so the user can click a camera."""
        self._view.setParent(parent)
        self._host.hide()
        if not self._headless:
            self._view.show()
        return self._view

    def _apply_headless_chrome(self, widget: QWidget, *, top_level: bool) -> None:
        """Keep Chromium alive off-screen: no visible/focused window."""
        widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if not top_level:
            return
        widget.setWindowFlag(Qt.WindowType.Tool, True)
        widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        widget.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        widget.setWindowFlag(Qt.WindowType.BypassWindowManagerHint, True)

    def _present_engine_host(self) -> None:
        if self._headless:
            self._apply_headless_chrome(self._host, top_level=True)
            self._apply_headless_chrome(self._view, top_level=False)
            self._host.show()
            self._view.show()
            return
        if not self._show_browser:
            self._host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self._host.show()
        self._view.show()

    def _apply_page_settings(self, page: QWebEnginePage) -> None:
        settings = page.settings()
        attrs = settings.WebAttribute
        wanted = {
            "JavascriptEnabled": True,
            "LocalStorageEnabled": True,
            "AutoLoadImages": True,
            "PlaybackRequiresUserGesture": False,
            "JavascriptCanOpenWindows": True,
            "LocalContentCanAccessRemoteUrls": True,
            "AllowRunningInsecureContent": True,
            "PluginsEnabled": True,
            "WebGLEnabled": True,
        }
        for name, value in wanted.items():
            attr = getattr(attrs, name, None)
            if attr is not None:
                settings.setAttribute(attr, value)

    def _wire_page(self, page: QWebEnginePage) -> None:
        page.urlChanged.connect(self._on_url_changed)
        page.loadFinished.connect(self._on_load_finished)

    def _create_popup_page(self) -> QWebEnginePage | None:
        if self._session.state in _CAMERA_LOCKED_STATES:
            diag(
                "popup_blocked",
                reason="camera_locked",
                state=self._session.state.value,
                worker=self._worker_view is not None,
            )
            return None
        if self._session.state in {HunterState.MAP_SEARCH, HunterState.CAMERA_SELECTED}:
            self._session.note_camera_selected()
            self._emit_state()
            self.status.emit(STATUS_CHOOSE_CAMERA)
        worker = self._ensure_worker_view()
        diag(
            "popup_routed_to_worker",
            state=self._session.state.value,
            locked=bool(self._session.camera_session_url),
        )
        QTimer.singleShot(150, self._cdp.prepare_for_navigation)
        return worker.page()

    def _hide_engine_from_user(self, view: QWebEngineView) -> None:
        """Keep Chromium 'visible' so players start, but never show the site to the user."""
        parent = self._view.parentWidget() or self._host
        view.setParent(parent)
        size = self._view.size()
        if size.width() < 64 or size.height() < 64:
            view.resize(1280, 720)
        else:
            view.resize(size)
        if self._headless:
            self._apply_headless_chrome(view, top_level=False)
            view.show()
            return
        view.show()
        view.lower()
        self._view.raise_()

    def _page_kind(self, page: object) -> str:
        if page is self._view.page():
            return "listing"
        if self._worker_view is not None and page is self._worker_view.page():
            return "worker"
        for index, popup in enumerate(self._popup_views):
            if page is popup.page():
                return f"popup:{index}"
        return "unknown"

    def _allow_page_navigation(self, page: QWebEnginePage, url: str, nav_type: object) -> bool:
        kind = self._page_kind(page)
        if kind == "listing" or page is self._view.page():
            if (
                self._session.camera_session_url
                and self._session.state in _CAMERA_LOCKED_STATES
                and not (self._interactive and self._session.listing_url)
            ):
                return self._allow_worker_navigation(url, nav_type, source="main")
            return self._allow_visible_navigation(page, url)
        if kind == "worker":
            return self._allow_worker_navigation(url, nav_type, source="worker")
        if kind.startswith("popup"):
            if self._session.state in _CAMERA_LOCKED_STATES:
                diag(
                    "popup_navigation_ignored",
                    url=url,
                    page=kind,
                    reason="camera_session_locked",
                )
                return False
            return True
        return True

    def _allow_worker_navigation(self, url: str, nav_type: object, *, source: str) -> bool:
        url = (url or "").strip()
        nav_name = str(getattr(nav_type, "name", nav_type) or "")
        if not url:
            return False
        if self._session.camera_session_url and normalize_session_url(
            url
        ) == normalize_session_url(self._session.camera_session_url):
            diag("worker_navigation", url=url, source=source, nav_type=nav_name)
            return True
        if is_listing_page(url) or is_ad_or_tracking(url) or is_promo_or_filler_page(url):
            diag(
                "worker_navigation_ignored",
                url=url,
                reason="ad_or_promo",
                source=source,
                nav_type=nav_name,
                selected=self._session.camera_session_url,
            )
            return False
        if not self._session.camera_session_url:
            if looks_like_camera_page(url):
                diag("worker_navigation", url=url, source=source, nav_type=nav_name)
                return True
            diag(
                "worker_navigation_ignored",
                url=url,
                reason="not_camera_page",
                source=source,
                nav_type=nav_name,
            )
            return False
        if is_redirect_navigation(nav_type):
            prev = self._session.camera_page or self._session.camera_session_url
            self._session.note_session_redirect(url)
            diag("worker_redirect", **{"from": prev, "to": url, "nav_type": nav_name, "source": source})
            return True
        diag("worker_navigation", url=url, source=source, nav_type=nav_name)
        return True

    def _allow_visible_navigation(self, page: QWebEnginePage, url: str) -> bool:
        if page is not self._view.page():
            return True
        action = visible_navigation_action(
            self._session.state,
            url,
            has_listing=bool(self._interactive and self._session.listing_url),
        )
        if action == "allow":
            return True
        if action == "background":
            if (
                self._session.state in _CAMERA_LOCKED_STATES
                and self._session.camera_session_url
                and not looks_like_camera_page(url)
            ):
                diag(
                    "listing_navigation_ignored",
                    url=url,
                    reason="camera_session_locked",
                    selected=self._session.camera_session_url,
                )
                return False
            self._open_camera_in_background(url)
        return False

    def _ensure_worker_view(self) -> QWebEngineView:
        if self._worker_view is not None:
            return self._worker_view
        view = QWebEngineView()
        page = _HunterPage(self._profile, self)
        view.setPage(page)
        self._apply_page_settings(page)
        self._wire_page(page)
        self._hide_engine_from_user(view)
        self._worker_view = view
        return view

    def _open_camera_in_background(self, url: str) -> None:
        url = (url or "").strip()
        if not url:
            return
        prior_state = self._session.state
        if self._session.state in {
            HunterState.MAP_SEARCH,
            HunterState.CAMERA_SELECTED,
            HunterState.LIVE,
            HunterState.FAILED,
        }:
            self._begin_camera_activation(url, overlay=True)
        elif self._session.camera_session_url and (
            is_promo_or_filler_page(url) or not looks_like_camera_page(url)
        ):
            diag(
                "worker_navigation_ignored",
                url=url,
                reason="camera_session_locked",
                source="background_open",
                selected=self._session.camera_session_url,
            )
            return
        worker = self._ensure_worker_view()
        current = worker.url().toString()
        self._cdp.prepare_for_navigation()
        already_loaded = current == url
        first_activation = prior_state in {
            HunterState.MAP_SEARCH,
            HunterState.CAMERA_SELECTED,
        }
        diag(
            "camera_url_background",
            url=url,
            worker_url=current,
            already_loaded=already_loaded,
            first_activation=first_activation,
            state=self._session.state.value,
            generation=self._session.generation,
        )
        if already_loaded:
            # First activation: keep the in-flight LinkClicked load.
            # Same-URL reopen from LIVE/FAILED still reloads. Recovery uses
            # _reload_camera_page, not this path.
            if not first_activation:
                worker.reload()
            return
        worker.setUrl(QUrl(url))

    def _reload_camera_page(self, url: str) -> None:
        """Reload the hidden camera page. Never replace the visible listing view.

        Same-URL setUrl is a no-op in WebEngine, so force reload when the worker
        is already on the selected camera — recovery needs a fresh HLS token.
        """
        target = QUrl(url)

        def _apply(view: QWebEngineView) -> None:
            current = view.url().toString()
            if current and normalize_session_url(current) == normalize_session_url(url):
                view.reload()
                return
            view.setUrl(target)

        if self._interactive and self._session.listing_url:
            _apply(self._ensure_worker_view())
            return
        if self._worker_view is not None:
            _apply(self._worker_view)
            return
        if self._popup_views:
            _apply(self._popup_views[-1])
            return
        _apply(self._view)

    def _emit_state(self) -> None:
        self._sync_network_capture()
        self.state_changed.emit(self._session.state.value)
        if self._session.overlay_visible:
            msg = STATUS_RECONNECTING if self._session.state == HunterState.RECONNECTING else STATUS_LOADING
            self.overlay_changed.emit(True, msg)
        else:
            self.overlay_changed.emit(False, "")

    def _sync_network_capture(self) -> None:
        listing = not self._session.discovery_enabled
        self._cdp.set_listing_capture(listing)
        self._cdp.set_generation(self._session.generation)
        diag(
            "cdp_session",
            generation=self._session.generation,
            listing_capture=listing,
            discovery_enabled=self._session.discovery_enabled,
            state=self._session.state.value,
        )

    @Slot(QNetworkCookie)
    def _on_cookie_added(self, cookie: QNetworkCookie) -> None:
        self._cookie_jar[_cookie_key(cookie)] = QNetworkCookie(cookie)

    @Slot(QNetworkCookie)
    def _on_cookie_removed(self, cookie: QNetworkCookie) -> None:
        self._cookie_jar.pop(_cookie_key(cookie), None)

    def _cookie_header_for(self, url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or "/"
        secure = parsed.scheme == "https"
        parts: list[str] = []
        for cookie in self._cookie_jar.values():
            domain = str(cookie.domain() or "").lower().lstrip(".")
            if not domain or not (host == domain or host.endswith("." + domain)):
                continue
            cookie_path = str(cookie.path() or "/") or "/"
            if not path.startswith(cookie_path):
                continue
            if cookie.isSecure() and not secure:
                continue
            name = _bytes_text(cookie.name())
            value = _bytes_text(cookie.value())
            if name:
                parts.append(f"{name}={value}")
        return "; ".join(parts)

    def _remember_hls_headers(
        self, url: str, headers: dict[str, str] | None, document_url: str | None = None
    ) -> None:
        if not url or not headers:
            return
        merged = merge_hls_headers(self._hls_request_headers.get(url), headers)
        self._hls_request_headers[url] = merged
        diag(
            "hls_request_headers",
            url=url,
            header_keys=sorted(merged),
            has_cookie="Cookie" in merged,
            cookie_names=cookie_names_from_header(merged.get("Cookie")),
            referer=merged.get("Referer"),
            origin=merged.get("Origin"),
            document_url=document_url,
        )
        if (
            self._live_hls_url == url
            and self._live_player is not None
            and not self._live_player.has_video
            and self._pending_live_src is not None
            and "Cookie" in merged
            and "Cookie" not in self._live_headers
        ):
            self._arm_live_playback(self._pending_live_src)

    def _playback_headers_for(self, src: CameraSource) -> dict[str, str]:
        captured = self._hls_request_headers.get(src.url) or {}
        fallback = hls_playback_headers(
            self._session.camera_page or self._current_url or self._page_url
        )
        jar = self._cookie_header_for(src.url)
        extra = {"Cookie": jar} if jar else None
        headers = merge_hls_headers(fallback, extra, captured)
        diag(
            "playback_headers",
            url=src.url,
            header_keys=sorted(headers),
            has_cookie="Cookie" in headers,
            cookie_names=cookie_names_from_header(headers.get("Cookie")),
            referer=headers.get("Referer"),
            origin=headers.get("Origin"),
            captured_keys=sorted(captured),
            jar_cookie_names=cookie_names_from_header(jar),
        )
        return headers

    def _stamp(self, obs: ObservedRequest) -> ObservedRequest:
        obs.page_url = self._session.camera_page or self._current_url or self._page_url
        obs.navigation_index = len(self._nav_chain)
        if not obs.session_id:
            obs.session_id = self._session.generation
        if not obs.document_url:
            obs.document_url = obs.page_url
        return obs

    @Slot(str, str, int, str, str)
    def _on_network_request(
        self,
        url: str,
        resource_type: str = "",
        session_id: int = 0,
        headers_json: str = "",
        first_party: str = "",
    ) -> None:
        if not self._busy:
            return
        gen = self._session.generation
        if session_id and session_id != gen:
            return
        headers: dict[str, str] = {}
        if headers_json:
            try:
                parsed = json.loads(headers_json)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict):
                headers = canonical_request_headers(parsed)
        if headers:
            self._remember_hls_headers(url, headers, first_party)
        if not should_classify_network_event(
            discovery_enabled=self._session.discovery_enabled,
            url=url,
            mime_type=None,
            session_id=session_id or gen,
            current_generation=gen,
        ):
            return
        self._url_session[url] = gen
        obs = self._stamp(
            ObservedRequest(
                url=url,
                resource_type=resource_type,
                source="NETWORK REQUEST",
                session_id=gen,
                request_headers=headers or None,
                document_url=first_party or None,
            )
        )
        self._observations.append(obs)
        self._ingest(obs)

    def _on_cdp_response(self, obs: object) -> None:
        if not self._busy:
            return
        if not isinstance(obs, ObservedRequest):
            return
        gen = self._session.generation
        if obs.session_id and obs.session_id != gen:
            return
        if not should_classify_network_event(
            discovery_enabled=self._session.discovery_enabled,
            url=obs.url,
            mime_type=obs.mime_type,
            session_id=obs.session_id or gen,
            current_generation=gen,
        ):
            return
        if not obs.session_id:
            obs.session_id = gen
        self._stamp(obs)
        if obs.request_headers:
            self._remember_hls_headers(obs.url, obs.request_headers, obs.document_url)
        self._observations.append(obs)
        self._ingest(obs)

    def _earthcam_keep_hls(
        self,
        url: str,
        obs: ObservedRequest | None = None,
        *,
        playlist_body: str | bytes | None = None,
    ) -> bool:
        if not earthcam_applies(url):
            return True
        headers = (obs.request_headers if obs is not None else None) or {}
        referer = headers.get("Referer") or headers.get("referer")
        initiator = obs.document_url if obs is not None else None
        decision = filter_hls_candidate(
            url,
            page_url=self._session.camera_page or self._page_url,
            referer=referer,
            initiator=initiator,
            source_type="hls",
            playlist_body=playlist_body,
        )
        if decision.keep:
            return True
        diag(
            "earthcam_hls_dropped",
            **safe_log_fields(
                url=url,
                binding=decision.binding_status,
                evidence=",".join(decision.evidence),
                validation=decision.validation_status,
            ),
        )
        return False

    def _ingest(self, obs: ObservedRequest) -> None:
        gen = self._session.generation
        if obs.session_id and obs.session_id != gen:
            return
        if is_ectv_player_hint(obs.url):
            diag("earthcam_player_api", **safe_log_fields(url=obs.url))
            return
        if not should_classify_network_event(
            discovery_enabled=self._session.discovery_enabled,
            url=obs.url,
            mime_type=obs.mime_type,
            session_id=obs.session_id or gen,
            current_generation=gen,
        ):
            return
        src = classify_url(
            obs.url,
            mime_type=obs.mime_type,
            resource_type=obs.resource_type,
            source_page=self._page_url,
            discovery_source=obs.source,
            page_url=obs.page_url,
            navigation_index=obs.navigation_index,
        )
        if src is None:
            return
        if src.source_type == SourceType.HLS:
            normalized = normalize_discovered_hls_url(src.url)
            if normalized != src.url:
                src = replace(src, url=normalized)
            if obs.request_headers:
                self._remember_hls_headers(src.url, obs.request_headers, obs.document_url)
            if not self._earthcam_keep_hls(src.url, obs):
                return
        is_stream = src.is_camera_hit() and src.source_type in {
            SourceType.HLS,
            SourceType.DASH,
            SourceType.VIDEO,
            SourceType.MJPEG,
        }
        if is_stream:
            if src.source_type == SourceType.HLS:
                if not self._session.can_accept_hls_candidate(src.url, obs.session_id or self._session.generation):
                    diag(
                        "hls_gated",
                        url=src.url,
                        state=self._session.state.value,
                        discovery_enabled=self._session.discovery_enabled,
                        session_id=obs.session_id or self._session.generation,
                        generation=self._session.generation,
                    )
                    return
            elif not self._session.discovery_enabled:
                return
        key = (src.url, src.source_type)
        prev = self._live_sources.get(key)
        if prev is not None:
            if prev.is_thumbnail() and not src.is_stream():
                return
            better = src.confidence > prev.confidence or (
                src.discovery_source == "NETWORK RESPONSE"
                and prev.discovery_source != "NETWORK RESPONSE"
            )
            if better:
                self._live_sources[key] = src
            return
        self._live_sources[key] = src
        self.source_found.emit(src)
        if src.source_type == SourceType.HLS and src.is_camera_hit():
            doc = (obs.document_url or "").strip()
            if (
                doc
                and (is_ad_or_tracking(doc) or is_promo_or_filler_page(doc))
            ):
                diag(
                    "hls_ignored_other_target",
                    url=src.url,
                    document_url=doc,
                    selected=self._session.camera_session_url,
                    reason="ad_or_promo_document",
                )
                return
            accepted = self._session.add_hls_candidate(
                src.url, obs.session_id or self._session.generation
            )
            diag(
                "hls_candidate",
                accepted=accepted,
                url=src.url,
                source=src.discovery_source,
                state=self._session.state.value,
                document_url=obs.document_url,
                header_keys=sorted(obs.request_headers or {}),
                has_cookie=bool(obs.request_headers and "Cookie" in obs.request_headers),
            )
            if accepted:
                self._session.mark_discovery_active()
                if self._live_hls_url and self._live_hls_url != src.url:
                    diag(
                        "hls_kept_selected",
                        selected=self._live_hls_url,
                        ignored=src.url,
                    )
                else:
                    self._arm_live_playback(src)
                    self._start_hls_validation(src, self._session.generation)
                self._emit_state()
        elif (
            src.is_camera_hit()
            and src.source_type in {SourceType.IMAGE, SourceType.REFRESH_IMAGE}
            and looks_like_jpeg_feed(src.url)
        ):
            if not self._session.discovery_enabled:
                return
            if self._hls_blocks_jpeg():
                return
            base = _strip_cache_bust(src.url)
            if obs.source == "NETWORK REQUEST":
                self._jpeg_request_hits[base] = self._jpeg_request_hits.get(base, 0) + 1
            hit_count = max(self._jpeg_request_hits.get(base, 0), 1)
            document = (
                obs.document_url
                or self._session.camera_page
                or obs.page_url
                or self._current_url
            )
            score = jpeg_camera_feed_score(
                src.url,
                document_url=document,
                discovery_source=src.discovery_source,
                hit_count=hit_count,
                source_type=src.source_type,
            )
            if score < 1:
                return
            jpg_diag(
                "jpg_candidate",
                url=src.url,
                source=src.discovery_source,
                state=self._session.state.value,
                document_url=document,
                score=score,
            )
            self._session.mark_discovery_active()
            self._arm_jpeg_playback(src, score)
            self._emit_state()
        elif src.is_camera_hit() and src.source_type in {SourceType.DASH}:
            if self._session.discovery_enabled:
                self.status.emit(f"🎯 CAMERA SOURCE FOUND ({src.kind_label()})")
                self._probe_timer.stop()

    def _begin_camera_activation(self, url: str, *, overlay: bool = True) -> None:
        self._earthcam_expiry.bind_page(url)
        self._session.activate_camera_page(url)
        self._url_session = {}
        self._observations = []
        self._live_sources = {
            key: src for key, src in self._live_sources.items() if src.is_thumbnail()
        }
        self._validated = None
        self._pending_live_src = None
        self._pending_jpeg_src = None
        self._live_hls_url = None
        self._live_jpeg_url = None
        self._jpeg_score = None
        self._jpeg_request_hits = {}
        self._hls_request_headers = {}
        self._hls_failed_urls.clear()
        self._capture_inflight = False
        self._stop_live_player()
        self._probe_timer.start()
        self._sync_network_capture()
        self._cdp.prepare_for_navigation()
        self.status.emit(STATUS_LOADING)
        self._emit_state()
        diag(
            "camera_activation",
            url=url,
            state=self._session.state.value,
            generation=self._session.generation,
            overlay=overlay,
        )
        diag("camera_session_locked", url=url, generation=self._session.generation)
        if not overlay:
            self.overlay_changed.emit(False, "")

    def _record_navigation(self, url: str, page_kind: str = "unknown") -> None:
        url = (url or "").strip()
        if not url or url.startswith(("about:", "chrome:")):
            return
        if (
            page_kind.startswith("popup")
            and self._session.state in _CAMERA_LOCKED_STATES
            and (self._session.camera_page or "") != url
        ):
            diag(
                "popup_navigation_ignored",
                url=url,
                page=page_kind,
                reason="camera_session_locked",
                selected=self._session.camera_page,
            )
            return
        if page_kind == "worker" and (
            is_ad_or_tracking(url) or is_promo_or_filler_page(url)
        ):
            diag(
                "worker_navigation_ignored",
                url=url,
                reason="ad_or_promo",
                source="url_changed",
                selected=self._session.camera_session_url,
            )
            return
        if self._nav_chain and self._nav_chain[-1] == url:
            self._maybe_activate_from_navigation(url, page_kind)
            return
        self._nav_chain.append(url)
        if page_kind != "listing":
            self._current_url = url
        self.navigation.emit(url, len(self._nav_chain))
        self._cdp.prepare_for_navigation()
        self._maybe_activate_from_navigation(url, page_kind)
        if self._interactive and self._session.state == HunterState.MAP_SEARCH:
            self.status.emit(STATUS_CHOOSE_CAMERA)
        elif self._interactive and self._session.overlay_visible:
            self.status.emit(STATUS_LOADING)
        elif self._interactive:
            self.status.emit(f"Navigáció {len(self._nav_chain)}: {url}")

    def _maybe_activate_from_navigation(self, url: str, page_kind: str = "unknown") -> None:
        if not self._interactive:
            return
        if self._session.state in _CAMERA_LOCKED_STATES:
            if page_kind == "worker":
                if is_ad_or_tracking(url) or is_promo_or_filler_page(url):
                    diag(
                        "worker_navigation_ignored",
                        url=url,
                        reason="ad_or_promo",
                        selected=self._session.camera_session_url,
                    )
                else:
                    self._session.note_session_redirect(url)
                    diag("worker_navigation", url=url, source="url_changed")
            return
        if is_listing_page(url):
            if self._session.state in {HunterState.IDLE}:
                self._session.start_listing(url)
                self._emit_state()
            return
        if looks_like_camera_page(url) and self._session.state in {
            HunterState.MAP_SEARCH,
            HunterState.CAMERA_SELECTED,
        }:
            diag(
                "activate_from_navigation",
                url=url,
                state=self._session.state.value,
                page=page_kind,
                has_listing=bool(self._interactive and self._session.listing_url),
            )
            if self._interactive and self._session.listing_url:
                self._open_camera_in_background(url)
            else:
                self._begin_camera_activation(url, overlay=True)

    @Slot(QUrl)
    def _on_url_changed(self, qurl: QUrl) -> None:
        if not self._busy:
            return
        url = qurl.toString()
        page_kind = self._page_kind(self.sender())
        diag(
            "url_changed",
            url=url,
            page=page_kind,
            state=self._session.state.value,
            generation=self._session.generation,
        )
        self._record_navigation(url, page_kind)

    def discover(self, url: str, *, interactive: bool = False) -> None:
        if self._busy:
            self.status.emit("Már folyamatban van egy felderítés.")
            return
        url = (url or "").strip()
        if not url:
            self.finished.emit(
                DiscoveryResult(page_url="", sources=[], error="Üres URL.")
            )
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self._busy = True
        self._interactive = interactive
        self._page_url = url
        self._current_url = url
        self._nav_chain = []
        self._observations = []
        self._live_sources = {}
        self._cdp_wait_tries = 0
        self._validated = None
        self._live_frame_path = None
        self._live_hls_url = None
        self._pending_live_src = None
        self._jpeg_score = None
        self._jpeg_request_hits = {}
        self._hls_failed_urls.clear()
        self._capture_inflight = False
        self._stop_live_player()
        self._session.reset()
        self._url_session = {}
        timeout = INTERACTIVE_MAX_MS if interactive else self._max_load_ms
        self._watchdog.start(timeout)
        self._cdp.prepare_for_navigation()
        if interactive and is_listing_page(url):
            self._session.start_listing(url)
            self.status.emit(STATUS_CHOOSE_CAMERA)
            self._emit_state()
        else:
            self._begin_camera_activation(url, overlay=interactive)
            if not interactive:
                self._session.mark_discovery_active()
                self._emit_state()
                self.status.emit("📹 A kamera kép betöltése... Kis türelmet...")
        if self._session.discovery_enabled:
            self._probe_timer.start()
        self._wait_for_cdp_then_load()

    def finish_session(self, timed_out: bool = False) -> None:
        if not self._busy:
            return
        self._collect_and_finish(timed_out=timed_out)

    def abort_in_flight(self) -> None:
        """Drop the current session immediately so discover() can start another URL.

        Unlike finish_session(), this does not scan the DOM or emit finished.
        In-flight JS callbacks see _busy is False and return.
        """
        if not self._busy:
            return
        self._watchdog.stop()
        self._settle_timer.stop()
        self._probe_timer.stop()
        self._health_timer.stop()
        self._stop_live_player()
        self._capture_inflight = False
        self._pending_live_src = None
        self._busy = False
        self._interactive = False

    def run_javascript(self, script: str, callback=None) -> None:
        page = self._view.page()
        if callback is None:
            page.runJavaScript(script, 0)
        else:
            page.runJavaScript(script, 0, callback)

    def _wait_for_cdp_then_load(self) -> None:
        if not self._busy:
            return
        if self._cdp.is_attached or self._cdp_wait_tries >= 20:
            self._view.setUrl(QUrl(self._page_url))
            return
        self._cdp_wait_tries += 1
        QTimer.singleShot(250, self._wait_for_cdp_then_load)

    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        if not self._busy:
            return
        page = self.sender()
        kind = self._page_kind(page) if isinstance(page, QWebEnginePage) else "listing"
        if isinstance(page, QWebEnginePage):
            self._record_navigation(page.url().toString(), kind)
        else:
            self._record_navigation(self._view.url().toString(), "listing")
        if not ok:
            self.status.emit("Az oldal betöltése bizonytalan — hálózati jelek gyűjtése...")
        elif self._session.overlay_visible:
            self.status.emit(
                STATUS_RECONNECTING
                if self._session.state == HunterState.RECONNECTING
                else STATUS_LOADING
            )
        elif self._interactive and is_listing_page(self._current_url):
            self.status.emit(STATUS_CHOOSE_CAMERA)
        elif self._interactive:
            self.status.emit(STATUS_CHOOSE_CAMERA)
        else:
            self.status.emit("Kis türelmet...")
        target = page if isinstance(page, QWebEnginePage) else self._view.page()
        target.runJavaScript(EARTHCAM_CONSENT_JS, 0)
        probe_this = True
        if kind == "listing" and self._interactive and self._session.listing_url:
            probe_this = False
        if self._session.discovery_enabled and probe_this:
            target.runJavaScript(_PREFETCH_JS, 0)
            self._run_stream_probe()
        self._cdp.prepare_for_navigation()
        self._settle_timer.start(self._settle_ms)

    def _run_stream_probe(self) -> None:
        if not self._busy:
            return
        if not self._session.discovery_enabled:
            return
        if self._session.state == HunterState.LIVE:
            self._probe_timer.stop()
            return
        if any(
            s.is_camera_hit() and s.source_type in {SourceType.HLS, SourceType.DASH}
            for s in self._live_sources.values()
        ) and self._live_player is not None and self._live_player.is_playing:
            return
        for page in self._probe_pages():
            page.runJavaScript(_STREAM_PROBE_JS, 0, self._on_probe_urls)

    def _probe_pages(self) -> list:
        if self._interactive and self._session.listing_url:
            if self._worker_view is not None:
                page = self._worker_view.page()
                return [page] if page is not None else []
            return []
        pages = [self._view.page()]
        if self._worker_view is not None:
            pages.append(self._worker_view.page())
        return [p for p in pages if p is not None]

    @Slot(object)
    def _on_probe_urls(self, result: object) -> None:
        if not self._busy or not self._session.discovery_enabled:
            return
        if self._session.state == HunterState.LIVE:
            return
        urls = result if isinstance(result, (list, tuple)) else []
        gen = self._session.generation
        for raw in urls:
            if not isinstance(raw, str) or not raw.startswith(("http://", "https://")):
                continue
            obs = self._stamp(
                ObservedRequest(
                    url=normalize_discovered_hls_url(raw),
                    mime_type="application/vnd.apple.mpegurl",
                    resource_type="XHR",
                    source="DOM PROBE",
                    session_id=gen,
                )
            )
            self._ingest(obs)

    def _start_hls_validation(self, src: CameraSource, generation: int) -> None:
        if not self._interactive:
            return
        if self._session.state == HunterState.LIVE:
            return
        if self._capture_inflight:
            return
        self._capture_inflight = True
        page_url = self._session.camera_page or self._current_url or self._page_url
        cookie = (self._hls_request_headers.get(src.url) or {}).get("Cookie") or self._cookie_header_for(
            src.url
        )
        thread = threading.Thread(
            target=self._hls_capture_worker,
            args=(src, generation, page_url, cookie or None),
            name="hls-validate",
            daemon=True,
        )
        thread.start()

    def _hls_capture_worker(
        self,
        src: CameraSource,
        generation: int,
        page_url: str | None,
        cookie: str | None,
    ) -> None:
        try:
            cap = capture_hls(src.url, page_url=page_url, cookie=cookie, print_report=False)
        except Exception as exc:
            cap = HlsCaptureResult(hls_url=src.url, error=str(exc))
        self._capture_bridge.finished.emit(src, cap, generation)

    @Slot(object, object, int)
    def _on_hls_capture_finished(self, src: object, cap: object, generation: int) -> None:
        self._capture_inflight = False
        if not self._busy or generation != self._session.generation:
            return
        if not isinstance(src, CameraSource) or not isinstance(cap, HlsCaptureResult):
            return
        if self._session.state == HunterState.LIVE:
            if cap.segment_url:
                self._session.last_segment_url = cap.segment_url
            if cap.headers_used:
                self._live_headers = merge_hls_headers(self._live_headers, cap.headers_used)
            return
        if cap.headers_used:
            self._live_headers = merge_hls_headers(self._live_headers, cap.headers_used)
        if not cap.video_frame:
            if earthcam_applies(src.url):
                self._handle_earthcam_validation_failure(src, cap)
            elif not self._arm_next_accepted_hls(src.url):
                self._probe_timer.start()
            return
        if cap.video_frame:
            self._pending_live_src = src
            self._arm_live_playback(src)
        self._probe_timer.start()
        return

    def _arm_next_accepted_hls(self, failed_url: str | None) -> bool:
        """Arm the next already-accepted HLS candidate after a pre-LIVE failure."""
        failed = (failed_url or "").strip()
        if failed:
            self._hls_failed_urls.add(failed)
        if self._session.state == HunterState.LIVE:
            return False
        if not failed or self._live_hls_url != failed:
            return False
        self._stop_live_player()
        self._live_hls_url = None
        self._pending_live_src = None
        generation = self._session.generation
        for session_id, url in self._session.hls_candidates:
            if session_id != generation:
                continue
            if url in self._hls_failed_urls:
                continue
            src = self._live_sources.get((url, SourceType.HLS))
            if src is None:
                continue
            diag(
                "hls_fallback_next",
                **safe_log_fields(failed=failed, next=url),
            )
            self._arm_live_playback(src)
            self._start_hls_validation(src, generation)
            return True
        diag("hls_fallback_exhausted", **safe_log_fields(failed=failed))
        return False

    def _handle_earthcam_validation_failure(self, src: CameraSource, cap: HlsCaptureResult) -> None:
        diag(
            "earthcam_hls_validation_failed",
            **safe_log_fields(url=src.url, error=cap.error),
        )
        if self._session.state == HunterState.LIVE:
            self._recover_live_source(reason=cap.error or "invalid_manifest")
            return
        if self._arm_next_accepted_hls(src.url):
            return
        self._probe_timer.start()

    def _arm_live_playback(self, src: CameraSource) -> None:
        """Start the real HLS player as soon as a playlist URL is known."""
        if (
            self._session.state == HunterState.LIVE
            and self._live_player is not None
            and self._live_player.has_video
            and self._live_hls_url == src.url
        ):
            return
        better = "hd-auth.skylinewebcams.com" in src.url and "hd-auth.skylinewebcams.com" not in (
            self._live_hls_url or ""
        )
        if (
            self._live_player is not None
            and self._live_player.has_video
            and self._live_hls_url == src.url
            and not better
        ):
            return
        self._pending_live_src = src
        self._live_hls_url = src.url
        self._live_headers = self._playback_headers_for(src)
        player = self._live_player
        diag(
            "arm_live_playback",
            url=src.url,
            player_attached=player is not None,
            headers=sorted(self._live_headers),
            has_cookie="Cookie" in self._live_headers,
            cookie_names=cookie_names_from_header(self._live_headers.get("Cookie")),
            referer=self._live_headers.get("Referer"),
            origin=self._live_headers.get("Origin"),
            state=self._session.state.value,
        )
        if player is not None:
            self._stop_jpeg_player()
            player.play(src.url, self._live_headers)
        else:
            diag("arm_live_playback_no_player", url=src.url)

    def _hls_blocks_jpeg(self) -> bool:
        if self._live_hls_url:
            return True
        live = self._session.live_result
        if live is not None and live.source_type == CameraResultType.HLS:
            return True
        player = self._live_player
        return player is not None and player.has_video

    def _arm_jpeg_playback(self, src: CameraSource, score: int) -> None:
        if self._hls_blocks_jpeg():
            return
        if (
            self._jpeg_player is not None
            and self._jpeg_player.has_image
            and self._live_jpeg_url == src.url
        ):
            return
        live_jpeg = (
            self._session.state == HunterState.LIVE
            and self._session.live_result is not None
            and self._session.live_result.source_type != CameraResultType.HLS
        )
        locked = live_jpeg or (
            self._jpeg_player is not None and self._jpeg_player.has_image
        )
        if self._live_jpeg_url and self._live_jpeg_url != src.url:
            if locked or not should_replace_jpeg_candidate(
                self._jpeg_score, score, live=locked
            ):
                jpg_diag(
                    "jpg_kept_selected",
                    selected=self._live_jpeg_url,
                    ignored=src.url,
                )
                return
        self._pending_jpeg_src = src
        self._live_jpeg_url = src.url
        self._jpeg_score = score
        headers = self._playback_headers_for(src)
        player = self._jpeg_player
        if player is None:
            jpg_diag("jpg_player_missing", url=src.url)
            return
        player.play(src.url, headers)

    def _publish_live_frame(self, path: str | None) -> None:
        if not path:
            return
        self._live_frame_path = path
        self.live_frame.emit(path)

    def _stop_jpeg_player(self) -> None:
        player = self._jpeg_player
        if player is not None:
            player.stop()
        self._live_jpeg_url = None
        self._pending_jpeg_src = None
        self._jpeg_score = None

    def _stop_live_player(self) -> None:
        player = self._live_player
        if player is not None:
            player.stop()
        self._stop_jpeg_player()

    def _promote_live_from_player(self) -> bool:
        src = self._pending_live_src
        if src is None or not self._busy:
            return False
        if self._session.state == HunterState.LIVE:
            existing = self._session.live_result
            if existing is not None and existing.source_type == CameraResultType.HLS:
                return True
        cap = HlsCaptureResult(
            hls_url=src.url,
            hls_fetch=True,
            segment=True,
            video_frame=True,
            headers_used=dict(self._live_headers),
        )
        result = self._session.accept_validated_hls(
            src,
            cap,
            session_id=self._session.generation,
            source_page=self._page_url,
            final_page=self._session.camera_page or self._current_url,
            user_agent=self._live_headers.get("User-Agent"),
            referer=self._live_headers.get("Referer"),
        )
        if result is not None and earthcam_applies(src.url):
            self._earthcam_expiry.note_live_accepted()
        if result is None:
            diag("promote_live_rejected", url=src.url, state=self._session.state.value)
            return False
        self._stop_jpeg_player()
        self._validated = result
        self._health_timer.stop()
        self._probe_timer.stop()
        self.live_ready.emit(result)
        self._emit_state()
        self.status.emit("🟢 LIVE")
        diag("promote_live_ok", url=src.url, state=self._session.state.value)
        return True

    def _promote_live_from_jpeg(self) -> bool:
        src = self._pending_jpeg_src
        if src is None or not self._busy:
            return False
        if self._hls_blocks_jpeg():
            return False
        if self._session.state == HunterState.LIVE:
            existing = self._session.live_result
            if existing is not None and existing.source_type == CameraResultType.HLS:
                return False
            if existing is not None and existing.camera_source_url == src.url:
                return True
        headers = self._playback_headers_for(src)
        result = self._session.accept_validated_jpeg(
            src,
            session_id=self._session.generation,
            source_page=self._page_url,
            final_page=self._session.camera_page or self._current_url,
            user_agent=headers.get("User-Agent"),
            referer=headers.get("Referer"),
        )
        if result is None:
            jpg_diag("jpg_promote_rejected", url=src.url, state=self._session.state.value)
            return False
        self._validated = result
        self._health_timer.start()
        self._probe_timer.stop()
        self.live_ready.emit(result)
        self._emit_state()
        self.status.emit(jpeg_status_text())
        jpg_diag("jpg_promote_ok", url=src.url, state=self._session.state.value)
        return True

    @Slot()
    def _on_player_video_started(self) -> None:
        diag(
            "video_started_signal",
            busy=self._busy,
            state=self._session.state.value,
            url=self._live_hls_url,
        )
        if not self._busy:
            return
        if self._session.state not in {
            HunterState.LIVE,
            HunterState.VALIDATING_HLS,
            HunterState.DISCOVERY_ACTIVE,
            HunterState.CAMERA_LOADING,
            HunterState.RECONNECTING,
        }:
            return
        self._promote_live_from_player()

    @Slot(str)
    def _on_player_playback_failed(self, message: str) -> None:
        if not self._busy:
            return
        if self._session.state == HunterState.LIVE:
            live = self._session.live_result
            if live is None or live.source_type != CameraResultType.HLS:
                return
            diag("player_dead_recover", error=message or "ended", url=self._live_hls_url)
            self._recover_live_source(reason=message or "player_dead")
            return
        if self._session.state not in {
            HunterState.VALIDATING_HLS,
            HunterState.DISCOVERY_ACTIVE,
            HunterState.CAMERA_LOADING,
            HunterState.RECONNECTING,
        }:
            return
        player = self._live_player
        if player is not None and player.has_video:
            return
        failed = (self._live_hls_url or "").strip()
        current = ""
        if player is not None:
            current = (getattr(player, "current_url", None) or "").strip()
        if current and failed and current != failed:
            return
        if current:
            failed = current
        diag(
            "player_pre_live_fail",
            error=message or "ended",
            **safe_log_fields(url=failed),
        )
        self._arm_next_accepted_hls(failed)

    @Slot()
    def _on_jpeg_live_started(self) -> None:
        jpg_diag(
            "jpg_live_started_signal",
            busy=self._busy,
            state=self._session.state.value,
            url=self._live_jpeg_url,
        )
        if not self._busy:
            return
        if self._session.state not in {
            HunterState.LIVE,
            HunterState.VALIDATING_HLS,
            HunterState.DISCOVERY_ACTIVE,
            HunterState.CAMERA_LOADING,
            HunterState.RECONNECTING,
        }:
            return
        self._promote_live_from_jpeg()

    @Slot(float)
    def _on_jpeg_refresh_interval(self, seconds: float) -> None:
        if not self._busy or self._session.state != HunterState.LIVE:
            return
        live = self._session.live_result
        if live is None or live.source_type == CameraResultType.HLS:
            return
        self.status.emit(jpeg_status_text(seconds))

    def _jpeg_stream_alive(self) -> bool:
        player = self._jpeg_player
        return player is not None and player.is_healthy()

    def _on_health_check(self) -> None:
        if not self._busy or self._session.state != HunterState.LIVE:
            return
        live = self._session.live_result
        if live is None or not live.camera_source_url:
            return
        if live.source_type == CameraResultType.HLS:
            # LiveWallpaper model: leave a working HLS player alone.
            # HTTP playlist probes are not the player watchdog.
            self._session.health_ok()
            return
        if live.source_type in {
            CameraResultType.REFRESHING_IMAGE,
            CameraResultType.STILL_IMAGE,
        }:
            if self._jpeg_stream_alive():
                self._session.health_ok()
                return
            self._recover_live_source(reason="jpeg_unhealthy")

    def _fail_earthcam_live(self, *, reason: str) -> None:
        diag(
            "earthcam_expiry_failed",
            **safe_log_fields(
                reason=reason,
                url=self._live_hls_url
                or (self._session.live_result.camera_source_url if self._session.live_result else None),
            ),
        )
        self._health_timer.stop()
        self._session.mark_failed()
        self._stop_live_player()
        self._live_hls_url = None
        self._pending_live_src = None
        self.status.emit("EarthCam stream unavailable")
        self._emit_state()

    def _recover_live_source(self, *, reason: str) -> None:
        """Drop the current (possibly expired) stream URL and rediscover on the same camera."""
        if not self._busy or self._session.state != HunterState.LIVE:
            return
        live_url = self._live_hls_url or (
            self._session.live_result.camera_source_url if self._session.live_result else None
        )
        if earthcam_applies(live_url):
            action = self._earthcam_expiry.decide(error=reason, reason=reason)
            if action == "fail":
                self._fail_earthcam_live(reason=reason)
                return
        cam = self._session.camera_page or self._current_url
        diag(
            "live_source_recover",
            **safe_log_fields(
                reason=reason,
                camera=cam,
                old_url=live_url,
            ),
        )
        self._health_timer.stop()
        self._session.health_fail()
        self._observations = []
        self._live_sources = {}
        self._validated = None
        self._live_frame_path = None
        self._live_hls_url = None
        self._live_jpeg_url = None
        self._jpeg_score = None
        self._jpeg_request_hits = {}
        self._stop_live_player()
        self._pending_live_src = None
        self._pending_jpeg_src = None
        self._capture_inflight = False
        self.status.emit(STATUS_RECONNECTING)
        self._emit_state()
        self._probe_timer.start()
        if cam:
            self._reload_camera_page(cam)

    def _on_settle(self) -> None:
        if not self._busy:
            return
        self._run_stream_probe()
        if self._interactive:
            self._scan_dom(finish=False)
            return
        self._collect_and_finish(timed_out=False)

    @Slot()
    def _on_watchdog(self) -> None:
        if not self._busy:
            return
        self.status.emit("Időtúllépés — eddig gyűjtött jelek kiértékelése...")
        self._collect_and_finish(timed_out=True)

    def _collect_and_finish(self, timed_out: bool = False) -> None:
        if not self._busy:
            return
        self._watchdog.stop()
        self._settle_timer.stop()
        self._probe_timer.stop()
        self._health_timer.stop()
        self._stop_live_player()
        self._capture_inflight = False
        self._pending_live_src = None
        self.status.emit("Források kiértékelése...")
        self._scan_dom(finish=True, timed_out=timed_out)

    def _scan_dom(self, *, finish: bool, timed_out: bool = False) -> None:
        page = self._view.page()
        if self._session.discovery_enabled and self._worker_view is not None:
            page = self._worker_view.page()
        elif self._session.discovery_enabled and self._popup_views:
            popup_page = self._popup_views[-1].page()
            if popup_page is not None:
                page = popup_page
        page.runJavaScript(
            _SCAN_JS,
            0,
            lambda result, f=finish, t=timed_out: self._after_scan(result, f, t),
        )

    def _after_scan(self, result: object, finish: bool, timed_out: bool) -> None:
        if not self._busy:
            return
        try:
            data = json.loads(result) if isinstance(result, str) else {}
        except (TypeError, json.JSONDecodeError):
            data = {}

        extras: list[tuple[str, str | None]] = []
        for u in data.get("images") or []:
            if u:
                extras.append((u, None))
        for u in data.get("videos") or []:
            if u:
                extras.append((u, None))
        for item in data.get("sources") or []:
            if isinstance(item, dict) and item.get("url"):
                extras.append((item["url"], item.get("type")))
            elif isinstance(item, str):
                extras.append((item, None))
        for entry in data.get("performance") or []:
            if isinstance(entry, dict) and entry.get("name"):
                extras.append((entry["name"], None))
        extras = [
            (u, m)
            for u, m in extras
            if should_classify_network_event(
                discovery_enabled=self._session.discovery_enabled,
                url=u,
                mime_type=m,
                session_id=self._session.generation,
                current_generation=self._session.generation,
            )
        ]

        merged = merge_observations(
            list(self._observations),
            source_page=self._current_url or self._page_url,
            extra_urls=extras,
        )
        for src in merged:
            if src.is_stream() and src.is_camera_hit():
                if src.source_type == SourceType.HLS:
                    if not self._earthcam_keep_hls(src.url):
                        continue
                    if not self._session.can_accept_hls_candidate(
                        src.url, self._session.generation
                    ):
                        continue
                elif not self._session.discovery_enabled:
                    continue
            key = (src.url, src.source_type)
            prev = self._live_sources.get(key)
            if prev is None or src.confidence > prev.confidence:
                is_new = prev is None
                self._live_sources[key] = src
                if is_new:
                    self.source_found.emit(src)

        if not finish:
            return

        sources = list(self._live_sources.values())
        page_url = self._current_url or self._page_url
        for iframe_url in data.get("iframes") or []:
            if not iframe_url:
                continue
            sources.append(
                CameraSource(
                    url=iframe_url,
                    source_type=SourceType.IFRAME,
                    confidence=0.3,
                    source_page=page_url,
                    notes="iframe detected",
                    discovery_source="DOM",
                    found_after=page_url,
                    navigation_index=len(self._nav_chain),
                )
            )
        if data.get("mediaSource"):
            sources.append(
                CameraSource(
                    url=page_url,
                    source_type=SourceType.MEDIA_SOURCE,
                    confidence=0.25,
                    source_page=page_url,
                    notes="MediaSource API available in page context (MSE possible)",
                    discovery_source="DOM",
                    found_after=page_url,
                    navigation_index=len(self._nav_chain),
                )
            )

        dedup: dict[tuple[str, SourceType], CameraSource] = {}
        for s in sources:
            key = (s.url, s.source_type)
            prev = dedup.get(key)
            if prev is None or s.confidence > prev.confidence:
                dedup[key] = s
        final = list(dedup.values())
        final.sort(
            key=lambda s: (
                0 if s.is_camera_hit() and s.is_stream() else 1,
                0 if s.is_direct_camera() else 1,
                -s.confidence,
                s.source_type.value,
                s.url,
            )
        )

        self._busy = False
        was_interactive = self._interactive
        self._interactive = False
        self.finished.emit(
            DiscoveryResult(
                page_url=page_url,
                sources=final,
                error=None,
                timed_out=timed_out,
                navigation_chain=list(self._nav_chain),
                interactive=was_interactive,
                camera_result=self._validated
                or camera_result_from_sources(
                    final,
                    source_page=self._page_url,
                    final_page=page_url,
                ),
            )
        )
