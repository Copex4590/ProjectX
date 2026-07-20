from .camera_registry import camera_registry
from .ship_registry import ShipRegistry, get_ship_registry

__all__ = ["ShipRegistry", "camera_registry", "get_ship_registry", "registry"]


def __getattr__(name: str):
    if name == "registry":
        return get_ship_registry()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
