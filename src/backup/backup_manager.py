# ============================================================================
# Project X
# Backup & Restore Manager (SAVE-210)
# ============================================================================

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock

from app.paths import (
    backups_dir,
    runtime_config_dir,
    runtime_data_dir,
)
from version import PROJECT_VERSION

logger = logging.getLogger(__name__)

BACKUP_MANIFEST_NAME = "manifest.json"
BACKUP_PREFIX = "ProjectX-backup"


class BackupKind(str, Enum):

    FULL = "full"
    DATABASE = "database"
    SETTINGS = "settings"


@dataclass(frozen=True)
class BackupEntry:
    path: Path
    kind: BackupKind
    created_at: datetime
    size_bytes: int
    label: str
    version: str
    file_count: int


@dataclass(frozen=True)
class BackupResult:
    success: bool
    message: str
    entry: BackupEntry | None = None


def format_bytes(size_bytes: int) -> str:

    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _database_sources() -> list[tuple[str, Path]]:
    """Logical zip path → filesystem path for database backups."""

    data = runtime_data_dir()
    candidates = [
        ("data/vessels.db", data / "vessels.db"),
        ("data/timeline.db", data / "timeline.db"),
        ("data/alerts.db", data / "alerts.db"),
        ("data/vessel_db_sync_state.json", data / "vessel_db_sync_state.json"),
    ]
    photos_db = data / "vessel_photos" / "photos.db"
    candidates.append(("data/vessel_photos/photos.db", photos_db))
    return candidates


def _settings_sources() -> list[tuple[str, Path]]:

    config = runtime_config_dir()
    candidates = [
        ("config/preferences.json", config / "preferences.json"),
        ("config/observation_points.json", config / "observation_points.json"),
        ("config/cameras.json", config / "cameras.json"),
        ("config/ais_api_key.txt", config / "ais_api_key.txt"),
        ("config/camera_packs_state.json", config / "camera_packs_state.json"),
        ("config/camera_packs/state.json", config / "camera_packs" / "state.json"),
    ]
    # Playback preferences may live under src/config in dev builds.
    playback = Path(
        __import__("os").environ.get(
            "PROJECTX_PLAYBACK_PREFERENCES_FILE",
            str(config / "playback_preferences.json"),
        )
    )
    candidates.append(("config/playback_preferences.json", playback))
    return candidates


def _sources_for_kind(kind: BackupKind) -> list[tuple[str, Path]]:

    if kind == BackupKind.DATABASE:
        return _database_sources()
    if kind == BackupKind.SETTINGS:
        return _settings_sources()
    return _database_sources() + _settings_sources()


def _copy_sqlite_safe(source: Path, destination: Path) -> None:

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        src = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30.0)
        try:
            dst = sqlite3.connect(destination)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except Exception:
        logger.debug("SQLite backup API failed for %s — file copy", source, exc_info=True)
        shutil.copy2(source, destination)
        for suffix in ("-wal", "-shm"):
            side = Path(str(source) + suffix)
            if side.exists():
                shutil.copy2(side, Path(str(destination) + suffix))


def _add_file_to_zip(archive: zipfile.ZipFile, source: Path, arcname: str) -> None:

    if source.suffix.lower() == ".db":
        with tempfile.TemporaryDirectory(prefix="px_bak_") as tmp:
            tmp_path = Path(tmp) / source.name
            _copy_sqlite_safe(source, tmp_path)
            archive.write(tmp_path, arcname)
            for suffix in ("-wal", "-shm"):
                side = Path(str(tmp_path) + suffix)
                if side.exists():
                    archive.write(side, arcname + suffix)
        return

    archive.write(source, arcname)


