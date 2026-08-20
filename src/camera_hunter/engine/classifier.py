from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlunparse

from camera_hunter.models import CameraSource, SourceRole, SourceType

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm"}
HLS_EXTS = {".m3u8"}
DASH_EXTS = {".mpd"}
MJPEG_EXTS = {".mjpg", ".mjpeg"}
MJPEG_HINTS = ("mjpeg", "mjpg", "multipart/x-mixed-replace")

IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
}
HLS_MIMES = {
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/mpegurl",
    "application/vnd.apple.mpegurl.audio",
    "audio/mpegurl",
    "audio/x-mpegurl",
}
DASH_MIMES = {
    "application/dash+xml",
}
MJPEG_MIMES = {
    "multipart/x-mixed-replace",
}

# HLS/DASH fragments — not the camera source itself.
FRAGMENT_EXTS = {".ts", ".m4s", ".cmfv", ".cmfa", ".m4t"}
FRAGMENT_MIMES = {"video/mp2t"}

LISTING_PAGE_HINTS = ("mapsearch",)
THUMBNAIL_URL_HINTS = (
    "/camshots/",
)
UI_ASSET_HINTS = (
    "openstreetmap.org",
    "/leaflet",
    "/images/header/",
    "/images/footer/",
    "apple-touch",
    "favicon",
    "/map_icons/",
    "icon-fullscreen",
    "icon_body",
    "/icons/",
    "logo.earthcam",
    "blank.gif",
    "blank.png",
    "page_bg",
    "arrow-caret",
    "morearrow",
    "hofstar",
    "cookiebot",
    "social-media-thumbnail",
    "facebook-icon",
    "instagram-icon",
    "linkedin-icon",
    "youtube-icon",
    "threads_icon",
    "touch-icon",
    "/ecnplayerhtml5/images/",
    "map_icon",
    "map_image.jpg",
    "/images/logos/",
    "loading.gif",
    "/ads/",
    "_ad.jpg",
    "_ad.png",
)

AD_TRACKING_HINTS = (
    "googlesyndication",
    "doubleclick.net",
    "googleads.",
    "googletagmanager",
    "google-analytics",
    "googleadservices",
    "pagead2.google",
    "adservice.google",
    "2mdn.net",
    "gstatic.com/ads",
    "imasdk.googleapis",
    "facebook.net",
    "facebook.com",
    "fbcdn.net",
    "scorecardresearch",
    "quantserve",
    "adsystem",
    "adnxs.com",
    "adsrvr.org",
    "advertising.com",
    "prebid",
    "criteo.com",
    "taboola",
    "outbrain",
    "adsbygoogle",
    "/pagead/",
    "cdn.skylinewebcams.com/as/",
    "ad.skylinewebcams.com",
    "fundingchoicesmessages.google",
    "adtrafficquality.google",
    "googletagservices",
    "google.com/pagead",
    "google.com/adsense",
    "ads.google.com",
    "tpc.googlesyndication",
)

CACHE_BUST_KEYS = {
    "t",
    "ts",
    "time",
    "timestamp",
    "_",
    "nocache",
    "cache",
    "cb",
    "r",
    "rand",
    "random",
    "v",
    "ver",
}


@dataclass
class ObservedRequest:
    url: str
    mime_type: str | None = None
    method: str = "GET"
    resource_type: str | None = None
    source: str = "NETWORK REQUEST"
    page_url: str | None = None
    navigation_index: int = 0
    session_id: int = 0
    request_headers: dict[str, str] | None = None
    document_url: str | None = None


def _path_ext(url: str) -> str:
    path = urlparse(url).path.lower()
    if "." not in path.rsplit("/", 1)[-1]:
        return ""
    return "." + path.rsplit(".", 1)[-1]


def _strip_cache_bust(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    kept = {
        k: v
        for k, v in qs.items()
        if k.lower() not in CACHE_BUST_KEYS and not re.fullmatch(r"\d+", k or "")
    }
    # Rebuild query preserving multi-values simply
    parts: list[str] = []
    for k, values in kept.items():
        for val in values:
            parts.append(f"{k}={val}" if val != "" else k)
    query = "&".join(parts)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, "")
    )


