# ============================================================================
# Project X
# AIS provider coverage information (UX)
# ============================================================================

from __future__ import annotations

from ais.providers import AISProviderType

_PROVIDER_COVERAGE_URLS: dict[AISProviderType, str] = {
    AISProviderType.AISSTREAM: "https://aisstream.io/",
    AISProviderType.MARINE_TRAFFIC: "https://www.marinetraffic.com/en/ais/coverage",
    AISProviderType.AISHUB: "https://www.aishub.net/",
}


def default_coverage_provider() -> AISProviderType:

    return AISProviderType.AISSTREAM


def provider_coverage_url(provider: AISProviderType) -> str | None:

    return _PROVIDER_COVERAGE_URLS.get(provider)
