# ============================================================================
# Project X
# Legacy Data Migration Engine (SAVE-107-B4)
# ============================================================================

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from storage.exceptions import MigrationError
from storage.layout import (
    DATA_SUBDIR_CACHE,
    DATA_SUBDIR_CONFIG,
    DATA_SUBDIR_DATABASES,
    DATA_SUBDIR_EXPORTS,
    DATA_SUBDIR_HAJOK,
    DATA_SUBDIR_LOGS,
)
from storage.legacy import LegacyDataInventory, collect_legacy_inventory
from storage.manager import ensure_data_layout, validate_data_directory_or_raise
from storage.marker import is_valid_data_root, require_marked_data_root
from storage.migration_state import (
    MigrationPhase,
    MigrationState,
    MigrationStateStore,
)

_LEGACY_DB_NAMES = ("vessels.db", "timeline.db", "alerts.db")
_LEGACY_CACHE_FILES = ("ship_cache.json", "obs_freeze.trace")
_LEGACY_CACHE_DIRS = ("deli_hajok", "vessel_photos")
_LEGACY_CONFIG_NAMES = (
    "observation_points.json",
    "cameras.json",
    "ais_api_key.txt",
    "camera_packs_state.json",
    "playback.json",
)


class CopyAction(str, Enum):
    COPIED = "copied"
    SKIPPED_IDENTICAL = "skipped_identical"
    SKIPPED_NEWER_DESTINATION = "skipped_newer_destination"


@dataclass(frozen=True)
class MigrationCopyItem:
    """One source file mapped to a destination path under the data root."""

    source: Path
    destination: Path


@dataclass
class MigrationVerificationReport:
    """Post-copy verification metrics."""

    ship_folder_count: int
    database_file_count: int
    file_count: int
    total_bytes: int
    expected_ship_folder_count: int
    expected_database_file_count: int
    expected_file_count: int
    expected_total_bytes: int

    @property
    def matches_source(self) -> bool:

        return (
            self.ship_folder_count == self.expected_ship_folder_count
            and self.database_file_count == self.expected_database_file_count
            and self.file_count == self.expected_file_count
            and self.total_bytes == self.expected_total_bytes
        )


@dataclass
class MigrationResult:
    """Outcome of a migration attempt."""

    success: bool
    destination_root: Path | None = None
    phase: MigrationPhase = MigrationPhase.PENDING
    verification: MigrationVerificationReport | None = None
    copied_files: int = 0
    message: str = ""
    rolled_back: bool = False


@dataclass
class _MigrationContext:
    destination_root: Path
    source_inventory: LegacyDataInventory
    state: MigrationState
    state_store: MigrationStateStore
    copy_items: list[MigrationCopyItem] = field(default_factory=list)


def migration_state_path() -> Path:

    return MigrationStateStore().path


def build_migration_copy_plan(
    inventory: LegacyDataInventory,
    destination_root: Path,
) -> list[MigrationCopyItem]:
    """Build the legacy → configured layout copy plan without touching disk."""

    return _build_copy_plan(inventory, destination_root)


