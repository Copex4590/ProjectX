"""Persistent catalog-validation results. Does not touch the listing catalog."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from camera_hunter.engine.catalog_validation import (
    ValidationRecord,
    ValidationStatus,
    ValidationSummary,
    _utc_now,
)

STORE_VERSION = 1


class CatalogValidationStore:
    """Resume-safe JSON of per-camera validation records."""

    def __init__(self, path: Path):

        self.path = Path(path)
        self._lock = RLock()
        self.records: dict[str, ValidationRecord] = {}
        self._load()

    def _load(self) -> None:

        if not self.path.exists():
            return
        try:
            with self.path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        for item in payload.get("cameras") or []:
            if not isinstance(item, dict):
                continue
            record = ValidationRecord.from_dict(item)
            if record.camera_id:
                self.records[record.camera_id] = record

    def save(self) -> None:

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STORE_VERSION,
            "updated_at": _utc_now(),
            "status": self.summary().to_dict(),
            "cameras": [record.to_dict() for record in self.records.values()],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
                handle.flush()
            tmp.replace(self.path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def put(self, record: ValidationRecord) -> None:

        with self._lock:
            self.records[record.camera_id] = record
            self.save()

    def get(self, camera_id: str) -> ValidationRecord | None:

        with self._lock:
            return self.records.get(str(camera_id or "").strip())

    def all_records(self) -> list[ValidationRecord]:

        with self._lock:
            return list(self.records.values())

    def validated(self) -> list[ValidationRecord]:

        with self._lock:
            return [
                record
                for record in self.records.values()
                if record.status == ValidationStatus.VALIDATED
            ]

    def should_skip(self, camera_id: str, *, retry_failed: bool) -> bool:

        record = self.get(camera_id)
        if record is None:
            return False
        if record.status == ValidationStatus.VALIDATED:
            return True
        return not retry_failed

    def summary(self, *, total: int | None = None) -> ValidationSummary:

        with self._lock:
            counts: dict[str, int] = {}
            for record in self.records.values():
                key = record.status.value
                counts[key] = counts.get(key, 0) + 1
            processed = len(self.records)
            catalog_total = processed if total is None else int(total)
            return ValidationSummary(
                total=catalog_total,
                processed=processed,
                validated=counts.get(ValidationStatus.VALIDATED.value, 0),
                failed=counts.get(ValidationStatus.FAILED.value, 0),
                no_stream_found=counts.get(ValidationStatus.NO_STREAM_FOUND.value, 0),
                playback_failed=counts.get(
                    ValidationStatus.PLAYBACK_FAILED.value, 0
                ),
                timeout=counts.get(ValidationStatus.TIMEOUT.value, 0),
                error=counts.get(ValidationStatus.ERROR.value, 0),
                pending=max(catalog_total - processed, 0),
                counts=counts,
            )

    def clear(self) -> None:

        with self._lock:
            self.records.clear()
            self.save()
