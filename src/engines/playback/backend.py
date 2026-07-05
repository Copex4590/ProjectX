# ============================================================================
# Project X
# Playback Backend
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.session import PlaybackSession, PlaybackState


@dataclass(frozen=True)
class PlaybackBackendStatus:

    state: PlaybackState
    backend_name: str
    session_id: str
    message: str = ""


class PlaybackBackend(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def supports(self, provider_session: ProviderSession) -> bool:
        ...

    @abstractmethod
    def prepare(self, provider_session: ProviderSession) -> PlaybackSession | None:
        ...

    @abstractmethod
    def start(self, session: PlaybackSession) -> PlaybackSession:
        ...

    @abstractmethod
    def stop(self, session: PlaybackSession) -> PlaybackSession:
        ...

    @abstractmethod
    def status(self, session: PlaybackSession) -> PlaybackBackendStatus:
        ...

    def _provider_name(self, provider_session: ProviderSession) -> str:

        return str(provider_session.provider_name).strip().lower()

    def _provider_protocol(self, provider_session: ProviderSession) -> str:

        metadata = provider_session.metadata or {}
        protocol = metadata.get("protocol", "")
        return str(protocol).strip().lower()
