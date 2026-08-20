"""Serial catalog validation scan. Probe is injected; no Qt/HLS here."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from camera_hunter.engine.catalog_validation import (
    ProbeOutcome,
    ValidationRecord,
    ValidationStatus,
    record_from_camera,
)
from camera_hunter.engine.validation_map import write_validated_map
from camera_hunter.engine.validation_store import CatalogValidationStore

logger = logging.getLogger(__name__)

Probe = Callable[[object], ProbeOutcome]
Progress = Callable[[int, int, ValidationRecord], None]


class CatalogValidationScanner:
    """Walk listing cameras one-by-one. A failed camera does not stop the scan."""

    def __init__(
        self,
        cameras: Sequence[object],
        store: CatalogValidationStore,
        probe: Probe,
        *,
        map_path: Path | None = None,
        delay_s: float = 2.0,
        retry_failed: bool = True,
        limit: int = 0,
        stop_flag: Callable[[], bool] | None = None,
    ) -> None:

        self.cameras = list(cameras or [])
        self.store = store
        self.probe = probe
        self.map_path = Path(map_path) if map_path is not None else None
        self.delay_s = max(float(delay_s), 0.0)
        self.retry_failed = bool(retry_failed)
        self.limit = max(int(limit), 0)
        self._stop_flag = stop_flag
        self._stop = False

    def stop(self) -> None:

        self._stop = True

    def _stopped(self) -> bool:

        if self._stop:
            return True
        if self._stop_flag is not None:
            try:
                return bool(self._stop_flag())
            except Exception:
                return False
        return False

    def pending(self) -> list[object]:

        pending: list[object] = []
        for camera in self.cameras:
            camera_id = str(
                getattr(camera, "key", None) or getattr(camera, "id", "") or ""
            ).strip()
            if not camera_id:
                continue
            if self.store.should_skip(camera_id, retry_failed=self.retry_failed):
                continue
            pending.append(camera)
        return pending

    def run(self, on_progress: Progress | None = None) -> list[ValidationRecord]:

        queue = self.pending()
        if self.limit:
            queue = queue[: self.limit]
        total = len(self.cameras)
        processed_now = 0
        for camera in queue:
            if self._stopped():
                break
            camera_id = str(
                getattr(camera, "key", None) or getattr(camera, "id", "") or ""
            ).strip()
            try:
                outcome = self.probe(camera)
            except Exception as exc:
                logger.exception("Catalog validation probe failed for %s", camera_id)
                outcome = ProbeOutcome(error=str(exc) or exc.__class__.__name__)
            record = record_from_camera(camera, outcome)
            if not record.camera_id:
                record.camera_id = camera_id or "unknown"
            self.store.put(record)
            processed_now += 1
            if on_progress is not None:
                on_progress(processed_now, total, record)
            if self.delay_s and not self._stopped():
                time.sleep(self.delay_s)
        if self.map_path is not None:
            write_validated_map(self.map_path, self.store.all_records())
        return self.store.all_records()
