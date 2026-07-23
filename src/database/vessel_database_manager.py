# ============================================================================
# Project X
# Vessel Database Manager (SAVE-208 + SAVE-209 auto-sync)
# ============================================================================

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from app.paths import runtime_data_dir, runtime_data_path
from database.vessel_database import VESSEL_DATABASE_FILE, vessel_database
from database.vessel_sync_provider import (
    LocalRegistrySyncProvider,
    OnlineVesselSyncProvider,
    ProgressCallback,
    VesselSyncProvider,
    VesselSyncResult,
)
from events import eventbus

logger = logging.getLogger(__name__)

VESSEL_DB_SCHEMA_VERSION = "1"
_DEFAULT_SYNC_INTERVAL_S = 300.0
_SCHEDULER_TICK_S = 1.0

VESSEL_DB_SYNC_STATE_FILE = Path(
    os.environ.get(
        "PROJECTX_VESSEL_DB_SYNC_STATE_FILE",
        str(runtime_data_path("vessel_db_sync_state.json")),
    )
)

EVENT_SYNC_STARTED = "vessel_db.sync.started"
EVENT_SYNC_PROGRESS = "vessel_db.sync.progress"
EVENT_SYNC_COMPLETED = "vessel_db.sync.completed"
EVENT_SYNC_FAILED = "vessel_db.sync.failed"
EVENT_SYNC_STATE_CHANGED = "vessel_db.sync.state_changed"
EVENT_AUTO_SYNC_CHANGED = "vessel_db.auto_sync.changed"


class DatabaseStatus(str, Enum):

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class IntegrityStatus(str, Enum):

    OK = "ok"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_CHECKED = "not_checked"


class AccessStatus(str, Enum):

    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    NO_ACCESS = "no_access"
    UNKNOWN = "unknown"


class SyncState(str, Enum):

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class LocalDatabaseInfo:
    vessel_count: int
    size_bytes: int
    last_updated: datetime | None
    schema_version: str
    database_path: Path


@dataclass(frozen=True)
class SynchronizationInfo:
    last_sync: datetime | None
    next_sync: datetime | None
    auto_sync_enabled: bool
    sync_interval_seconds: float
    state: SyncState = SyncState.IDLE
    last_error: str = ""


@dataclass(frozen=True)
class SyncStatistics:
    imported_vessels: int
    updated_vessels: int
    unknown_vessels: int
    failed_lookups: int


@dataclass(frozen=True)
class DiagnosticsInfo:
    database_status: DatabaseStatus
    integrity: IntegrityStatus
    integrity_detail: str
    access: AccessStatus
    access_detail: str


@dataclass(frozen=True)
class VesselDatabaseManagerSnapshot:
    local: LocalDatabaseInfo
    synchronization: SynchronizationInfo
    statistics: SyncStatistics
    diagnostics: DiagnosticsInfo
    collected_at: datetime = field(default_factory=datetime.now)


