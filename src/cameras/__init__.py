from .loader import CameraLoader, CameraLoadError
from .manager import CameraManager, camera_manager
from .pack_manager import CameraPack, CameraPackManager

__all__ = [
    "CameraLoader",
    "CameraLoadError",
    "CameraManager",
    "camera_manager",
    "CameraPack",
    "CameraPackManager",
    "camera_pack_manager",
]


def __getattr__(name: str):
    if name == "camera_pack_manager":
        from .pack_manager import get_camera_pack_manager

        return get_camera_pack_manager()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
