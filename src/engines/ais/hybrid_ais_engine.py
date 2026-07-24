# ============================================================================
# Project X
# Hybrid AIS Engine
#
# Single ingestion layer between AIS runtime providers and ShipRegistry.
#
# Canonical ship-update pipeline (SAVE-232):
#   AIS/RTL Providers -> HybridAisEngine -> ShipRegistry
#       -> EventBus("ship.updated") -> EventBridge (coalesce)
#       -> Qt signals -> ALL UI consumers
# ============================================================================

from __future__ import annotations

from debug.obs_freeze_trace import trace_block
from database import registry
from engines.ais.runtime_provider import AISRuntimeProvider, ShipCallback
from events import eventbus
from models.ship import Ship


class HybridAisEngine:
    """Orchestrates AIS providers and publishes ships to the runtime registry.

    This is the **only** canonical publisher of ``ship.updated`` for live traffic.
    """

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
        """Ingest one ship and publish the canonical ``ship.updated`` event."""

        registry.add(ship)
        with trace_block(
            f"HybridAisEngine.publish_ship mmsi={ship.mmsi} source={ship.source}"
        ):
            eventbus.publish("ship.updated", ship=ship)

    def notify_ships_changed(self, ship: Ship | None = None) -> None:
        """Publish ``ship.updated`` after registry mutations (e.g. purge).

        Prefer ``publish_ship`` for normal ingest. Use this when the registry
        changed without a single new Ship payload (bulk remove / reconnect).
        """

        if ship is not None:
            self.publish_ship(ship)
            return

        with trace_block("HybridAisEngine.notify_ships_changed"):
            eventbus.publish("ship.updated")

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
