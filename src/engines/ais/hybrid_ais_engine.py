# ============================================================================
# Project X
# Hybrid AIS Engine
#
# Single ingestion layer between AIS runtime providers and ShipRegistry.
#
# Architecture:
#   AIS Providers -> HybridAisEngine -> ShipRegistry -> EventBus -> UI
# ============================================================================

from __future__ import annotations

from debug.obs_freeze_trace import trace_block
from engines.ais.runtime_provider import AISRuntimeProvider, ShipCallback
from events import eventbus
from models.ship import Ship


class HybridAisEngine:
    """Orchestrates AIS providers and publishes ships to the runtime registry."""

    def __init__(self) -> None:
        self._providers: list[AISRuntimeProvider] = []
        self._started = False

    def register_provider(self, provider: AISRuntimeProvider) -> None:
        if provider in self._providers:
            return
        self._providers.append(provider)

    def clear_providers(self) -> None:
        self.stop()
        self._providers.clear()

    @property
    def providers(self) -> tuple[AISRuntimeProvider, ...]:
        return tuple(self._providers)

    @property
    def is_started(self) -> bool:
        return self._started

    def publish_ship(self, ship: Ship) -> None:
        """Publish one ship update through the single registry ingestion path."""

        from database.ship_registry import get_ship_registry

        get_ship_registry().add(ship)
        with trace_block(
            f"HybridAisEngine.publish_ship mmsi={ship.mmsi} source={ship.source}"
        ):
            eventbus.publish("ship.updated", ship=ship)

    def _on_provider_ship(self, ship: Ship) -> None:
        self.publish_ship(ship)

    def start(self) -> None:
        if self._started:
            return

        callback: ShipCallback = self._on_provider_ship
        for provider in self._providers:
            provider.start(on_ship=callback)

        self._started = True

    def stop(self) -> None:
        if not self._started and not self._providers:
            return

        for provider in self._providers:
            provider.stop()

        self._started = False


hybrid_ais_engine = HybridAisEngine()
