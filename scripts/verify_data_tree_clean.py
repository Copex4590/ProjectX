#!/usr/bin/env python3
# ============================================================================
# Project X — Verify repo data/ contains no developer runtime artifacts (SAVE-237)
# ============================================================================
"""Release gate for the repository ``data/`` tree.

Allowed (repository-managed assets):
  - data/Hajók/**          ship database / logbook assets
  - data/vessel_photos/**  photo assets (except runtime DBs)
  - any ``.gitkeep`` under data/

Blocked (runtime / temporary — must not ship or block clean builds):
  - alerts.db, timeline.db*, vessels.db*, photos.db
  - hybrid/**, logs/**, cache/**, __pycache__/**
  - *.wal, *.shm, *.db-wal, *.db-shm, *.db
  - other runtime state files and common temp junk at data/ root
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# Top-level asset trees that may contain version-controlled content.
_ASSET_ROOTS = frozenset({"Hajók", "vessel_photos"})

# Directory names banned anywhere under data/.
_BLOCKED_DIR_NAMES = frozenset(
    {
        "hybrid",
        "logs",
        "cache",
        "__pycache__",
    }
)

# Exact file basenames banned anywhere under data/.
_BLOCKED_FILE_NAMES = frozenset(
    {
        "alerts.db",
        "photos.db",
        "vessel_db_sync_state.json",
        "plugins_state.json",
        "obs_freeze.trace",
    }
)

# Prefixes for SQLite primary + sidecar names (timeline.db, timeline.db-wal, …).
_BLOCKED_DB_PREFIXES = (
    "timeline.db",
    "vessels.db",
    "alerts.db",
    "photos.db",
)


def _relative_to_data(path: Path, data_dir: Path) -> Path:
    return path.relative_to(data_dir)


def _is_gitkeep(path: Path) -> bool:
    return path.name == ".gitkeep"


def _is_blocked_dirname(name: str) -> bool:
    return name in _BLOCKED_DIR_NAMES


def _is_runtime_database_name(name: str) -> bool:
    lowered = name.lower()
    if lowered.endswith(".db"):
        return True
    if lowered.endswith(".db-wal") or lowered.endswith(".db-shm"):
        return True
    if lowered.endswith(".wal") or lowered.endswith(".shm"):
        return True
    for prefix in _BLOCKED_DB_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "-"):
            return True
    return name in _BLOCKED_FILE_NAMES


def _is_temporary_name(name: str) -> bool:
    lowered = name.lower()
    if lowered.endswith((".tmp", ".temp", ".pyc", ".pyo", ".log", "~")):
        return True
    if name in {".DS_Store", "Thumbs.db"}:
        return True
    if name.startswith("~$"):
        return True
    return False


def is_runtime_artifact(path: Path, *, data_dir: Path = DATA_DIR) -> bool:
    """Return True if ``path`` under data/ must fail the release gate."""

    try:
        relative = _relative_to_data(path, data_dir)
    except ValueError:
        return True

    parts = relative.parts
    if not parts:
        return False

    if any(_is_blocked_dirname(part) for part in parts):
        return True

    if path.is_dir():
        return False

    name = path.name
    if _is_gitkeep(path):
        return False

    if _is_runtime_database_name(name) or _is_temporary_name(name):
        return True

    if name in _BLOCKED_FILE_NAMES:
        return True

    # Non-asset paths under data/ (e.g. stray files at data/ root) are runtime.
    top = parts[0]
    if top not in _ASSET_ROOTS:
        return True

    return False


def find_violations(data_dir: Path = DATA_DIR) -> list[Path]:
    violations: list[Path] = []

    if not data_dir.is_dir():
        return violations

    for path in sorted(data_dir.rglob("*")):
        if is_runtime_artifact(path, data_dir=data_dir):
            # Report blocked directories once (the dir itself), not every child,
            # when the dir name is the ban reason.
            if path.is_dir():
                relative = _relative_to_data(path, data_dir)
                if relative.name in _BLOCKED_DIR_NAMES or any(
                    part in _BLOCKED_DIR_NAMES for part in relative.parts[:-1]
                ):
                    # Skip children of already-blocked trees to keep output short.
                    if any(part in _BLOCKED_DIR_NAMES for part in relative.parts[:-1]):
                        continue
            elif any(
                part in _BLOCKED_DIR_NAMES
                for part in _relative_to_data(path, data_dir).parts[:-1]
            ):
                continue
            violations.append(path)

    return violations


def main() -> int:
    violations = find_violations()

    if not violations:
        print(
            "data/ tree is clean "
            "(repository ship/photo assets allowed; no runtime artifacts)."
        )
        return 0

    print(
        "ERROR: data/ contains developer runtime artifacts that must not ship:",
        file=sys.stderr,
    )
    for path in violations:
        print(f"  - {path.relative_to(ROOT)}", file=sys.stderr)

    print(
        "\nRemove runtime files before building a release package.",
        file=sys.stderr,
    )
    print(
        "Allowed: data/Hajók/**, data/vessel_photos/**, .gitkeep\n"
        "Blocked: alerts.db, timeline.db*, vessels.db*, photos.db, "
        "hybrid/**, logs/**, cache/**, __pycache__/**, *.wal, *.shm, "
        "and other runtime/temp files.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
