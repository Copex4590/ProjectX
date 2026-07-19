# ============================================================================
# Project X
# Logbook Manager
# ============================================================================

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from logbook.duna_format import build_csv_row, sanitize_name
from logbook.paths import (
    CSV_FILENAME,
    CSV_HEADER,
    NOTES_FILENAME,
    PHOTOS_DIRNAME,
    XLSX_FILENAME,
    logbook_dir,
)
from logbook.xlsx_generator import regenerate_xlsx


@dataclass(frozen=True)
class LegacyImportResult:

    imported_folders: int = 0
    skipped_folders: int = 0


class LogbookManager:

    def __init__(self, base_dir: Path | None = None):

        self._base_dir = Path(base_dir or logbook_dir())
        self._lock = Lock()
        self._base_dir.mkdir(parents=True, exist_ok=True)

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

        return self.xlsx_path(ship) is not None

    def has_logbook_for_mmsi(self, mmsi: int) -> bool:

        return self.xlsx_path_for_mmsi(mmsi) is not None

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

        ship_dir = self.ensure_ship_folder(ship)
        csv_file = ship_dir / CSV_FILENAME
        row = build_csv_row(ship)

        with self._lock:
            with csv_file.open("a", encoding="utf-8") as handle:
                handle.write(row)

            return regenerate_xlsx(ship_dir)

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
                    regenerate_xlsx(destination)

        return LegacyImportResult(
            imported_folders=imported,
            skipped_folders=skipped,
        )

    def open_logbook(self, mmsi: int) -> bool:

        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        xlsx_file = self.xlsx_path_for_mmsi(mmsi)

        if xlsx_file is None:
            return False

        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(xlsx_file.resolve())))


logbook_manager = LogbookManager()
