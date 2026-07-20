#!/usr/bin/env python3
# ============================================================================
# Project X — Reset repo data/ to release placeholder structure
# ============================================================================

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

ALLOWED_FILES = {
    DATA_DIR / "Hajók" / ".gitkeep",
    DATA_DIR / "vessel_photos" / ".gitkeep",
}

ALLOWED_DIRS = {
    DATA_DIR,
    DATA_DIR / "Hajók",
    DATA_DIR / "vessel_photos",
}


def _allowed_paths(data_dir: Path) -> tuple[set[Path], set[Path]]:
    allowed_dirs = {
        data_dir,
        data_dir / "Hajók",
        data_dir / "vessel_photos",
    }
    allowed_files = {
        data_dir / "Hajók" / ".gitkeep",
        data_dir / "vessel_photos" / ".gitkeep",
    }
    return allowed_dirs, allowed_files


def clean_data_tree(data_dir: Path = DATA_DIR) -> list[Path]:
    """Remove developer runtime artifacts under data/, keeping placeholders only."""

    removed: list[Path] = []
    allowed_dirs, allowed_files = _allowed_paths(data_dir)

    if not data_dir.is_dir():
        return removed

    for path in sorted(data_dir.rglob("*"), reverse=True):
        if path.is_dir():
            if path not in allowed_dirs:
                shutil.rmtree(path)
                removed.append(path)
            continue

        if path not in allowed_files:
            path.unlink(missing_ok=True)
            removed.append(path)

    for directory in (data_dir / "Hajók", data_dir / "vessel_photos"):
        directory.mkdir(parents=True, exist_ok=True)

    for gitkeep in allowed_files:
        gitkeep.parent.mkdir(parents=True, exist_ok=True)
        if not gitkeep.is_file():
            gitkeep.write_text("", encoding="utf-8")
            removed.append(gitkeep)

    return removed


def main() -> int:
    removed = clean_data_tree()

    if removed:
        print(f"Cleaned {len(removed)} path(s) under data/.")
    else:
        print("data/ tree was already clean.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
