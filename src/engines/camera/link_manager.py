# ============================================================================
# Project X
# Intelligent Camera ↔ AIS Link Manager (SAVE-217)
# ============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import Lock

from cameras.manager import CameraManager, camera_manager
from database import registry
from engines.camera.coverage_model import (
    CameraCoverageModel,
    CoverageSector,
    camera_coverage_model,
)
from engines.camera.link_states import (
    EVENT_CAMERA_COVERAGE_TOGGLED,
    EVENT_CAMERA_LINK_CHANGED,
    EVENT_CAMERA_LINK_MODE,
    CameraLinkMode,
    CameraLinkState,
)
from engines.camera.scoring_engine import (
    CameraScoringEngine,
    ScoredCamera,
    camera_scoring_engine,
)
from events import eventbus
from models.ship import Ship

logger = logging.getLogger(__name__)

# Prefer a new camera only when it is clearly better than the current link.
AUTO_SWITCH_SCORE_DELTA = 0.08


@dataclass
class CameraLinkSnapshot:
    """Current link decision for the selected vessel."""

    mmsi: int | None = None
    mode: CameraLinkMode = CameraLinkMode.AUTO
    active: ScoredCamera | None = None
    alternatives: list[ScoredCamera] = field(default_factory=list)
    explanation: str = ""
    coverage_visible: bool = False
    switched: bool = False
    reason: str = ""