def _build_copy_plan(
    inventory: LegacyDataInventory,
    destination_root: Path,
) -> list[MigrationCopyItem]:

    root = destination_root.resolve()
    items: list[MigrationCopyItem] = []

    hajok_source = inventory.data_root / DATA_SUBDIR_HAJOK

    if hajok_source.is_dir():
        items.extend(
            _tree_copy_items(
                hajok_source,
                root / DATA_SUBDIR_HAJOK,
            )
        )

    for name in _LEGACY_DB_NAMES:
        source = inventory.data_root / name

        if source.is_file():
            items.append(
                MigrationCopyItem(
                    source=source,
                    destination=root / DATA_SUBDIR_DATABASES / name,
                )
            )

    for name in _LEGACY_CACHE_FILES:
        source = inventory.data_root / name

        if source.is_file():
            items.append(
                MigrationCopyItem(
                    source=source,
                    destination=root / DATA_SUBDIR_CACHE / name,
                )
            )

    for name in _LEGACY_CACHE_DIRS:
        source = inventory.data_root / name

        if source.exists():
            items.extend(
                _tree_copy_items(
                    source,
                    root / DATA_SUBDIR_CACHE / name,
                )
            )

    exports_source = inventory.data_root / "exports"

    if exports_source.exists():
        items.extend(
            _tree_copy_items(
                exports_source,
                root / DATA_SUBDIR_EXPORTS,
            )
        )

    for name in _LEGACY_CONFIG_NAMES:
        source = inventory.config_root / name

        if source.is_file():
            items.append(
                MigrationCopyItem(
                    source=source,
                    destination=root / DATA_SUBDIR_CONFIG / name,
                )
            )

    dev_pack_state = inventory.config_root / "camera_packs" / "state.json"
    configured_pack_state = root / DATA_SUBDIR_CONFIG / "camera_packs_state.json"

    if dev_pack_state.is_file() and not configured_pack_state.is_file():
        items.append(
            MigrationCopyItem(
                source=dev_pack_state,
                destination=configured_pack_state,
            )
        )

    if inventory.logs_root.is_dir():
        items.extend(
            _tree_copy_items(
                inventory.logs_root,
                root / DATA_SUBDIR_LOGS,
            )
        )

    return items


def _tree_copy_items(source_root: Path, destination_root: Path) -> list[MigrationCopyItem]:

    items: list[MigrationCopyItem] = []

    if not source_root.exists():
        return items

    for path in sorted(source_root.rglob("*")):

        if not path.is_file():
            continue

        relative = path.relative_to(source_root)
        items.append(
            MigrationCopyItem(
                source=path,
                destination=destination_root / relative,
            )
        )

    return items


