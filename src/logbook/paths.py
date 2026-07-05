# ============================================================================
# Project X
# Logbook Paths
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_HAJOK_DIR = _PROJECT_ROOT / "data" / "Hajók"

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
