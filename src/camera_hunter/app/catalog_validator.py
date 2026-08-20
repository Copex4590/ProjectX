"""Standalone Hunter catalog playback-validation CLI.

Uses the existing HunterLiveSession discover(interactive=True) + HlsPlayer
path. Does not start Project X, listing scanner, or the map GUI.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from camera_hunter.app.listing_hunter import listing_store_path
from camera_hunter.engine.catalog_scanner import CatalogValidationScanner
from camera_hunter.engine.catalog_validation import ProbeOutcome, ValidationRecord
from camera_hunter.engine.listing_store import ListingCatalogStore
from camera_hunter.engine.validation_store import CatalogValidationStore

STORE_FILENAME = "hunter_catalog_validation.json"
MAP_FILENAME = "hunter_validated_cameras.html"
DEFAULT_TIMEOUT_S = 90.0
DEFAULT_DELAY_S = 2.0


def validation_store_path() -> Path:

    override = os.environ.get("PROJECTX_HUNTER_VALIDATION", "").strip()
    if override:
        return Path(override)
    return listing_store_path().with_name(STORE_FILENAME)


def validation_map_path() -> Path:

    override = os.environ.get("PROJECTX_HUNTER_VALIDATION_MAP", "").strip()
    if override:
        return Path(override)
    return listing_store_path().with_name(MAP_FILENAME)


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="catalog-validator",
        description=(
            "Validate every Hunter listing camera by running the existing "
            "Hunter discovery + HlsPlayer path. Only cameras that actually "
            "play are marked VALIDATED. Does not start Project X."
        ),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=None,
        help="Hunter listing catalog JSON (default: data/cache listing store).",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Validation results JSON (default: data/cache/hunter_catalog_validation.json).",
    )
    parser.add_argument(
        "--map",
        dest="map_path",
        type=Path,
        default=None,
        help="Validated-cameras HTML map (default: data/cache/hunter_validated_cameras.html).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"Per-camera discovery/playback timeout (default: {int(DEFAULT_TIMEOUT_S)}).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_S,
        metavar="SECONDS",
        help=f"Pause between cameras (default: {DEFAULT_DELAY_S}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Validate at most N pending cameras (0 = all).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore previous validation results and start over.",
    )
    parser.add_argument(
        "--no-retry-failed",
        action="store_true",
        help="Resume: skip every already-processed camera, not only VALIDATED.",
    )
    return parser


def load_listing_cameras(path: Path):

    store = ListingCatalogStore(path)
    return store.all_cameras()


def format_progress(index: int, total: int, record: ValidationRecord) -> str:

    return (
        f"[{index}/{total}] {record.status.value} "
        f"id={record.camera_id} name={record.name or '-'} "
        f"type={record.source_type or '-'} "
        f"error={record.error or '-'}"
    )


class HunterPlaybackProbe:
    """One camera: HunterLiveSession.discover(interactive=True) until video or fail."""

    def __init__(self, session, *, timeout_s: float) -> None:

        self._session = session
        self._timeout_ms = max(int(float(timeout_s) * 1000), 1000)

    def __call__(self, camera: object) -> ProbeOutcome:

        from PySide6.QtCore import QEventLoop, QTimer

        from cameras.hunter_session import (
            camera_result_provider_type,
            camera_result_stream_url,
        )

        web_url = str(getattr(camera, "web_url", "") or "").strip()
        if not web_url:
            return ProbeOutcome(error="Camera page URL is empty.")

        outcome = ProbeOutcome()
        loop = QEventLoop()

        def _finish() -> None:

            if loop.isRunning():
                loop.quit()

        def on_ready(result: object) -> None:

            outcome.discovered = True
            outcome.stream_url = camera_result_stream_url(result)
            outcome.source_type = camera_result_provider_type(result)
            outcome.source_page = str(getattr(result, "source_page", "") or "")
            engine_player = getattr(self._session, "_player", None)
            has_video = bool(
                engine_player is not None
                and (engine_player.has_video or engine_player.is_playing)
            )
            outcome.playback_ok = has_video
            if not has_video:
                outcome.error = "Stream found but HlsPlayer did not start video."
            _finish()

        def on_failed(message: str) -> None:

            if outcome.discovered:
                return
            outcome.error = str(message or "").strip()
            _finish()

        def on_timeout() -> None:

            if outcome.discovered or outcome.error:
                return
            outcome.timed_out = True
            outcome.error = "timeout"
            _finish()

        self._session.stop()
        self._session.live_ready.connect(on_ready)
        self._session.failed.connect(on_failed)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(on_timeout)
        started = self._session.discover(web_url)
        if not started:
            try:
                self._session.live_ready.disconnect(on_ready)
                self._session.failed.disconnect(on_failed)
            except (RuntimeError, TypeError):
                pass
            if not outcome.error:
                outcome.error = "Discovery already running."
            return outcome
        timer.start(self._timeout_ms)
        loop.exec()
        timer.stop()
        try:
            self._session.live_ready.disconnect(on_ready)
            self._session.failed.disconnect(on_failed)
        except (RuntimeError, TypeError):
            pass
        self._session.stop()
        return outcome


def create_scanner(
    args: argparse.Namespace,
    *,
    probe,
    cameras=None,
    store=None,
) -> CatalogValidationScanner:

    catalog_path = Path(args.catalog) if args.catalog is not None else listing_store_path()
    store_path = Path(args.store) if args.store is not None else validation_store_path()
    map_path = Path(args.map_path) if args.map_path is not None else validation_map_path()
    if cameras is None:
        cameras = load_listing_cameras(catalog_path)
    if store is None:
        store = CatalogValidationStore(store_path)
        if bool(getattr(args, "fresh", False)):
            store.clear()
    return CatalogValidationScanner(
        cameras,
        store,
        probe,
        map_path=map_path,
        delay_s=float(getattr(args, "delay", DEFAULT_DELAY_S)),
        retry_failed=not bool(getattr(args, "no_retry_failed", False)),
        limit=int(getattr(args, "limit", 0) or 0),
    )


def run_cli(args: argparse.Namespace, scanner: CatalogValidationScanner) -> int:

    def on_progress(index: int, total: int, record: ValidationRecord) -> None:

        print(format_progress(index, total, record), flush=True)

    print(
        f"Catalog validator catalog={len(scanner.cameras)} "
        f"store={scanner.store.path} map={scanner.map_path} "
        f"timeout={args.timeout}s delay={args.delay}s "
        f"pending={len(scanner.pending())}",
        flush=True,
    )
    try:
        scanner.run(on_progress=on_progress)
    except KeyboardInterrupt:
        print("[STOPPED] interrupted; stopping validator...", flush=True)
        scanner.stop()
    summary = scanner.store.summary(total=len(scanner.cameras))
    print(
        f"[DONE] processed={summary.processed}/{summary.total} "
        f"validated={summary.validated} "
        f"no_stream={summary.no_stream_found} "
        f"playback_failed={summary.playback_failed} "
        f"timeout={summary.timeout} error={summary.error}",
        flush=True,
    )
    if scanner.map_path is not None:
        print(f"[MAP] {scanner.map_path}", flush=True)
    return 0


def create_live_session():
    """Hunter session for catalog validation: same playback path, hidden WebEngine."""

    from cameras.hunter_session import HunterLiveSession

    return HunterLiveSession(headless=True)


def main(argv: list[str] | None = None) -> int:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)

    from camera_hunter.app.webengine_setup import configure_remote_debugging
    from PySide6.QtWidgets import QApplication

    configure_remote_debugging()
    app = QApplication.instance()
    if app is None:
        app = QApplication(["projectx-catalog-validator"])

    session = create_live_session()
    probe = HunterPlaybackProbe(session, timeout_s=float(args.timeout))
    scanner = create_scanner(args, probe=probe)

    def _handle_stop(_signum, _frame) -> None:

        print("[STOPPED] signal received; asking validator to stop...", flush=True)
        scanner.stop()
        session.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)
    return run_cli(args, scanner)


if __name__ == "__main__":
    raise SystemExit(main())
