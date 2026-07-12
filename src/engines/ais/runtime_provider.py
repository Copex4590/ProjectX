# ============================================================================
# Project X
# AIS Runtime Provider Protocol
# ============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from ais.providers.provider import AISProviderType

if TYPE_CHECKING:
    from models.ship import Ship

ShipCallback = Callable[["Ship"], None]


class AISRuntimeProvider(ABC):
    """Runtime AIS data source consumed by HybridAisEngine."""

    provider_type: AISProviderType

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def start(self, *, on_ship: ShipCallback) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        return False
