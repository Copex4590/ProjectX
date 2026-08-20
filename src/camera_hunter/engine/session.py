"""Explicit Hunter session/state machine. Discovery is gated by state + generation."""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse, urlunparse

from camera_hunter.engine.classifier import is_ad_or_tracking, is_listing_page
from camera_hunter.engine.hls_capture import HlsCaptureResult
from camera_hunter.engine.providers.earthcam import session_rejects_hls
from camera_hunter.models import CameraResult, CameraResultType, CameraSource, camera_result_from_source
from camera_hunter.models.camera_source import SourceType

CAMERA_ACTIVATION_DELAY_SEC = 6.5
CAMERA_ACTIVATION_DELAY_MS = 6500
HEALTH_CHECK_INTERVAL_SEC = 30
HEALTH_CHECK_INTERVAL_MS = 30_000

DEFAULT_MAPSEARCH_URL = "https://www.earthcam.com/mapsearch/"

STATUS_CHOOSE_CAMERA = "📷 Válasszon egy kamerát a térképen..."
STATUS_LOADING = "📷 Kamera betöltése..."
STATUS_PLEASE_WAIT = "Kérjük, várjon..."
STATUS_RECONNECTING = "📷 Kamera újracsatlakoztatása..."
STATUS_LIVE = "🟢 LIVE"
STATUS_LIVE_JPEG = "🟢 ÉLŐ — JPEG"


class HunterState(str, Enum):
    IDLE = "IDLE"
    MAP_SEARCH = "MAP_SEARCH"
    CAMERA_SELECTED = "CAMERA_SELECTED"
    CAMERA_LOADING = "CAMERA_LOADING"
    DISCOVERY_ACTIVE = "DISCOVERY_ACTIVE"
    VALIDATING_HLS = "VALIDATING_HLS"
    LIVE = "LIVE"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"


_DISCOVERY_STATES = {
    HunterState.CAMERA_LOADING,
    HunterState.DISCOVERY_ACTIVE,
    HunterState.VALIDATING_HLS,
    HunterState.RECONNECTING,
}

_OVERLAY_STATES = {
    HunterState.CAMERA_LOADING,
    HunterState.DISCOVERY_ACTIVE,
    HunterState.VALIDATING_HLS,
    HunterState.RECONNECTING,
}


def is_camera_page_url(url: str | None) -> bool:
    if not url or url.startswith(("about:", "chrome:", "data:", "blob:")):
        return False
    if not url.startswith(("http://", "https://")):
        return False
    if is_listing_page(url):
        return False
    if is_ad_or_tracking(url):
        return False
    return True


_PROMO_PATHS = {
    "",
    "/",
    "/index.php",
    "/index.html",
    "/home",
    "/home.php",
    "/home.html",
    "/default.aspx",
}
_CAMERA_PATH_HINTS = (
    "/webcam",
    "webcam",
    "/livecam",
    "/livecams",
    "/cam/",
    "/cams/",
    "/player",
    "?cam=",
    "&cam=",
)


