# ============================================================================
# Project X
# YouTube Provider (architecture stub)
# ============================================================================

from .base_provider import (
    CameraProvider,
    ProviderSession,
    ProviderState,
    ProviderStatus,
)
from models.camera import Camera


class YouTubeProvider(CameraProvider):

    def __init__(self):

        self._camera: Camera | None = None
        self._session: ProviderSession | None = None
        self._state = ProviderState.CLOSED
        self._message = ""

    @property
    def name(self) -> str:

        return "youtube"

    def supports(self, camera: Camera) -> bool:

        provider_type = self._camera_provider_type(camera)
        stream_url = self._camera_stream_url(camera).lower()

        if provider_type == "youtube":
            return bool(stream_url)

        return (
            "youtube.com" in stream_url
            or "youtu.be" in stream_url
        )

    def open(self, camera: Camera) -> ProviderSession | None:

        if not self.supports(camera):
            self._state = ProviderState.ERROR
            self._message = "Camera is not supported by YouTube provider"
            return None

        self._state = ProviderState.OPENING
        self._camera = camera

        self._session = ProviderSession(
            camera_id=camera.id,
            provider_name=self.name,
            stream_url=self._camera_stream_url(camera),
            metadata={"protocol": "youtube"},
        )

        self._state = ProviderState.OPEN
        self._message = "YouTube session prepared"
        return self._session

    def close(self) -> None:

        self._camera = None
        self._session = None
        self._state = ProviderState.CLOSED
        self._message = ""

    def status(self) -> ProviderStatus:

        return ProviderStatus(
            state=self._state,
            provider_name=self.name,
            camera_id=self._camera.id if self._camera else "",
            message=self._message,
        )
