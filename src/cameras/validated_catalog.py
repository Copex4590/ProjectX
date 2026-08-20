# ============================================================================
# Project X
# VALIDATED Hunter cameras on the map (read-only JSON)
# ============================================================================
"""Map layer sourced from hunter_catalog_validation.json.

Project X never starts catalog_validator. The overnight scanner is a separate
process and writes the JSON atomically. This module only reads VALIDATED
records and supplies marker id/lat/lon plus web_url for the existing
selectCamera → HunterLiveSession → HlsPlayer click path.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot

from app.paths import runtime_data_dir
from camera_hunter.engine.catalog_validation import ValidationRecord, ValidationStatus
from camera_hunter.engine.validation_preview import (
    load_validated_records,
    records_by_id,
    web_url_for_validated_camera,
)

logger = logging.getLogger(__name__)

STORE_FILENAME = "hunter_catalog_validation.json"
DEFAULT_REFRESH_MS = 30_000


def validation_json_path() -> Path:
    """Same file the catalog validator writes. PX does not create or write it."""

    override = os.environ.get("PROJECTX_HUNTER_VALIDATION", "").strip()
    if override:
        return Path(override)
    return runtime_data_dir() / "cache" / STORE_FILENAME


def validated_camera_markers(records) -> list[dict]:
    """Map payloads: id/lat/lon only. No name, location, or popup text."""

    markers: list[dict] = []
    seen: set[str] = set()
    for record in records or []:
        status = getattr(record, "status", None)
        status_text = str(getattr(status, "value", status) or "")
        if status_text != ValidationStatus.VALIDATED.value:
            continue
        camera_id = str(
            getattr(record, "camera_id", None) or getattr(record, "id", "") or ""
        ).strip()
        if not camera_id or camera_id in seen:
            continue
        try:
            lat = float(getattr(record, "lat", 0.0) or 0.0)
            lon = float(getattr(record, "lon", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(lat) or not math.isfinite(lon):
            continue
        if lat == 0.0 and lon == 0.0:
            continue
        if abs(lat) > 90.0 or abs(lon) > 180.0:
            continue
        seen.add(camera_id)
        markers.append({"id": camera_id, "lat": lat, "lon": lon})
    return markers


def should_publish_markers(
    fingerprint: tuple, previous: tuple, *, published: bool
) -> bool:
    """First successful read always publishes; later reads only if the layer changed."""

    if not published:
        return True
    return fingerprint != previous


def load_validated_layer(path: Path | None = None) -> tuple[list[dict], dict[str, ValidationRecord]]:
    """Read VALIDATED cameras. Never opens the JSON for writing."""

    target = Path(path) if path is not None else validation_json_path()
    if not target.exists():
        return [], {}
    records = load_validated_records(target)
    markers = validated_camera_markers(records)
    index = records_by_id(records)
    return markers, index


class ValidatedCatalogService(QObject):
    """Periodic read-only refresh of VALIDATED map cameras.

    Does not start, stop, or configure catalog_validator.
    """

    cameras_updated = Signal(object)
    _layer_ready = Signal(object)

    def __init__(self, parent: QObject | None = None, *, path: Path | None = None) -> None:

        super().__init__(parent)
        self._path = Path(path) if path is not None else validation_json_path()
        self._timer = QTimer(self)
        self._timer.setInterval(DEFAULT_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)
        self._busy = False
        self._lock = threading.Lock()
        self._markers: list[dict] = []
        self._index: dict[str, ValidationRecord] = {}
        self._fingerprint: tuple = ()
        self._loaded = False
        self._published = False
        # Worker emit → GUI thread, same pattern as MapWidget ship flushes.
        self._layer_ready.connect(
            self._publish_on_gui,
            Qt.ConnectionType.QueuedConnection,
        )

    @property
    def path(self) -> Path:

        return self._path

    def current_markers(self) -> list[dict]:

        with self._lock:
            return list(self._markers)

    @property
    def has_loaded(self) -> bool:

        with self._lock:
            return bool(self._loaded)

    def web_url_for(self, camera_id: str) -> str:

        with self._lock:
            return web_url_for_validated_camera(self._index, camera_id)

    def start(self, interval_ms: int = DEFAULT_REFRESH_MS) -> None:

        self._timer.setInterval(max(int(interval_ms), 1000))
        if not self._timer.isActive():
            self._timer.start()
        self.refresh()

    def stop(self) -> None:

        self._timer.stop()

    def refresh(self) -> None:
        """Re-read JSON on a worker thread so the GUI stays responsive."""

        if self._busy:
            return
        self._busy = True
        thread = threading.Thread(
            target=self._read_and_publish,
            name="validated-catalog-refresh",
            daemon=True,
        )
        thread.start()

    @Slot(object)
    def _publish_on_gui(self, markers) -> None:

        self.cameras_updated.emit(list(markers or []))

    def _read_and_publish(self) -> None:

        try:
            try:
                markers, index = load_validated_layer(self._path)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Validated camera JSON unreadable (%s); keeping previous layer",
                    exc,
                )
                return
            except Exception:
                logger.exception("Failed reading validated camera layer")
                return

            fingerprint = tuple(
                (item["id"], item["lat"], item["lon"]) for item in markers
            )
            with self._lock:
                self._markers = markers
                self._index = index
                self._loaded = True
                publish = should_publish_markers(
                    fingerprint,
                    self._fingerprint,
                    published=self._published,
                )
                self._fingerprint = fingerprint
                if publish:
                    self._published = True
            if publish:
                self._layer_ready.emit(markers)
        finally:
            self._busy = False
