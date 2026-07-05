from ais.providers.aisstream_provider import AISSTREAM_REGISTER_URL, AISStreamProvider
from ais.providers.hybrid_provider import HybridAISProvider
from ais.providers.local_provider import LocalAISProvider
from ais.providers.provider import (
    AISProvider,
    AISProviderType,
    AISTestResult,
    FUTURE_AIS_PROVIDERS,
    SUPPORTED_AIS_PROVIDERS,
    normalize_provider_type,
)

_PROVIDERS: dict[AISProviderType, AISProvider] = {
    AISProviderType.AISSTREAM: AISStreamProvider(),
    AISProviderType.LOCAL: LocalAISProvider(),
    AISProviderType.HYBRID: HybridAISProvider(),
}


def get_provider(provider_type: str | AISProviderType | None) -> AISProvider | None:

    normalized = normalize_provider_type(provider_type)

    if normalized == AISProviderType.LATER:
        return None

    return _PROVIDERS.get(normalized)


def provider_display_name(provider_type: str | AISProviderType | None) -> str:

    normalized = normalize_provider_type(provider_type)

    if normalized == AISProviderType.LATER:
        return "Not configured"

    provider = _PROVIDERS.get(normalized)

    if provider is None:
        return normalized.value

    return provider.display_name


__all__ = [
    "AISSTREAM_REGISTER_URL",
    "AISProvider",
    "AISProviderType",
    "AISStreamProvider",
    "AISTestResult",
    "FUTURE_AIS_PROVIDERS",
    "HybridAISProvider",
    "LocalAISProvider",
    "SUPPORTED_AIS_PROVIDERS",
    "get_provider",
    "normalize_provider_type",
    "provider_display_name",
]
