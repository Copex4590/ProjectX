# ============================================================================
# Project X
# Consume Hunter listing-catalog store (no EarthCam HTTP here)
# ============================================================================
"""Load cameras persisted by camera_hunter.engine.listing_scanner.

Project X does not fetch mapsearch APIs itself. Pack/user cameras stay in
camera_manager. Marker clicks use Camera.web_url with the existing
HunterLiveSession.discover() camera-page path.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.paths import runtime_data_dir
from models.camera import SOURCE_EARTHCAM, Camera

logger = logging.getLogger(__name__)

_FALSEY = {"0", "false", "no", "off"}


def listing_catalog_path() -> Path:

    override = os.environ.get("PROJECTX_HUNTER_LISTING_CATALOG", "").strip()
    if override:
        return Path(override)
    path = runtime_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path / "hunter_listing_catalog.json"


def listing_scan_disabled() -> bool:

    flag = os.environ.get("PROJECTX_HUNTER_LISTING_SCAN", "").strip().lower()
    return flag in _FALSEY


def listing_camera_to_px(record) -> Camera:
    """Hunter ListingCamera → PX Camera. No stream URL / HLS inventing."""

    location = str(getattr(record, "location", "") or "")
    return Camera(
        id=str(getattr(record, "key", "") or "").strip(),
        name=str(getattr(record, "name", "") or "").strip() or "EarthCam",
        country=str(getattr(record, "country", "") or "").strip(),
        lat=float(getattr(record, "lat", 0.0) or 0.0),
        lon=float(getattr(record, "lon", 0.0) or 0.0),
        visibility_radius_km=0.0,
        enabled=True,
        description=location,
        location=location,
        provider_type="",
        stream_url="",
        snapshot_url=str(getattr(record, "thumbnail_url", "") or "").strip(),
        web_url=str(getattr(record, "web_url", "") or "").strip(),
        provider_name="EarthCam",
        city=str(getattr(record, "city", "") or "").strip(),
        tags=("earthcam", "mapsearch", str(getattr(record, "source", "") or "")),
        source=SOURCE_EARTHCAM,
    )


def load_listing_cameras(path: Path | None = None) -> list[Camera]:
    """Read the Hunter store. Empty list if the scan has not run yet."""

    from camera_hunter.engine.listing_store import ListingCatalogStore

    store = ListingCatalogStore(path or listing_catalog_path())
    cameras = []
    for record in store.all_cameras():
        camera = listing_camera_to_px(record)
        if not camera.id:
            continue
        cameras.append(camera)
    return cameras


class HunterListingCatalogService(QObject):
    """Background Hunter listing scan; PX only reloads the persisted store."""

    status_changed = Signal(object)
    cameras_updated = Signal()

    def __init__(self, parent: QObject | None = None):

        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._scanner = None

    @property
    def is_running(self) -> bool:

        thread = self._thread
        return bool(thread is not None and thread.is_alive())

    def start(self) -> bool:

        if listing_scan_disabled():
            logger.info("Hunter listing catalog scan disabled")
            return False
        if self.is_running:
            return False

        from camera_hunter.engine.listing_scanner import ListingCatalogScanner
        from camera_hunter.engine.listing_store import ListingCatalogStore

        store = ListingCatalogStore(listing_catalog_path())
        self._scanner = ListingCatalogScanner(store)
        self.status_changed.emit(store.status())
        thread = threading.Thread(
            target=self._run,
            name="hunter-listing-catalog",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        return True

    def _run(self) -> None:

        scanner = self._scanner
        if scanner is None:
            return
        try:
            status = scanner.run(on_progress=self._on_progress)
            self._on_progress(status)
            logger.info(
                "Hunter listing catalog scan done discovered=%s new=%s "
                "processed=%s failed=%s",
                status.discovered,
                status.new_records,
                status.processed,
                status.failed,
            )
        except Exception:
            logger.exception("Hunter listing catalog scan failed")
            try:
                self.status_changed.emit(scanner.status())
            except Exception:
                pass

    def _on_progress(self, status) -> None:

        self.status_changed.emit(status)
        self.cameras_updated.emit()


hunter_listing_catalog_service = HunterListingCatalogService()