def _normalize_mime(mime: str | None) -> str:
    if not mime:
        return ""
    return mime.lower().split(";")[0].strip()


def _mime_suggests(mime: str | None) -> SourceType | None:
    m = _normalize_mime(mime)
    if not m:
        return None
    if m in FRAGMENT_MIMES:
        return None
    if m in IMAGE_MIMES:
        return SourceType.IMAGE
    if m in VIDEO_MIMES or m.startswith("video/"):
        return SourceType.VIDEO
    if m in HLS_MIMES:
        return SourceType.HLS
    if m in DASH_MIMES:
        return SourceType.DASH
    if m in MJPEG_MIMES or "multipart/x-mixed-replace" in m:
        return SourceType.MJPEG
    return None


def is_listing_page(url: str | None) -> bool:
    if not url:
        return False
    lower = url.lower()
    return any(h in lower for h in LISTING_PAGE_HINTS)


def looks_like_thumbnail_url(url: str) -> bool:
    lower = url.lower()
    return any(h in lower for h in THUMBNAIL_URL_HINTS)


def looks_like_ui_asset(url: str) -> bool:
    lower = url.lower()
    return any(h in lower for h in UI_ASSET_HINTS)


# Live JPEG camera feed vs ordinary page image. Used only when arming the
# JPEG viewer — classify_url still records the IMAGE itself.
JPEG_FEED_MIN_SCORE = 30
_JPEG_FEED_PATH_SEGMENTS = {
    "jpeg",
    "jpg",
    "cam",
    "camera",
    "livecam",
    "webcams",
    "webcam",
    "snapshot",
    "snapshots",
    "stillimage",
    "stills",
    "axis-cgi",
    "cgi-bin",
    "oneshot",
    "mjpg",
    "mjpeg",
}
_JPEG_FEED_BASENAMES = {
    "webcam",
    "livecam",
    "snapshot",
    "stillimage",
    "still",
    "snap",
    "latest",
    "current",
    "live",
    "oneshot",
    "image",
    "cam",
    "camera",
    "record",
    "last",
}
_JPEG_CHROME_PATH_HINTS = (
    "/themes/",
    "/template",
    "/assets/images/home",
    "/images/home/",
    "/images/header",
    "/images/footer",
    "/images/banner",
    "/icons/",
    "/logo",
)
_JPEG_CHROME_NAME_HINTS = (
    "intro",
    "banner",
    "hero",
    "featured",
    "header",
    "footer",
    "logo",
    "sprite",
    "background",
    "wallpaper",
    "og-image",
    "opengraph",
    "placeholder",
    "dummy",
)
_JPEG_CAM_QUERY_KEYS = ("cam", "camera", "webcam", "channel", "stream", "camid", "cameraid")
_JPEG_GENERIC_SEGMENTS = {
    "www",
    "com",
    "net",
    "org",
    "html",
    "php",
    "asp",
    "aspx",
    "index",
    "home",
    "page",
    "images",
    "image",
    "img",
    "assets",
    "static",
    "content",
    "uploads",
    "themes",
    "app",
    "webroot",
    "css",
    "js",
    "fonts",
    "media",
    "video",
    "live",
    "cam",
    "camera",
    "webcam",
    "jpeg",
    "jpg",
    "demo",
    "timelapse",
    "wp-content",
    "wp-includes",
}
_CMS_MEDIA_DATE_RE = re.compile(r"/20\d{2}/\d{2}/")


def _jpeg_path_segments(url: str) -> list[str]:
    path = urlparse(url).path.lower()
    return [p for p in path.split("/") if p]


def _jpeg_basename_stem(url: str) -> str:
    name = urlparse(url).path.rsplit("/", 1)[-1].lower()
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name


