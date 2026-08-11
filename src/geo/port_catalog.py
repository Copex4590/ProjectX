# ============================================================================
# Project X — global port / place catalog (coord → name)
#
# Used only when a trusted voyage source supplies coordinates that need a
# human-readable place label. Never invents a ship's departure or route from
# AIS history / GPS track alone.
# ============================================================================

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.paths import resource_path, runtime_data_path

# Optional override next to voyage.db / user data.
_RUNTIME_PORTS = Path(runtime_data_path("ports.json"))
_RESOURCE_PORTS = Path(resource_path("geo", "ports.json"))

# Accept a hit only inside this radius (km). Wider would guess too freely.
_DEFAULT_MAX_KM = 3.0


@dataclass(frozen=True)
class PortMatch:
    name: str
    country: str = ""
    lat: float = 0.0
    lon: float = 0.0
    distance_km: float = 0.0
    source: str = "port_catalog"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _load_entries(path: Path) -> tuple[dict, ...]:
    if not path.is_file():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(raw, list):
        return ()
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except (TypeError, ValueError):
            continue
        if not name or (lat == 0.0 and lon == 0.0):
            continue
        out.append(
            {
                "name": name,
                "country": str(item.get("country") or "").strip(),
                "lat": lat,
                "lon": lon,
            }
        )
    return tuple(out)


@lru_cache(maxsize=1)
def _catalog_entries() -> tuple[dict, ...]:
    # Prefer runtime override when an operator ships a fuller global list.
    runtime = _load_entries(_RUNTIME_PORTS)
    if runtime:
        return runtime
    return _load_entries(_RESOURCE_PORTS)


class PortCatalog:
    """Nearest-port lookup against an optional global place list."""

    def reload(self) -> None:
        _catalog_entries.cache_clear()

    def available(self) -> bool:
        return bool(_catalog_entries())

    def nearest(
        self,
        lat: float,
        lon: float,
        *,
        max_km: float = _DEFAULT_MAX_KM,
    ) -> PortMatch | None:
        """Return a catalog hit within max_km, or None (no guessing)."""

        try:
            lat_f = float(lat)
            lon_f = float(lon)
            limit = float(max_km)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(lat_f) or not math.isfinite(lon_f):
            return None
        if lat_f == 0.0 and lon_f == 0.0:
            return None

        best: PortMatch | None = None
        for entry in _catalog_entries():
            dist = _haversine_km(lat_f, lon_f, entry["lat"], entry["lon"])
            if dist > limit:
                continue
            if best is None or dist < best.distance_km:
                best = PortMatch(
                    name=entry["name"],
                    country=entry["country"],
                    lat=entry["lat"],
                    lon=entry["lon"],
                    distance_km=dist,
                )
        return best

    def label_near(
        self,
        lat: float,
        lon: float,
        *,
        max_km: float = _DEFAULT_MAX_KM,
    ) -> str:
        match = self.nearest(lat, lon, max_km=max_km)
        if match is None:
            return ""
        if match.country:
            return f"{match.name}, {match.country}"
        return match.name


port_catalog = PortCatalog()
