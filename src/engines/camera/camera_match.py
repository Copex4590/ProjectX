# ============================================================================
# Project X
# Camera Match
# ============================================================================

from dataclasses import dataclass

from models.camera import Camera

WEIGHT_DISTANCE = 0.40
WEIGHT_DIRECTION = 0.35
WEIGHT_MARGIN = 0.25


@dataclass(frozen=True)
class CameraMatch:

    camera: Camera
    distance_km: float
    bearing_difference_deg: float
    visibility_margin: float
    confidence: float


def bearing_difference_deg(camera: Camera, lat: float, lon: float) -> float:

    target_bearing = camera.bearing_deg_to(lat, lon)
    delta = abs(target_bearing - camera.direction_deg)

    if delta > 180.0:
        delta = 360.0 - delta

    return delta


def compute_confidence(
    camera: Camera,
    distance_km: float,
    bearing_difference_deg: float,
    visibility_margin: float,
) -> float:

    radius = camera.visibility_radius_km
    half_fov = camera.fov_deg / 2.0

    if radius <= 0.0 or half_fov <= 0.0:
        return 0.0

    distance_score = max(0.0, 1.0 - (distance_km / radius))
    direction_score = max(0.0, 1.0 - (bearing_difference_deg / half_fov))
    margin_score = max(0.0, min(1.0, visibility_margin / radius))

    confidence = (
        distance_score * WEIGHT_DISTANCE
        + direction_score * WEIGHT_DIRECTION
        + margin_score * WEIGHT_MARGIN
    )

    return round(min(1.0, max(0.0, confidence)), 4)


def build_camera_match(camera: Camera, lat: float, lon: float) -> CameraMatch:

    distance_km = camera.distance_km_to(lat, lon)
    bearing_delta = bearing_difference_deg(camera, lat, lon)
    visibility_margin = max(0.0, camera.visibility_radius_km - distance_km)
    confidence = compute_confidence(
        camera,
        distance_km,
        bearing_delta,
        visibility_margin,
    )

    return CameraMatch(
        camera=camera,
        distance_km=round(distance_km, 4),
        bearing_difference_deg=round(bearing_delta, 4),
        visibility_margin=round(visibility_margin, 4),
        confidence=confidence,
    )