def _jpeg_query_tokens(url: str, keys: tuple[str, ...] | None = None) -> set[str]:
    qs = parse_qs(urlparse(url).query, keep_blank_values=False)
    wanted = {k.lower() for k in (keys or _JPEG_CAM_QUERY_KEYS)}
    tokens: set[str] = set()
    for key, values in qs.items():
        if key.lower() not in wanted:
            continue
        for val in values:
            token = (val or "").strip().lower()
            if len(token) >= 3:
                tokens.add(token)
    return tokens


def _jpeg_looks_like_page_chrome(url: str) -> bool:
    lower = url.lower()
    if any(h in lower for h in _JPEG_CHROME_PATH_HINTS):
        return True
    stem = _jpeg_basename_stem(url)
    return any(h in stem for h in _JPEG_CHROME_NAME_HINTS)


def _jpeg_looks_like_dated_media(url: str) -> bool:
    return bool(_CMS_MEDIA_DATE_RE.search(urlparse(url).path.lower()))


def _jpeg_has_feed_path(url: str) -> bool:
    return any(seg in _JPEG_FEED_PATH_SEGMENTS for seg in _jpeg_path_segments(url))


def _jpeg_has_feed_filename(url: str) -> bool:
    stem = _jpeg_basename_stem(url)
    if stem in _JPEG_FEED_BASENAMES:
        return True
    if re.fullmatch(r"\d+", stem or ""):
        return True
    parts = [p for p in re.split(r"[-_.]", stem) if p]
    return any(token in parts for token in ("webcam", "livecam", "snapshot"))


def _jpeg_linked_to_document(url: str, document_url: str | None) -> bool:
    if not document_url:
        return False
    image = url.lower()
    for token in _jpeg_query_tokens(document_url):
        if token in image:
            return True
    doc_segs = [
        s.rsplit(".", 1)[0]
        for s in _jpeg_path_segments(document_url)
        if s.rsplit(".", 1)[0] not in _JPEG_GENERIC_SEGMENTS and len(s) >= 4
    ]
    img_blob = " ".join(_jpeg_path_segments(url)) + " " + urlparse(url).query.lower()
    return any(seg in img_blob for seg in doc_segs)


def jpeg_camera_feed_score(
    url: str,
    *,
    document_url: str | None = None,
    discovery_source: str = "",
    hit_count: int = 1,
    source_type: SourceType | None = None,
) -> int:
    """How strongly `url` looks like the selected camera's live JPEG feed.

    0 means ordinary page image — not a JPEG camera source to play.
    """
    if not url:
        return 0
    feed_path = _jpeg_has_feed_path(url)
    feed_file = _jpeg_has_feed_filename(url)
    doc_link = _jpeg_linked_to_document(url, document_url)
    chrome = _jpeg_looks_like_page_chrome(url)
    dated = _jpeg_looks_like_dated_media(url)
    refresh = hit_count >= 2 or source_type == SourceType.REFRESH_IMAGE
    if chrome and not (feed_path or feed_file or doc_link):
        return 0
    if dated and not (feed_path or feed_file or doc_link or refresh):
        return 0
    score = 0
    if feed_path:
        score += 40
    if feed_file:
        score += 30
    if doc_link:
        score += 35
    if refresh:
        score += 30
    if discovery_source == "NETWORK RESPONSE":
        score += 10
    if chrome:
        score -= 40
    if score < JPEG_FEED_MIN_SCORE:
        return 0
    return score


def is_jpeg_camera_feed_candidate(
    url: str,
    *,
    document_url: str | None = None,
    discovery_source: str = "",
    hit_count: int = 1,
    source_type: SourceType | None = None,
) -> bool:
    return (
        jpeg_camera_feed_score(
            url,
            document_url=document_url,
            discovery_source=discovery_source,
            hit_count=hit_count,
            source_type=source_type,
        )
        >= JPEG_FEED_MIN_SCORE
    )


