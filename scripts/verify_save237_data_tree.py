#!/usr/bin/env python3
# SAVE-237 — data/ release gate allows repo ship DB, blocks runtime artifacts
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_data_tree_clean import find_violations, is_runtime_artifact  # noqa: E402


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "Hajók" / "MONZA").mkdir(parents=True)
        (data / "Hajók" / ".gitkeep").write_text("")
        (data / "Hajók" / "MONZA" / "adatlap.csv").write_text("mmsi,1\n")
        (data / "vessel_photos").mkdir()
        (data / "vessel_photos" / ".gitkeep").write_text("")
        (data / "vessel_photos" / "readme.txt").write_text("ok")

        # Allowed assets must not be violations
        for path in (
            data / "Hajók" / "MONZA" / "adatlap.csv",
            data / "Hajók" / ".gitkeep",
            data / "vessel_photos" / "readme.txt",
            data / "vessel_photos" / ".gitkeep",
        ):
            if is_runtime_artifact(path, data_dir=data):
                failures.append(f"false positive: {path.relative_to(data)}")

        clean = find_violations(data)
        if clean:
            failures.append(f"clean tree reported violations: {clean}")

        # Runtime artifacts must fail
        blocked = [
            data / "alerts.db",
            data / "timeline.db",
            data / "timeline.db-wal",
            data / "vessels.db-shm",
            data / "vessel_photos" / "photos.db",
            data / "hybrid" / "ship_cache.json",
            data / "logs" / "app.log",
            data / "cache" / "x.bin",
            data / "Hajók" / "__pycache__" / "x.pyc",
            data / "stray.tmp",
            data / "vessel_db_sync_state.json",
        ]
        (data / "hybrid").mkdir()
        (data / "logs").mkdir()
        (data / "cache").mkdir()
        (data / "Hajók" / "__pycache__").mkdir()
        for path in blocked:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("x")

        dirty = {p.relative_to(data).as_posix() for p in find_violations(data)}
        expected_markers = (
            "alerts.db",
            "timeline.db",
            "timeline.db-wal",
            "vessels.db-shm",
            "vessel_photos/photos.db",
            "hybrid",
            "logs",
            "cache",
            "Hajók/__pycache__",
            "stray.tmp",
            "vessel_db_sync_state.json",
        )
        for marker in expected_markers:
            if not any(marker == item or item.startswith(marker + "/") for item in dirty):
                failures.append(f"missing violation for {marker}; got {sorted(dirty)}")

        # Ship CSV still allowed alongside dirt
        if is_runtime_artifact(data / "Hajók" / "MONZA" / "adatlap.csv", data_dir=data):
            failures.append("ship CSV incorrectly blocked when runtime dirt present")

    if failures:
        print("SAVE-237 FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("SAVE-237 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
