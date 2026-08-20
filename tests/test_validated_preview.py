#!/usr/bin/python3
"""Temporary VALIDATED-camera preview: JSON read-only + Hunter click path."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.app.validated_preview import (
    load_preview_cameras,
    start_hunter_preview,
)
from camera_hunter.engine.catalog_validation import ValidationStatus
from camera_hunter.engine.validation_preview import (
    load_validated_records,
    load_validation_payload,
    render_preview_map_html,
    validated_records_from_payload,
    web_url_for_validated_camera,
    records_by_id,
)

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = ROOT / "src" / "camera_hunter" / "app" / "validated_preview.py"
ENGINE_SRC = ROOT / "src" / "camera_hunter" / "engine" / "validation_preview.py"


def _payload(*cameras) -> dict:

    return {"version": 1, "cameras": list(cameras)}


def _camera(**overrides) -> dict:

    values = {
        "camera_id": "id:ok",
        "name": "OK Cam",
        "lat": 47.5,
        "lon": 19.04,
        "source": "network",
        "web_url": "https://www.earthcam.com/world/hungary/budapest/",
        "country": "Hungary",
        "location": "Budapest",
        "city": "Budapest",
        "status": "VALIDATED",
        "discovery_result": "found",
        "stream_url": "https://cdn.example/live.m3u8",
        "source_type": "hls",
        "playback_ok": True,
        "error": "",
        "timestamp": "2026-08-20T00:00:00+00:00",
    }
    values.update(overrides)
    return values


class LoadValidatedJsonTests(unittest.TestCase):

    def test_only_validated_cameras_are_kept(self) -> None:

        payload = _payload(
            _camera(camera_id="id:ok", status="VALIDATED"),
            _camera(camera_id="id:timeout", status="TIMEOUT", playback_ok=False),
            _camera(camera_id="id:failed", status="PLAYBACK_FAILED", playback_ok=False),
        )
        records = validated_records_from_payload(payload)
        self.assertEqual([item.camera_id for item in records], ["id:ok"])
        self.assertEqual(records[0].status, ValidationStatus.VALIDATED)
        self.assertEqual(
            records[0].web_url,
            "https://www.earthcam.com/world/hungary/budapest/",
        )

    def test_load_validated_records_reads_file(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hunter_catalog_validation.json"
            path.write_text(
                json.dumps(
                    _payload(
                        _camera(camera_id="id:a", name="A"),
                        _camera(camera_id="id:b", status="TIMEOUT", name="B"),
                    )
                ),
                encoding="utf-8",
            )
            records = load_validated_records(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "A")

    def test_refresh_picks_up_newly_validated_cameras(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hunter_catalog_validation.json"
            path.write_text(json.dumps(_payload(_camera(camera_id="id:a"))), encoding="utf-8")
            first, error = load_preview_cameras(path)
            self.assertIsNone(error)
            self.assertEqual([item.camera_id for item in first], ["id:a"])
            path.write_text(
                json.dumps(
                    _payload(
                        _camera(camera_id="id:a"),
                        _camera(camera_id="id:b", name="Later"),
                    )
                ),
                encoding="utf-8",
            )
            second, error = load_preview_cameras(path)
        self.assertIsNone(error)
        self.assertEqual([item.camera_id for item in second], ["id:a", "id:b"])

    def test_load_opens_json_read_only(self) -> None:

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hunter_catalog_validation.json"
            path.write_text(json.dumps(_payload(_camera())), encoding="utf-8")
            modes: list[str] = []
            real_open = Path.open

            def tracking_open(self, mode="r", *args, **kwargs):
                modes.append(str(mode))
                return real_open(self, mode, *args, **kwargs)

            with patch.object(Path, "open", tracking_open):
                load_validation_payload(path)
        self.assertTrue(modes)
        self.assertTrue(all("w" not in mode and "a" not in mode and "+" not in mode for mode in modes))

    def test_missing_file_does_not_raise(self) -> None:

        records, error = load_preview_cameras(Path("/tmp/does-not-exist-px-validation.json"))
        self.assertEqual(records, [])
        self.assertIn("not found", error or "")


class ClickPathTests(unittest.TestCase):

    def test_click_uses_json_web_url_not_stream_url(self) -> None:

        records = validated_records_from_payload(
            _payload(
                _camera(
                    camera_id="id:ok",
                    web_url="https://www.earthcam.com/usa/newyork/911memorialmuseum/?cam=911memorial",
                    stream_url="https://cdn.example/playlist.m3u8",
                )
            )
        )
        url = web_url_for_validated_camera(records_by_id(records), "id:ok")
        self.assertIn("earthcam.com", url)
        self.assertNotIn(".m3u8", url)

    def test_unknown_or_non_validated_has_no_url(self) -> None:

        records = validated_records_from_payload(_payload(_camera(camera_id="id:ok")))
        index = records_by_id(records)
        self.assertEqual(web_url_for_validated_camera(index, "missing"), "")

    def test_start_hunter_preview_mirrors_px_panel(self) -> None:

        session = MagicMock()
        session.discover.return_value = True
        widget = MagicMock()
        widget.parent.return_value = None
        session.player_widget.return_value = widget
        host = MagicMock()
        layout = MagicMock()
        host.layout.return_value = layout

        started = start_hunter_preview(
            session,
            "https://www.earthcam.com/world/hungary/budapest/",
            host,
        )

        self.assertTrue(started)
        self.assertEqual(
            [item[0] for item in session.method_calls if item[0] in {"ensure", "stop", "discover"}],
            ["ensure", "stop", "discover"],
        )
        session.discover.assert_called_once_with(
            "https://www.earthcam.com/world/hungary/budapest/"
        )
        layout.addWidget.assert_called_once_with(widget)
        widget.show.assert_called()


class MapHtmlTests(unittest.TestCase):

    def test_html_clicks_select_camera_not_iframe(self) -> None:

        html = render_preview_map_html(
            [
                {
                    "id": "id:ok",
                    "name": "OK Cam",
                    "lat": 47.5,
                    "lon": 19.04,
                }
            ]
        )
        self.assertIn("bridge.selectCamera", html)
        self.assertIn("qwebchannel.js", html)
        self.assertIn("updateCameras", html)
        self.assertNotIn("<iframe", html.lower())
        self.assertIn("id:ok", html)


class IsolationTests(unittest.TestCase):

    def test_modules_do_not_write_validation_json_or_start_scan(self) -> None:

        app_src = APP_SRC.read_text(encoding="utf-8")
        engine_src = ENGINE_SRC.read_text(encoding="utf-8")
        combined = app_src + "\n" + engine_src
        self.assertNotIn("CatalogValidationScanner", combined)
        self.assertNotIn("CatalogValidationStore", combined)
        self.assertNotIn(".save(", combined)
        self.assertNotIn(".put(", combined)
        self.assertNotIn("store.clear", combined)
        self.assertNotIn("scanner.run", combined)
        self.assertIn("HunterLiveSession", app_src)
        self.assertIn("start_hunter_preview", app_src)
        self.assertNotIn("hunter_live_session", app_src.split("create_preview_session")[1][:400])

    def test_open_is_read_only_in_engine_loader(self) -> None:

        src = ENGINE_SRC.read_text(encoding="utf-8")
        self.assertIn('target.open(encoding="utf-8")', src)
        self.assertNotIn('open("w"', src)
        self.assertNotIn("open('w'", src)
        self.assertNotIn('mode="w"', src)
