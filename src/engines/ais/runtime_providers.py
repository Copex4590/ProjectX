# ============================================================================
# Project X
# AIS Runtime Provider Registry and Stubs
# ============================================================================

from __future__ import annotations

import logging

from ais.providers.provider import AISProviderType, FUTURE_AIS_PROVIDERS
from engines.ais.runtime_provider import AISRuntimeProvider, ShipCallback

logger = logging.getLogger(__name__)


class _StubRuntimeProvider(AISRuntimeProvider):

    def __init__(
        self,
        provider_type: AISProviderType,
        label: str,
    ) -> None:
        self.provider_type = provider_type
        self._label = label
        self._running = False

    @property
    def display_name(self) -> str:
        return self._label

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, *, on_ship: ShipCallback) -> None:
        # Supported stubs may be wired later; future providers never start.
        if self.provider_type in FUTURE_AIS_PROVIDERS:
            logger.debug(
                "Ignoring start for inactive future provider %s",
                self.provider_type.value,
            )
            self._running = False
            return
        self._running = True

    def stop(self) -> None:
        self._running = False


class AISStreamRuntimeProvider(_StubRuntimeProvider):

    def __init__(self) -> None:
        super().__init__(AISProviderType.AISSTREAM, "AISStream")


class RtlAisRuntimeProvider(_StubRuntimeProvider):

    def __init__(self) -> None:
        super().__init__(AISProviderType.LOCAL, "RTL AIS")


class MarineTrafficRuntimeProvider(_StubRuntimeProvider):

    def __init__(self) -> None:
        super().__init__(AISProviderType.MARINE_TRAFFIC, "MarineTraffic")


class AISHubRuntimeProvider(_StubRuntimeProvider):

    def __init__(self) -> None:
        super().__init__(AISProviderType.AISHUB, "AISHub")


RUNTIME_AIS_PROVIDERS: dict[AISProviderType, AISRuntimeProvider] = {
    AISProviderType.AISSTREAM: AISStreamRuntimeProvider(),
    AISProviderType.LOCAL: RtlAisRuntimeProvider(),
    AISProviderType.MARINE_TRAFFIC: MarineTrafficRuntimeProvider(),
    AISProviderType.AISHUB: AISHubRuntimeProvider(),
}


def get_runtime_provider(provider_type: AISProviderType) -> AISRuntimeProvider | None:
    return RUNTIME_AIS_PROVIDERS.get(provider_type)
