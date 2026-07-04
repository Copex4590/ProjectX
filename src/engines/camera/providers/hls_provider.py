# ============================================================================
# Project X
# HLS Provider
# ============================================================================

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from engines.camera.providers.base_provider import (
    CameraProvider,
    ProviderSession,
    ProviderState,
    ProviderStatus,
)
from models.camera import Camera

_HLS_PROVIDER_TYPES = frozenset({"hls", "m3u8"})
_VALID_SCHEMES = frozenset({"http", "https"})


class HLSReadinessStatus(Enum):

    READY = "ready"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class HLSValidationResult:

    valid: bool
    status: HLSReadinessStatus
    message: str = ""
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class HLSSession(ProviderSession):

    readiness: HLSReadinessStatus = HLSReadinessStatus.READY

    @property
    def playlist_url(self) -> str:

        return self.stream_url


class HLSProvider(CameraProvider):

    def __init__(self):

        self._camera: Camera | None = None
        self._session: HLSSession | None = None
        self._state = ProviderState.CLOSED
        self._message = ""

    @property
    def name(self) -> str:

        return "hls"

    def supports(self, camera: Camera) -> bool:

        provider_type = self._camera_provider_type(camera)

        if provider_type and provider_type not in _HLS_PROVIDER_TYPES:
            return False

        stream_url = self._camera_stream_url(camera)

        if not stream_url:
            return provider_type in _HLS_PROVIDER_TYPES

        if provider_type in _HLS_PROVIDER_TYPES:
            return True

        return self._is_hls_playlist_url(stream_url)

    def validate(self, camera: Camera) -> HLSValidationResult:

        if not self.supports(camera):
            return HLSValidationResult(
                valid=False,
                status=HLSReadinessStatus.UNSUPPORTED,
                message="Camera is not configured for HLS",
                errors=("unsupported_provider",),
            )

        stream_url = self._normalized_stream_url(camera)

        if not stream_url:
            return HLSValidationResult(
                valid=False,
                status=HLSReadinessStatus.INVALID,
                message="HLS stream URL is missing",
                errors=("missing_stream_url",),
            )

        errors = []

        parsed = urlparse(stream_url)
        scheme = parsed.scheme.lower()

        if scheme not in _VALID_SCHEMES:
            errors.append("invalid_url_scheme")

        if not parsed.netloc:
            errors.append("missing_url_host")

        provider_type = self._camera_provider_type(camera)
        explicit_hls = provider_type in _HLS_PROVIDER_TYPES

        if not explicit_hls and not self._is_hls_playlist_url(stream_url):
            errors.append("missing_m3u8_playlist")

        if errors:
            return HLSValidationResult(
                valid=False,
                status=HLSReadinessStatus.INVALID,
                message="HLS camera configuration is invalid",
                errors=tuple(errors),
            )

        return HLSValidationResult(
            valid=True,
            status=HLSReadinessStatus.READY,
            message="HLS camera is ready for playback preparation",
        )

    def status(self, camera: Camera | None = None) -> ProviderStatus | HLSReadinessStatus:

        if camera is not None:
            return self.validate(camera).status

        return ProviderStatus(
            state=self._state,
            provider_name=self.name,
            camera_id=self._camera.id if self._camera else "",
            message=self._message,
        )

    def open(self, camera: Camera) -> HLSSession | None:

        validation = self.validate(camera)

        if not validation.valid:
            self._state = ProviderState.ERROR
            self._camera = camera
            self._session = None
            self._message = validation.message
            return None

        self._state = ProviderState.OPENING
        self._camera = camera

        playlist_url = self._normalized_stream_url(camera)

        self._session = HLSSession(
            camera_id=camera.id,
            provider_name=self.name,
            stream_url=playlist_url,
            readiness=HLSReadinessStatus.READY,
            metadata={
                "protocol": "hls",
                "playlist_url": playlist_url,
                "provider_type": self._camera_provider_type(camera) or "hls",
                "validation_errors": [],
                "playback_prepared": True,
            },
        )

        self._state = ProviderState.OPEN
        self._message = "HLS playback session prepared"
        return self._session

    def close(self) -> None:

        self._camera = None
        self._session = None
        self._state = ProviderState.CLOSED
        self._message = ""

    def _normalized_stream_url(self, camera: Camera) -> str:

        return self._camera_stream_url(camera).strip()

    @staticmethod
    def _is_hls_playlist_url(stream_url: str) -> bool:

        parsed = urlparse(stream_url.strip())
        return parsed.path.lower().endswith(".m3u8")
