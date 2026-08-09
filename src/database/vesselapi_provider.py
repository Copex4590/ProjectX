# ============================================================================
# Project X
# VesselAPI OnlineVesselSyncProvider (Phase A)
# ============================================================================

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import Lock

from database.ship_registry import registry
from database.vessel_database import vessel_database
from database.vessel_sync_provider import (
    OnlineVesselSyncProvider,
    ProgressCallback,
    VesselSyncResult,
)
from database.vesselapi_client import (
    PHASE_A_KEY_FILE,
    VesselApiResult,
    VesselApiVessel,
    fetch_vessel_by_mmsi,
    load_api_key,
    resolve_api_key,
)
from models.vessel_record import VesselRecord

logger = logging.getLogger(__name__)

_SUCCESS_TTL_S = 24 * 3600
_FAILURE_TTL_S = 60 * 60
_MIN_REQUEST_INTERVAL_S = 0.35
_MAX_LOOKUPS_PER_SYNC = 40


class VesselAPIOnlineProvider(OnlineVesselSyncProvider):
    """MMSI enrichment via VesselAPI, writing fill-only into VesselRecord/SQLite.

    Runs inside VesselDatabaseManager sync worker threads — never on the GUI
    hot path for every AIS position update.
    """

    def __init__(
        self,
        *,
        key_file: Path | None = None,
        enabled: bool | None = None,
        success_ttl_s: float = _SUCCESS_TTL_S,
        failure_ttl_s: float = _FAILURE_TTL_S,
        min_request_interval_s: float = _MIN_REQUEST_INTERVAL_S,
        max_lookups_per_sync: int = _MAX_LOOKUPS_PER_SYNC,
        fetch_fn=None,
    ) -> None:

        super().__init__(provider_id="vesselapi")
        self._key_file = Path(key_file or PHASE_A_KEY_FILE)
        self._success_ttl_s = float(success_ttl_s)
        self._failure_ttl_s = float(failure_ttl_s)
        self._min_request_interval_s = float(min_request_interval_s)
        self._max_lookups_per_sync = int(max_lookups_per_sync)
        self._fetch_fn = fetch_fn or fetch_vessel_by_mmsi
        self._cache_lock = Lock()
        # mmsi -> (monotonic_ts, ok, vessel|None)
        self._cache: dict[int, tuple[float, bool, VesselApiVessel | None]] = {}
        self._last_request_at = 0.0

        if enabled is None:
            enabled = self._default_enabled()
        self.set_enabled(bool(enabled))

    def apply_preferences(self) -> None:
        """Refresh enablement after Settings save (Preferences is source of truth)."""

        self.set_enabled(self._default_enabled())

    def _default_enabled(self) -> bool:
        """Prefs enable flag when prefs key set; else Phase A file-key fallback."""

        try:
            from preferences.preferences_manager import preferences_manager

            prefs = preferences_manager.get()
            prefs_key = str(prefs.vesselapi_api_key or "").strip()
            if prefs_key:
                return bool(prefs.vesselapi_enabled)
        except Exception:
            logger.debug("VesselAPI preferences unavailable", exc_info=True)

        return bool(load_api_key(key_file=self._key_file))

    def synchronize(
        self,
        *,
        progress: ProgressCallback | None = None,
    ) -> VesselSyncResult:

        if not self.enabled:
            if progress is not None:
                progress(1.0, "VesselAPI provider inactive")
            return VesselSyncResult(
                success=True,
                message="VesselAPI provider inactive",
                details={"source": self.provider_id, "active": False},
            )

        api_key = resolve_api_key(key_file=self._key_file)
        if not api_key:
            if progress is not None:
                progress(1.0, "VesselAPI key unavailable")
            return VesselSyncResult(
                success=False,
                failed_lookups=1,
                message="VesselAPI key unavailable",
                details={"source": self.provider_id, "active": True},
            )

        targets = self._collect_target_mmsis()
        if not targets:
            if progress is not None:
                progress(1.0, "No vessels to enrich")
            return VesselSyncResult(
                success=True,
                message="No vessels to enrich",
                details={"source": self.provider_id, "targets": 0},
            )

        imported = 0
        updated = 0
        failed = 0
        skipped = 0
        looked_up = 0

        total = len(targets)
        for index, mmsi in enumerate(targets):
            if looked_up >= self._max_lookups_per_sync:
                skipped += total - index
                break

            if progress is not None:
                progress(
                    float(index) / float(max(1, total)),
                    f"VesselAPI enrich {index + 1}/{total}",
                )

            before = vessel_database.get(mmsi)
            result = self.enrich_mmsi(mmsi, api_key=api_key)
            if not result.ok:
                if result.error in {"cache_hit_failure", "rate_limited"}:
                    skipped += 1
                else:
                    failed += 1
                continue

            looked_up += 1
            after = vessel_database.get(mmsi)
            if after is None:
                failed += 1
                continue
            if before is None:
                imported += 1
            elif after.updated_at != before.updated_at:
                updated += 1

        if progress is not None:
            progress(1.0, "VesselAPI enrichment complete")

        success = failed == 0
        return VesselSyncResult(
            success=success,
            imported=imported,
            updated=updated,
            failed_lookups=failed,
            message=(
                f"VesselAPI enriched ({updated} updated, {imported} imported, "
                f"{failed} failed, {skipped} skipped)"
            ),
            details={
                "source": self.provider_id,
                "targets": total,
                "looked_up": looked_up,
                "skipped": skipped,
            },
        )

    def enrich_mmsi(
        self,
        mmsi: int,
        *,
        api_key: str | None = None,
        force: bool = False,
    ) -> VesselApiResult:
        """Fetch (or use cache) and apply fill-only enrichment for one MMSI."""

        try:
            mmsi_int = int(mmsi)
        except (TypeError, ValueError):
            return VesselApiResult(ok=False, error="invalid_mmsi")

        cached = self._cache_get(mmsi_int, force=force)
        if cached is not None:
            ok, vessel = cached
            if not ok or vessel is None:
                return VesselApiResult(ok=False, error="cache_hit_failure")
            self._apply_enrichment(mmsi_int, vessel)
            return VesselApiResult(ok=True, vessel=vessel)

        key = (
            api_key
            if api_key is not None
            else resolve_api_key(key_file=self._key_file)
        ).strip()
        if not key:
            return VesselApiResult(ok=False, error="missing_api_key")

        self._throttle()
        result = self._fetch_fn(mmsi_int, api_key=key)
        self._cache_put(mmsi_int, result)
        if not result.ok or result.vessel is None:
            return result

        self._apply_enrichment(mmsi_int, result.vessel)
        return result

    def _collect_target_mmsis(self) -> list[int]:

        mmsis: set[int] = set()
        for ship in registry.all():
            try:
                mmsis.add(int(ship.mmsi))
            except (TypeError, ValueError):
                continue
        for record in vessel_database.all():
            try:
                mmsis.add(int(record.mmsi))
            except (TypeError, ValueError):
                continue
        return sorted(m for m in mmsis if m > 0)

    def _throttle(self) -> None:

        now = time.monotonic()
        wait = self._min_request_interval_s - (now - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _cache_get(
        self, mmsi: int, *, force: bool
    ) -> tuple[bool, VesselApiVessel | None] | None:

        if force:
            return None
        with self._cache_lock:
            entry = self._cache.get(mmsi)
        if entry is None:
            return None
        stamped, ok, vessel = entry
        ttl = self._success_ttl_s if ok else self._failure_ttl_s
        if (time.monotonic() - stamped) > ttl:
            return None
        return ok, vessel

    def _cache_put(self, mmsi: int, result: VesselApiResult) -> None:

        with self._cache_lock:
            self._cache[mmsi] = (
                time.monotonic(),
                bool(result.ok and result.vessel is not None),
                result.vessel,
            )

    def _apply_enrichment(self, mmsi: int, vessel: VesselApiVessel) -> VesselRecord:
        """Fill missing VesselRecord fields only; never write VesselAPI draught."""

        existing = vessel_database.get(mmsi)
        now = datetime.now().replace(microsecond=0)
        if existing is None:
            existing = VesselRecord(mmsi=mmsi, first_seen=now, last_seen=now, created_at=now, updated_at=now)

        changed = False
        name = existing.name
        callsign = existing.callsign
        ship_type = existing.ship_type
        flag = existing.flag
        imo = existing.imo
        length = existing.length
        width = existing.width
        draft = existing.draft  # preserve AIS/RTL/DB draft; never from VesselAPI Phase A

        if not name and vessel.name:
            name = vessel.name
            changed = True
        if not callsign and vessel.callsign:
            callsign = vessel.callsign
            changed = True
        if not ship_type and vessel.ship_type:
            ship_type = vessel.ship_type
            changed = True
        # Prefer ISO country code for flag_manager; fall back to country name.
        flag_value = vessel.country_code or vessel.country
        if not flag and flag_value:
            flag = flag_value
            changed = True
        if not imo and vessel.imo:
            imo = vessel.imo
            changed = True
        if length is None and vessel.length_m is not None:
            length = float(vessel.length_m)
            changed = True
        if width is None and vessel.width_m is not None:
            width = float(vessel.width_m)
            changed = True

        if not changed:
            return existing

        updated = replace(
            existing,
            name=name,
            callsign=callsign,
            ship_type=ship_type,
            flag=flag,
            imo=imo,
            length=length,
            width=width,
            draft=draft,
            updated_at=now,
        )
        return vessel_database.upsert(updated)


def register_default_vesselapi_provider(
    *,
    manager=None,
    key_file: Path | None = None,
) -> VesselAPIOnlineProvider:
    """Register+enable Phase A provider on VesselDatabaseManager when a key exists."""

    from database.vessel_database_manager import vessel_database_manager

    target = manager or vessel_database_manager
    provider = VesselAPIOnlineProvider(key_file=key_file)
    target.register_online_provider(provider)
    if provider.enabled:
        logger.info("VesselAPI online provider registered and enabled (Phase A)")
    else:
        logger.info("VesselAPI online provider registered but inactive (no key)")
    return provider
