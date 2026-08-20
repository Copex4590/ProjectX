#!/usr/bin/python3
"""Catalog playback-validation workflow (mocked discovery/playback)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.app.catalog_validator import (
    build_parser,
    create_scanner,
    format_progress,
    run_cli,
)
from camera_hunter.engine.catalog_scanner import CatalogValidationScanner
from camera_hunter.engine.catalog_validation import (
    ProbeOutcome,
    ValidationStatus,
    classify_outcome,
    record_from_camera,
)
from camera_hunter.engine.validation_map import (
    render_validated_map_html,
    validated_map_cameras,
)
from camera_hunter.engine.validation_store import CatalogValidationStore


def _camera(**overrides) -> SimpleNamespace:

    values = {
        "key": "url:abc",
        "name": "Test Cam",
        "lat": 47.5,
        "lon": 19.04,
        "source": "bbox",
        "web_url": "https://www.earthcam.com/world/hungary/budapest/",
        "country": "HU",
        "location": "Budapest",
        "city": "Budapest",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class ClassifyOutcomeTests(unittest.TestCase):

    def test_working_playback_is_validated(self) -> None:

        status = classify_outcome(
            ProbeOutcome(
                discovered=True,
                playback_ok=True,
                stream_url="https://cdn.example/live.m3u8",
                source_type="hls",
            )
        )
        self.assertEqual(status, ValidationStatus.VALIDATED)

    def test_no_stream_is_not_validated(self) -> None:

        status = classify_outcome(ProbeOutcome(discovered=False))
        self.assertEqual(status, ValidationStatus.NO_STREAM_FOUND)
        self.assertNotEqual(status, ValidationStatus.VALIDATED)

    def test_stream_without_playback_is_not_validated(self) -> None:

        status = classify_outcome(
            ProbeOutcome(
                discovered=True,
                playback_ok=False,
                stream_url="https://cdn.example/dead.m3u8",
                source_type="hls",
                error="HlsPlayer did not start video.",
            )
        )
        self.assertEqual(status, ValidationStatus.PLAYBACK_FAILED)
        self.assertNotEqual(status, ValidationStatus.VALIDATED)

    def test_timeout_status(self) -> None:

        status = classify_outcome(ProbeOutcome(timed_out=True, error="timeout"))
        self.assertEqual(status, ValidationStatus.TIMEOUT)
        self.assertNotEqual(status, ValidationStatus.VALIDATED)

    def test_unexpected_error_status(self) -> None:

        status = classify_outcome(ProbeOutcome(error="boom"))
        self.assertEqual(status, ValidationStatus.ERROR)


class CatalogValidationScannerTests(unittest.TestCase):

    def setUp(self) -> None:

        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.store = CatalogValidationStore(root / "validation.json")
        self.map_path = root / "validated.html"

    def tearDown(self) -> None:

        self._tmp.cleanup()

    def test_working_camera_is_validated_and_mapped(self) -> None:

        def probe(_camera):
            return ProbeOutcome(
                discovered=True,
                playback_ok=True,
                stream_url="https://cdn.example/live.m3u8",
                source_type="hls",
            )

        camera = _camera()
        scanner = CatalogValidationScanner(
            [camera],
            self.store,
            probe,
            map_path=self.map_path,
            delay_s=0,
        )
        scanner.run()
        record = self.store.get("url:abc")
        self.assertIsNotNone(record)
        self.assertEqual(record.status, ValidationStatus.VALIDATED)
        self.assertTrue(record.playback_ok)
        html = self.map_path.read_text(encoding="utf-8")
        self.assertIn("url:abc", html)
        self.assertIn("Test Cam", html)

    def test_no_stream_not_on_map(self) -> None:

        scanner = CatalogValidationScanner(
            [_camera()],
            self.store,
            lambda _c: ProbeOutcome(discovered=False),
            map_path=self.map_path,
            delay_s=0,
        )
        scanner.run()
        self.assertEqual(
            self.store.get("url:abc").status,
            ValidationStatus.NO_STREAM_FOUND,
        )
        self.assertNotIn("url:abc", self.map_path.read_text(encoding="utf-8"))
        self.assertEqual(validated_map_cameras(self.store.all_records()), [])

    def test_playback_failed_not_on_map(self) -> None:

        scanner = CatalogValidationScanner(
            [_camera()],
            self.store,
            lambda _c: ProbeOutcome(
                discovered=True,
                playback_ok=False,
                stream_url="https://cdn.example/x.m3u8",
            ),
            map_path=self.map_path,
            delay_s=0,
        )
        scanner.run()
        self.assertEqual(
            self.store.get("url:abc").status,
            ValidationStatus.PLAYBACK_FAILED,
        )
        self.assertEqual(validated_map_cameras(self.store.all_records()), [])

    def test_timeout_does_not_stop_scan(self) -> None:

        outcomes = {
            "one": ProbeOutcome(timed_out=True, error="timeout"),
            "two": ProbeOutcome(
                discovered=True,
                playback_ok=True,
                stream_url="https://cdn.example/ok.m3u8",
                source_type="hls",
            ),
        }

        def probe(camera):
            return outcomes[camera.key]

        scanner = CatalogValidationScanner(
            [_camera(key="one", name="Timeout Cam"), _camera(key="two", name="Ok Cam")],
            self.store,
            probe,
            map_path=self.map_path,
            delay_s=0,
        )
        scanner.run()
        self.assertEqual(self.store.get("one").status, ValidationStatus.TIMEOUT)
        self.assertEqual(self.store.get("two").status, ValidationStatus.VALIDATED)
        html = self.map_path.read_text(encoding="utf-8")
        self.assertIn("two", html)
        self.assertNotIn("Timeout Cam", html)

    def test_probe_exception_continues_to_next_camera(self) -> None:

        def probe(camera):
            if camera.key == "bad":
                raise RuntimeError("probe exploded")
            return ProbeOutcome(
                discovered=True,
                playback_ok=True,
                stream_url="https://cdn.example/ok.m3u8",
                source_type="hls",
            )

        scanner = CatalogValidationScanner(
            [_camera(key="bad", name="Broken"), _camera(key="good", name="Good")],
            self.store,
            probe,
            map_path=self.map_path,
            delay_s=0,
        )
        scanner.run()
        self.assertEqual(self.store.get("bad").status, ValidationStatus.ERROR)
        self.assertEqual(self.store.get("good").status, ValidationStatus.VALIDATED)

    def test_only_validated_cameras_are_on_the_map(self) -> None:

        records = [
            record_from_camera(
                _camera(key="ok", name="Live", lat=10.0, lon=20.0),
                ProbeOutcome(discovered=True, playback_ok=True),
            ),
            record_from_camera(
                _camera(key="dead", name="Dead", lat=11.0, lon=21.0),
                ProbeOutcome(discovered=False),
            ),
            record_from_camera(
                _camera(key="playfail", name="PlayFail", lat=12.0, lon=22.0),
                ProbeOutcome(discovered=True, playback_ok=False),
            ),
        ]
        markers = validated_map_cameras(records)
        self.assertEqual([item["id"] for item in markers], ["ok"])
        html = render_validated_map_html(markers)
        self.assertIn("Live", html)
        self.assertNotIn("Dead", html)
        self.assertNotIn("PlayFail", html)

    def test_resume_skips_validated(self) -> None:

        first = CatalogValidationScanner(
            [_camera(key="ok")],
            self.store,
            lambda _c: ProbeOutcome(discovered=True, playback_ok=True),
            delay_s=0,
        )
        first.run()
        calls = []

        def probe(camera):
            calls.append(camera.key)
            return ProbeOutcome(discovered=False)

        second = CatalogValidationScanner(
            [_camera(key="ok"), _camera(key="next")],
            self.store,
            probe,
            delay_s=0,
        )
        second.run()
        self.assertEqual(calls, ["next"])
        self.assertEqual(self.store.get("ok").status, ValidationStatus.VALIDATED)

    def test_store_does_not_write_listing_catalog(self) -> None:

        listing = Path(self._tmp.name) / "hunter_listing_catalog.json"
        listing.write_text('{"version": 1, "cameras": []}\n', encoding="utf-8")
        CatalogValidationScanner(
            [_camera()],
            self.store,
            lambda _c: ProbeOutcome(discovered=True, playback_ok=True),
            delay_s=0,
        ).run()
        self.assertEqual(
            listing.read_text(encoding="utf-8"),
            '{"version": 1, "cameras": []}\n',
        )


class CatalogValidatorCliTests(unittest.TestCase):

    def test_help_exits_zero(self) -> None:

        parser = build_parser()
        with self.assertRaises(SystemExit) as raised:
            parser.parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_create_scanner_wires_store_and_retry(self) -> None:

        args = Namespace(
            catalog=Path("/tmp/listing.json"),
            store=Path("/tmp/validation.json"),
            map_path=Path("/tmp/map.html"),
            delay=0,
            limit=0,
            fresh=False,
            no_retry_failed=False,
            timeout=90,
        )
        probe = lambda _c: ProbeOutcome()
        cameras = [_camera()]
        store = MagicMock()
        scanner = create_scanner(
            args, probe=probe, cameras=cameras, store=store
        )
        self.assertIs(scanner.store, store)
        self.assertTrue(scanner.retry_failed)
        self.assertEqual(scanner.map_path, Path("/tmp/map.html"))

    def test_run_cli_invokes_scanner(self) -> None:

        args = Namespace(timeout=90, delay=0)
        scanner = MagicMock()
        scanner.cameras = []
        scanner.store.path = Path("validation.json")
        scanner.map_path = Path("map.html")
        scanner.pending.return_value = []
        scanner.store.summary.return_value = SimpleNamespace(
            processed=0,
            total=0,
            validated=0,
            no_stream_found=0,
            playback_failed=0,
            timeout=0,
            error=0,
        )
        code = run_cli(args, scanner)
        self.assertEqual(code, 0)
        scanner.run.assert_called_once()

    def test_progress_line_includes_status(self) -> None:

        record = record_from_camera(
            _camera(),
            ProbeOutcome(discovered=True, playback_ok=True, source_type="hls"),
        )
        line = format_progress(1, 10, record)
        self.assertIn("[1/10]", line)
        self.assertIn("VALIDATED", line)
        self.assertIn("url:abc", line)

    def test_main_not_imported_as_scan_start(self) -> None:

        import camera_hunter.catalog_validator as entry

        self.assertTrue(callable(entry.main))

    def test_create_live_session_requests_headless_engine(self) -> None:

        from camera_hunter.app.catalog_validator import create_live_session

        session = create_live_session()
        self.assertTrue(session._headless)

    def test_catalog_validator_headless_flags_are_in_discovery_engine(self) -> None:

        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "camera_hunter"
            / "engine"
            / "discovery.py"
        )
        text = source.read_text(encoding="utf-8")
        self.assertIn("headless: bool = False", text)
        chrome = text.split("def _apply_headless_chrome")[1].split("def ")[0]
        self.assertIn("WA_DontShowOnScreen", chrome)
        self.assertIn("WA_ShowWithoutActivating", chrome)
        self.assertIn("BypassWindowManagerHint", chrome)
        present = text.split("def _present_engine_host")[1].split("def ")[0]
        self.assertIn("self._apply_headless_chrome(self._host, top_level=True)", present)
        hide = text.split("def _hide_engine_from_user")[1].split("def ")[0]
        self.assertIn("if self._headless:", hide)
        headless_block = hide.split("if self._headless:")[1].split("return")[0]
        self.assertNotIn("self._view.raise_()", headless_block)

    def test_default_present_host_still_shows_without_bypass_flag(self) -> None:

        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "camera_hunter"
            / "engine"
            / "discovery.py"
        )
        present = source.read_text(encoding="utf-8").split(
            "def _present_engine_host"
        )[1].split("def ")[0]
        default_branch = present.split("if not self._show_browser:")[1]
        self.assertIn("self._host.show()", default_branch)
        self.assertIn("self._view.show()", default_branch)
        self.assertNotIn("BypassWindowManagerHint", default_branch)


if __name__ == "__main__":
    unittest.main()
