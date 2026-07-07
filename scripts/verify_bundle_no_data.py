#!/usr/bin/env python3
# ============================================================================
# Project X — Verify PyInstaller bundle does not ship a data/ directory
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DATA_DIR = ROOT / "dist" / "projectx" / "data"


def main() -> int:
    if not BUNDLE_DATA_DIR.exists():
        print("Bundle check passed: dist/projectx/data/ is absent.")
        return 0

    print(
        "ERROR: dist/projectx/data/ must not exist in release bundles.",
        file=sys.stderr,
    )
    print(
        "Runtime data is created in the user data directory at first launch.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
