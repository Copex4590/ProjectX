"""Temporary VALIDATED-camera preview entrypoint (not the catalog validator)."""

from __future__ import annotations

from camera_hunter.app.validated_preview import main

if __name__ == "__main__":
    raise SystemExit(main())