def is_promo_or_filler_page(url: str | None) -> bool:
    """Generic homepages/interstitials that are not a selected camera page."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    if is_ad_or_tracking(url):
        return True
    parsed = urlparse(url)
    path = (parsed.path or "/").lower()
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    blob = f"{parsed.netloc}{parsed.path}?{parsed.query}".lower()
    if any(hint in blob for hint in _CAMERA_PATH_HINTS):
        return False
    return path in _PROMO_PATHS


def looks_like_camera_page(url: str | None) -> bool:
    """User-selected camera destination — not a listing, ad, or bare promo homepage."""
    return is_camera_page_url(url) and not is_promo_or_filler_page(url)


def is_redirect_navigation(nav_type: object) -> bool:
    name = str(getattr(nav_type, "name", nav_type) or "").lower()
    return "redirect" in name


def normalize_session_url(url: str | None) -> str:
    parsed = urlparse((url or "").strip())
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def same_camera_site(url_a: str | None, url_b: str | None) -> bool:
    host_a = (urlparse(url_a or "").hostname or "").lower()
    host_b = (urlparse(url_b or "").hostname or "").lower()
    if not host_a or not host_b:
        return False
    if host_a == host_b:
        return True
    return host_a.endswith("." + host_b) or host_b.endswith("." + host_a)


def visible_navigation_action(state: HunterState, url: str, *, has_listing: bool) -> str:
    """Keep the user-visible view on the listing; camera pages load in the background."""
    if not has_listing:
        return "allow"
    if state == HunterState.IDLE:
        return "allow"
    if is_listing_page(url):
        return "allow"
    if is_ad_or_tracking(url) or is_promo_or_filler_page(url):
        return "block"
    if looks_like_camera_page(url):
        return "background"
    return "block"


class HunterSession:
    """One Hunter run. generation isolates network candidates across camera activations."""

    def __init__(self) -> None:
        self.state = HunterState.IDLE
        self.generation = 0
        self.camera_page: str | None = None
        self.camera_session_url: str | None = None
        self.camera_redirect_chain: list[str] = []
        self.listing_url: str | None = None
        self.hls_candidates: list[tuple[int, str]] = []
        self.live_result: CameraResult | None = None
        self.last_segment_url: str | None = None
        self.reload_requested = False
        self.health_reloads = 0

    @property
    def discovery_enabled(self) -> bool:
        return self.state in _DISCOVERY_STATES

    @property
    def overlay_visible(self) -> bool:
        return self.state in _OVERLAY_STATES

    def reset(self) -> None:
        self.state = HunterState.IDLE
        self.generation += 1
        self.camera_page = None
        self.camera_session_url = None
        self.camera_redirect_chain = []
        self.listing_url = None
        self._clear_candidates()
        self.reload_requested = False

    def _clear_candidates(self) -> None:
        self.hls_candidates.clear()
        self.live_result = None
        self.last_segment_url = None

    def start_listing(self, url: str) -> None:
        self.generation += 1
        self._clear_candidates()
        self.listing_url = url
        self.camera_page = None
        self.camera_session_url = None
        self.camera_redirect_chain = []
        self.reload_requested = False
        self.state = HunterState.MAP_SEARCH

    def note_camera_selected(self) -> None:
        """Card/popup on the listing — does not enable HLS discovery."""
        if self.state in {HunterState.MAP_SEARCH, HunterState.CAMERA_SELECTED}:
            self.state = HunterState.CAMERA_SELECTED

    def activate_camera_page(self, url: str) -> int:
        """User opened a real camera page. New generation; previous candidates dropped."""
        self.generation += 1
        self._clear_candidates()
        self.camera_page = url
        self.camera_session_url = url
        self.camera_redirect_chain = [url]
        self.reload_requested = False
        self.state = HunterState.CAMERA_LOADING
        return self.generation

    def belongs_to_session(self, url: str | None) -> bool:
        """True if url is the locked camera page, a same-site follow, or a recorded redirect."""
        if not url or not self.camera_session_url:
            return False
        if is_listing_page(url) or is_ad_or_tracking(url):
            return False
        target = normalize_session_url(url)
        for item in self.camera_redirect_chain or [self.camera_session_url]:
            if normalize_session_url(item) == target:
                return True
            if same_camera_site(item, url):
                return True
        return False

    def note_session_redirect(self, url: str) -> None:
        url = (url or "").strip()
        if not url:
            return
        self.camera_page = url
        if url not in self.camera_redirect_chain:
            self.camera_redirect_chain.append(url)

    def mark_discovery_active(self) -> None:
        if self.state == HunterState.CAMERA_LOADING:
            self.state = HunterState.DISCOVERY_ACTIVE

    def can_accept_hls_candidate(self, url: str, session_id: int) -> bool:
        if session_id != self.generation:
            return False
        if not self.discovery_enabled:
            return False
        if self.state in {HunterState.MAP_SEARCH, HunterState.CAMERA_SELECTED, HunterState.IDLE}:
            return False
        if not url or is_ad_or_tracking(url):
            return False
        if is_listing_page(url):
            return False
        if session_rejects_hls(url):
            return False
        return True

    def add_hls_candidate(self, url: str, session_id: int) -> bool:
        if not self.can_accept_hls_candidate(url, session_id):
            return False
        key = (session_id, url)
        if key in self.hls_candidates:
            return False
        self.hls_candidates.append(key)
        if self.state in {HunterState.CAMERA_LOADING, HunterState.DISCOVERY_ACTIVE}:
            self.state = HunterState.VALIDATING_HLS
        return True

    def accept_validated_hls(
        self,
        src: CameraSource,
        capture: HlsCaptureResult,
        *,
        session_id: int,
        source_page: str | None,
        final_page: str | None,
        user_agent: str | None = None,
        referer: str | None = None,
    ) -> CameraResult | None:
        if session_id != self.generation:
            return None
        if not capture.video_frame or not capture.hls_url:
            return None
        if is_ad_or_tracking(capture.hls_url):
            return None
        if session_rejects_hls(src.url) or session_rejects_hls(capture.hls_url):
            return None
        if src.source_type != SourceType.HLS:
            return None
        result = camera_result_from_source(
            src,
            source_page=source_page,
            final_page=final_page,
            user_agent=user_agent,
            referer=referer,
        )
        if result.source_type.value != "hls" or not result.is_live:
            return None
        if result.camera_source_url != src.url:
            return None
        self.live_result = result
        self.last_segment_url = capture.segment_url
        self.state = HunterState.LIVE
        self.reload_requested = False
        return result

    def accept_validated_jpeg(
        self,
        src: CameraSource,
        *,
        session_id: int,
        source_page: str | None,
        final_page: str | None,
        user_agent: str | None = None,
        referer: str | None = None,
    ) -> CameraResult | None:
        """Promote a discovered JPEG camera URL to LIVE. Does not replace an HLS LIVE result."""
        if session_id != self.generation:
            return None
        if src.source_type not in {SourceType.IMAGE, SourceType.REFRESH_IMAGE}:
            return None
        if not src.url or is_ad_or_tracking(src.url) or is_listing_page(src.url):
            return None
        if self.live_result is not None and self.live_result.source_type == CameraResultType.HLS:
            return None
        page = source_page or src.source_page
        final = final_page or src.found_after or src.source_page
        used_referer = referer or src.found_after or src.source_page
        result = CameraResult(
            source_page=page,
            final_page=final,
            camera_source_url=src.url,
            source_type=CameraResultType.REFRESHING_IMAGE,
            content_type=src.mime_type or "image/jpeg",
            is_live=True,
            extraction_method=src.discovery_source or None,
            referer=used_referer,
            user_agent=user_agent,
            discovered_at=src.discovered_at,
        )
        self.live_result = result
        self.state = HunterState.LIVE
        self.reload_requested = False
        return result

    def health_ok(self) -> None:
        """Stream still alive — no reload."""
        if self.state != HunterState.LIVE:
            return
        self.reload_requested = False

    def health_fail(self) -> int:
        """Invalidate current source and start reconnect with a new generation."""
        self.live_result = None
        self.last_segment_url = None
        self.hls_candidates.clear()
        self.generation += 1
        self.reload_requested = True
        self.health_reloads += 1
        self.state = HunterState.RECONNECTING
        return self.generation

    def mark_failed(self) -> None:
        self.state = HunterState.FAILED
        self.live_result = None
