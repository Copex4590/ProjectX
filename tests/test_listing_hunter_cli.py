#!/usr/bin/env python3
"""Standalone listing Hunter CLI: wires ListingCatalogScanner, no GUI/HLS."""

from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.app.listing_hunter import (
    ProgressPrinter,
    build_parser,
    create_scanner,
    format_status_line,
    listing_store_path,
    main,
    run_cli,
)
from camera_hunter.engine.listing_scanner import DEFAULT_REFRESH_INTERVAL_S
from camera_hunter.engine.listing_store import ListingScanStatus


class ListingHunterCliTests(unittest.TestCase):

    def test_help_exits_zero(self) -> None:

        parser = build_parser()
        with self.assertRaises(SystemExit) as raised:
            parser.parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_create_scanner_uses_store_path_and_refresh_interval(self) -> None:

        args = Namespace(refresh_interval=123, store=Path("/tmp/hunter-test.json"), once=False)
        store_cls = MagicMock()
        scanner_cls = MagicMock()
        store = store_cls.return_value
        create_scanner(args, store_cls=store_cls, scanner_cls=scanner_cls)
        store_cls.assert_called_once_with(Path("/tmp/hunter-test.json"))
        scanner_cls.assert_called_once_with(store, refresh_interval_s=123.0)

    def test_once_passes_watch_false(self) -> None:

        args = Namespace(once=True, refresh_interval=1800, store=None)
        scanner = MagicMock()
        scanner.store.path = Path("catalog.json")
        run_cli(args, scanner)
        scanner.run.assert_called_once()
        kwargs = scanner.run.call_args.kwargs
        self.assertFalse(kwargs["watch"])
        self.assertTrue(callable(kwargs["on_progress"]))

    def test_default_mode_watch_true(self) -> None:

        args = build_parser().parse_args([])
        self.assertFalse(args.once)
        self.assertEqual(args.refresh_interval, DEFAULT_REFRESH_INTERVAL_S)
        scanner = MagicMock()
        scanner.store.path = Path("catalog.json")
        run_cli(args, scanner)
        self.assertTrue(scanner.run.call_args.kwargs["watch"])

    def test_refresh_interval_is_passed_through(self) -> None:

        args = build_parser().parse_args(["--refresh-interval", "45"])
        self.assertEqual(args.refresh_interval, 45)
        store_cls = MagicMock()
        scanner_cls = MagicMock()
        create_scanner(args, store_cls=store_cls, scanner_cls=scanner_cls)
        self.assertEqual(
            scanner_cls.call_args.kwargs["refresh_interval_s"],
            45.0,
        )

    def test_keyboard_interrupt_calls_stop(self) -> None:

        args = Namespace(once=False, refresh_interval=1800, store=None)
        scanner = MagicMock()
        scanner.store.path = Path("catalog.json")
        scanner.run.side_effect = KeyboardInterrupt()
        code = run_cli(args, scanner)
        scanner.stop.assert_called()
        self.assertEqual(code, 0)

    def test_progress_line_uses_listing_scan_status(self) -> None:

        scanner = MagicMock()
        job = MagicMock()
        job.id = "network"
        scanner.store.pending_jobs.return_value = [job]
        status = ListingScanStatus(
            discovered=12,
            queued=3,
            processed=5,
            failed=1,
            total=8,
            new_records=4,
            phase="INITIAL_SCAN",
        )
        line = format_status_line(status, scanner)
        self.assertIn("[INITIAL_SCAN]", line)
        self.assertIn("job=network", line)
        self.assertIn("processed=5/8", line)
        self.assertIn("queued=3", line)
        self.assertIn("failed=1", line)
        self.assertIn("discovered=12", line)
        self.assertIn("new_records=4", line)

    def test_progress_printer_notes_complete_and_refresh(self) -> None:

        scanner = MagicMock()
        scanner.store.pending_jobs.return_value = []
        scanner._refresh_interval_s = 1800
        import io

        buf = io.StringIO()
        printer = ProgressPrinter(scanner, stream=buf)
        printer(
            ListingScanStatus(phase="INITIAL_SCAN_COMPLETE", discovered=10, processed=2, total=2)
        )
        printer(ListingScanStatus(phase="WATCHING", discovered=10, processed=2, total=2))
        printer(ListingScanStatus(phase="REFRESHING", discovered=11, processed=2, total=2))
        text = buf.getvalue()
        self.assertIn("INITIAL_SCAN_COMPLETE", text)
        self.assertIn("WATCHING", text)
        self.assertIn("REFRESHING", text)
        self.assertIn("+1 new cameras", text)

    def test_store_path_honors_env_override(self) -> None:

        with patch.dict("os.environ", {"PROJECTX_HUNTER_LISTING_CATALOG": "/tmp/custom.json"}):
            self.assertEqual(listing_store_path(), Path("/tmp/custom.json"))

    def test_main_wires_create_scanner_and_run_cli(self) -> None:

        scanner = MagicMock()
        with patch(
            "camera_hunter.app.listing_hunter.create_scanner",
            return_value=scanner,
        ) as created:
            with patch("camera_hunter.app.listing_hunter.run_cli", return_value=0) as run:
                code = main(["--once", "--refresh-interval", "9"])
        self.assertEqual(code, 0)
        created.assert_called_once()
        self.assertTrue(created.call_args.args[0].once)
        self.assertEqual(created.call_args.args[0].refresh_interval, 9)
        run.assert_called_once()
        self.assertIs(run.call_args.args[1], scanner)


if __name__ == "__main__":
    unittest.main()
