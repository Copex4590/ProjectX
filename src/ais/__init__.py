from ais.ais_manager import AISManager
from ais.provider_manager import (
    ConfiguredProvider,
    ProviderManager,
    provider_manager,
)
from ais.providers import (
    AISSTREAM_REGISTER_URL,
    SUPPORTED_AIS_PROVIDERS,
    AISProviderType,
    AISTestResult,
    get_provider,
    provider_display_name,
)
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "AISSTREAM_REGISTER_URL",
    "AISManager",
    "AISProviderType",
    "AISTestResult",
    "ConfiguredProvider",
    "ProviderManager",
    "SUPPORTED_AIS_PROVIDERS",
    "ais_manager",
    "get_provider",
    "provider_display_name",
    "provider_manager",
]


def __getattr__(name: str):
    if name == "ais_manager":
        return lazy_submodule_export(__name__, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
