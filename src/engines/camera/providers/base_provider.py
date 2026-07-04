# ============================================================================
# Project X
# Camera Provider Base
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from models.camera import Camera


class ProviderState(Enum):

    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    ERROR = "error"


@dataclass(frozen=True)
class ProviderStatus:

    state: ProviderState
    provider_name: str = ""
    camera_id: str = ""
    message: str = ""


@dataclass(frozen=True)
class ProviderSession:

    camera_id: str
    provider_name: str
    stream_url: str = ""
    metadata: dict = field(default_factory=dict)


class CameraProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def supports(self, camera: Camera) -> bool:
        ...

    @abstractmethod
    def open(self, camera: Camera) -> ProviderSession | None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def status(self) -> ProviderStatus:
        ...

    def _camera_provider_type(self, camera: Camera) -> str:

        return str(getattr(camera, "provider_type", "")).strip().lower()

    def _camera_stream_url(self, camera: Camera) -> str:

        return str(getattr(camera, "stream_url", "")).strip()
