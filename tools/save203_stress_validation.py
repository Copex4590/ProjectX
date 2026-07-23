#!/usr/bin/env python3
"""SAVE-203 sustained AIS stress harness (headless).

Measures CPU/RSS, active vessels, synthetic EventBus latency under load.

Usage:
  PYTHONPATH=src .venv/bin/python tools/save203_stress_validation.py [--seconds 30]
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--vessels", type=int, default=400)
    parser.add_argument("--updates_per_sec", type=float, default=400.0)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "docs" / "reports" / "save203_stress_validation.json",
    )
    args = parser.parse_args()

    td = Path(tempfile.mkdtemp(prefix="save203_stress_"))
    os.environ["PROJECTX_VESSEL_DATABASE_FILE"] = str(td / "vessels.db")
    os.environ["PROJECTX_TIMELINE_DATABASE_FILE"] = str(td / "timeline.db")

    from database.ship_registry import ShipRegistry
    from database.vessel_database import VesselDatabase
    from database.vessel_sync import VesselSync
    from events import eventbus
    from models.ship import Ship
    from timeline.timeline_manager import TimelineManager
    from timeline.timeline_recorder import TimelineRecorder
    from timeline.timeline_registry import TimelineRegistry

    vessel_db = VesselDatabase(td / "vessels.db")
    timeline_db = TimelineRegistry(td / "timeline.db")
    registry = ShipRegistry()
    vessel_sync = VesselSync(vessel_db)
    timeline_rec = TimelineRecorder(TimelineManager(timeline_db))

    latencies_ms: list[float] = []
    lock = threading.Lock()

    def on_ship(_ship):
        # latency measured at publish site below
        pass

    eventbus.subscribe("ship.updated", on_ship)

    stop_at = time.monotonic() + args.seconds
    interval = 1.0 / max(args.updates_per_sec, 1.0)
    n = 0
    started = time.monotonic()
    cpu_samples: list[float] = []
    rss_samples: list[float] = []
    vessel_samples: list[int] = []

    process_start = time.process_time()
    wall_start = time.monotonic()

    while time.monotonic() < stop_at:
        mmsi = 300000000 + (n % args.vessels)
        ship = Ship(
            mmsi=mmsi,
            name=f"V{mmsi}",
            callsign="TST",
            ship_type="tanker",
            lat=47.4 + (n % 100) * 0.0005,
            lon=19.1 + (n % 100) * 0.0005,
            speed=8.0,
            course=float(n % 360),
            heading=float(n % 360),
            destination="BUD",
            eta="",
            source="AIS",
            last_seen=datetime.now(),
            ais_visible=True,
            rtl_visible=False,
        )
        with registry._lock:
            registry._ships[mmsi] = ship
        t0 = time.perf_counter()
        eventbus.publish("ship.updated", ship)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        with lock:
            latencies_ms.append(dt_ms)
        vessel_sync.enqueue(ship)
        timeline_rec.enqueue(ship)
        n += 1
        if n % 50 == 0:
            wall = time.monotonic() - wall_start
            cpu = time.process_time() - process_start
            cpu_pct = (cpu / wall) * 100.0 if wall > 0 else 0.0
            cpu_samples.append(cpu_pct)
            rss_samples.append(_rss_mb())
            vessel_samples.append(registry.count())
        time.sleep(interval)

    time.sleep(1.0)
    vessel_sync.stop()
    timeline_rec.stop()

    def pct(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
        return ordered[idx]

    report = {
        "duration_s": args.seconds,
        "target_vessels": args.vessels,
        "updates_per_sec": args.updates_per_sec,
        "updates_sent": n,
        "active_vessels_final": registry.count(),
        "active_vessels_max": max(vessel_samples, default=0),
        "cpu_pct_avg": round(statistics.mean(cpu_samples), 2) if cpu_samples else None,
        "cpu_pct_max": round(max(cpu_samples), 2) if cpu_samples else None,
        "rss_mb_start": round(rss_samples[0], 2) if rss_samples else None,
        "rss_mb_end": round(rss_samples[-1], 2) if rss_samples else None,
        "rss_mb_max": round(max(rss_samples), 2) if rss_samples else None,
        "eventbus_latency_ms": {
            "p50": round(pct(latencies_ms, 50), 3),
            "p95": round(pct(latencies_ms, 95), 3),
            "p99": round(pct(latencies_ms, 99), 3),
            "max": round(max(latencies_ms), 3) if latencies_ms else None,
        },
        "gui_responsiveness_note": (
            "Headless harness — GUI responsiveness verified manually via "
            "map incremental patch mode (see release_readiness_v3.md)."
        ),
        "vessel_db_count": vessel_db.count(),
        "timeline_count": timeline_db.count(),
    }
    report["verdict"] = (
        "PASS"
        if (
            report["eventbus_latency_ms"]["p95"] is not None
            and report["eventbus_latency_ms"]["p95"] < 5.0
            and (report["rss_mb_end"] or 0) - (report["rss_mb_start"] or 0) < 250
        )
        else "FAIL"
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {args.report}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
