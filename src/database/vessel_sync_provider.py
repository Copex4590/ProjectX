# ============================================================================
# Project X
# Vessel Database Sync Providers (SAVE-209)
# Local registry sync + hook for future online providers
# ============================================================================

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from database.ship_registry import registry
from database.vessel_database import vessel_database
from database.vessel_sync import vessel_sync
from models.ship import Ship

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


@dataclass
class VesselSyncResult:
    success: bool
    imported: int = 0
    updated: int = 0
    unknown: int = 0
    failed_lookups: int = 0
    message: str = ""
    details: dict = field(default_factory=dict)


class VesselSyncProvider(ABC):
    """Pluggable sync backend (local today, online providers later)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def synchronize(
        self,
        *,
        progress: ProgressCallback | None = None,
    ) -> VesselSyncResult:
        raise NotImplementedError


class LocalRegistrySyncProvider(VesselSyncProvider):
    """Reconcile in-memory ShipRegistry into the local SQLite vessel database."""

    @property
    def provider_id(self) -> str:
        return "local_registry"

    def synchronize(
        self,
        *,
        progress: ProgressCallback | None = None,
    ) -> VesselSyncResult:

        ships: list[Ship] = list(registry.all())
        total = len(ships)
        imported = 0
        updated = 0
        failed = 0

        if progress is not None:
            progress(0.0, "Starting local registry sync")

        if total == 0:
            if progress is not None:
                progress(1.0, "No vessels in registry")
            return VesselSyncResult(
                success=True,
                message="Registry empty — nothing to sync",
            )

        for index, ship in enumerate(ships):
            try:
                existing = vessel_database.get(ship.mmsi)
                saved = vessel_sync.sync_now(ship)
                if saved is None:
                    failed += 1
                elif existing is None:
                    imported += 1
                else:
                    updated += 1
            except Exception:
                logger.exception(
                    "Local registry sync failed for MMSI %s",
                    getattr(ship, "mmsi", None),
                )
                failed += 1

            if progress is not None:
                fraction = float(index + 1) / float(total)
                progress(
                    fraction,
                    f"Synced {index + 1}/{total}",
                )

        success = failed == 0
        message = (
            f"Local sync complete ({imported} imported, {updated} updated)"
            if success
            else f"Local sync finished with {failed} failure(s)"
        )
        return VesselSyncResult(
            success=success,
            imported=imported,
            updated=updated,
            failed_lookups=failed,
            message=message,
            details={"source": self.provider_id, "total": total},
        )


class OnlineVesselSyncProvider(VesselSyncProvider):
    """
    Hook stub for MarineTraffic / AISHub / other online enrichment.

    Disabled until a real provider is registered; synchronize() is a no-op success.
    """

    def __init__(self, provider_id: str = "online_stub") -> None:

        self._provider_id = provider_id
        self._enabled = False

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def synchronize(
        self,
        *,
        progress: ProgressCallback | None = None,
    ) -> VesselSyncResult:

        if not self._enabled:
            if progress is not None:
                progress(1.0, "Online provider inactive")
            return VesselSyncResult(
                success=True,
                message="Online provider hook inactive",
                details={"source": self.provider_id, "active": False},
            )

        # Future SAVE: call remote API here.
        if progress is not None:
            progress(1.0, "Online provider not implemented")
        return VesselSyncResult(
            success=True,
            unknown=0,
            failed_lookups=0,
            message="Online provider hook ready (no-op)",
            details={"source": self.provider_id, "active": True},
        )
