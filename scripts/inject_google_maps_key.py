#!/usr/bin/env python3
"""Inject Google Maps API key into a gitignored bundled resource (build-time).

Reads (first non-empty wins):
  PROJECTX_GOOGLE_MAPS_API_KEY
  PROJECTX_GOOGLE_MAPS_DEMO_KEY

Writes:
  src/resources/map/google_maps_api_key.bundled

Never prints the key value. Exit codes:
  0  injected (or already present with --allow-missing skipped)
  2  missing key when required
  3  invalid key shape
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "resources" / "map" / "google_maps_api_key.bundled"
ENV_NAMES = (
    "PROJECTX_GOOGLE_MAPS_API_KEY",
    "PROJECTX_GOOGLE_MAPS_DEMO_KEY",
)


def _read_key() -> str:
    for name in ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--required",
        action="store_true",
        help="Fail if no key is available in the environment",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit 0 without writing when no key is set (dev builds)",
    )
    args = parser.parse_args()

    key = _read_key()
    if not key:
        if args.required and not args.allow_missing:
            print(
                "[FAIL] Google Maps API key missing. Set "
                "PROJECTX_GOOGLE_MAPS_API_KEY for release builds.",
                file=sys.stderr,
            )
            return 2
        if OUT.is_file():
            # Keep a previously injected file for local iteration.
            length = len(OUT.read_text(encoding="utf-8").strip())
            print(f"[OK] Using existing bundled key file (len={length})")
            return 0
        print("[SKIP] No Google Maps API key in env; bundled file not written")
        return 0

    if not key.startswith("AIza") or len(key) < 20:
        print("[FAIL] Google Maps API key failed basic shape check", file=sys.stderr)
        return 3

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(key + "\n", encoding="utf-8")
    # Restrictive perms when the OS supports it (no-op on Windows).
    try:
        os.chmod(OUT, 0o600)
    except OSError:
        pass
    print(f"[OK] Injected bundled Google Maps API key (len={len(key)}) → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
