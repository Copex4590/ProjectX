# ============================================================================
# Project X
# Live Camera Workflow
# ============================================================================

from dataclasses import dataclass
import logging

from engines.camera import camera_selection_engine
from engines.camera.camera_match import CameraMatch
from engines.camera.providers import provider_registry
from engines.camera.providers.base_provider import ProviderSession
from engines.playback.backend import PlaybackBackend
from engines.playback.session import PlaybackSession, PlaybackState
from models.ship import Ship
from playback.preferences import PlaybackSelector, playback_selector

logger = logging.getLogger(__name__)


@dataclass
class LiveCameraResult:

    success: bool
    message: str
    match: CameraMatch | None = None
    provider_session: ProviderSession | None = None
    playback_session: PlaybackSession | None = None
    backend: PlaybackBackend | None = None
    backend_name: str = ""


class LiveCameraWorkflow:

    def __init__(self, selector: PlaybackSelector | None = None):

        self._selector = selector or playback_selector
        self._active_backend: PlaybackBackend | None = None
        self._active_session: PlaybackSession | None = None
        self._active_provider = None

    def start_for_ship(self, ship: Ship) -> LiveCameraResult:

        try:
            return self._start_for_ship(ship)
        except Exception:
            logger.exception("Live camera start failed")
            return LiveCameraResult(
                success=False,
                message="An unexpected camera error occurred. Please try again.",
                match=None,
            )

    def start_for_match(self, match: CameraMatch) -> LiveCameraResult:
        """Start playback for an explicit camera match (manual override)."""

        try:
            return self._start_for_match(match)
        except Exception:
            logger.exception("Live camera start failed for match")
            return LiveCameraResult(
                success=False,
                message="An unexpected camera error occurred. Please try again.",
                match=match,
            )

    def _start_for_ship(self, ship: Ship) -> LiveCameraResult:

        self.stop()

        match = camera_selection_engine.get_best_camera(ship)

        if match is None:
            return LiveCameraResult(
                success=False,
                message="No camera available",
            )

        return self._start_for_match(match)

    def _start_for_match(self, match: CameraMatch) -> LiveCameraResult:

        self.stop()

        camera = match.camera
        provider = provider_registry.get_provider(camera)

        if provider is None:
            return LiveCameraResult(
                success=False,
                message="No compatible camera provider is available for this camera.",
                match=match,
            )

        provider_session = provider.open(camera)

        if provider_session is None:
            return LiveCameraResult(
                success=False,
                message="The camera stream could not be prepared.",
                match=match,
            )

        backend = self._selector.select_backend(provider_session)

        if backend is None:
            provider.close()
            return LiveCameraResult(
                success=False,
                message="No playback backend is available for this camera stream.",
                match=match,
                provider_session=provider_session,
            )

        playback_session = backend.prepare(provider_session)

        if playback_session is None:
            provider.close()
            return LiveCameraResult(
                success=False,
                message="Playback preparation failed for the selected camera.",
                match=match,
                provider_session=provider_session,
                backend=backend,
                backend_name=backend.name,
            )

        playback_session = backend.start(playback_session)

        if playback_session.state == PlaybackState.ERROR:
            provider.close()
            error_message = str(
                playback_session.metadata.get(
                    "message",
                    "Playback could not be started.",
                )
            )
            return LiveCameraResult(
                success=False,
                message=error_message,
                match=match,
                provider_session=provider_session,
                playback_session=playback_session,
                backend=backend,
                backend_name=backend.name,
            )

        self._active_backend = backend
        self._active_session = playback_session
        self._active_provider = provider

        return LiveCameraResult(
            success=True,
            message="Live camera playback started.",
            match=match,
            provider_session=provider_session,
            playback_session=playback_session,
            backend=backend,
            backend_name=backend.name,
        )

    def stop(self):

        if self._active_backend is not None and self._active_session is not None:
            try:
                self._active_backend.stop(self._active_session)
            except Exception:
                logger.exception("Failed to stop live camera playback backend")

        if self._active_provider is not None:
            try:
                self._active_provider.close()
            except Exception:
                logger.exception("Failed to close live camera provider")

        self._active_backend = None
        self._active_session = None
        self._active_provider = None


live_camera_workflow = LiveCameraWorkflow()
