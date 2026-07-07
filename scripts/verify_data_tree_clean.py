#!/usr/bin/env python3
# ============================================================================
# Project X — Verify repo data/ contains no developer runtime artifacts
# ============================================================================

from __future__ import annotations

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


def find_violations(data_dir: Path = DATA_DIR) -> list[Path]:
    violations: list[Path] = []

    if not data_dir.is_dir():
        return violations

    for path in sorted(data_dir.rglob("*")):
        if path.is_dir():
            if path not in ALLOWED_DIRS:
                violations.append(path)
            continue

        if path not in ALLOWED_FILES:
            violations.append(path)

    return violations


def main() -> int:
    violations = find_violations()

    if not violations:
        print("data/ tree is clean (structure placeholders only).")
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
        "Allowed contents: data/Hajók/.gitkeep, data/vessel_photos/.gitkeep",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
