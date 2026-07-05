# ============================================================================
# Project X
# Playback Session
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from engines.camera.providers.base_provider import ProviderSession


class PlaybackState(Enum):

    CREATED = "created"
    PREPARED = "prepared"
    STARTING = "starting"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PlaybackSession:

    provider_session: ProviderSession
    backend_name: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    state: PlaybackState = PlaybackState.CREATED
    metadata: dict = field(default_factory=dict)

    def with_state(
        self,
        state: PlaybackState,
        *,
        message: str = "",
        **metadata,
    ) -> "PlaybackSession":

        merged_metadata = dict(self.metadata)

        if message:
            merged_metadata["message"] = message

        merged_metadata.update(metadata)

        return PlaybackSession(
            session_id=self.session_id,
            provider_session=self.provider_session,
            backend_name=self.backend_name,
            created_at=self.created_at,
            state=state,
            metadata=merged_metadata,
        )