class IntelligentCameraLinkManager:
    """Assign best camera to a selected ship; auto-switch or manual override."""

    def __init__(
        self,
        scoring: CameraScoringEngine | None = None,
        coverage: CameraCoverageModel | None = None,
        cameras: CameraManager | None = None,
    ):

        self._scoring = scoring or camera_scoring_engine
        self._coverage = coverage or camera_coverage_model
        self._cameras = cameras or camera_manager
        self._lock = Lock()
        self._mode = CameraLinkMode.AUTO
        self._override_camera_id: str | None = None
        self._selected_mmsi: int | None = None
        self._active_camera_id: str | None = None
        self._coverage_visible = False
        self._last: CameraLinkSnapshot = CameraLinkSnapshot()

    @property
    def mode(self) -> CameraLinkMode:

        return self._mode

    @property
    def coverage_visible(self) -> bool:

        return self._coverage_visible

    @property
    def last_snapshot(self) -> CameraLinkSnapshot:

        with self._lock:
            return self._last

    def set_mode(self, mode: CameraLinkMode | str) -> CameraLinkMode:

        value = (
            mode
            if isinstance(mode, CameraLinkMode)
            else CameraLinkMode(str(mode))
        )
        with self._lock:
            self._mode = value
            if value == CameraLinkMode.AUTO:
                self._override_camera_id = None
        eventbus.publish(EVENT_CAMERA_LINK_MODE, mode=self._mode.value)
        return self.evaluate()

    def set_manual_override(self, camera_id: str | None) -> CameraLinkSnapshot:

        with self._lock:
            self._mode = CameraLinkMode.MANUAL
            self._override_camera_id = str(camera_id).strip() if camera_id else None
        eventbus.publish(EVENT_CAMERA_LINK_MODE, mode=CameraLinkMode.MANUAL.value)
        return self.evaluate(force_switch_reason="Manual override")

    def clear_manual_override(self) -> CameraLinkSnapshot:

        return self.set_mode(CameraLinkMode.AUTO)

    def set_coverage_visible(self, visible: bool) -> bool:

        with self._lock:
            self._coverage_visible = bool(visible)
            visible_now = self._coverage_visible
        eventbus.publish(EVENT_CAMERA_COVERAGE_TOGGLED, visible=visible_now)
        return visible_now

    def select_vessel(self, mmsi: int | None) -> CameraLinkSnapshot:

        with self._lock:
            self._selected_mmsi = int(mmsi) if mmsi is not None else None
            if self._mode == CameraLinkMode.AUTO:
                self._override_camera_id = None
        return self.evaluate(force_switch_reason="Vessel selected")

    def evaluate(self, *, force_switch_reason: str = "") -> CameraLinkSnapshot:

        with self._lock:
            mmsi = self._selected_mmsi
            mode = self._mode
            override_id = self._override_camera_id
            previous_id = self._active_camera_id
            coverage_visible = self._coverage_visible

        if mmsi is None:
            snapshot = CameraLinkSnapshot(
                mmsi=None,
                mode=mode,
                coverage_visible=coverage_visible,
                explanation="No vessel selected.",
                reason=force_switch_reason or "Cleared",
            )
            with self._lock:
                self._active_camera_id = None
                self._last = snapshot
            eventbus.publish(EVENT_CAMERA_LINK_CHANGED, snapshot=snapshot)
            return snapshot

        ship = registry.get(mmsi)
        if ship is None:
            snapshot = CameraLinkSnapshot(
                mmsi=mmsi,
                mode=mode,
                coverage_visible=coverage_visible,
                explanation="Vessel not found in registry.",
                reason=force_switch_reason or "Missing vessel",
            )
            with self._lock:
                self._active_camera_id = None
                self._last = snapshot
            eventbus.publish(EVENT_CAMERA_LINK_CHANGED, snapshot=snapshot)
            return snapshot

        ranked = self._scoring.rank_for_ship(
            ship,
            active_camera_id=previous_id,
            include_out_of_fov=True,
            limit=10,
        )
        in_fov = [item for item in ranked if item.in_fov]
        preferred = in_fov[0] if in_fov else None

        active: ScoredCamera | None = None
        switched = False
        reason = force_switch_reason

        if mode == CameraLinkMode.MANUAL and override_id:
            override = next(
                (item for item in ranked if item.camera.id == override_id),
                None,
            )
            if override is None:
                camera = self._cameras.get(override_id)
                if camera is not None:
                    override = self._scoring.score_camera(
                        camera,
                        ship.lat,
                        ship.lon,
                        busy=True,
                    )
            if override is not None and override.in_fov:
                active = self._scoring.score_camera(
                    override.camera,
                    ship.lat,
                    ship.lon,
                    preferred=False,
                    busy=True,
                )
                reason = reason or "Manual override active"
            else:
                # Left FOV or invalid — fall back to auto best.
                active = preferred
                switched = True
                reason = (
                    "Manual camera left coverage — switched to best available"
                    if preferred
                    else "Manual camera left coverage — no alternative"
                )
                with self._lock:
                    self._mode = CameraLinkMode.AUTO
                    self._override_camera_id = None
                mode = CameraLinkMode.AUTO
                eventbus.publish(EVENT_CAMERA_LINK_MODE, mode=mode.value)
        else:
            # AUTO: keep current if still in FOV and still competitive; else switch.
            current = next(
                (item for item in in_fov if item.camera.id == previous_id),
                None,
            )
            if current is not None and preferred is not None:
                # Hysteresis: keep current unless preferred is clearly better.
                if preferred.camera.id == current.camera.id:
                    active = self._scoring.score_camera(
                        current.camera,
                        ship.lat,
                        ship.lon,
                        preferred=True,
                        busy=True,
                    )
                elif preferred.score >= current.score + AUTO_SWITCH_SCORE_DELTA:
                    active = self._scoring.score_camera(
                        preferred.camera,
                        ship.lat,
                        ship.lon,
                        preferred=True,
                        busy=True,
                    )
                    switched = previous_id is not None and previous_id != active.camera.id
                    reason = reason or (
                        "Higher-priority camera available "
                        f"({preferred.camera.name})"
                    )
                else:
                    active = self._scoring.score_camera(
                        current.camera,
                        ship.lat,
                        ship.lon,
                        preferred=True,
                        busy=True,
                    )
            elif preferred is not None:
                active = self._scoring.score_camera(
                    preferred.camera,
                    ship.lat,
                    ship.lon,
                    preferred=True,
                    busy=True,
                )
                switched = previous_id is not None and previous_id != active.camera.id
                if switched and not reason:
                    reason = "Ship left previous camera FOV — auto-switched"
                elif not reason:
                    reason = "Best camera assigned"
            else:
                active = None
                switched = previous_id is not None
                reason = reason or "No camera covers this vessel"

        alternatives = [
            item
            for item in ranked
            if active is None or item.camera.id != active.camera.id
        ][:5]

        if active is not None:
            explanation = self._scoring.explain(active)
        else:
            explanation = "No suitable camera in coverage."

        snapshot = CameraLinkSnapshot(
            mmsi=mmsi,
            mode=mode,
            active=active,
            alternatives=alternatives,
            explanation=explanation,
            coverage_visible=coverage_visible,
            switched=switched,
            reason=reason,
        )

        with self._lock:
            self._active_camera_id = (
                active.camera.id if active is not None else None
            )
            self._last = snapshot
            self._mode = mode

        # Keep ship.camera_visible in sync for alerts/analytics.
        self._update_ship_camera_flag(ship, active is not None)

        eventbus.publish(EVENT_CAMERA_LINK_CHANGED, snapshot=snapshot)
        return snapshot

    def coverage_sectors(self) -> list[CoverageSector]:

        snapshot = self.last_snapshot
        states: dict[str, CameraLinkState] = {}
        for item in snapshot.alternatives:
            states[item.camera.id] = item.state
        if snapshot.active is not None:
            states[snapshot.active.camera.id] = CameraLinkState.BUSY

        cameras = self._cameras.enabled()
        return self._coverage.sectors_for_cameras(cameras, states=states)

    def link_overlay_payload(self) -> dict | None:

        snapshot = self.last_snapshot
        if snapshot.mmsi is None or snapshot.active is None:
            return None

        ship = registry.get(snapshot.mmsi)
        if ship is None:
            return None

        camera = snapshot.active.camera
        return {
            "mmsi": snapshot.mmsi,
            "ship_lat": ship.lat,
            "ship_lon": ship.lon,
            "camera_id": camera.id,
            "camera_name": camera.name,
            "camera_lat": camera.lat,
            "camera_lon": camera.lon,
            "state": snapshot.active.state.value,
            "score": snapshot.active.score,
            "mode": snapshot.mode.value,
        }

    @staticmethod
    def _update_ship_camera_flag(ship: Ship, visible: bool) -> None:

        try:
            ship.camera_visible = bool(visible)
        except Exception:
            logger.debug(
                "Unable to update ship.camera_visible for MMSI %s",
                getattr(ship, "mmsi", None),
                exc_info=True,
            )


intelligent_camera_link_manager = IntelligentCameraLinkManager()
