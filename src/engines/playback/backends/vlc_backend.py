# ============================================================================
# Project X
# VLC Backend (architecture stub)
# ============================================================================

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.backend import PlaybackBackend, PlaybackBackendStatus
from engines.playback.session import PlaybackSession, PlaybackState

_SUPPORTED_PROVIDERS = frozenset({"hls", "rtsp", "youtube"})


class VLCBackend(PlaybackBackend):

    @property
    def name(self) -> str:

        return "vlc"

    def supports(self, provider_session: ProviderSession) -> bool:

        provider_name = self._provider_name(provider_session)
        protocol = self._provider_protocol(provider_session)

        return (
            provider_name in _SUPPORTED_PROVIDERS
            or protocol in _SUPPORTED_PROVIDERS
        )

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
            message="VLC backend start prepared",
            started_by=self.name,
        )

    def stop(self, session: PlaybackSession) -> PlaybackSession:

        return session.with_state(
            PlaybackState.STOPPED,
            message="VLC backend stopped",
            stopped_by=self.name,
        )

    def status(self, session: PlaybackSession) -> PlaybackBackendStatus:

        return PlaybackBackendStatus(
            state=session.state,
            backend_name=self.name,
            session_id=session.session_id,
            message=str(session.metadata.get("message", "")),
        )
