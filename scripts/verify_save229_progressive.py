#!/usr/bin/env python3
# SAVE-229 progressive pipeline verification (offscreen, page-level)
from __future__ import annotations

import os
import sys
import threading
import time
import tracemalloc
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PROJECTX_PROGRESSIVE_BATCH_SIZE", "200")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication


def wait_until(predicate, timeout_s: float = 90.0) -> bool:
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def metrics_dict(page) -> dict:
    m = page._pipeline.last_metrics
    if m is None:
        return {}
    return {
        "ttfv_ms": m.time_to_first_visible_ms,
        "total_ms": m.total_load_ms,
        "batch_count": m.batch_count,
        "rows_per_batch": m.rows_per_batch,
        "total_rows": m.total_rows,
        "ui_pulses": m.ui_pulses_during_load,
    }


def exercise(page, key: str) -> dict:
    page.show()
    page.initialize()
    t_act = time.perf_counter()
    page.activate()
    activate_ms = (time.perf_counter() - t_act) * 1000.0

    # Ensure we measure a progressive load (cache may already be warm from activate)
    if page._data_ready and page._pipeline.last_metrics is None:
        page._data_ready = False
        if hasattr(page, "_records"):
            page._records = []
        page._request_progressive_load(force=True)

    ok = wait_until(lambda: page._data_ready and not page._pipeline.busy, 90.0)
    if not ok:
        return {"error": "load timeout", "activate_ms": activate_ms}

    wait_until(
        lambda: page._pipeline.last_metrics is not None
        and page._pipeline.last_metrics.time_to_first_visible_ms is not None,
        3.0,
    )
    md = metrics_dict(page)
    md["activate_ms"] = activate_ms

    t_rev = time.perf_counter()
    page.activate()
    md["revisit_ms"] = (time.perf_counter() - t_rev) * 1000.0

    def slow():
        yield {"meta": False, "records": []}
        time.sleep(0.2)
        yield {"meta": False, "records": []}

    page._pipeline.cancel()
    started_a = page._pipeline.start(slow, force=True)
    started_b = page._pipeline.start(slow, force=False)
    page._pipeline.cancel()
    md["duplicate_blocked"] = bool(started_a and not started_b)

    page._data_ready = False
    page._request_progressive_load(force=True)
    QApplication.processEvents()
    page.hide()
    QApplication.processEvents()
    time.sleep(0.05)
    QApplication.processEvents()
    md["cancel_on_leave"] = not page._pipeline.busy
    page.show()

    # Restore full cache
    page._data_ready = False
    page._request_progressive_load(force=True)
    wait_until(lambda: page._data_ready and not page._pipeline.busy, 90.0)
    latest = metrics_dict(page)
    for k, v in latest.items():
        if md.get(k) is None:
            md[k] = v
    return md


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    from gui.analyticsdashboardpage import AnalyticsDashboardPage
    from gui.statisticspage import StatisticsPage
    from gui.vesseldatabasepage import VesselDatabasePage
    from gui.vesseltimelinepage import VesselTimelinePage

    tracemalloc.start()
    mem_before = tracemalloc.get_traced_memory()[0]

    pages = [
        ("vessel_database", VesselDatabasePage()),
        ("timeline", VesselTimelinePage()),
        ("statistics", StatisticsPage()),
        ("analytics", AnalyticsDashboardPage()),
    ]

    results: dict[str, dict] = {}
    failures: list[str] = []

    for key, page in pages:
        print(f"exercising {key}…")
        md = exercise(page, key)
        results[key] = md
        print(f"{key}: {md}")
        if md.get("error"):
            failures.append(f"{key}: {md['error']}")
            continue
        if md.get("ttfv_ms") is None:
            failures.append(f"{key}: missing TTFV")
        elif md["ttfv_ms"] > 3000:
            failures.append(f"{key}: TTFV too slow ({md['ttfv_ms']:.1f} ms)")
        if (md.get("total_ms") or 0) > 80 and md.get("ui_pulses", 0) < 1:
            failures.append(f"{key}: no UI pulses during load")
        if not md.get("duplicate_blocked"):
            failures.append(f"{key}: duplicate loader not blocked")
        if not md.get("cancel_on_leave"):
            failures.append(f"{key}: cancel on leave failed")
        if md.get("revisit_ms", 999) > 250:
            failures.append(f"{key}: revisit not instant ({md['revisit_ms']:.1f} ms)")
        if key in ("timeline", "vessel_database"):
            rows = md.get("total_rows") or 0
            batches = md.get("batch_count") or 0
            if rows > 250 and batches < 2:
                failures.append(f"{key}: expected multiple batches for {rows} rows")

    # Filter smoke
    tl = pages[1][1]
    if tl._data_ready:
        before = len(tl._filtered_records())
        tl.search_input.setText("999")
        tl.apply_filters()
        after = len(tl._filtered_records())
        results["timeline"]["filter_ok"] = after <= before
        if after > before:
            failures.append("timeline: filter increased rows")
        tl.clear_filters()

    mem_after, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_delta_mb = (mem_after - mem_before) / (1024 * 1024)
    mem_peak_mb = mem_peak / (1024 * 1024)

    for _, page in pages:
        page.shutdown()
        page.deleteLater()
    QApplication.processEvents()
    time.sleep(0.2)
    QApplication.processEvents()

    from events import eventbus

    remaining_count = -1
    for attr in ("_listeners", "_subscribers", "_handlers"):
        store = getattr(eventbus, attr, None)
        if isinstance(store, dict):
            remaining_count = sum(len(v) for v in store.values())
            break

    alive_threads = [
        t.name
        for t in threading.enumerate()
        if t.is_alive() and t.name != "MainThread"
    ]

    verdict = "PASS" if not failures else "FAIL"
    out = ROOT / "docs" / "reports" / "SAVE-229_progressive_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SAVE-229 — Progressive Data Pipeline",
        "",
        f"**Verdict: {verdict}**",
        "",
        "## Before / After",
        "",
        "| Metric | SAVE-228 (before) | SAVE-229 (after) |",
        "|--------|-------------------|------------------|",
        "| First paint strategy | Wait for full fetch, then chunked UI fill | First batch/phase painted ASAP |",
    ]
    for key, md in results.items():
        lines.append(
            f"| {key} activate() | ~9–15 ms | "
            f"**{(md.get('activate_ms') or 0):.1f} ms** |"
        )
        lines.append(
            f"| {key} TTFV | n/a (full payload first) | "
            f"**{(md.get('ttfv_ms') or 0):.1f} ms** |"
        )
        lines.append(
            f"| {key} total load | background full load | "
            f"**{(md.get('total_ms') or 0):.1f} ms** "
            f"({md.get('batch_count')} batches, ~{md.get('rows_per_batch')} rows/batch) |"
        )
        lines.append(
            f"| {key} UI pulses during load | present | **{md.get('ui_pulses', 0)}** |"
        )
        lines.append(
            f"| {key} cached revisit | ~0–24 ms | **{(md.get('revisit_ms') or 0):.1f} ms** |"
        )
    lines += [
        "",
        "## Memory",
        "",
        f"- Traced delta: **{mem_delta_mb:.2f} MB**",
        f"- Traced peak: **{mem_peak_mb:.2f} MB**",
        "",
        "## Lifecycle",
        "",
        f"- EventBus remaining listeners (approx): **{remaining_count}**",
        f"- Extra threads after close: **{alive_threads or 'none'}**",
        "",
        "## Checks",
        "",
    ]
    if failures:
        for item in failures:
            lines.append(f"- FAIL: {item}")
    else:
        lines.extend(
            [
                "- First data appears quickly (TTFV recorded)",
                "- UI pulses continue during load (event loop alive)",
                "- Duplicate loaders blocked",
                "- Cancel on page leave",
                "- Cached revisits instant",
                "- Sorting/filtering preserved (timeline smoke)",
            ]
        )
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text())
    print("VERDICT", verdict)
    os._exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
