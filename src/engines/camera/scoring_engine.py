# ============================================================================
# Project X
# Camera Scoring Engine (SAVE-217)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass

from cameras.manager import CameraManager, camera_manager
from engines.camera.camera_match import (
    CameraMatch,
    bearing_difference_deg,
    build_camera_match,
)
from engines.camera.link_states import CameraLinkState
from models.camera import Camera
from models.ship import Ship


@dataclass(frozen=True)
class ScoreBreakdown:
    """Why a camera scored the way it did (human-readable factors)."""

    distance_score: float
    direction_score: float
    margin_score: float
    total: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoredCamera:
    """Ranked camera candidate with status and explanation."""

    match: CameraMatch
    breakdown: ScoreBreakdown
    state: CameraLinkState
    in_fov: bool

    @property
    def camera(self) -> Camera:

        return self.match.camera

    @property
    def score(self) -> float:

        return self.breakdown.total


def _camera_runtime_state(camera: Camera, *, preferred: bool, busy: bool) -> CameraLinkState:

    if busy:
        return CameraLinkState.BUSY
    if preferred:
        return CameraLinkState.PREFERRED
    if not camera.enabled:
        return CameraLinkState.OFFLINE
    if camera.visibility_radius_km <= 0.0 or camera.fov_deg <= 0.0:
        return CameraLinkState.OFFLINE
    if not (
        camera.playback_stream_url
        or camera.playback_snapshot_url
        or camera.playback_web_url
        or camera.playback_provider_type
    ):
        # Configured but no stream — still Online for coverage, Offline for play.
        return CameraLinkState.ONLINE if camera.enabled else CameraLinkState.OFFLINE
    return CameraLinkState.ONLINE


class CameraScoringEngine:
    """Prioritize cameras by distance, FOV alignment, and visibility margin."""

    WEIGHT_DISTANCE = 0.40
    WEIGHT_DIRECTION = 0.35
    WEIGHT_MARGIN = 0.25

    def __init__(self, manager: CameraManager | None = None):

        self._manager = manager or camera_manager

    def score_camera(
        self,
        camera: Camera,
        lat: float,
        lon: float,
        *,
        preferred: bool = False,
        busy: bool = False,
    ) -> ScoredCamera:

        match = build_camera_match(camera, lat, lon)
        radius = max(0.0, float(camera.visibility_radius_km or 0.0))
        half_fov = max(0.0, float(camera.fov_deg or 0.0) / 2.0)

        if radius <= 0.0 or half_fov <= 0.0:
            breakdown = ScoreBreakdown(
                distance_score=0.0,
                direction_score=0.0,
                margin_score=0.0,
                total=0.0,
                reasons=("Camera has no usable coverage radius or FOV.",),
            )
            return ScoredCamera(
                match=match,
                breakdown=breakdown,
                state=_camera_runtime_state(camera, preferred=preferred, busy=busy),
                in_fov=False,
            )

        distance_score = max(0.0, 1.0 - (match.distance_km / radius))
        direction_score = max(0.0, 1.0 - (match.bearing_difference_deg / half_fov))
        margin_score = max(0.0, min(1.0, match.visibility_margin / radius))
        total = round(
            distance_score * self.WEIGHT_DISTANCE
            + direction_score * self.WEIGHT_DIRECTION
            + margin_score * self.WEIGHT_MARGIN,
            4,
        )

        reasons: list[str] = []
        reasons.append(
            f"Distance {match.distance_km:.2f} km / {radius:.2f} km "
            f"→ {distance_score * 100:.0f}% (weight {int(self.WEIGHT_DISTANCE * 100)}%)"
        )
        reasons.append(
            f"Bearing offset {match.bearing_difference_deg:.1f}° "
            f"vs FOV±{half_fov:.1f}° → {direction_score * 100:.0f}% "
            f"(weight {int(self.WEIGHT_DIRECTION * 100)}%)"
        )
        reasons.append(
            f"Visibility margin {match.visibility_margin:.2f} km "
            f"→ {margin_score * 100:.0f}% (weight {int(self.WEIGHT_MARGIN * 100)}%)"
        )

        in_fov = camera.can_observe(lat, lon)
        if in_fov:
            reasons.append("Ship is inside the camera coverage sector.")
        elif not camera.is_within_radius(lat, lon):
            reasons.append("Ship is outside the visibility radius.")
        else:
            reasons.append("Ship is outside the viewing direction (FOV).")

        if preferred:
            reasons.append("Selected as preferred (highest score).")
        if busy:
            reasons.append("Currently active / busy for this vessel.")

        breakdown = ScoreBreakdown(
            distance_score=round(distance_score, 4),
            direction_score=round(direction_score, 4),
            margin_score=round(margin_score, 4),
            total=total,
            reasons=tuple(reasons),
        )

        return ScoredCamera(
            match=match,
            breakdown=breakdown,
            state=_camera_runtime_state(camera, preferred=preferred, busy=busy),
            in_fov=in_fov,
        )

    def rank_for_ship(
        self,
        ship: Ship,
        *,
        active_camera_id: str | None = None,
        include_out_of_fov: bool = True,
        limit: int = 8,
    ) -> list[ScoredCamera]:

        cameras = list(self._manager.all())
        raw: list[ScoredCamera] = []

        for camera in cameras:
            scored = self.score_camera(camera, ship.lat, ship.lon)
            if not include_out_of_fov and not scored.in_fov:
                continue
            if scored.in_fov or scored.score > 0.05:
                raw.append(scored)

        # Prefer in-FOV first, then score.
        raw.sort(
            key=lambda item: (
                0 if item.in_fov else 1,
                -item.score,
                item.match.distance_km,
                item.camera.id,
            )
        )

        ranked: list[ScoredCamera] = []
        for index, item in enumerate(raw[: max(1, limit)]):
            preferred = index == 0 and item.in_fov
            busy = bool(active_camera_id) and item.camera.id == active_camera_id
            ranked.append(
                self.score_camera(
                    item.camera,
                    ship.lat,
                    ship.lon,
                    preferred=preferred,
                    busy=busy,
                )
            )

        return ranked

    def best_for_ship(self, ship: Ship) -> ScoredCamera | None:

        ranked = self.rank_for_ship(
            ship,
            include_out_of_fov=False,
            limit=1,
        )
        return ranked[0] if ranked else None

    def explain(self, scored: ScoredCamera) -> str:

        lines = [
            f"{scored.camera.name} — score {scored.score * 100:.1f}% "
            f"[{scored.state.value}]",
            *scored.breakdown.reasons,
        ]
        return "\n".join(lines)


camera_scoring_engine = CameraScoringEngine()
