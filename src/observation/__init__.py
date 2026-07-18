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
from observation.observation_manager import (
    OBSERVATION_POINTS_FILE,
    ObservationManager,
    observation_manager,
)
from observation.observation_point import ObservationPoint

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

    if name == "geo_context":
        from observation.geo_context import geo_context

        return geo_context

    if name == "GeoContext":
        from observation.geo_context import GeoContext

        return GeoContext

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
