from engines.playback.backend import PlaybackBackend, PlaybackBackendStatus
from engines.playback.backend_registry import BackendRegistry, backend_registry
from engines.playback.backends import (
    BrowserBackend,
    CustomBackend,
    MPVBackend,
    QtBackend,
    VLCBackend,
)
from engines.playback.mpv_launch import MPVLaunchConfiguration
from engines.playback.session import PlaybackSession, PlaybackState


def register_default_backends(
    registry: BackendRegistry | None = None,
) -> BackendRegistry:

    target = registry or backend_registry

    target.register(MPVBackend(), priority=50)
    target.register(VLCBackend(), priority=40)
    target.register(QtBackend(), priority=30)
    target.register(BrowserBackend(), priority=20)
    target.register(CustomBackend(), priority=10)

    return target


register_default_backends()

__all__ = [
    "PlaybackBackend",
    "PlaybackBackendStatus",
    "PlaybackSession",
    "PlaybackState",
    "BackendRegistry",
    "backend_registry",
    "MPVBackend",
    "MPVLaunchConfiguration",
    "QtBackend",
    "VLCBackend",
    "BrowserBackend",
    "CustomBackend",
    "register_default_backends",
]
