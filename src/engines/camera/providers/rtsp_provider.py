# ============================================================================
# Project X
# RTSP Provider (architecture stub)
# ============================================================================

from engines.camera.providers.base_provider import (
    CameraProvider,
    ProviderSession,
    ProviderState,
    ProviderStatus,
)
from models.camera import Camera


class RTSPProvider(CameraProvider):

    def __init__(self):

        self._camera: Camera | None = None
        self._session: ProviderSession | None = None
        self._state = ProviderState.CLOSED
        self._message = ""

    @property
    def name(self) -> str:

        return "rtsp"

    def supports(self, camera: Camera) -> bool:

        provider_type = self._camera_provider_type(camera)
        stream_url = self._camera_stream_url(camera).lower()

        if provider_type == "rtsp":
            return bool(stream_url)

        return stream_url.startswith("rtsp://")

    def open(self, camera: Camera) -> ProviderSession | None:

        if not self.supports(camera):
            self._state = ProviderState.ERROR
            self._message = "Camera is not supported by RTSP provider"
            return None

        self._state = ProviderState.OPENING
        self._camera = camera

        self._session = ProviderSession(
            camera_id=camera.id,
            provider_name=self.name,
            stream_url=self._camera_stream_url(camera),
            metadata={"protocol": "rtsp"},
        )

        self._state = ProviderState.OPEN
        self._message = "RTSP session prepared"
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
