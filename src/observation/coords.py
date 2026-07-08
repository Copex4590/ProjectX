# ============================================================================
# Project X
# Observation Coordinates Helpers
# ============================================================================

from __future__ import annotations

import math

from observation.observation_manager import observation_manager


def observation_coordinates() -> tuple[float, float] | None:

    return observation_manager.coordinates()


def reference_coordinates() -> tuple[float, float] | None:

    return observation_manager.reference_coordinates()


def fallback_coordinates() -> tuple[float, float] | None:

    return reference_coordinates()


def distance_km_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float | None:

    if origin_lat is None or origin_lon is None:
        coords = fallback_coordinates()

        if coords is None:
            return None

        origin_lat, origin_lon = coords

    delta_lat = latitude - origin_lat
    delta_lon = longitude - origin_lon
    return math.sqrt(delta_lat ** 2 + delta_lon ** 2) * 111.0


_KM_PER_DEGREE_LAT = 111.0


def max_observation_radius_km(latitude: float, longitude: float) -> float:

    lat_margin_deg = min(latitude - (-90.0), 90.0 - latitude)
    lat_limit_km = lat_margin_deg * _KM_PER_DEGREE_LAT

    cos_lat = math.cos(math.radians(latitude))

    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6

    lon_margin_deg = min(longitude - (-180.0), 180.0 - longitude)
    lon_limit_km = lon_margin_deg * _KM_PER_DEGREE_LAT * abs(cos_lat)

    return max(0.0, min(lat_limit_km, lon_limit_km))


def coverage_bounding_box(
    latitude: float,
    longitude: float,
    coverage_radius_km: float,
) -> list[list[float]]:

    if coverage_radius_km <= 0:
        raise ValueError("coverage_radius_km must be positive")

    lat_delta = coverage_radius_km / _KM_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(latitude))

    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6

    lon_delta = coverage_radius_km / (_KM_PER_DEGREE_LAT * abs(cos_lat))

    lat_min = max(-90.0, latitude - lat_delta)
    lat_max = min(90.0, latitude + lat_delta)
    lon_min = max(-180.0, longitude - lon_delta)
    lon_max = min(180.0, longitude + lon_delta)

    return [[lat_min, lon_min], [lat_max, lon_max]]


def bearing_deg_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float | None:

    if origin_lat is None or origin_lon is None:
        coords = fallback_coordinates()

        if coords is None:
            return None

        origin_lat, origin_lon = coords

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
