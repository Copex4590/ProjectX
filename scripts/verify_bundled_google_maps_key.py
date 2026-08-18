#!/usr/bin/env python3
"""Verify a PyInstaller/AppImage/deb bundle contains a Google Maps key file.

Never prints the key. Checks presence, length, and AIza prefix only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle_root",
        type=Path,
        help="Path to dist/projectx or AppDir usr/… root containing resources/",
    )
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail when the bundled key file is missing/empty",
    )
    args = parser.parse_args()

    path = args.bundle_root / "resources" / "map" / "google_maps_api_key.bundled"
    if not path.is_file():
        msg = f"bundled Google Maps key missing: {path}"
        if args.required:
            print(f"[FAIL] {msg}", file=sys.stderr)
            return 1
        print(f"[WARN] {msg}")
        return 0

    key = path.read_text(encoding="utf-8").strip()
    if not key:
        msg = f"bundled Google Maps key empty: {path}"
        if args.required:
            print(f"[FAIL] {msg}", file=sys.stderr)
            return 1
        print(f"[WARN] {msg}")
        return 0

    if not key.startswith("AIza") or len(key) < 20:
        print("[FAIL] bundled Google Maps key failed basic shape check", file=sys.stderr)
        return 1

    print(f"[OK] Bundled Google Maps API key present (len={len(key)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
