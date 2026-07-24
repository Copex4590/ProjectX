# ============================================================================
# Project X
# Session Storage (.pxsession) (SAVE-219)
# ============================================================================

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from threading import Lock

from app.paths import sessions_dir
from session.models import (
    SESSION_EVENTS_NAME,
    SESSION_FILE_EXTENSION,
    SESSION_MANIFEST_NAME,
    RecordedEvent,
    SessionEntry,
    SessionManifest,
)

logger = logging.getLogger(__name__)


def format_bytes(size_bytes: int) -> str:

    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: float) -> str:

    total = int(max(0, seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


class SessionStorage:
    """List / load / save / import / export compressed session archives."""

    def __init__(self, root: Path | None = None):

        self._root = root
        self._lock = Lock()

    @property
    def root(self) -> Path:

        path = self._root or sessions_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_sessions(self) -> list[SessionEntry]:

        entries: list[SessionEntry] = []
        for path in sorted(self.root.glob(f"*{SESSION_FILE_EXTENSION}"), reverse=True):
            try:
                manifest = self.read_manifest(path)
                entries.append(
                    SessionEntry(
                        path=path,
                        manifest=manifest,
                        size_bytes=path.stat().st_size,
                    )
                )
            except Exception:
                logger.exception("Failed to read session %s", path)
        return entries

    def read_manifest(self, path: Path) -> SessionManifest:

        with zipfile.ZipFile(path, "r") as archive:
            raw = archive.read(SESSION_MANIFEST_NAME)
        return SessionManifest.from_dict(json.loads(raw.decode("utf-8")))

    def load_events(self, path: Path) -> tuple[SessionManifest, list[RecordedEvent]]:

        with zipfile.ZipFile(path, "r") as archive:
            manifest = SessionManifest.from_dict(
                json.loads(archive.read(SESSION_MANIFEST_NAME).decode("utf-8"))
            )
            events: list[RecordedEvent] = []
            with archive.open(SESSION_EVENTS_NAME) as handle:
                for line in handle:
                    text = line.decode("utf-8").strip()
                    if not text:
                        continue
                    events.append(RecordedEvent.from_dict(json.loads(text)))
        return manifest, events

    def write_session(
        self,
        *,
        manifest: SessionManifest,
        events: list[RecordedEvent],
        path: Path | None = None,
    ) -> Path:

        target = path or (
            self.root
            / f"session-{manifest.session_id}{SESSION_FILE_EXTENSION}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            with zipfile.ZipFile(
                target,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.writestr(
                    SESSION_MANIFEST_NAME,
                    json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
                )
                lines = [
                    json.dumps(event.to_dict(), ensure_ascii=False)
                    for event in events
                ]
                archive.writestr(
                    SESSION_EVENTS_NAME,
                    "\n".join(lines) + ("\n" if lines else ""),
                )
        return target

    def delete(self, path: Path) -> bool:

        resolved = path.resolve()
        root = self.root.resolve()
        if root not in resolved.parents and resolved.parent != root:
            # Allow delete of imported copies only under sessions dir.
            if not str(resolved).endswith(SESSION_FILE_EXTENSION):
                return False
        try:
            resolved.unlink(missing_ok=True)
            return True
        except OSError:
            logger.exception("Failed to delete session %s", path)
            return False

    def export_session(self, source: Path, destination: Path) -> Path:

        destination = Path(destination)
        if destination.suffix.lower() != SESSION_FILE_EXTENSION:
            destination = destination.with_suffix(SESSION_FILE_EXTENSION)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def import_session(self, source: Path) -> Path:

        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(str(source))
        # Validate archive.
        self.read_manifest(source)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.root / f"imported-{stamp}-{source.name}"
        if not target.name.endswith(SESSION_FILE_EXTENSION):
            target = target.with_suffix(SESSION_FILE_EXTENSION)
        shutil.copy2(source, target)
        return target


session_storage = SessionStorage()
