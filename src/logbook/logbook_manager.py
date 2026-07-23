# ============================================================================
# Project X
# Logbook Manager
# ============================================================================

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread

from logbook.duna_format import build_csv_row, sanitize_name
from logbook.paths import (
    CSV_FILENAME,
    CSV_HEADER,
    HAJOK_DIR,
    NOTES_FILENAME,
    PHOTOS_DIRNAME,
    XLSX_FILENAME,
)
from logbook.xlsx_generator import regenerate_xlsx

logger = logging.getLogger(__name__)

_STOP = object()


@dataclass(frozen=True)
class LegacyImportResult:

    imported_folders: int = 0
    skipped_folders: int = 0


class LogbookManager:

    def __init__(self, base_dir: Path | None = None):

        self._base_dir = Path(base_dir or HAJOK_DIR)
        self._lock = Lock()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._xlsx_queue: Queue[Path | object] = Queue()
        self._xlsx_worker: Thread | None = None
        self._xlsx_worker_lock = Lock()
        self._xlsx_pending: set[str] = set()
        self._stop_requested = False

    @property
    def base_dir(self) -> Path:

        return self._base_dir

    def ship_folder_name(self, ship) -> str:

        name = sanitize_name(getattr(ship, "name", ""))
        mmsi = getattr(ship, "mmsi", "")

        if name:
            return name

        return str(mmsi)

    def resolve_ship_dir(self, ship) -> Path:

        name = sanitize_name(getattr(ship, "name", ""))
        mmsi = str(getattr(ship, "mmsi", ""))

        for candidate in (name, mmsi):
            if not candidate:
                continue

            path = self._base_dir / candidate

            if path.exists():
                return path

        return self._base_dir / (name or mmsi)

    def resolve_ship_dir_by_mmsi(self, mmsi: int) -> Path | None:

        from database import registry

        ship = registry.get(int(mmsi))

        if ship is not None:
            path = self.resolve_ship_dir(ship)

            if path.exists():
                return path

        fallback = self._base_dir / str(int(mmsi))

        if fallback.exists():
            return fallback

        if self._base_dir.exists():
            for child in self._base_dir.iterdir():
                if not child.is_dir():
                    continue

                csv_file = child / CSV_FILENAME

                if not csv_file.exists():
                    continue

                if child.name == str(int(mmsi)):
                    return child

        return None

    def xlsx_path(self, ship) -> Path | None:

        ship_dir = self.resolve_ship_dir(ship)
        xlsx_file = ship_dir / XLSX_FILENAME

        if xlsx_file.exists():
            return xlsx_file

        return None

    def xlsx_path_for_mmsi(self, mmsi: int) -> Path | None:

        ship_dir = self.resolve_ship_dir_by_mmsi(mmsi)

        if ship_dir is None:
            return None

        xlsx_file = ship_dir / XLSX_FILENAME
        return xlsx_file if xlsx_file.exists() else None

    def has_logbook(self, ship) -> bool:

        ship_dir = self.resolve_ship_dir(ship)
        return (ship_dir / CSV_FILENAME).exists() or (ship_dir / XLSX_FILENAME).exists()

    def has_logbook_for_mmsi(self, mmsi: int) -> bool:

        ship_dir = self.resolve_ship_dir_by_mmsi(mmsi)

        if ship_dir is None:
            return False

        return (ship_dir / CSV_FILENAME).exists() or (ship_dir / XLSX_FILENAME).exists()

    def ensure_ship_folder(self, ship) -> Path:

        ship_dir = self.resolve_ship_dir(ship)
        created = not ship_dir.exists()
        ship_dir.mkdir(parents=True, exist_ok=True)
        (ship_dir / PHOTOS_DIRNAME).mkdir(parents=True, exist_ok=True)

        csv_file = ship_dir / CSV_FILENAME

        if not csv_file.exists():
            csv_file.write_text(CSV_HEADER, encoding="utf-8")

            if created:
                notes_file = ship_dir / NOTES_FILENAME

                if not notes_file.exists():
                    notes_file.write_text("", encoding="utf-8")

        return ship_dir

    def append_observation(self, ship) -> Path | None:
        """Append CSV on caller thread; schedule XLSX off the hot path."""

        ship_dir = self.ensure_ship_folder(ship)
        csv_file = ship_dir / CSV_FILENAME
        row = build_csv_row(ship)

        with self._lock:
            with csv_file.open("a", encoding="utf-8") as handle:
                handle.write(row)

        self.schedule_xlsx_regeneration(ship_dir)
        return ship_dir / XLSX_FILENAME

    def schedule_xlsx_regeneration(self, ship_dir: Path) -> None:

        if self._stop_requested:
            return

        key = str(Path(ship_dir).resolve())

        with self._xlsx_worker_lock:
            if key in self._xlsx_pending:
                return
            self._xlsx_pending.add(key)
            self._ensure_xlsx_worker_unlocked()
            self._xlsx_queue.put(Path(ship_dir))

    def ensure_xlsx(self, ship_dir: Path) -> Path | None:
        """Synchronously regenerate XLSX (UI open / import only)."""

        try:
            with self._lock:
                return regenerate_xlsx(Path(ship_dir))
        except Exception:
            logger.exception("Failed to regenerate logbook XLSX for %s", ship_dir)
            return None

    def stop(self, timeout: float = 5.0) -> None:

        self._stop_requested = True

        with self._xlsx_worker_lock:
            worker = self._xlsx_worker
            if worker is not None and worker.is_alive():
                self._xlsx_queue.put(_STOP)

        if worker is not None and worker.is_alive():
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning("Logbook XLSX worker did not stop within %.1fs", timeout)

    def _ensure_xlsx_worker_unlocked(self) -> None:

        if self._xlsx_worker is not None and self._xlsx_worker.is_alive():
            return

        self._stop_requested = False
        self._xlsx_worker = Thread(
            target=self._xlsx_worker_loop,
            name="LogbookXlsxWorker",
            daemon=True,
        )
        self._xlsx_worker.start()

    def _xlsx_worker_loop(self) -> None:

        while True:
            try:
                item = self._xlsx_queue.get(timeout=0.5)
            except Empty:
                if self._stop_requested:
                    return
                continue

            try:
                if item is _STOP:
                    return

                ship_dir = Path(item)
                key = str(ship_dir.resolve())

                with self._xlsx_worker_lock:
                    self._xlsx_pending.discard(key)

                try:
                    with self._lock:
                        regenerate_xlsx(ship_dir)
                except Exception:
                    logger.exception(
                        "Background XLSX regeneration failed for %s",
                        ship_dir,
                    )
            finally:
                self._xlsx_queue.task_done()

    def import_legacy(self, source_dir: Path) -> LegacyImportResult:

        source = Path(source_dir)

        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(f"Legacy logbook folder not found: {source}")

        imported = 0
        skipped = 0

        with self._lock:
            self._base_dir.mkdir(parents=True, exist_ok=True)

            for child in sorted(source.iterdir()):
                if not child.is_dir():
                    continue

                destination = self._base_dir / child.name

                if destination.exists():
                    skipped += 1
                    continue

                shutil.copytree(child, destination)
                imported += 1

                csv_file = destination / CSV_FILENAME

                if csv_file.exists():
                    try:
                        regenerate_xlsx(destination)
                    except Exception:
                        logger.exception(
                            "Legacy import XLSX failed for %s",
                            destination,
                        )

        return LegacyImportResult(
            imported_folders=imported,
            skipped_folders=skipped,
        )

    def open_logbook(self, mmsi: int) -> bool:

        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        ship_dir = self.resolve_ship_dir_by_mmsi(mmsi)

        if ship_dir is None:
            return False

        xlsx_file = self.ensure_xlsx(ship_dir)

        if xlsx_file is None or not xlsx_file.exists():
            return False

        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(xlsx_file.resolve())))


logbook_manager = LogbookManager()
