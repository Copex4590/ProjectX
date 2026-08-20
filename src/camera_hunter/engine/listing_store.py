"""Persistent Hunter listing-catalog store (JSON). Resume-safe."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from camera_hunter.engine.listing_catalog import ListingCamera

STORE_VERSION = 1


def _utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()


@dataclass
class ListingJob:
    id: str
    kind: str
    state: str = "queued"  # queued | processed | failed
    params: dict = field(default_factory=dict)
    error: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "params": dict(self.params),
            "error": self.error,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ListingJob:

        return cls(
            id=str(data.get("id") or ""),
            kind=str(data.get("kind") or ""),
            state=str(data.get("state") or "queued"),
            params=dict(data.get("params") or {}),
            error=str(data.get("error") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class ListingScanStatus:
    discovered: int = 0
    queued: int = 0
    processed: int = 0
    failed: int = 0
    total: int = 0
    new_records: int = 0
    phase: str = ""

    def to_dict(self) -> dict:

        return {
            "discovered": self.discovered,
            "queued": self.queued,
            "processed": self.processed,
            "failed": self.failed,
            "total": self.total,
            "new_records": self.new_records,
            "phase": self.phase,
        }


class ListingCatalogStore:
    """On-disk cameras + job queue. Writes after every successful change."""

    def __init__(self, path: Path):

        self.path = Path(path)
        self._lock = RLock()
        self.jobs: dict[str, ListingJob] = {}
        self.cameras: dict[str, ListingCamera] = {}
        self.new_records = 0
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
        for item in payload.get("jobs") or []:
            if not isinstance(item, dict):
                continue
            job = ListingJob.from_dict(item)
            if job.id:
                self.jobs[job.id] = job
        for item in payload.get("cameras") or []:
            if not isinstance(item, dict):
                continue
            camera = ListingCamera.from_dict(item)
            if camera is not None:
                self.cameras[camera.key] = camera

    def save(self) -> None:

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": STORE_VERSION,
            "updated_at": _utc_now(),
            "status": self.status().to_dict(),
            "jobs": [job.to_dict() for job in self.jobs.values()],
            "cameras": [camera.to_dict() for camera in self.cameras.values()],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle)
                handle.write("\n")
                handle.flush()
            tmp.replace(self.path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def ensure_jobs(self, jobs: list[ListingJob]) -> None:

        with self._lock:
            changed = False
            for job in jobs:
                existing = self.jobs.get(job.id)
                if existing is None:
                    self.jobs[job.id] = job
                    changed = True
                    continue
                if existing.state == "failed":
                    existing.state = "queued"
                    existing.error = ""
                    existing.updated_at = _utc_now()
                    changed = True
            if changed:
                self.save()

    def pending_jobs(self) -> list[ListingJob]:

        with self._lock:
            return [
                job
                for job in self.jobs.values()
                if job.state in {"queued", "failed"}
            ]

    def mark_processed(self, job_id: str) -> None:

        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                return
            job.state = "processed"
            job.error = ""
            job.updated_at = _utc_now()
            self.save()

    def mark_failed(self, job_id: str, error: str) -> None:

        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                return
            job.state = "failed"
            job.error = str(error or "error")
            job.updated_at = _utc_now()
            self.save()

    def add_cameras(self, cameras: list[ListingCamera]) -> int:
        """Insert unseen keys only. Already discovered cameras are skipped."""

        added = 0
        with self._lock:
            seen_urls = {
                camera.web_url.strip().lower()
                for camera in self.cameras.values()
                if camera.web_url.strip()
            }
            for camera in cameras:
                if camera.key in self.cameras:
                    continue
                url_key = camera.web_url.strip().lower()
                if url_key and url_key in seen_urls:
                    continue
                self.cameras[camera.key] = camera
                if url_key:
                    seen_urls.add(url_key)
                added += 1
                self.new_records += 1
                self.save()
        return added

    def is_initial_scan_complete(self) -> bool:
        """True when every known initial job is processed (none queued/failed)."""

        with self._lock:
            if not self.jobs:
                return False
            return all(job.state == "processed" for job in self.jobs.values())

    def all_cameras(self) -> list[ListingCamera]:

        with self._lock:
            return list(self.cameras.values())

    def status(self) -> ListingScanStatus:

        with self._lock:
            return self._status_unlocked()

    def _status_unlocked(self) -> ListingScanStatus:

        queued = processed = failed = 0
        for job in self.jobs.values():
            if job.state == "processed":
                processed += 1
            elif job.state == "failed":
                failed += 1
            else:
                queued += 1
        return ListingScanStatus(
            discovered=len(self.cameras),
            queued=queued,
            processed=processed,
            failed=failed,
            total=len(self.jobs),
            new_records=self.new_records,
        )