class BackupManager:

    def __init__(self, root: Path | None = None) -> None:

        self._root = Path(root) if root is not None else backups_dir()
        self._lock = Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def backups_root(self) -> Path:

        return self._root

    def list_backups(self) -> list[BackupEntry]:

        with self._lock:
            entries: list[BackupEntry] = []
            if not self._root.exists():
                return entries

            for path in sorted(self._root.glob(f"{BACKUP_PREFIX}-*.zip"), reverse=True):
                entry = self._read_entry(path)
                if entry is not None:
                    entries.append(entry)
            return entries

    def create_backup(self, kind: BackupKind) -> BackupResult:

        kind = BackupKind(kind)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{BACKUP_PREFIX}-{kind.value}-{stamp}.zip"
        target = self._root / filename

        sources = [
            (arc, path)
            for arc, path in _sources_for_kind(kind)
            if path.exists() and path.is_file()
        ]

        if not sources:
            return BackupResult(
                success=False,
                message="No files available for this backup type",
            )

        included: list[str] = []
        try:
            with self._lock:
                self._root.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(
                    target,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                ) as archive:
                    for arcname, source in sources:
                        _add_file_to_zip(archive, source, f"files/{arcname}")
                        included.append(arcname)

                    manifest = {
                        "format": 1,
                        "kind": kind.value,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "project_version": PROJECT_VERSION,
                        "files": included,
                        "label": f"{kind.value} backup",
                    }
                    archive.writestr(
                        BACKUP_MANIFEST_NAME,
                        json.dumps(manifest, indent=2),
                    )
        except Exception as exc:
            logger.exception("Failed to create backup %s", target)
            if target.exists():
                try:
                    target.unlink()
                except OSError:
                    pass
            return BackupResult(success=False, message=str(exc))

        entry = self._read_entry(target)
        return BackupResult(
            success=True,
            message=f"Backup created ({len(included)} files)",
            entry=entry,
        )

    def restore_backup(self, path: Path | str) -> BackupResult:

        archive_path = Path(path)
        if not archive_path.is_file():
            return BackupResult(success=False, message="Backup file not found")

        entry = self._read_entry(archive_path)
        if entry is None:
            return BackupResult(success=False, message="Invalid backup archive")

        try:
            with self._lock:
                with tempfile.TemporaryDirectory(prefix="px_restore_") as tmp:
                    tmp_root = Path(tmp)
                    with zipfile.ZipFile(archive_path, mode="r") as archive:
                        archive.extractall(tmp_root)

                    files_root = tmp_root / "files"
                    if not files_root.exists():
                        return BackupResult(
                            success=False,
                            message="Backup archive has no files payload",
                        )

                    restored = 0
                    for source in files_root.rglob("*"):
                        if not source.is_file():
                            continue
                        rel = source.relative_to(files_root).as_posix()
                        destination = self._destination_for_arcname(rel)
                        if destination is None:
                            logger.warning("Skipping unknown backup path %s", rel)
                            continue
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, destination)
                        restored += 1
        except Exception as exc:
            logger.exception("Failed to restore backup %s", archive_path)
            return BackupResult(success=False, message=str(exc))

        return BackupResult(
            success=True,
            message=f"Restored {restored} file(s) from {entry.kind.value} backup",
            entry=entry,
        )

    def delete_backup(self, path: Path | str) -> BackupResult:

        archive_path = Path(path)
        if not archive_path.is_file():
            return BackupResult(success=False, message="Backup file not found")

        try:
            # Only allow deletes inside backups root.
            archive_path.resolve().relative_to(self._root.resolve())
        except ValueError:
            return BackupResult(success=False, message="Backup is outside backups directory")

        try:
            with self._lock:
                archive_path.unlink()
        except Exception as exc:
            logger.exception("Failed to delete backup %s", archive_path)
            return BackupResult(success=False, message=str(exc))

        return BackupResult(success=True, message="Backup deleted")

    def _destination_for_arcname(self, arcname: str) -> Path | None:

        normalized = arcname.replace("\\", "/").lstrip("/")
        if normalized.startswith("data/"):
            return runtime_data_dir() / normalized[len("data/") :]
        if normalized.startswith("config/"):
            return runtime_config_dir() / normalized[len("config/") :]
        return None

    def _read_entry(self, path: Path) -> BackupEntry | None:

        try:
            size_bytes = path.stat().st_size
            with zipfile.ZipFile(path, mode="r") as archive:
                if BACKUP_MANIFEST_NAME not in archive.namelist():
                    return None
                payload = json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))
        except Exception:
            logger.debug("Failed to read backup manifest %s", path, exc_info=True)
            return None

        kind_raw = str(payload.get("kind", BackupKind.FULL.value)).strip().lower()
        try:
            kind = BackupKind(kind_raw)
        except ValueError:
            kind = BackupKind.FULL

        created_raw = payload.get("created_at")
        created: datetime | None = None
        if created_raw:
            try:
                created = datetime.fromisoformat(str(created_raw))
            except ValueError:
                created = None
        if created is None:
            created = datetime.fromtimestamp(path.stat().st_mtime)

        files = payload.get("files") or []
        return BackupEntry(
            path=path,
            kind=kind,
            created_at=created,
            size_bytes=int(size_bytes),
            label=str(payload.get("label") or path.name),
            version=str(payload.get("project_version") or ""),
            file_count=len(files) if isinstance(files, list) else 0,
        )


backup_manager = BackupManager()