def should_replace_jpeg_candidate(
    selected_score: int | None,
    new_score: int,
    *,
    live: bool,
) -> bool:
    """Later JPEG wins only when it is a stronger feed and LIVE is not yet locked."""
    if new_score < JPEG_FEED_MIN_SCORE:
        return False
    if live:
        return False
    if selected_score is None:
        return True
    return new_score > selected_score


def is_ad_or_tracking(url: str) -> bool:
    lower = url.lower()
    return any(h in lower for h in AD_TRACKING_HINTS)


_THUMBNAIL_IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
_THUMBNAIL_EXTS = (".jpg", ".jpeg", ".png", ".webp")


_MAP_TILE_HINTS = (
    "/tiles/",
    "/tile/",
    "tile.openstreetmap",
    "basemaps.",
)


def is_listing_thumbnail_candidate(url: str, mime_type: str | None = None) -> bool:
    """True for mapsearch camera previews; false for tiles, ads, scripts, streams."""
    if not url or url.startswith(("data:", "blob:", "about:", "chrome:")):
        return False
    if is_ad_or_tracking(url) or looks_like_ui_asset(url):
        return False
    lower = url.lower()
    if any(h in lower for h in _MAP_TILE_HINTS):
        return False
    if looks_like_thumbnail_url(url):
        return True
    if ".m3u8" in lower or ".mpd" in lower or "mpegurl" in lower:
        return False
    mime = _normalize_mime(mime_type)
    if mime.startswith("video/") or mime in HLS_MIMES or mime in DASH_MIMES or mime in MJPEG_MIMES:
        return False
    if mime in _THUMBNAIL_IMAGE_MIMES:
        return True
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _THUMBNAIL_EXTS)


_LISTING_DROP_RESOURCE_TYPES = {
    "script",
    "stylesheet",
    "font",
    "xhr",
    "fetch",
    "websocket",
    "cspviolationreport",
    "ping",
    "prefetch",
    "preflight",
    "manifest",
    "signedexchange",
    "texttrack",
    "eventsource",
    "media",
    "document",
}


def should_emit_cdp_response(
    *,
    listing_capture: bool,
    url: str,
    mime_type: str | None = None,
    resource_type: str | None = None,
) -> bool:
    """Listing mode forwards only potential camera thumbnails into Python."""
    if not listing_capture:
        return True
    rtype = (resource_type or "").lower()
    if rtype in _LISTING_DROP_RESOURCE_TYPES:
        return False
    return is_listing_thumbnail_candidate(url, mime_type)


def should_classify_network_event(
    *,
    discovery_enabled: bool,
    url: str,
    mime_type: str | None = None,
    session_id: int = 0,
    current_generation: int = 0,
) -> bool:
    """Gate before classify_url. Listing: thumbnails only. Stale session: never."""
    if session_id and current_generation and session_id != current_generation:
        return False
    if discovery_enabled:
        return True
    return is_listing_thumbnail_candidate(url, mime_type)


def _is_skyline_context(url: str, page_url: str | None) -> bool:
    blob = f"{url} {page_url or ''}".lower()
    return "skylinewebcams.com" in blob


def infer_role(
    source_type: SourceType,
    url: str,
    page_url: str | None,
    mime_type: str | None = None,
) -> SourceRole | None:
    if source_type in {
        SourceType.HLS,
        SourceType.DASH,
        SourceType.VIDEO,
        SourceType.MJPEG,
    }:
        return SourceRole.CAMERA_SOURCE
    if source_type in {SourceType.IMAGE, SourceType.REFRESH_IMAGE}:
        if looks_like_ui_asset(url):
            return None
        mime_norm = _normalize_mime(mime_type)
        is_webp = (
            mime_norm == "image/webp"
            or url.lower().endswith(".webp")
            or ".webp?" in url.lower()
        )
        if is_webp or looks_like_thumbnail_url(url) or is_listing_page(page_url):
            return SourceRole.CAMERA_THUMBNAIL
        if _is_skyline_context(url, page_url):
            return None
        return SourceRole.CAMERA_SOURCE
    return SourceRole.CAMERA_SOURCE


