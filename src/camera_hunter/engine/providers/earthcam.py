"""EarthCam discovery filter. Camera-specific HLS only; no playback engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from camera_hunter.engine.classifier import is_ad_or_tracking, is_listing_page

PROVIDER = "earthcam"
BINDING_CAMERA_SPECIFIC = "camera_specific"
BINDING_SHARED = "shared"
BINDING_ARCHIVE = "archive"
BINDING_UNKNOWN = "unknown"

EVIDENCE_PAGE = "page_context_match"
EVIDENCE_INITIATOR = "runtime_initiator_match"
EVIDENCE_STREAM = "stream_path_match"
EVIDENCE_PROVIDER = "provider_pattern_match"
EVIDENCE_SHARED = "shared_resource"
EVIDENCE_ARCHIVE = "archive_resource"

STRONG_EVIDENCE = (
    EVIDENCE_PAGE,
    EVIDENCE_INITIATOR,
    EVIDENCE_STREAM,
    EVIDENCE_PROVIDER,
)
MIN_STRONG_EVIDENCE = 3

TOKEN_QUERY_NAMES = frozenset({"t", "td", "a", "token", "sig", "hdnts", "expires", "exp"})
_SECRET_LOG_KEYS = frozenset({"cookie", "authorization", "set-cookie", "set_cookie"})
_SHARED_FECNETWORK_IDS = frozenset({"21001", "24322"})
_PROVIDER_HOST = "videos-3.earthcam.com"
_PROVIDER_PATH = re.compile(r"^/fecnetwork/(\d+)\.flv/playlist\.m3u8$", re.IGNORECASE)
_FECNETWORK_ID = re.compile(r"/fecnetwork/(\d+)\.flv/", re.IGNORECASE)
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_ECTV_HINT_PATHS = ("/api/ectv/player/playlist", "/api/ectv/config")


@dataclass(frozen=True)
class EarthCamDecision:
    provider: str
    camera_id: str | None
    source_url: str
    technology: str
    source_role: str
    binding_status: str
    binding_confidence: float
    evidence: tuple[str, ...]
    validation_status: str
    keep: bool


class EarthCamExpiryGuard:
    """One page rediscovery after a live EarthCam HLS fails. No token minting."""

    def __init__(self) -> None:
        self.page_url: str | None = None
        self.accepted_live = False
        self.rediscovery_used = False

    def bind_page(self, page_url: str | None) -> None:
        page = (page_url or "").strip()
        if page == (self.page_url or ""):
            return
        self.page_url = page or None
        self.accepted_live = False
        self.rediscovery_used = False

    def note_live_accepted(self) -> None:
        self.accepted_live = True

    def decide(
        self,
        *,
        status_code: int | None = None,
        error: str | None = None,
        playlist_valid: bool | None = None,
        reason: str | None = None,
    ) -> str:
        """Return 'rediscover' or 'fail'. Never invents a token."""
        del status_code, error, playlist_valid, reason
        if not self.accepted_live:
            return "fail"
        if self.rediscovery_used:
            return "fail"
        self.rediscovery_used = True
        return "rediscover"


def applies(url: str | None) -> bool:
    host = _host(url)
    return bool(host) and (host == "earthcam.com" or host.endswith(".earthcam.com"))


def is_ectv_player_hint(url: str | None) -> bool:
    if not applies(url):
        return False
    path = _path(url)
    return any(path.startswith(token) or token in path for token in _ECTV_HINT_PATHS)


def session_rejects_hls(url: str | None) -> bool:
    """URL-only hard rejects. Binding evidence is applied in discovery."""
    if not applies(url):
        return False
    role = _url_role(url)
    return role in {BINDING_ARCHIVE, BINDING_SHARED}


def filter_hls_candidate(
    url: str,
    *,
    page_url: str | None = None,
    referer: str | None = None,
    initiator: str | None = None,
    source_type: str | None = "hls",
    from_ectv_playlist: bool = False,
    extracted_from: str | None = None,
    playlist_body: str | bytes | None = None,
) -> EarthCamDecision:
    camera_id = page_camera_id(page_url)
    validation = "skipped"
    if playlist_body is not None:
        validation = "ok" if is_valid_hls_manifest(playlist_body) else "invalid"
        if validation == "invalid":
            return _decision(
                url,
                camera_id=camera_id,
                status=BINDING_UNKNOWN,
                role="invalid",
                evidence=(),
                confidence=0.0,
                validation=validation,
                keep=False,
            )

    from_shared_api = from_ectv_playlist or _from_shared_ectv(
        url, extracted_from=extracted_from, referer=referer, initiator=initiator
    )
    role = _url_role(url)
    if role == BINDING_ARCHIVE:
        return _decision(
            url,
            camera_id=camera_id,
            status=BINDING_ARCHIVE,
            role="archive",
            evidence=(EVIDENCE_ARCHIVE,),
            confidence=1.0,
            validation=validation,
            keep=False,
        )
    if role == BINDING_SHARED or from_shared_api:
        return _decision(
            url,
            camera_id=camera_id,
            status=BINDING_SHARED,
            role="shared",
            evidence=(EVIDENCE_SHARED,),
            confidence=0.95,
            validation=validation,
            keep=False,
        )

    evidence = _strong_evidence(
        url,
        page_url=page_url,
        referer=referer,
        initiator=initiator,
        source_type=source_type,
    )
    keep = (
        EVIDENCE_PROVIDER in evidence
        and len(evidence) >= MIN_STRONG_EVIDENCE
        and not from_shared_api
        and not is_listing_page(page_url)
    )
    if keep:
        return _decision(
            url,
            camera_id=camera_id,
            status=BINDING_CAMERA_SPECIFIC,
            role="live",
            evidence=evidence,
            confidence=min(1.0, 0.55 + 0.15 * len(evidence)),
            validation=validation,
            keep=True,
        )
    return _decision(
        url,
        camera_id=camera_id,
        status=BINDING_UNKNOWN,
        role="unknown",
        evidence=evidence or (),
        confidence=0.2 if evidence else 0.0,
        validation=validation,
        keep=False,
    )


def is_valid_hls_manifest(body: str | bytes | None) -> bool:
    if body is None:
        return False
    text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    head = text.lstrip()
    if not head.startswith("#EXTM3U"):
        return False
    upper = head.upper()
    return "#EXT-X-" in upper or "#EXTINF" in upper


def page_camera_id(page_url: str | None) -> str | None:
    if not page_url:
        return None
    for key, value in parse_qsl(urlparse(page_url).query, keep_blank_values=True):
        if key.lower() == "cam" and value.strip():
            return value.strip()
    return None


def fecnetwork_id(url: str | None) -> str | None:
    match = _FECNETWORK_ID.search(_path(url))
    return match.group(1) if match else None


def provider_pattern_match(url: str | None) -> bool:
    if _host(url) != _PROVIDER_HOST:
        return False
    return bool(_PROVIDER_PATH.match(_path(url)))


def mask_url(url: str | None) -> str:
    raw = url or ""
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.query:
        return raw
    pairs = [
        (key, "*") if key.lower() in TOKEN_QUERY_NAMES else (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunparse(parsed._replace(query=urlencode(pairs, safe="*")))


def durable_pattern(url: str | None) -> str:
    masked = mask_url(url)
    return _FECNETWORK_ID.sub("/fecnetwork/{id}.flv/", masked)


def mask_text(text: str | None) -> str:
    if not text:
        return ""
    return _URL_IN_TEXT.sub(lambda match: mask_url(match.group(0)), text)


def mask_log_value(key: str, value: object) -> object:
    name = (key or "").lower().replace("-", "_")
    if name in _SECRET_LOG_KEYS:
        return "*"
    if isinstance(value, str):
        return mask_text(value)
    return value


def safe_log_fields(**fields: object) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in fields.items():
        name = key.lower().replace("-", "_")
        if name in _SECRET_LOG_KEYS:
            continue
        out[key] = mask_log_value(key, value)
    return out


def _decision(
    url: str,
    *,
    camera_id: str | None,
    status: str,
    role: str,
    evidence: tuple[str, ...],
    confidence: float,
    validation: str,
    keep: bool,
) -> EarthCamDecision:
    return EarthCamDecision(
        provider=PROVIDER,
        camera_id=camera_id,
        source_url=url,
        technology="hls",
        source_role=role,
        binding_status=status,
        binding_confidence=confidence,
        evidence=evidence,
        validation_status=validation,
        keep=keep,
    )


def _url_role(url: str | None) -> str | None:
    host = _host(url)
    path = _path(url)
    raw = (url or "").lower()
    if "video2archives.earthcam.com" in host or "/archives/" in path or "/archive/" in path:
        return BINDING_ARCHIVE
    if host.startswith("ectvradio.") or "/earthcamradio/" in path:
        return BINDING_SHARED
    if is_ectv_player_hint(url):
        return BINDING_SHARED
    ident = fecnetwork_id(url)
    if ident in _SHARED_FECNETWORK_IDS:
        return BINDING_SHARED
    if "ectvradio." in raw:
        return BINDING_SHARED
    return None


def _from_shared_ectv(
    url: str,
    *,
    extracted_from: str | None,
    referer: str | None,
    initiator: str | None,
) -> bool:
    for candidate in (url, extracted_from, referer, initiator):
        if is_ectv_player_hint(candidate):
            return True
    return False


def _strong_evidence(
    url: str,
    *,
    page_url: str | None,
    referer: str | None,
    initiator: str | None,
    source_type: str | None,
) -> tuple[str, ...]:
    evidence: list[str] = []
    if _page_context_match(page_url, referer):
        evidence.append(EVIDENCE_PAGE)
    if _initiator_match(page_url, initiator):
        evidence.append(EVIDENCE_INITIATOR)
    if _stream_path_match(url, source_type):
        evidence.append(EVIDENCE_STREAM)
    if provider_pattern_match(url):
        evidence.append(EVIDENCE_PROVIDER)
    return tuple(evidence)


def _page_context_match(page_url: str | None, referer: str | None) -> bool:
    page = referer or page_url
    if not _is_earthcam_camera_page(page) or not _is_earthcam_camera_page(page_url or page):
        return False
    return _same_camera_page(page, page_url or page)


def _initiator_match(page_url: str | None, initiator: str | None) -> bool:
    if not initiator or not _is_earthcam_camera_page(initiator):
        return False
    if is_ad_or_tracking(initiator):
        return False
    if page_url and not _same_camera_page(initiator, page_url):
        return False
    return True


def _is_earthcam_camera_page(url: str | None) -> bool:
    if not applies(url) or is_listing_page(url) or is_ad_or_tracking(url):
        return False
    parsed = urlparse(url or "")
    if page_camera_id(url):
        return True
    path = (parsed.path or "/").rstrip("/") or "/"
    return path not in {"/", "/mapsearch"}


def _same_camera_page(url_a: str | None, url_b: str | None) -> bool:
    cam_a = page_camera_id(url_a)
    cam_b = page_camera_id(url_b)
    if cam_a and cam_b:
        return cam_a.lower() == cam_b.lower()
    return _norm_page(url_a) == _norm_page(url_b)


def _norm_page(url: str | None) -> str:
    parsed = urlparse((url or "").strip())
    path = (parsed.path or "/").rstrip("/") or "/"
    return f"{(parsed.hostname or '').lower()}{path}?{parsed.query.lower()}"


def _stream_path_match(url: str | None, source_type: str | None) -> bool:
    path = _path(url)
    if path.endswith(".m3u8") or path.endswith("/playlist.m3u8"):
        return True
    return (source_type or "").lower() == "hls"


def _host(url: str | None) -> str:
    return (urlparse(url or "").hostname or "").lower()


def _path(url: str | None) -> str:
    return urlparse(url or "").path or ""
