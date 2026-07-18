# ============================================================================
# Project X
# Observation Coordinates Helpers
#
# Backward-compatible wrappers around GeoContext. New code should import
# observation.geo_context.geo_context directly.
# ============================================================================

from __future__ import annotations

import math

from observation.geo_context import EARTH_RADIUS_KM, geo_context
from observation.observation_manager import observation_manager
from observation.observation_point import ObservationPoint

_KM_PER_DEGREE_LAT = 111.0


def observation_coordinates() -> tuple[float, float] | None:

    return geo_context.coordinates()


def reference_coordinates() -> tuple[float, float] | None:

    return observation_manager.reference_coordinates()


def reference_observation_point() -> ObservationPoint | None:

    return geo_context.reference()


def fallback_coordinates() -> tuple[float, float] | None:
    """Deprecated alias for reference_coordinates()."""

    return geo_context.coordinates()


def is_within_reference_coverage(
    latitude: float | None,
    longitude: float | None,
) -> bool:

    return geo_context.is_within_coverage(latitude, longitude)


def distance_km_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float | None:

    return geo_context.distance_km(
        latitude,
        longitude,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )


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

    return geo_context.coverage_bounding_box(
        latitude,
        longitude,
        coverage_radius_km,
    )


def bearing_deg_from_origin(
    latitude: float,
    longitude: float,
    *,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> float | None:

    return geo_context.bearing_deg(
        latitude,
        longitude,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )


__all__ = [
    "EARTH_RADIUS_KM",
    "bearing_deg_from_origin",
    "coverage_bounding_box",
    "distance_km_from_origin",
    "fallback_coordinates",
    "is_within_reference_coverage",
    "max_observation_radius_km",
    "observation_coordinates",
    "reference_coordinates",
    "reference_observation_point",
]
