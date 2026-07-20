# ============================================================================
# Project X
# Camera Package
# ============================================================================

from camera.camera import (
    CAMERA_TYPES,
    SUPPORTED_CAMERA_TYPES,
    Camera,
)
from camera.camera_manager import CameraManager
from camera.camera_registry import CameraRegistry
from camera.stream_test import StreamTestResult, test_stream, validate_stream_url
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "CAMERAS_FILE",
    "CAMERA_TYPES",
    "Camera",
    "CameraManager",
    "CameraRegistry",
    "SUPPORTED_CAMERA_TYPES",
    "StreamTestResult",
    "camera_manager",
    "test_stream",
    "validate_stream_url",
]


def __getattr__(name: str):
    if name == "camera_manager":
        return lazy_submodule_export(__name__, name)
    if name == "CAMERAS_FILE":
        from camera.camera_manager import cameras_file

        return cameras_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
