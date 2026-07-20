# ============================================================================
# Project X
# Observation Package
# ============================================================================

from observation.coords import (
    coverage_bounding_box,
    fallback_coordinates,
    is_within_reference_coverage,
    max_observation_radius_km,
    observation_coordinates,
    reference_observation_point,
)
from observation.geo_context import GeoContext, geo_context
from observation.observation_point import ObservationPoint
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "OBSERVATION_POINTS_FILE",
    "GeoContext",
    "ObservationManager",
    "ObservationPoint",
    "coverage_bounding_box",
    "fallback_coordinates",
    "geo_context",
    "is_within_reference_coverage",
    "max_observation_radius_km",
    "observation_coordinates",
    "reference_observation_point",
    "observation_manager",
]


def __getattr__(name: str):
    if name == "ObservationManager":
        from observation.observation_manager import ObservationManager

        return ObservationManager
    if name == "observation_manager":
        return lazy_submodule_export(__name__, name)
    if name == "OBSERVATION_POINTS_FILE":
        from observation.observation_manager import observation_points_file

        return observation_points_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
