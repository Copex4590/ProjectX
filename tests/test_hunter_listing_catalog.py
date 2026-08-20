#!/usr/bin/env python3
"""Hunter listing catalog: network + bbox merge, dedup, persist, resume."""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.engine.listing_catalog import (
    SOURCE_BBOX,
    SOURCE_NETWORK,
    cameras_from_payload,
    extract_places,
    listing_camera_from_place,
    stable_listing_key,
)
from camera_hunter.engine.listing_scanner import (
    DEFAULT_REFRESH_INTERVAL_S,
    HunterPhase,
    ListingCatalogScanner,
)
from camera_hunter.engine.listing_store import ListingCatalogStore, ListingJob
from cameras.hunter_catalog import listing_camera_to_px, load_listing_cameras
from cameras.manager import CameraManager
from database.camera_registry import CameraRegistry
from models.camera import SOURCE_CATALOG, SOURCE_EARTHCAM, SOURCE_USER, Camera

ROOT = Path(__file__).resolve().parent
NETWORK_FIXTURE = ROOT / "fixtures" / "earthcam_mapsearch_sample.json"
BBOX_FIXTURE = ROOT / "fixtures" / "earthcam_mapsearch_bbox_sample.json"


def _load_json(path: Path):

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _camera(**overrides) -> Camera:

    values = {
        "id": "local-1",
        "name": "Local catalog",
        "lat": 47.501539,
        "lon": 19.039856,
        "enabled": True,
        "source": SOURCE_CATALOG,
        "created_at": datetime(2026, 8, 18, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 18, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Camera(**values)


class ListingParseTests(unittest.TestCase):

    def test_network_payload_keeps_valid_lat_lon_and_page_url(self) -> None:

        payload = _load_json(NETWORK_FIXTURE)
        places = extract_places(payload)
        self.assertEqual(len(places), 5)
        cameras = cameras_from_payload(payload, source=SOURCE_NETWORK)
        by_id = {camera.listing_id: camera for camera in cameras}
        self.assertEqual(len(cameras), 2)
        abbey = by_id["9d4ed10fa9ccba996480f206e5619c9b"]
        self.assertEqual(abbey.name, "Abbey Road Crossing Cam")
        self.assertAlmostEqual(abbey.lat, 51.5321471)
        self.assertAlmostEqual(abbey.lon, -0.1779579)
        self.assertEqual(
            abbey.web_url,
            "https://www.earthcam.com/world/england/london/abbeyroad/",
        )
        self.assertTrue(abbey.thumbnail_url.endswith("abbey.jpg"))
        self.assertEqual(abbey.location, "London, England")
        self.assertEqual(abbey.city, "London")
        self.assertEqual(abbey.country, "England")
        self.assertEqual(abbey.source, SOURCE_NETWORK)
        self.assertTrue(abbey.key.startswith("id:"))

    def test_bbox_payload_without_id_uses_page_url_key(self) -> None:

        payload = [_load_json(BBOX_FIXTURE)]
        cameras = cameras_from_payload(payload, source=SOURCE_BBOX)
        self.assertEqual(len(cameras), 2)
        steyr = cameras[0]
        self.assertEqual(steyr.listing_id, "")
        self.assertTrue(steyr.key.startswith("url:"))
        self.assertEqual(steyr.web_url, "http://www.steyr.at/webcam")
        self.assertEqual(steyr.source, SOURCE_BBOX)
        self.assertEqual(cameras[1].name, "Cafe52 Cam")

    def test_page_url_comes_from_listing_url_not_thumbnail(self) -> None:

        camera = listing_camera_from_place(
            {
                "id": "abc",
                "name": "Test",
                "url": "https://www.earthcam.com/world/hungary/budapest/",
                "thumbnail": "https://static.earthcam.com/camshots/256x144/x.jpg",
                "posn": ["47.5", "19.0"],
            },
            source=SOURCE_NETWORK,
        )
        self.assertIsNotNone(camera)
        self.assertEqual(
            camera.web_url,
            "https://www.earthcam.com/world/hungary/budapest/",
        )
        self.assertNotEqual(camera.web_url, camera.thumbnail_url)

    def test_skips_missing_page_url(self) -> None:

        camera = listing_camera_from_place(
            {
                "id": "no-url",
                "name": "Nope",
                "posn": ["47.5", "19.0"],
                "thumbnail": "https://static.earthcam.com/camshots/256x144/x.jpg",
            },
            source=SOURCE_NETWORK,
        )
        self.assertIsNone(camera)


class ListingScannerTests(unittest.TestCase):

    def test_merges_network_and_bbox_and_dedups_by_url(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        with TemporaryDirectory() as tmp:
            store = ListingCatalogStore(Path(tmp) / "catalog.json")
            scanner = ListingCatalogScanner(
                store,
                jobs=[
                    ListingJob(id="network", kind="network"),
                    ListingJob(id="bbox:world", kind="bbox", params={"zoom": 4}),
                ],
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
            )
            status = scanner.run(watch=False)
            keys = {camera.key for camera in store.all_cameras()}
            urls = {camera.web_url for camera in store.all_cameras()}
            self.assertGreater(status.discovered, 2)
            self.assertEqual(status.discovered, 4)
            self.assertEqual(status.processed, 2)
            self.assertEqual(status.queued, 0)
            self.assertEqual(status.failed, 0)
            self.assertEqual(status.new_records, 4)
            self.assertIn("https://www.earthcam.com/world/hungary/budapest/", urls)
            self.assertIn("http://www.steyr.at/webcam", urls)
            self.assertEqual(len(urls), 4)
            self.assertEqual(len(keys), 4)

    def test_restart_skips_processed_jobs_and_known_cameras(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        calls = {"network": 0, "bbox": 0}

        def network_fetcher():
            calls["network"] += 1
            return network

        def bbox_fetcher(_params):
            calls["bbox"] += 1
            return bbox

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            jobs = [
                ListingJob(id="network", kind="network"),
                ListingJob(id="bbox:world", kind="bbox", params={"zoom": 4}),
            ]
            first = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=jobs,
                network_fetcher=network_fetcher,
                bbox_fetcher=bbox_fetcher,
                request_pause_s=0.0,
            )
            first.run(watch=False)
            self.assertEqual(calls["network"], 1)
            store = ListingCatalogStore(path)
            second = ListingCatalogScanner(
                store,
                jobs=jobs,
                network_fetcher=network_fetcher,
                bbox_fetcher=bbox_fetcher,
                request_pause_s=0.0,
            )
            status = second.run(watch=False)
            self.assertEqual(calls["network"], 1)
            self.assertEqual(calls["bbox"], 1)
            self.assertEqual(status.discovered, 4)
            self.assertEqual(status.new_records, 0)
            self.assertEqual(status.processed, 2)

    def test_failed_job_keeps_already_saved_cameras(self) -> None:

        network = _load_json(NETWORK_FIXTURE)

        def bbox_fetcher(_params):
            raise RuntimeError("network down")

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            jobs = [
                ListingJob(id="network", kind="network"),
                ListingJob(id="bbox:world", kind="bbox", params={"zoom": 4}),
            ]
            scanner = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=jobs,
                network_fetcher=lambda: network,
                bbox_fetcher=bbox_fetcher,
                request_pause_s=0.0,
            )

            def stop_on_fail(status) -> None:
                if status.failed:
                    scanner.stop()

            status = scanner.run(watch=False, on_progress=stop_on_fail)
            self.assertEqual(status.discovered, 2)
            self.assertEqual(status.processed, 1)
            self.assertEqual(status.failed, 1)
            self.assertEqual(
                [camera.name for camera in ListingCatalogStore(path).all_cameras()][0],
                "Abbey Road Crossing Cam",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"]["discovered"], 2)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

            retry = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=jobs,
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: [_load_json(BBOX_FIXTURE)],
                request_pause_s=0.0,
            )
            retry_status = retry.run(watch=False)
            self.assertEqual(retry_status.discovered, 4)
            self.assertEqual(retry_status.failed, 0)
            self.assertEqual(retry_status.processed, 2)
            self.assertEqual(retry.phase, HunterPhase.INITIAL_SCAN_COMPLETE)


class CameraManagerHunterCatalogTests(unittest.TestCase):

    def test_manager_consumes_store_and_keeps_pack_user_cameras(self) -> None:

        payload = _load_json(NETWORK_FIXTURE)
        with TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "catalog.json"
            store = ListingCatalogStore(store_path)
            ListingCatalogScanner(
                store,
                jobs=[ListingJob(id="network", kind="network")],
                network_fetcher=lambda: payload,
                bbox_fetcher=lambda _params: [],
                request_pause_s=0.0,
            ).run(watch=False)

            packs = MagicMock()
            packs.load_enabled_cameras.return_value = []
            manager = CameraManager(
                registry=CameraRegistry(),
                user_path=Path(tmp) / "cameras.json",
                pack_manager=packs,
                hunter_catalog_loader=lambda: load_listing_cameras(store_path),
            )
            manager.loader.load_cameras = lambda: [
                _camera(id="hu-budapest-duna-north", name="Duna North")
            ]
            manager.load()
            user = _camera(
                id="user-1",
                name="User cam",
                source=SOURCE_USER,
                observation_point_id="op-1",
            )
            manager.registry.add(user)
            manager.reload_hunter_catalog()

            cameras = {camera.id: camera for camera in manager.all()}
            self.assertEqual(cameras["hu-budapest-duna-north"].source, SOURCE_CATALOG)
            self.assertEqual(cameras["user-1"].source, SOURCE_USER)
            hunter_ids = [
                camera.id
                for camera in cameras.values()
                if camera.source == SOURCE_EARTHCAM
            ]
            self.assertEqual(len(hunter_ids), 2)
            budapest = next(
                camera
                for camera in cameras.values()
                if camera.name == "Budapest Cam"
            )
            self.assertEqual(
                budapest.web_url,
                "https://www.earthcam.com/world/hungary/budapest/",
            )
            px = listing_camera_to_px(store.all_cameras()[0])
            self.assertEqual(px.source, SOURCE_EARTHCAM)
            self.assertEqual(px.stream_url, "")


class StableKeyTests(unittest.TestCase):

    def test_same_bbox_url_shares_key(self) -> None:

        place_a = {
            "name": "A",
            "url": "http://www.cafe52.com/node/3",
            "posn": ["40.74", "-73.90"],
        }
        place_b = {
            "name": "B",
            "url": "http://www.cafe52.com/node/3/",
            "posn": ["40.74", "-73.90"],
        }
        self.assertEqual(stable_listing_key(place_a), stable_listing_key(place_b))


def _scan_jobs() -> list[ListingJob]:

    return [
        ListingJob(id="network", kind="network"),
        ListingJob(id="bbox:world", kind="bbox", params={"zoom": 4}),
    ]


def _extra_place() -> dict:

    return {
        "id": "newcam-refresh-001",
        "name": "New Watch Cam",
        "url": "https://www.earthcam.com/world/test/newwatch/",
        "thumbnail": "https://static.earthcam.com/camshots/256x144/newwatch.jpg",
        "posn": ["41.0", "29.0"],
        "location": "Istanbul, Turkey",
        "city": "Istanbul",
        "country": "Turkey",
    }


class ListingHunterLifecycleTests(unittest.TestCase):

    def test_refresh_interval_default_is_seven_days(self) -> None:

        self.assertEqual(DEFAULT_REFRESH_INTERVAL_S, 7 * 24 * 60 * 60)
        self.assertEqual(DEFAULT_REFRESH_INTERVAL_S, 604800)

    def test_initial_scan_completes_then_watch_mode(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        phases: list[str] = []
        with TemporaryDirectory() as tmp:
            scanner = ListingCatalogScanner(
                ListingCatalogStore(Path(tmp) / "catalog.json"),
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
                refresh_interval_s=60,
            )

            def on_progress(status) -> None:
                phases.append(status.phase)
                if status.phase == HunterPhase.WATCHING:
                    scanner.stop()

            status = scanner.run(watch=True, on_progress=on_progress)
            self.assertIn(HunterPhase.INITIAL_SCAN.value, phases)
            self.assertIn(HunterPhase.INITIAL_SCAN_COMPLETE.value, phases)
            self.assertIn(HunterPhase.WATCHING.value, phases)
            self.assertEqual(status.discovered, 4)
            self.assertEqual(scanner.phase, HunterPhase.STOPPED)
            self.assertTrue(ListingCatalogStore(Path(tmp) / "catalog.json").is_initial_scan_complete())

    def test_refresh_finds_new_camera(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        with TemporaryDirectory() as tmp:
            store = ListingCatalogStore(Path(tmp) / "catalog.json")
            scanner = ListingCatalogScanner(
                store,
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
            )
            scanner.run(watch=False)
            before = store.status().discovered
            network["data"][0]["places"] = list(network["data"][0]["places"]) + [
                _extra_place()
            ]
            status = scanner.refresh_once()
            self.assertEqual(status.discovered, before + 1)
            names = {camera.name for camera in store.all_cameras()}
            self.assertIn("New Watch Cam", names)
            extra = next(c for c in store.all_cameras() if c.name == "New Watch Cam")
            self.assertEqual(
                extra.web_url,
                "https://www.earthcam.com/world/test/newwatch/",
            )
            reloaded = ListingCatalogStore(Path(tmp) / "catalog.json")
            self.assertEqual(reloaded.status().discovered, before + 1)

    def test_refresh_does_not_duplicate_existing_cameras(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        with TemporaryDirectory() as tmp:
            store = ListingCatalogStore(Path(tmp) / "catalog.json")
            scanner = ListingCatalogScanner(
                store,
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
            )
            first = scanner.run(watch=False)
            second = scanner.refresh_once()
            self.assertEqual(second.discovered, first.discovered)
            self.assertEqual(store.new_records, first.new_records)
            keys = [camera.key for camera in store.all_cameras()]
            self.assertEqual(len(keys), len(set(keys)))

    def test_refresh_network_error_keeps_catalog_and_stays_alive(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        live = {"fail": False}

        def network_fetcher():
            if live["fail"]:
                raise RuntimeError("earthcam down")
            return network

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            store = ListingCatalogStore(path)
            scanner = ListingCatalogScanner(
                store,
                jobs=_scan_jobs(),
                network_fetcher=network_fetcher,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
                refresh_interval_s=0.0,
            )
            scanner.run(watch=False)
            live["fail"] = True
            status = scanner.refresh_once()
            self.assertEqual(status.discovered, 4)
            self.assertEqual(scanner.phase, HunterPhase.ERROR)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"]["discovered"], 4)
            live["fail"] = False
            recovered = scanner.refresh_once()
            self.assertEqual(recovered.discovered, 4)
            self.assertNotEqual(scanner.phase, HunterPhase.STOPPED)

    def test_stop_then_restart_continues_incomplete_initial_scan(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            first = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
            )

            def stop_after_first_job(status) -> None:
                if status.processed >= 1:
                    first.stop()

            interrupted = first.run(watch=False, on_progress=stop_after_first_job)
            self.assertLess(interrupted.processed, 2)
            self.assertGreaterEqual(interrupted.discovered, 1)
            self.assertEqual(first.phase, HunterPhase.STOPPED)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload["status"]["discovered"], 1)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

            resumed = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
            )
            phases: list[str] = []

            def capture(status) -> None:
                phases.append(status.phase)

            done = resumed.run(watch=False, on_progress=capture)
            self.assertIn(HunterPhase.INITIAL_SCAN.value, phases)
            self.assertEqual(done.discovered, 4)
            self.assertEqual(done.processed, 2)
            self.assertEqual(resumed.phase, HunterPhase.INITIAL_SCAN_COMPLETE)

    def test_restart_after_complete_initial_scan_starts_watching(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        calls = {"network": 0, "bbox": 0}

        def network_fetcher():
            calls["network"] += 1
            return network

        def bbox_fetcher(_params):
            calls["bbox"] += 1
            return bbox

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            jobs = _scan_jobs()
            ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=jobs,
                network_fetcher=network_fetcher,
                bbox_fetcher=bbox_fetcher,
                request_pause_s=0.0,
            ).run(watch=False)
            self.assertEqual(calls["network"], 1)
            watcher = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=jobs,
                network_fetcher=network_fetcher,
                bbox_fetcher=bbox_fetcher,
                request_pause_s=0.0,
                refresh_interval_s=60,
            )
            phases: list[str] = []

            def on_progress(status) -> None:
                phases.append(status.phase)
                if status.phase == HunterPhase.WATCHING:
                    watcher.stop()

            watcher.run(watch=True, on_progress=on_progress)
            self.assertNotIn(HunterPhase.INITIAL_SCAN.value, phases)
            self.assertIn(HunterPhase.INITIAL_SCAN_COMPLETE.value, phases)
            self.assertIn(HunterPhase.WATCHING.value, phases)
            self.assertEqual(calls["network"], 1)
            self.assertEqual(calls["bbox"], 1)

    def test_watch_refresh_survives_error_until_stop(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        live = {"fail": False}

        def network_fetcher():
            if live["fail"]:
                raise RuntimeError("earthcam down")
            return network

        with TemporaryDirectory() as tmp:
            scanner = ListingCatalogScanner(
                ListingCatalogStore(Path(tmp) / "catalog.json"),
                jobs=_scan_jobs(),
                network_fetcher=network_fetcher,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.0,
                refresh_interval_s=0.0,
            )
            phases: list[str] = []

            def on_progress(status) -> None:
                phases.append(status.phase)
                if status.phase == HunterPhase.INITIAL_SCAN_COMPLETE:
                    live["fail"] = True
                if status.phase == HunterPhase.ERROR:
                    scanner.stop()

            status = scanner.run(watch=True, on_progress=on_progress)
            self.assertIn(HunterPhase.ERROR.value, phases)
            self.assertEqual(status.discovered, 4)
            self.assertEqual(scanner.phase, HunterPhase.STOPPED)

    def test_store_json_survives_stop_from_another_thread(self) -> None:

        network = _load_json(NETWORK_FIXTURE)
        bbox = [_load_json(BBOX_FIXTURE)]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            scanner = ListingCatalogScanner(
                ListingCatalogStore(path),
                jobs=_scan_jobs(),
                network_fetcher=lambda: network,
                bbox_fetcher=lambda _params: bbox,
                request_pause_s=0.05,
                refresh_interval_s=30,
            )
            thread = threading.Thread(
                target=lambda: scanner.run(watch=True),
                name="listing-hunter-test",
            )
            thread.start()
            deadline = time.monotonic() + 2.0
            while thread.is_alive() and time.monotonic() < deadline:
                if scanner.phase in {
                    HunterPhase.WATCHING,
                    HunterPhase.INITIAL_SCAN_COMPLETE,
                }:
                    break
                thread.join(0.02)
            scanner.stop()
            thread.join(2.0)
            self.assertFalse(thread.is_alive())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload["status"]["discovered"], 2)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))
            self.assertEqual(scanner.phase, HunterPhase.STOPPED)


if __name__ == "__main__":
    unittest.main()
