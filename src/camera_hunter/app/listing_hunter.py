"""Standalone listing-catalog Hunter CLI (no Project X GUI, no Qt, no HLS).

Starts the existing ListingCatalogScanner and prints ListingScanStatus.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from camera_hunter.engine.listing_scanner import (
    DEFAULT_REFRESH_INTERVAL_S,
    ListingCatalogScanner,
)
from camera_hunter.engine.listing_store import ListingCatalogStore, ListingScanStatus

STORE_FILENAME = "hunter_listing_catalog.json"


def listing_store_path() -> Path:
    """Same location as Project X ``listing_catalog_path()``, without Qt."""

    override = os.environ.get("PROJECTX_HUNTER_LISTING_CATALOG", "").strip()
    if override:
        return Path(override)
    try:
        from app.paths import runtime_data_dir

        cache = runtime_data_dir() / "cache"
    except ImportError:
        cache = Path(__file__).resolve().parents[3] / "data" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / STORE_FILENAME


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="listing-hunter",
        description=(
            "Standalone Camera Hunter listing scanner. "
            "Discovers EarthCam mapsearch cameras, then watches for new ones. "
            "Does not start Project X or HLS discovery."
        ),
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=DEFAULT_REFRESH_INTERVAL_S,
        metavar="SECONDS",
        help=(
            "Watch/refresh interval in seconds "
            f"(default: {int(DEFAULT_REFRESH_INTERVAL_S)})."
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the initial scan only (watch=False), then exit.",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Catalog JSON path (default: Project X data/cache listing store).",
    )
    return parser


def create_scanner(
    args: argparse.Namespace,
    *,
    store_cls=ListingCatalogStore,
    scanner_cls=ListingCatalogScanner,
) -> ListingCatalogScanner:

    path = Path(args.store) if args.store is not None else listing_store_path()
    store = store_cls(path)
    return scanner_cls(
        store,
        refresh_interval_s=float(args.refresh_interval),
    )


def _current_job_id(scanner: ListingCatalogScanner) -> str:

    store = getattr(scanner, "store", None)
    pending = getattr(store, "pending_jobs", None)
    if not callable(pending):
        return "-"
    try:
        jobs = pending()
    except Exception:
        return "-"
    if jobs:
        return str(getattr(jobs[0], "id", "") or "-")
    return "-"


def format_status_line(status: ListingScanStatus, scanner: ListingCatalogScanner) -> str:

    phase = str(getattr(status, "phase", "") or "-")
    job = _current_job_id(scanner)
    processed = int(getattr(status, "processed", 0) or 0)
    queued = int(getattr(status, "queued", 0) or 0)
    failed = int(getattr(status, "failed", 0) or 0)
    total = int(getattr(status, "total", 0) or 0)
    discovered = int(getattr(status, "discovered", 0) or 0)
    new_records = int(getattr(status, "new_records", 0) or 0)
    return (
        f"[{phase}] job={job} "
        f"processed={processed}/{total} queued={queued} failed={failed} "
        f"discovered={discovered} new_records={new_records}"
    )


class ProgressPrinter:
    """Write ListingScanStatus lines to the console."""

    def __init__(self, scanner: ListingCatalogScanner, stream=None):

        self.scanner = scanner
        self.stream = stream if stream is not None else sys.stdout
        self._last_phase = ""
        self._last_discovered = None

    def __call__(self, status: ListingScanStatus) -> None:

        line = format_status_line(status, self.scanner)
        phase = str(getattr(status, "phase", "") or "")
        discovered = int(getattr(status, "discovered", 0) or 0)
        if phase == "INITIAL_SCAN_COMPLETE":
            line += "  (initial scan complete; switching to watch/refresh)"
        elif phase == "WATCHING":
            interval = getattr(self.scanner, "_refresh_interval_s", None)
            if interval is not None:
                line += f"  (refresh every {int(interval)}s)"
        elif phase == "REFRESHING":
            line += "  (checking network + world bbox)"
        elif phase == "ERROR":
            line += "  (refresh error; catalog kept, will retry)"
        if (
            self._last_discovered is not None
            and discovered > self._last_discovered
            and phase in {"REFRESHING", "WATCHING", "ERROR"}
        ):
            line += f"  (+{discovered - self._last_discovered} new cameras)"
        print(line, file=self.stream, flush=True)
        self._last_phase = phase
        self._last_discovered = discovered


def run_cli(args: argparse.Namespace, scanner: ListingCatalogScanner) -> int:

    printer = ProgressPrinter(scanner)
    watch = not bool(args.once)
    print(
        f"Listing Hunter store={getattr(scanner.store, 'path', '-')} "
        f"watch={watch} refresh_interval={args.refresh_interval}s",
        flush=True,
    )
    try:
        scanner.run(watch=watch, on_progress=printer)
    except KeyboardInterrupt:
        print("[STOPPED] interrupted; stopping scanner...", flush=True)
        scanner.stop()
    print("[STOPPED] listing hunter exit", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    scanner = create_scanner(args)

    def _handle_stop(_signum, _frame) -> None:

        print("[STOPPED] signal received; asking scanner to stop...", flush=True)
        scanner.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)
    return run_cli(args, scanner)


if __name__ == "__main__":
    raise SystemExit(main())
