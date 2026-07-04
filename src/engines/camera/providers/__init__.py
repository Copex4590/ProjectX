from engines.camera.providers.base_provider import (
    CameraProvider,
    ProviderSession,
    ProviderState,
    ProviderStatus,
)
from engines.camera.providers.hls_provider import HLSProvider
from engines.camera.providers.provider_registry import ProviderRegistry, provider_registry
from engines.camera.providers.rtsp_provider import RTSPProvider
from engines.camera.providers.snapshot_provider import SnapshotProvider
from engines.camera.providers.youtube_provider import YouTubeProvider


def register_default_providers(
    registry: ProviderRegistry | None = None,
) -> ProviderRegistry:

    target = registry or provider_registry

    target.register(RTSPProvider(), priority=40)
    target.register(HLSProvider(), priority=30)
    target.register(YouTubeProvider(), priority=20)
    target.register(SnapshotProvider(), priority=10)

    return target


register_default_providers()

__all__ = [
    "CameraProvider",
    "ProviderSession",
    "ProviderState",
    "ProviderStatus",
    "ProviderRegistry",
    "provider_registry",
    "HLSProvider",
    "RTSPProvider",
    "SnapshotProvider",
    "YouTubeProvider",
    "register_default_providers",
]
