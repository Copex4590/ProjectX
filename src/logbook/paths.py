# ============================================================================
# Project X
# Logbook Paths
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from app.paths import runtime_data_dir

DEFAULT_HAJOK_DIR = runtime_data_dir() / "Hajók"

HAJOK_DIR = Path(
    os.environ.get(
        "PROJECTX_LOGBOOK_DIR",
        str(DEFAULT_HAJOK_DIR),
    )
)

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