def classify_url(
    url: str,
    *,
    mime_type: str | None = None,
    resource_type: str | None = None,
    hit_count: int = 1,
    source_page: str | None = None,
    discovery_source: str = "NETWORK RESPONSE",
    page_url: str | None = None,
    navigation_index: int = 0,
) -> CameraSource | None:
    if not url or url.startswith(("data:", "blob:", "about:", "chrome:")):
        return None
    if is_ad_or_tracking(url):
        return None

    lower = url.lower()
    ext = _path_ext(url)
    mime_type_hint = mime_type
    found_after = page_url or source_page
    nav_i = navigation_index
    mime_norm = _normalize_mime(mime_type_hint)

    if ext == ".gif" or mime_norm == "image/gif":
        return None
    if ext in FRAGMENT_EXTS or mime_norm in FRAGMENT_MIMES:
        return None

    def _make(
        source_type: SourceType,
        *,
        mime: str | None,
        confidence: float,
        notes: str | None = None,
    ) -> CameraSource:
        role = infer_role(source_type, url, found_after, mime)
        if role is None:
            return None
        return CameraSource(
            url=url,
            source_type=source_type,
            mime_type=mime,
            confidence=confidence,
            source_page=source_page,
            hit_count=hit_count,
            notes=notes,
            discovery_source=discovery_source,
            role=role,
            found_after=found_after,
            navigation_index=nav_i,
        )

    # WebSocket
    if lower.startswith(("ws://", "wss://")):
        return _make(SourceType.WEBSOCKET, mime=mime_type_hint, confidence=0.4)

    mime_guess = _mime_suggests(mime_type_hint)
    from_response = discovery_source == "NETWORK RESPONSE" and bool(mime_guess)
    conf_boost = 0.08 if from_response else 0.0

    # HLS / DASH by Content-Type or extension
    if mime_guess == SourceType.HLS or ext in HLS_EXTS or ".m3u8" in lower:
        return _make(
            SourceType.HLS,
            mime=mime_type_hint or "application/vnd.apple.mpegurl",
            confidence=min(0.95 + conf_boost, 1.0),
        )
    if mime_guess == SourceType.DASH or ext in DASH_EXTS or "/manifest.mpd" in lower:
        return _make(
            SourceType.DASH,
            mime=mime_type_hint or "application/dash+xml",
            confidence=min(0.9 + conf_boost, 1.0),
        )

    if mime_guess == SourceType.MJPEG or ext in MJPEG_EXTS or any(
        h in lower for h in MJPEG_HINTS
    ):
        return _make(
            SourceType.MJPEG,
            mime=mime_type_hint or "multipart/x-mixed-replace",
            confidence=min(0.85 + conf_boost, 1.0),
        )

    if ext in VIDEO_EXTS or mime_guess == SourceType.VIDEO:
        return _make(
            SourceType.VIDEO,
            mime=mime_type_hint or (f"video/{ext.lstrip('.')}" if ext else None),
            confidence=(0.95 if from_response else 0.9 if ext in VIDEO_EXTS else 0.7),
        )

    if ext in IMAGE_EXTS or mime_guess == SourceType.IMAGE:
        st = SourceType.REFRESH_IMAGE if hit_count >= 2 else SourceType.IMAGE
        conf = 0.9 if hit_count >= 2 else (0.95 if from_response else 0.85 if ext in IMAGE_EXTS else 0.65)
        guessed_mime = mime_type_hint
        if not guessed_mime and ext in {".jpg", ".jpeg"}:
            guessed_mime = "image/jpeg"
        elif not guessed_mime and ext == ".png":
            guessed_mime = "image/png"
        elif not guessed_mime and ext == ".webp":
            guessed_mime = "image/webp"
        elif not guessed_mime and ext == ".gif":
            guessed_mime = "image/gif"
        return _make(
            st,
            mime=guessed_mime,
            confidence=conf,
            notes="repeated requests / cache-busting" if hit_count >= 2 else None,
        )

    if resource_type in {"Media", "media", "ResourceTypeMedia"} and mime_guess is None:
        return _make(
            SourceType.UNKNOWN_MEDIA,
            mime=mime_type_hint,
            confidence=0.35,
        )

    return None


