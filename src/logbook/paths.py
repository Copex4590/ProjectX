# ============================================================================
# Project X
# Logbook Paths
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from storage import active_data_path
from storage.layout import DATA_SUBDIR_HAJOK

CSV_FILENAME = "adatlap.csv"
XLSX_FILENAME = "adatlap.xlsx"
PHOTOS_DIRNAME = "photos"
NOTES_FILENAME = "notes.txt"

CSV_HEADER = (
    "Időpont;"
    "Távolság;"
    "Haladási irány;"
    "Sebesség;"
    "Célállomás + ETA;"
    "Hívójel;"
    "Merülés;"
    "MMSI;"
    "Hajótípus;"
    "Hossz;"
    "Szélesség\n"
)


def logbook_dir() -> Path:
    """Return the active logbook root directory (Hajók)."""

    override = os.environ.get("PROJECTX_LOGBOOK_DIR", "").strip()

    if override:
        return Path(override).expanduser().resolve()

    return active_data_path(DATA_SUBDIR_HAJOK)
