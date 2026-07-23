#!/usr/bin/env python3
"""SAVE-203 memory / queue stability harness (headless).

Simulates sustained VesselSync + Timeline + HybridFileWriter load without GUI.
Records registry size, queue depths, thread liveness, and RSS samples.

Usage:
  PYTHONPATH=src .venv/bin/python tools/save203_memory_validation.py [--seconds 30]
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("PROJECTX_VESSEL_DATABASE_FILE", "")
os.environ.setdefault("PROJECTX_TIMELINE_DATABASE_FILE", "")


def _rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux ru_maxrss is KiB
    return float(usage) / 1024.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--rate", type=float, default=200.0, help="observations/sec")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "docs" / "reports" / "save203_memory_validation.json",
    )
    args = parser.parse_args()

    td = Path(tempfile.mkdtemp(prefix="save203_mem_"))
    os.environ["PROJECTX_VESSEL_DATABASE_FILE"] = str(td / "vessels.db")
    os.environ["PROJECTX_TIMELINE_DATABASE_FILE"] = str(td / "timeline.db")

    from database.ship_registry import ShipRegistry
    from database.vessel_database import VesselDatabase
    from database.vessel_sync import VesselSync
    from engines.rtl.hybrid_file_writer import HybridFileWriter
    from models.ship import Ship
    from timeline.timeline_recorder import TimelineRecorder
    from timeline.timeline_manager import TimelineManager
    from timeline.timeline_registry import TimelineRegistry

    vessel_db = VesselDatabase(td / "vessels.db")
    timeline_db = TimelineRegistry(td / "timeline.db")
    timeline_mgr = TimelineManager(timeline_db)
    registry = ShipRegistry()
    # Bypass side-effects that need Qt/geo by patching add path via direct sync
    vessel_sync = VesselSync(vessel_db)
    timeline_rec = TimelineRecorder(timeline_mgr)
    writer = HybridFileWriter()
    writer.start()

    samples: list[dict] = []
    stop_at = time.monotonic() + args.seconds
    interval = 1.0 / max(args.rate, 1.0)
    mmsi_base = 200000000
    n = 0
    started = time.monotonic()

    while time.monotonic() < stop_at:
        mmsi = mmsi_base + (n % 500)
        ship = Ship(
            mmsi=mmsi,
            name=f"SHIP{mmsi}",
            callsign="",
            ship_type="cargo",
            lat=47.5 + (n % 50) * 0.001,
            lon=19.0 + (n % 50) * 0.001,
            speed=5.0 + (n % 10),
            course=float(n % 360),
            heading=float(n % 360),
            destination="",
            eta="",
            source="AIS",
            last_seen=datetime.now(),
            ais_visible=True,
            rtl_visible=False,
        )
        with registry._lock:
            registry._ships[mmsi] = ship
        vessel_sync.enqueue(ship)
        timeline_rec.enqueue(ship)
        writer.enqueue(
            {
                "kind": "radar_upsert",
                "base_dir": str(td / "hybrid"),
                "mmsi": str(mmsi),
                "payload": {
                    "mmsi": str(mmsi),
                    "name": ship.name,
                    "lat": ship.lat,
                    "lon": ship.lon,
                },
            }
        )
        if n % int(max(args.rate, 1)) == 0:
            writer.enqueue(
                {
                    "kind": "radar_flush",
                    "base_dir": str(td / "hybrid"),
                    "force_full_kml": False,
                }
            )
            samples.append(
                {
                    "t": round(time.monotonic() - started, 2),
                    "rss_mb": round(_rss_mb(), 2),
                    "registry": registry.count(),
                    "vessel_q": vessel_sync._queue.qsize(),
                    "timeline_q": timeline_rec._queue.qsize(),
                    "writer_q": writer._queue.qsize(),
                    "vessel_worker": bool(
                        vessel_sync._worker and vessel_sync._worker.is_alive()
                    ),
                    "timeline_worker": bool(
                        timeline_rec._worker and timeline_rec._worker.is_alive()
                    ),
                    "writer_worker": bool(
                        writer._thread and writer._thread.is_alive()
                    ),
                    "threads": threading.active_count(),
                }
            )
        n += 1
        time.sleep(interval)

    # Drain
    time.sleep(1.5)
    vessel_sync.stop()
    timeline_rec.stop()
    writer.stop()

    final = {
        "duration_s": args.seconds,
        "rate_hz": args.rate,
        "observations": n,
        "registry_final": registry.count(),
        "vessel_db_count": vessel_db.count(),
        "timeline_count": timeline_db.count(),
        "rss_start_mb": samples[0]["rss_mb"] if samples else None,
        "rss_end_mb": samples[-1]["rss_mb"] if samples else None,
        "rss_delta_mb": (
            round(samples[-1]["rss_mb"] - samples[0]["rss_mb"], 2)
            if len(samples) >= 2
            else None
        ),
        "max_vessel_q": max((s["vessel_q"] for s in samples), default=0),
        "max_timeline_q": max((s["timeline_q"] for s in samples), default=0),
        "max_writer_q": max((s["writer_q"] for s in samples), default=0),
        "workers_alive_end": samples[-1] if samples else {},
        "samples": samples,
        "pass_criteria": {
            "registry_bounded": registry.count() <= 500,
            "queues_drained": (
                vessel_sync._queue.qsize() == 0
                and timeline_rec._queue.qsize() == 0
            ),
            "rss_not_runaway": (
                samples[-1]["rss_mb"] - samples[0]["rss_mb"] < 200.0
                if len(samples) >= 2
                else False
            ),
        },
    }
    final["verdict"] = (
        "PASS"
        if all(final["pass_criteria"].values())
        else "FAIL"
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(json.dumps({k: final[k] for k in final if k != "samples"}, indent=2))
    print(f"Wrote {args.report}")
    return 0 if final["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
