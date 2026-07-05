# ============================================================================
# Project X
# AIS Provider Base
# ============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class AISProviderType(str, Enum):

    AISSTREAM = "aisstream"
    LOCAL = "local"
    HYBRID = "hybrid"
    LATER = "later"
    MARINE_TRAFFIC = "marinetraffic"
    VESSELFINDER = "vesselfinder"
    OTHER = "other"


SUPPORTED_AIS_PROVIDERS = (
    AISProviderType.AISSTREAM,
    AISProviderType.LOCAL,
    AISProviderType.HYBRID,
    AISProviderType.LATER,
)

FUTURE_AIS_PROVIDERS = (
    AISProviderType.MARINE_TRAFFIC,
    AISProviderType.VESSELFINDER,
    AISProviderType.OTHER,
)


@dataclass(frozen=True)
class AISTestResult:

    success: bool
    message: str = ""


class AISProvider(ABC):

    provider_type: AISProviderType

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def test(self, **config) -> AISTestResult:
        raise NotImplementedError


def normalize_provider_type(value: str | AISProviderType | None) -> AISProviderType:

    if isinstance(value, AISProviderType):
        return value

    normalized = str(value or AISProviderType.LATER.value).strip().lower()

    for provider_type in AISProviderType:
        if provider_type.value == normalized:
            return provider_type

    return AISProviderType.LATER
