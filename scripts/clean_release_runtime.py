#!/usr/bin/env python3
# ============================================================================
# Project X — Remove developer runtime artifacts before release build (SAVE-238)
# ============================================================================
"""Delete ONLY runtime-generated files/dirs under the repo.

Never removes repository-managed assets under ``data/Hajók/**`` (except
``__pycache__`` nested there). Never removes vessel photo assets other than
``photos.db``.

Safe if targets are missing. Prints every removed path.
After this script, ``verify_data_tree_clean.py`` is expected to PASS.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# Skip these trees when sweeping __pycache__ outside data/.
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        ".venv-win",
        "venv",
        "build",
        "dist",
        ".cache",
        "node_modules",
    }
)


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_protected_hajok_asset(path: Path) -> bool:
    """True for ship-database content that must never be deleted."""

    hajok = DATA_DIR / "Hajók"
    if not hajok.is_dir() or not _is_under(path, hajok):
        return False
    if "__pycache__" in path.parts:
        return False
    return True


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _collect_targets() -> tuple[list[Path], list[Path]]:
    """Return (files, directories) to remove."""

    files: list[Path] = []
    directories: list[Path] = []

    if DATA_DIR.is_dir():
        for path in (
            DATA_DIR / "alerts.db",
            DATA_DIR / "vessel_db_sync_state.json",
            DATA_DIR / "plugins_state.json",
            DATA_DIR / "obs_freeze.trace",
            DATA_DIR / "vessel_photos" / "photos.db",
        ):
            if path.is_file():
                files.append(path)

        for pattern in ("timeline.db*", "vessels.db*"):
            for path in DATA_DIR.glob(pattern):
                if path.is_file():
                    files.append(path)

        for dirname in ("hybrid", "logs", "cache"):
            path = DATA_DIR / dirname
            if path.is_dir():
                directories.append(path)

        for path in DATA_DIR.rglob("*"):
            if not path.is_file():
                continue
            if _is_protected_hajok_asset(path):
                continue
            name = path.name.lower()
            if (
                name.endswith(".wal")
                or name.endswith(".shm")
                or name.endswith(".db-wal")
                or name.endswith(".db-shm")
            ):
                files.append(path)

    for path in ROOT.rglob("__pycache__"):
        if not path.is_dir():
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        directories.append(path)

    # De-dupe
    file_map = {p.resolve(): p for p in files}
    dir_map = {p.resolve(): p for p in directories}

    # Drop files already covered by a directory we will rmtree.
    pruned_files: list[Path] = []
    for path in file_map.values():
        if any(_is_under(path, directory) for directory in dir_map.values()):
            continue
        if _is_protected_hajok_asset(path):
            continue
        pruned_files.append(path)

    pruned_dirs = [
        path
        for path in dir_map.values()
        if not _is_protected_hajok_asset(path)
    ]

    # Prefer parent __pycache__/hybrid removal over nested duplicates.
    pruned_dirs.sort(key=lambda p: len(p.parts))
    final_dirs: list[Path] = []
    for path in pruned_dirs:
        if any(_is_under(path, kept) and path != kept for kept in final_dirs):
            continue
        final_dirs.append(path)

    pruned_files.sort(key=lambda p: str(p))
    final_dirs.sort(key=lambda p: (-len(p.parts), str(p)))
    return pruned_files, final_dirs


def main() -> int:
    print("Cleaning release runtime artifacts...")
    removed = 0

    files, directories = _collect_targets()

    for path in files + directories:
        if not path.exists():
            continue
        if _is_protected_hajok_asset(path):
            print(f"  [skip protected] {_display(path)}")
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as error:
            print(f"  [FAIL] {_display(path)}: {error}", file=sys.stderr)
            return 1
        print(f"  removed {_display(path)}")
        removed += 1

    if removed == 0:
        print("  (nothing to remove)")
    else:
        print(f"Removed {removed} runtime path(s).")

    print("Runtime cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
