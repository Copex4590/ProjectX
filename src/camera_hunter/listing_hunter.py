"""Standalone Camera Hunter listing scanner entrypoint (no Project X GUI)."""

from __future__ import annotations

from camera_hunter.app.listing_hunter import main

if __name__ == "__main__":
    raise SystemExit(main())