def _file_digest(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _copy_file(source: Path, destination: Path) -> CopyAction:

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file():
        if destination.stat().st_mtime > source.stat().st_mtime:
            if _file_digest(source) == _file_digest(destination):
                return CopyAction.SKIPPED_IDENTICAL
            return CopyAction.SKIPPED_NEWER_DESTINATION

        if _file_digest(source) == _file_digest(destination):
            return CopyAction.SKIPPED_IDENTICAL

    shutil.copy2(source, destination)
    return CopyAction.COPIED


def _relative_destination_path(destination_root: Path, path: Path) -> str:

    return str(path.resolve().relative_to(destination_root.resolve()))


def _collect_migrated_inventory(
    destination_root: Path,
    *,
    source_inventory: LegacyDataInventory,
    copy_items: list[MigrationCopyItem],
) -> MigrationVerificationReport:

    hajok_dir = destination_root / DATA_SUBDIR_HAJOK
    ship_folder_count = 0

    if hajok_dir.is_dir():
        ship_folder_count = sum(1 for child in hajok_dir.iterdir() if child.is_dir())

    database_file_count = sum(
        1
        for name in _LEGACY_DB_NAMES
        if (destination_root / DATA_SUBDIR_DATABASES / name).is_file()
    )

    destination_files = {
        item.destination.resolve()
        for item in copy_items
        if item.destination.is_file()
    }

    file_count = 0
    total_bytes = 0

    for path in destination_files:
        file_count += 1

        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue

    expected_file_count = 0
    expected_total_bytes = 0

    for item in copy_items:
        if not item.source.is_file():
            continue

        expected_file_count += 1

        try:
            expected_total_bytes += item.source.stat().st_size
        except OSError:
            continue

    return MigrationVerificationReport(
        ship_folder_count=ship_folder_count,
        database_file_count=database_file_count,
        file_count=file_count,
        total_bytes=total_bytes,
        expected_ship_folder_count=source_inventory.ship_folder_count,
        expected_database_file_count=len(source_inventory.database_files),
        expected_file_count=expected_file_count,
        expected_total_bytes=expected_total_bytes,
    )


def _verify_sqlite_files(destination_root: Path) -> None:

    for name in _LEGACY_DB_NAMES:
        db_path = destination_root / DATA_SUBDIR_DATABASES / name

        if not db_path.is_file():
            continue

        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
                connection.execute("SELECT 1")
        except sqlite3.Error as exc:
            raise MigrationError(
                f"SQLite verification failed for {name}: {exc}"
            ) from exc


def _verify_config_files(destination_root: Path) -> None:

    config_dir = destination_root / DATA_SUBDIR_CONFIG

    if not config_dir.is_dir():
        return

    for path in sorted(config_dir.iterdir()):

        if not path.is_file():
            continue

        if path.suffix == ".json":
            try:
                with path.open(encoding="utf-8") as handle:
                    json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise MigrationError(
                    f"Configuration verification failed for {path.name}: {exc}"
                ) from exc

            continue

        try:
            path.read_text(encoding="utf-8")
        except OSError as exc:
            raise MigrationError(
                f"Configuration verification failed for {path.name}: {exc}"
            ) from exc


def _verify_migration(context: _MigrationContext) -> MigrationVerificationReport:

    report = _collect_migrated_inventory(
        context.destination_root,
        source_inventory=context.source_inventory,
        copy_items=context.copy_items,
    )

    if not report.matches_source:
        raise MigrationError(
            "Migration verification failed: destination inventory does not match "
            f"source (ships {report.ship_folder_count}/{report.expected_ship_folder_count}, "
            f"databases {report.database_file_count}/{report.expected_database_file_count}, "
            f"files {report.file_count}/{report.expected_file_count}, "
            f"bytes {report.total_bytes}/{report.expected_total_bytes})"
        )

    _verify_sqlite_files(context.destination_root)
    _verify_config_files(context.destination_root)
    return report


def _rollback_destination(context: _MigrationContext) -> None:

    destination_root = context.destination_root.resolve()

    if not is_valid_data_root(destination_root):
        raise MigrationError(
            "Rollback refused: destination does not contain a valid "
            ".projectx-data-root marker"
        )

    marked_root = require_marked_data_root(destination_root)

    for relative_path in reversed(context.state.copied_paths):
        target = marked_root / relative_path

        try:
            target.relative_to(marked_root.resolve())
        except ValueError as exc:
            raise MigrationError(
                f"Rollback refused: path escapes marked data root: {target}"
            ) from exc

        if target.is_file():
            target.unlink(missing_ok=True)

    context.state.touch(phase=MigrationPhase.ROLLED_BACK)
    context.state_store.save(context.state)


class DataMigrationService:
    """Copy → verify → commit migration service for legacy Project X data."""

    def __init__(
        self,
        *,
        state_store: MigrationStateStore | None = None,
        preferences_manager=None,
    ) -> None:

        self._state_store = state_store or MigrationStateStore()

        if preferences_manager is None:
            from preferences.preferences_manager import preferences_manager as default_manager

            preferences_manager = default_manager

        self._preferences_manager = preferences_manager

    def run(self, destination: Path) -> MigrationResult:

        destination_root = validate_data_directory_or_raise(Path(destination)).resolve()

        preferences = self._preferences_manager.get()

        if preferences.has_data_directory():
            configured = Path(preferences.data_directory).expanduser().resolve()

            if configured == destination_root and is_valid_data_root(destination_root):
                return MigrationResult(
                    success=True,
                    destination_root=destination_root,
                    phase=MigrationPhase.COMPLETED,
                    message="Data directory already configured.",
                )

            raise MigrationError(
                "Migration refused: preferences already point to a different data directory."
            )

        source_inventory = collect_legacy_inventory()
        existing_state = self._state_store.load()

        if (
            existing_state is not None
            and Path(existing_state.destination_root).resolve() == destination_root
            and existing_state.phase in {
                MigrationPhase.COPYING,
                MigrationPhase.VERIFYING,
                MigrationPhase.FAILED,
            }
        ):
            self.rollback(existing_state)

        destination_preexisting = destination_root.exists() and any(
            (destination_root / name).exists() for name in (
                DATA_SUBDIR_HAJOK,
                DATA_SUBDIR_CACHE,
                DATA_SUBDIR_CONFIG,
                DATA_SUBDIR_DATABASES,
            )
        )

        state = MigrationState.new(
            destination_root,
            source_inventory.to_dict(),
            destination_preexisting=destination_preexisting,
        )
        self._state_store.save(state)

        context = _MigrationContext(
            destination_root=destination_root,
            source_inventory=source_inventory,
            state=state,
            state_store=self._state_store,
            copy_items=_build_copy_plan(source_inventory, destination_root),
        )

        copied_files = 0

        try:
            ensure_data_layout(destination_root)

            context.state.touch(phase=MigrationPhase.COPYING)
            context.state_store.save(context.state)

            for item in context.copy_items:
                relative = _relative_destination_path(destination_root, item.destination)
                action = _copy_file(item.source, item.destination)

                if action is CopyAction.SKIPPED_NEWER_DESTINATION:
                    raise MigrationError(
                        "Migration refused: destination file is newer than legacy source "
                        f"for {relative}"
                    )

                if action is CopyAction.COPIED:
                    copied_files += 1
                    context.state.copied_paths.append(relative)

                context.state_store.save(context.state)

            context.state.touch(phase=MigrationPhase.VERIFYING)
            context.state_store.save(context.state)

            verification = _verify_migration(context)

            context.state.touch(phase=MigrationPhase.COMMITTING)
            context.state_store.save(context.state)

            self._preferences_manager.set_data_directory(str(destination_root))

            context.state.touch(phase=MigrationPhase.COMPLETED, error=None)
            context.state_store.save(context.state)

            return MigrationResult(
                success=True,
                destination_root=destination_root,
                phase=MigrationPhase.COMPLETED,
                verification=verification,
                copied_files=copied_files,
                message="Migration completed successfully.",
            )

        except Exception as exc:
            message = str(exc) or exc.__class__.__name__

            try:
                self.rollback(context.state)
                rolled_back = True
            except MigrationError:
                context.state.touch(phase=MigrationPhase.FAILED, error=message)
                context.state_store.save(context.state)
                rolled_back = False

            return MigrationResult(
                success=False,
                destination_root=destination_root,
                phase=MigrationPhase.FAILED,
                copied_files=copied_files,
                message=message,
                rolled_back=rolled_back,
            )

    def rollback(self, state: MigrationState | None = None) -> MigrationResult:

        active_state = state or self._state_store.load()

        if active_state is None:
            return MigrationResult(
                success=True,
                message="No migration state to roll back.",
                rolled_back=False,
            )

        if active_state.phase == MigrationPhase.COMPLETED:
            raise MigrationError(
                "Rollback refused: migration already committed to preferences."
            )

        destination_root = Path(active_state.destination_root).resolve()
        source_inventory = LegacyDataInventory(
            data_root=Path(active_state.source_inventory["data_root"]),
            config_root=Path(active_state.source_inventory["config_root"]),
            logs_root=Path(active_state.source_inventory["logs_root"]),
            ship_folder_count=int(active_state.source_inventory["ship_folder_count"]),
            database_files=tuple(
                Path(path)
                for path in active_state.source_inventory.get("database_files", [])
            ),
            config_files=tuple(
                Path(path)
                for path in active_state.source_inventory.get("config_files", [])
            ),
            file_count=int(active_state.source_inventory["file_count"]),
            total_bytes=int(active_state.source_inventory["total_bytes"]),
        )

        context = _MigrationContext(
            destination_root=destination_root,
            source_inventory=source_inventory,
            state=active_state,
            state_store=self._state_store,
        )

        _rollback_destination(context)

        return MigrationResult(
            success=True,
            destination_root=destination_root,
            phase=MigrationPhase.ROLLED_BACK,
            message="Migration rollback completed.",
            rolled_back=True,
        )