def _format_size(size_bytes: int) -> str:

    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _parse_timestamp(value: object) -> datetime | None:

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class VesselDatabaseManager:
    """Vessel DB status, auto-sync scheduler, and provider-backed synchronization."""

    def __init__(
        self,
        db_path: Path | None = None,
        *,
        state_path: Path | None = None,
        local_provider: VesselSyncProvider | None = None,
        online_provider: OnlineVesselSyncProvider | None = None,
    ) -> None:

        self._db_path = Path(db_path or VESSEL_DATABASE_FILE)
        self._state_path = Path(state_path or VESSEL_DB_SYNC_STATE_FILE)
        self._lock = Lock()
        self._auto_sync_enabled = False
        self._sync_interval_seconds = _DEFAULT_SYNC_INTERVAL_S
        self._last_sync: datetime | None = None
        self._next_sync: datetime | None = None
        self._sync_state = SyncState.IDLE
        self._last_error = ""
        self._imported = 0
        self._updated = 0
        self._unknown = 0
        self._failed_lookups = 0
        self._last_integrity = IntegrityStatus.NOT_CHECKED
        self._last_integrity_detail = ""

        self._local_provider = local_provider or LocalRegistrySyncProvider()
        self._online_provider = online_provider or OnlineVesselSyncProvider()
        self._progress_callback: ProgressCallback | None = None

        self._scheduler_stop = Event()
        self._scheduler_wake = Event()
        self._scheduler_thread: Thread | None = None
        self._sync_thread: Thread | None = None
        self._stop_requested = False

        self._load_persisted_state()
        self._ensure_scheduler()

    @property
    def database_path(self) -> Path:

        return self._db_path

    @property
    def sync_state(self) -> SyncState:

        with self._lock:
            return self._sync_state

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Prepare UI/progress consumers without requiring UI changes in SAVE-209."""

        with self._lock:
            self._progress_callback = callback

    def register_online_provider(
        self,
        provider: OnlineVesselSyncProvider | None,
    ) -> None:
        """Hook: replace/clear the online enrichment provider for later SAVEs."""

        with self._lock:
            self._online_provider = provider or OnlineVesselSyncProvider()
        logger.info(
            "Vessel DB online sync provider registered: %s",
            self._online_provider.provider_id,
        )

    def collect_snapshot(self, *, run_integrity: bool = False) -> VesselDatabaseManagerSnapshot:

        local = self._collect_local()
        if run_integrity:
            integrity, detail = self.verify_integrity()
        else:
            with self._lock:
                integrity = self._last_integrity
                detail = self._last_integrity_detail

        access, access_detail = self._probe_access()
        status = self._derive_status(local, integrity, access)

        with self._lock:
            synchronization = SynchronizationInfo(
                last_sync=self._last_sync,
                next_sync=self._next_sync,
                auto_sync_enabled=self._auto_sync_enabled,
                sync_interval_seconds=self._sync_interval_seconds,
                state=self._sync_state,
                last_error=self._last_error,
            )
            statistics = SyncStatistics(
                imported_vessels=self._imported,
                updated_vessels=self._updated,
                unknown_vessels=self._unknown,
                failed_lookups=self._failed_lookups,
            )

        return VesselDatabaseManagerSnapshot(
            local=local,
            synchronization=synchronization,
            statistics=statistics,
            diagnostics=DiagnosticsInfo(
                database_status=status,
                integrity=integrity,
                integrity_detail=detail,
                access=access,
                access_detail=access_detail,
            ),
        )

    def set_auto_sync(self, enabled: bool) -> None:
        """Enable/disable automatic synchronization; persists and wakes scheduler."""

        enabled = bool(enabled)
        with self._lock:
            previous = self._auto_sync_enabled
            self._auto_sync_enabled = enabled
            if enabled:
                self._recompute_next_sync_locked(datetime.now())
            else:
                self._next_sync = None
            interval = self._sync_interval_seconds
            next_sync = self._next_sync

        self._persist_state()
        self._ensure_scheduler()
        self._scheduler_wake.set()

        if previous != enabled:
            eventbus.publish(
                EVENT_AUTO_SYNC_CHANGED,
                enabled=enabled,
                next_sync=next_sync,
                interval_seconds=interval,
            )
        logger.info("Vessel DB auto-sync %s", "enabled" if enabled else "disabled")

    def set_sync_interval(self, seconds: float) -> None:

        seconds = max(30.0, float(seconds))
        with self._lock:
            self._sync_interval_seconds = seconds
            if self._auto_sync_enabled:
                self._recompute_next_sync_locked(datetime.now())
        self._persist_state()
        self._scheduler_wake.set()

    def start_synchronization(self) -> bool:
        """Manual sync — returns False if a sync is already running."""

        return self._begin_sync(trigger="manual")

    def stop(self, timeout: float = 5.0) -> None:

        self._stop_requested = True
        self._scheduler_stop.set()
        self._scheduler_wake.set()

        scheduler = self._scheduler_thread
        if scheduler is not None and scheduler.is_alive():
            scheduler.join(timeout=timeout)

        sync_thread = self._sync_thread
        if sync_thread is not None and sync_thread.is_alive():
            sync_thread.join(timeout=timeout)

    def verify_integrity(self) -> tuple[IntegrityStatus, str]:

        path = self._db_path
        if not path.exists():
            status = IntegrityStatus.UNKNOWN
            detail = "Database file not found"
            with self._lock:
                self._last_integrity = status
                self._last_integrity_detail = detail
            return status, detail

        try:
            connection = sqlite3.connect(
                path,
                timeout=30.0,
                check_same_thread=False,
            )
            try:
                row = connection.execute("PRAGMA integrity_check").fetchone()
            finally:
                connection.close()
            result = str(row[0]) if row else "unknown"
            if result.lower() == "ok":
                status = IntegrityStatus.OK
                detail = "ok"
            else:
                status = IntegrityStatus.FAILED
                detail = result[:200]
        except Exception as exc:
            logger.exception("Vessel DB integrity check failed")
            status = IntegrityStatus.FAILED
            detail = str(exc)

        with self._lock:
            self._last_integrity = status
            self._last_integrity_detail = detail
        return status, detail

    def record_import(self, count: int = 1) -> None:

        with self._lock:
            self._imported += max(0, int(count))

    def record_update(self, count: int = 1) -> None:

        with self._lock:
            self._updated += max(0, int(count))

    def record_unknown(self, count: int = 1) -> None:

        with self._lock:
            self._unknown += max(0, int(count))

    def record_failed_lookup(self, count: int = 1) -> None:

        with self._lock:
            self._failed_lookups += max(0, int(count))

    def reset_session_statistics(self) -> None:

        with self._lock:
            self._imported = 0
            self._updated = 0
            self._unknown = 0
            self._failed_lookups = 0

    def _begin_sync(self, *, trigger: str) -> bool:

        with self._lock:
            if self._sync_state == SyncState.RUNNING:
                return False
            if self._sync_thread is not None and self._sync_thread.is_alive():
                return False
            previous, new_state, err = self._set_state_locked(SyncState.RUNNING, error="")
            thread = Thread(
                target=self._run_sync_job,
                kwargs={"trigger": trigger},
                name="VesselDatabaseSync",
                daemon=True,
            )
            self._sync_thread = thread

        if previous != new_state:
            eventbus.publish(
                EVENT_SYNC_STATE_CHANGED,
                state=new_state.value,
                previous=previous.value,
                error=err,
            )
        eventbus.publish(EVENT_SYNC_STARTED, trigger=trigger)
        thread.start()
        return True

    def _run_sync_job(self, *, trigger: str) -> None:

        def progress(fraction: float, message: str) -> None:

            callback: ProgressCallback | None
            with self._lock:
                callback = self._progress_callback
            eventbus.publish(
                EVENT_SYNC_PROGRESS,
                fraction=max(0.0, min(1.0, float(fraction))),
                message=str(message),
                trigger=trigger,
            )
            if callback is not None:
                try:
                    callback(fraction, message)
                except Exception:
                    logger.exception("Vessel DB sync progress callback failed")

        try:
            local_provider = self._local_provider
            online_provider = self._online_provider

            progress(0.0, "Local registry synchronization")
            local_result = local_provider.synchronize(progress=progress)

            progress(0.92, "Online provider hook")
            online_result = online_provider.synchronize(
                progress=lambda _f, msg: progress(0.95, msg)
            )

            combined = self._merge_results(local_result, online_result)
            now = datetime.now()

            with self._lock:
                self._imported += combined.imported
                self._updated += combined.updated
                self._unknown += combined.unknown
                self._failed_lookups += combined.failed_lookups
                self._last_sync = now
                if combined.success:
                    previous, new_state, err = self._set_state_locked(
                        SyncState.IDLE, error=""
                    )
                else:
                    previous, new_state, err = self._set_state_locked(
                        SyncState.ERROR,
                        error=combined.message or "Synchronization failed",
                    )
                if self._auto_sync_enabled:
                    self._recompute_next_sync_locked(now)
                else:
                    self._next_sync = None
                last_error = self._last_error
                next_sync = self._next_sync

            if previous != new_state:
                eventbus.publish(
                    EVENT_SYNC_STATE_CHANGED,
                    state=new_state.value,
                    previous=previous.value,
                    error=err,
                )

            self._persist_state()

            if combined.success:
                eventbus.publish(
                    EVENT_SYNC_COMPLETED,
                    trigger=trigger,
                    result=combined,
                    last_sync=now,
                    next_sync=next_sync,
                )
                progress(1.0, combined.message or "Synchronization complete")
            else:
                eventbus.publish(
                    EVENT_SYNC_FAILED,
                    trigger=trigger,
                    result=combined,
                    error=last_error,
                )
        except Exception as exc:
            logger.exception("Vessel DB synchronization crashed")
            now = datetime.now()
            with self._lock:
                self._last_sync = now
                previous, new_state, err = self._set_state_locked(
                    SyncState.ERROR, error=str(exc)
                )
                if self._auto_sync_enabled:
                    self._recompute_next_sync_locked(now)
                else:
                    self._next_sync = None
                next_sync = self._next_sync
            if previous != new_state:
                eventbus.publish(
                    EVENT_SYNC_STATE_CHANGED,
                    state=new_state.value,
                    previous=previous.value,
                    error=err,
                )
            self._persist_state()
            eventbus.publish(
                EVENT_SYNC_FAILED,
                trigger=trigger,
                error=str(exc),
                next_sync=next_sync,
            )
        finally:
            with self._lock:
                running_stuck = self._sync_state == SyncState.RUNNING
                if running_stuck:
                    previous, new_state, err = self._set_state_locked(
                        SyncState.IDLE, error=self._last_error
                    )
                else:
                    previous = new_state = None
                    err = ""
                self._sync_thread = None
            if previous is not None and previous != new_state:
                eventbus.publish(
                    EVENT_SYNC_STATE_CHANGED,
                    state=new_state.value,
                    previous=previous.value,
                    error=err,
                )
            self._scheduler_wake.set()

    @staticmethod
    def _merge_results(
        local: VesselSyncResult,
        online: VesselSyncResult,
    ) -> VesselSyncResult:

        success = local.success and online.success
        message_parts = [part for part in (local.message, online.message) if part]
        return VesselSyncResult(
            success=success,
            imported=local.imported + online.imported,
            updated=local.updated + online.updated,
            unknown=local.unknown + online.unknown,
            failed_lookups=local.failed_lookups + online.failed_lookups,
            message=" | ".join(message_parts),
            details={
                "local": local.details,
                "online": online.details,
            },
        )

    def _ensure_scheduler(self) -> None:

        with self._lock:
            if self._stop_requested:
                return
            thread = self._scheduler_thread
            if thread is not None and thread.is_alive():
                return
            self._scheduler_stop.clear()
            self._scheduler_thread = Thread(
                target=self._scheduler_loop,
                name="VesselDatabaseSyncScheduler",
                daemon=True,
            )
            self._scheduler_thread.start()

    def _scheduler_loop(self) -> None:

        while not self._scheduler_stop.is_set():
            wait_s = _SCHEDULER_TICK_S
            due = False

            with self._lock:
                if (
                    self._auto_sync_enabled
                    and self._next_sync is not None
                    and self._sync_state != SyncState.RUNNING
                ):
                    remaining = (self._next_sync - datetime.now()).total_seconds()
                    if remaining <= 0:
                        due = True
                    else:
                        wait_s = min(_SCHEDULER_TICK_S, max(0.05, remaining))

            if due:
                started = self._begin_sync(trigger="auto")
                if not started:
                    with self._lock:
                        # Busy — retry shortly.
                        self._next_sync = datetime.now() + timedelta(seconds=5)
                self._scheduler_wake.wait(timeout=_SCHEDULER_TICK_S)
                self._scheduler_wake.clear()
                continue

            self._scheduler_wake.wait(timeout=wait_s)
            self._scheduler_wake.clear()

    def _recompute_next_sync_locked(self, reference: datetime) -> None:

        if not self._auto_sync_enabled:
            self._next_sync = None
            return
        base = self._last_sync or reference
        candidate = base + timedelta(seconds=self._sync_interval_seconds)
        if candidate <= reference:
            candidate = reference + timedelta(seconds=self._sync_interval_seconds)
        self._next_sync = candidate

    def _set_state_locked(self, state: SyncState, *, error: str) -> tuple[SyncState, SyncState, str]:
        """Update state under lock. Returns (previous, new, error) for event publish."""

        previous = self._sync_state
        self._sync_state = state
        self._last_error = str(error or "")
        return previous, state, self._last_error

    def _apply_state(self, state: SyncState, *, error: str = "") -> None:

        with self._lock:
            previous, new_state, err = self._set_state_locked(state, error=error)
        if previous != new_state:
            eventbus.publish(
                EVENT_SYNC_STATE_CHANGED,
                state=new_state.value,
                previous=previous.value,
                error=err,
            )

    def _load_persisted_state(self) -> None:

        path = self._state_path
        if not path.exists():
            return

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load vessel DB sync state from %s", path)
            return

        if not isinstance(payload, dict):
            return

        with self._lock:
            self._auto_sync_enabled = bool(payload.get("auto_sync_enabled", False))
            try:
                interval = float(
                    payload.get("sync_interval_seconds", _DEFAULT_SYNC_INTERVAL_S)
                )
            except (TypeError, ValueError):
                interval = _DEFAULT_SYNC_INTERVAL_S
            self._sync_interval_seconds = max(30.0, interval)
            self._last_sync = _parse_timestamp(payload.get("last_sync"))
            self._imported = int(payload.get("imported_vessels", 0) or 0)
            self._updated = int(payload.get("updated_vessels", 0) or 0)
            self._unknown = int(payload.get("unknown_vessels", 0) or 0)
            self._failed_lookups = int(payload.get("failed_lookups", 0) or 0)
            if self._auto_sync_enabled:
                self._recompute_next_sync_locked(datetime.now())
            else:
                self._next_sync = None

    def _persist_state(self) -> None:

        with self._lock:
            payload = {
                "auto_sync_enabled": self._auto_sync_enabled,
                "sync_interval_seconds": self._sync_interval_seconds,
                "last_sync": (
                    self._last_sync.isoformat(timespec="seconds")
                    if self._last_sync
                    else None
                ),
                "imported_vessels": self._imported,
                "updated_vessels": self._updated,
                "unknown_vessels": self._unknown,
                "failed_lookups": self._failed_lookups,
            }
            path = self._state_path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist vessel DB sync state to %s", path)

    def _collect_local(self) -> LocalDatabaseInfo:

        path = self._db_path
        size_bytes = 0
        last_updated: datetime | None = None

        if path.exists():
            try:
                stat = path.stat()
                size_bytes = int(stat.st_size)
                last_updated = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                logger.debug("Failed to stat vessel database", exc_info=True)

        try:
            vessel_count = int(vessel_database.count())
        except Exception:
            logger.exception("Failed to count vessels")
            vessel_count = 0

        try:
            latest = vessel_database.latest_updated_at()
            if latest is not None:
                last_updated = latest
        except Exception:
            logger.debug("Failed to read latest vessel updated_at", exc_info=True)

        return LocalDatabaseInfo(
            vessel_count=vessel_count,
            size_bytes=size_bytes,
            last_updated=last_updated,
            schema_version=VESSEL_DB_SCHEMA_VERSION,
            database_path=path,
        )

    def _probe_access(self) -> tuple[AccessStatus, str]:

        path = self._db_path
        parent = path.parent

        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return AccessStatus.NO_ACCESS, str(exc)

        readable = os.access(parent, os.R_OK)
        writable = os.access(parent, os.W_OK)

        if path.exists():
            readable = readable and os.access(path, os.R_OK)
            writable = writable and os.access(path, os.W_OK)

        if readable and writable:
            return AccessStatus.READ_WRITE, "Read/Write"
        if readable:
            return AccessStatus.READ_ONLY, "Read-only"
        return AccessStatus.NO_ACCESS, "No access"

    @staticmethod
    def _derive_status(
        local: LocalDatabaseInfo,
        integrity: IntegrityStatus,
        access: AccessStatus,
    ) -> DatabaseStatus:

        if access == AccessStatus.NO_ACCESS:
            return DatabaseStatus.ERROR
        if integrity == IntegrityStatus.FAILED:
            return DatabaseStatus.ERROR
        if not local.database_path.exists():
            return DatabaseStatus.WARNING
        if access == AccessStatus.READ_ONLY:
            return DatabaseStatus.WARNING
        if integrity in (IntegrityStatus.OK, IntegrityStatus.NOT_CHECKED):
            return DatabaseStatus.OK
        return DatabaseStatus.UNKNOWN


def format_bytes(size_bytes: int) -> str:

    return _format_size(size_bytes)


def default_database_folder() -> Path:

    path = VESSEL_DATABASE_FILE.parent
    if path.exists():
        return path
    return runtime_data_dir()


vessel_database_manager = VesselDatabaseManager()
