# ============================================================================
# Project X
# AIS Provider Manager
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass

from ais.providers import AISProviderType

_PROVIDER_CATALOG = (
    (AISProviderType.AISSTREAM, "AISStream", "AISStream"),
    (AISProviderType.LOCAL, "RTL-SDR", "RTL-SDR"),
)


@dataclass(frozen=True)
class ConfiguredProvider:
    provider_id: str
    display_name: str
    label_key: str


class ProviderManager:
    def configured_providers(self) -> list[ConfiguredProvider]:

        return [
            ConfiguredProvider(
                provider_id=provider_type.value,
                display_name=display_name,
                label_key=label_key,
            )
            for provider_type, display_name, label_key in _PROVIDER_CATALOG
        ]


provider_manager = ProviderManager()