def _best_source_label(group: list[ObservedRequest]) -> str:
    labels = [g.source for g in group if g.source]
    if "NETWORK RESPONSE" in labels:
        return "NETWORK RESPONSE"
    if "NETWORK REQUEST" in labels:
        return "NETWORK REQUEST"
    if labels:
        return labels[0]
    return "DOM"


def merge_observations(
    observations: list[ObservedRequest],
    *,
    source_page: str | None,
    extra_urls: list[tuple[str, str | None]] | None = None,
) -> list[CameraSource]:
    """Classify and merge network observations into CameraSource list.

    Refresh-image detection uses *network* hits only (cache-busting / repeats).
    DOM extras fill gaps without inflating hit counts.
    """
    net_by_base: dict[str, list[ObservedRequest]] = defaultdict(list)
    for obs in observations:
        net_by_base[_strip_cache_bust(obs.url)].append(obs)

    extra_by_base: dict[str, list[ObservedRequest]] = defaultdict(list)
    if extra_urls:
        for url, mime in extra_urls:
            key = _strip_cache_bust(url)
            extra_by_base[key].append(
                ObservedRequest(
                    url=url,
                    mime_type=mime,
                    source="DOM",
                    page_url=source_page,
                )
            )

    all_bases = set(net_by_base) | set(extra_by_base)
    results: list[CameraSource] = []
    seen: set[tuple[str, SourceType, SourceRole]] = set()

    for base in all_bases:
        net_group = net_by_base.get(base, [])
        extra_group = extra_by_base.get(base, [])
        combined = net_group + extra_group
        net_urls = [g.url for g in net_group]
        unique_net = len(set(net_urls))

        response_obs = [g for g in net_group if g.source == "NETWORK RESPONSE"]
        mime = next((g.mime_type for g in response_obs if g.mime_type), None)
        if not mime:
            mime = next((g.mime_type for g in combined if g.mime_type), None)
        rtype = next((g.resource_type for g in combined if g.resource_type), None)
        display_url = (
            response_obs[0].url if response_obs else (net_urls[0] if net_urls else extra_group[0].url)
        )
        discovery_source = _best_source_label(net_group or extra_group)
        page_url = next((g.page_url for g in response_obs if g.page_url), None)
        if not page_url:
            page_url = next((g.page_url for g in combined if g.page_url), None)
        nav_i = next((g.navigation_index for g in combined if g.navigation_index), 0)

        src = classify_url(
            display_url,
            mime_type=mime,
            resource_type=rtype,
            hit_count=unique_net if net_group else 1,
            source_page=source_page,
            discovery_source=discovery_source,
            page_url=page_url or source_page,
            navigation_index=nav_i,
        )
        if src is None:
            continue
        key = (src.url, src.source_type, src.role)
        if src.source_type == SourceType.IMAGE and unique_net >= 2:
            st = SourceType.REFRESH_IMAGE
            role = infer_role(st, src.url, src.found_after, src.mime_type)
            if role is None:
                continue
            src = CameraSource(
                url=src.url,
                source_type=st,
                mime_type=src.mime_type,
                confidence=max(src.confidence, 0.9),
                source_page=source_page,
                hit_count=unique_net,
                notes="repeated requests / cache-busting",
                discovery_source=src.discovery_source,
                role=role,
                found_after=src.found_after,
                navigation_index=src.navigation_index,
            )
            key = (src.url, src.source_type, src.role)
        if key in seen:
            continue
        seen.add(key)
        results.append(src)

    results.sort(
        key=lambda s: (
            0 if s.is_camera_hit() and s.is_stream() else 1,
            0 if s.discovery_source == "NETWORK RESPONSE" else 1,
            0 if s.is_direct_camera() else 1,
            -s.confidence,
            s.source_type.value,
            s.url,
        )
    )
    return results
