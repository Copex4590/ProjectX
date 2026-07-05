# ============================================================================
# Project X
# Observation Coordinates Helpers
# ============================================================================

from __future__ import annotations

import math

from engines.rtl.hybrid_engine import CAMERA_LAT, CAMERA_LON
from observation.observation_manager import observation_manager


def observation_coordinates() -> tuple[float, float] | None:

    return observation_manager.coordinates()


def fallback_coordinates() -> tuple[float, float]:

    coords = observation_coordinates()

    if coords is not None:
        return coords

    return CAMERA_LAT, CAMERA_LON


def distance_km_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float:

    if origin_lat is None or origin_lon is None:
        origin_lat, origin_lon = fallback_coordinates()

    delta_lat = latitude - origin_lat
    delta_lon = longitude - origin_lon
    return math.sqrt(delta_lat ** 2 + delta_lon ** 2) * 111.0


def bearing_deg_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float:

    if origin_lat is None or origin_lon is None:
        origin_lat, origin_lon = fallback_coordinates()

    lat1 = math.radians(origin_lat)
    lat2 = math.radians(latitude)
    dlon = math.radians(longitude - origin_lon)

    x = math.sin(dlon) * math.cos(lat2)
    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0
