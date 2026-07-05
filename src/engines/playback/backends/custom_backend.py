# ============================================================================
# Project X
# Custom Backend (architecture stub)
# ============================================================================

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.backend import PlaybackBackend, PlaybackBackendStatus
from engines.playback.session import PlaybackSession, PlaybackState


class CustomBackend(PlaybackBackend):

    @property
    def name(self) -> str:

        return "custom"

    def supports(self, provider_session: ProviderSession) -> bool:

        metadata = provider_session.metadata or {}
        return bool(metadata.get("custom_backend"))

    def prepare(self, provider_session: ProviderSession) -> PlaybackSession | None:

        if not self.supports(provider_session):
            return None

        return PlaybackSession(
            provider_session=provider_session,
            backend_name=self.name,
            state=PlaybackState.PREPARED,
            metadata={"prepared_by": self.name},
        )

    def start(self, session: PlaybackSession) -> PlaybackSession:

        return session.with_state(
            PlaybackState.STARTED,
            message="Custom backend start prepared",
            started_by=self.name,
        )

    def stop(self, session: PlaybackSession) -> PlaybackSession:

        return session.with_state(
            PlaybackState.STOPPED,
            message="Custom backend stopped",
            stopped_by=self.name,
        )

    def status(self, session: PlaybackSession) -> PlaybackBackendStatus:

        return PlaybackBackendStatus(
            state=session.state,
            backend_name=self.name,
            session_id=session.session_id,
            message=str(session.metadata.get("message", "")),
        )
