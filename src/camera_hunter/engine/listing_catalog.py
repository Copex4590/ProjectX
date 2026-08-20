"""EarthCam mapsearch listing catalog — JSON places only, no HLS/LIVE.

Two listing APIs used by https://www.earthcam.com/mapsearch/:

1. In-network:
   GET .../get_locations_network.php?r=ecn&a=fetch
   payload ``data[0].places`` (ECN cameras, have ``id``)

2. Viewport / bbox (out of network):
   GET .../get_locations?nwx=&nwy=&nex=&ney=&sex=&sey=&swx=&swy=&zoom=
   payload ``[0].places`` (usually no ``id``)

This module does not open camera pages, extract tokens, or start a player.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

MAPSEARCH_PAGE_URL = "https://www.earthcam.com/mapsearch/"
NETWORK_LOCATIONS_URL = (
    "https://www.earthcam.com/api/mapsearch/"
    "get_locations_network.php?r=ecn&a=fetch"
)
BBOX_LOCATIONS_URL = "https://www.earthcam.com/api/mapsearch/get_locations"
DEFAULT_TIMEOUT_S = 30.0
SOURCE_NETWORK = "network"
SOURCE_BBOX = "bbox"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/javascript,*/*;q=0.1",
    "Referer": MAPSEARCH_PAGE_URL,
}

WORLD_BBOX = {
    "nwx": 85.0,
    "nwy": -180.0,
    "nex": 85.0,
    "ney": 180.0,
    "sex": -85.0,
    "sey": 180.0,
    "swx": -85.0,
    "swy": -180.0,
    "zoom": 4,
}


def _text(value: Any) -> str:

    if value is None:
        return ""
    return str(value).strip()


def normalize_web_url(url: str | None) -> str:

    raw = _text(url)
    if not raw:
        return ""
    parsed = urlparse(raw)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    host = (parsed.netloc or "").lower()
    scheme = (parsed.scheme or "https").lower()
    return urlunparse((scheme, host, path, "", parsed.query, ""))


def parse_posn(value: Any) -> tuple[float, float] | None:

    lat = lon = None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        lat, lon = value[0], value[1]
    elif isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lon = value.get("lon", value.get("lng", value.get("longitude")))
    else:
        return None
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat_f) or not math.isfinite(lon_f):
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None
    if abs(lat_f) > 90.0 or abs(lon_f) > 180.0:
        return None
    return lat_f, lon_f


def extract_places(payload: Any) -> list[dict]:
    """Return place dicts from network or bbox mapsearch JSON."""

    blocks: list = []
    if isinstance(payload, list):
        blocks = payload
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            blocks = data
        elif isinstance(data, dict):
            blocks = [data]
        elif isinstance(payload.get("places"), list):
            blocks = [payload]
    places: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        raw = block.get("places")
        if not isinstance(raw, list):
            continue
        places.extend(item for item in raw if isinstance(item, dict))
    return places


def thumbnail_from_place(place: Mapping[str, Any]) -> str:

    thumb = _text(place.get("thumbnail"))
    if thumb:
        return thumb
    icon = place.get("icon")
    if isinstance(icon, dict):
        return _text(icon.get("icon"))
    if isinstance(icon, str):
        return icon.strip()
    return ""


def stable_listing_key(place: Mapping[str, Any]) -> str | None:
    """Dedup key: listing id when present, otherwise normalized camera-page URL."""

    listing_id = _text(place.get("id"))
    if listing_id:
        return f"id:{listing_id}"
    web_url = normalize_web_url(_text(place.get("url")))
    if web_url:
        digest = hashlib.sha1(web_url.encode("utf-8")).hexdigest()[:20]
        return f"url:{digest}"
    coords = parse_posn(place.get("posn"))
    name = _text(place.get("name")).lower()
    if coords is None or not name:
        return None
    lat, lon = coords
    return f"geo:{name}:{lat:.5f}:{lon:.5f}"


@dataclass(frozen=True)
class ListingCamera:
    key: str
    source: str
    listing_id: str
    name: str
    lat: float
    lon: float
    web_url: str
    thumbnail_url: str
    location: str
    city: str
    country: str

    def to_dict(self) -> dict:

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ListingCamera | None:

        if not isinstance(data, Mapping):
            return None
        key = _text(data.get("key"))
        try:
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
        except (TypeError, ValueError):
            return None
        if not key or not math.isfinite(lat) or not math.isfinite(lon):
            return None
        return cls(
            key=key,
            source=_text(data.get("source")) or SOURCE_BBOX,
            listing_id=_text(data.get("listing_id")),
            name=_text(data.get("name")) or "EarthCam",
            lat=lat,
            lon=lon,
            web_url=_text(data.get("web_url")),
            thumbnail_url=_text(data.get("thumbnail_url")),
            location=_text(data.get("location")),
            city=_text(data.get("city")),
            country=_text(data.get("country")),
        )


def listing_camera_from_place(
    place: Mapping[str, Any],
    *,
    source: str,
) -> ListingCamera | None:

    if not isinstance(place, Mapping):
        return None
    coords = parse_posn(place.get("posn"))
    if coords is None:
        return None
    key = stable_listing_key(place)
    if not key:
        return None
    lat, lon = coords
    location = _text(place.get("location"))
    name = _text(place.get("name")) or location or "EarthCam"
    web_url = _text(place.get("url"))
    if not web_url:
        return None
    return ListingCamera(
        key=key,
        source=source,
        listing_id=_text(place.get("id")),
        name=name,
        lat=lat,
        lon=lon,
        web_url=web_url,
        thumbnail_url=thumbnail_from_place(place),
        location=location,
        city=_text(place.get("city")),
        country=_text(place.get("country")),
    )


def cameras_from_payload(payload: Any, *, source: str) -> list[ListingCamera]:

    cameras: list[ListingCamera] = []
    seen: set[str] = set()
    for place in extract_places(payload):
        camera = listing_camera_from_place(place, source=source)
        if camera is None or camera.key in seen:
            continue
        seen.add(camera.key)
        cameras.append(camera)
    return cameras


def bbox_query(
    *,
    nwx: float,
    nwy: float,
    nex: float,
    ney: float,
    sex: float,
    sey: float,
    swx: float,
    swy: float,
    zoom: int,
) -> dict[str, float | int]:

    return {
        "nwx": nwx,
        "nwy": nwy,
        "nex": nex,
        "ney": ney,
        "sex": sex,
        "sey": sey,
        "swx": swx,
        "swy": swy,
        "zoom": int(zoom),
    }


def bbox_from_corners(
    north: float,
    west: float,
    south: float,
    east: float,
    *,
    zoom: int,
) -> dict[str, float | int]:
    """Mapsearch bbox: nwx/nex/sex/swx are latitudes, *y are longitudes."""

    return bbox_query(
        nwx=north,
        nwy=west,
        nex=north,
        ney=east,
        sex=south,
        sey=east,
        swx=south,
        swy=west,
        zoom=zoom,
    )


def bbox_locations_url(params: Mapping[str, Any]) -> str:

    return f"{BBOX_LOCATIONS_URL}?{urlencode(dict(params))}"


def fetch_json(url: str, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> Any:

    request = Request(url, headers=_BROWSER_HEADERS, method="GET")
    with urlopen(request, timeout=float(timeout_s)) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def fetch_network_payload(*, timeout_s: float = DEFAULT_TIMEOUT_S) -> Any:

    return fetch_json(NETWORK_LOCATIONS_URL, timeout_s=timeout_s)


def fetch_bbox_payload(
    params: Mapping[str, Any],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Any:

    return fetch_json(bbox_locations_url(params), timeout_s=timeout_s)
