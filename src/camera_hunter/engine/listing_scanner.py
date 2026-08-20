"""Hunter listing-catalog scanner: network + bbox sweep, then watch/refresh.

Separate from DiscoveryEngine.discover() / MAP_SEARCH click-to-LIVE.
No HLS, tokens, player, or LIVE promotion.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import Callable

from camera_hunter.engine.listing_catalog import (
    SOURCE_BBOX,
    SOURCE_NETWORK,
    WORLD_BBOX,
    bbox_from_corners,
    cameras_from_payload,
    fetch_bbox_payload,
    fetch_network_payload,
)
from camera_hunter.engine.listing_store import (
    ListingCatalogStore,
    ListingJob,
    ListingScanStatus,
)

logger = logging.getLogger(__name__)

NetworkFetcher = Callable[[], object]
BboxFetcher = Callable[[dict], object]
ProgressCallback = Callable[[ListingScanStatus], None]

DEFAULT_REFRESH_INTERVAL_S = 7 * 24 * 60 * 60
DEFAULT_FAILED_RETRY_PAUSE_S = 5.0


class HunterPhase(str, Enum):
    INITIAL_SCAN = "INITIAL_SCAN"
    INITIAL_SCAN_COMPLETE = "INITIAL_SCAN_COMPLETE"
    WATCHING = "WATCHING"
    REFRESHING = "REFRESHING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


def default_listing_jobs(*, include_grid: bool = True) -> list[ListingJob]:
    """Full EarthCam coverage: in-network dump, world bbox, then coarse tiles."""

    jobs = [
        ListingJob(id="network", kind="network"),
        ListingJob(id="bbox:world", kind="bbox", params=dict(WORLD_BBOX)),
    ]
    if not include_grid:
        return jobs
    zoom = 5
    lat = -60.0
    while lat < 80.0:
        north = min(lat + 40.0, 85.0)
        south = lat
        lon = -180.0
        while lon < 180.0:
            west = lon
            east = min(lon + 60.0, 180.0)
            job_id = f"bbox:{int(south)}:{int(west)}:{int(north)}:{int(east)}:{zoom}"
            jobs.append(
                ListingJob(
                    id=job_id,
                    kind="bbox",
                    params=bbox_from_corners(north, west, south, east, zoom=zoom),
                )
            )
            lon += 60.0
        lat += 40.0
    return jobs


class ListingCatalogScanner:
    """Resume-safe initial listing scan, then continuous network/world refresh."""

    def __init__(
        self,
        store: ListingCatalogStore,
        *,
        jobs: list[ListingJob] | None = None,
        network_fetcher: NetworkFetcher | None = None,
        bbox_fetcher: BboxFetcher | None = None,
        request_pause_s: float = 0.15,
        refresh_interval_s: float = DEFAULT_REFRESH_INTERVAL_S,
        failed_retry_pause_s: float | None = None,
    ):

        self.store = store
        self._jobs = jobs if jobs is not None else default_listing_jobs()
        self._network_fetcher = network_fetcher or fetch_network_payload
        self._bbox_fetcher = bbox_fetcher or fetch_bbox_payload
        self._request_pause_s = max(0.0, float(request_pause_s))
        self._refresh_interval_s = max(0.0, float(refresh_interval_s))
        if failed_retry_pause_s is None:
            self._failed_retry_pause_s = (
                DEFAULT_FAILED_RETRY_PAUSE_S if self._request_pause_s else 0.0
            )
        else:
            self._failed_retry_pause_s = max(0.0, float(failed_retry_pause_s))
        self._stop = False
        self._stop_event = threading.Event()
        self.phase = HunterPhase.STOPPED
        self.store.ensure_jobs(self._jobs)

    def status(self) -> ListingScanStatus:

        snapshot = self.store.status()
        snapshot.phase = self.phase.value
        return snapshot

    def stop(self) -> None:

        self._stop = True
        self._stop_event.set()

    def run(
        self,
        on_progress: ProgressCallback | None = None,
        *,
        watch: bool = True,
    ) -> ListingScanStatus:
        """Initial scan remaining jobs, then watch/refresh until stop().

        ``watch=False`` returns after the first complete (or interrupted) scan
        and is for tests / one-shot catch-up. Production uses the default.
        """

        self._stop = False
        self._stop_event.clear()
        self.store.ensure_jobs(self._jobs)
        if not self.store.is_initial_scan_complete():
            self._run_initial_scan(on_progress)
        if self._stop:
            self._set_phase(HunterPhase.STOPPED, on_progress)
            return self.status()
        if not self.store.is_initial_scan_complete():
            self._set_phase(HunterPhase.STOPPED, on_progress)
            return self.status()

        self._set_phase(HunterPhase.INITIAL_SCAN_COMPLETE, on_progress)
        logger.info(
            "INITIAL SCAN COMPLETE discovered=%s processed=%s",
            self.store.status().discovered,
            self.store.status().processed,
        )
        if not watch:
            return self.status()

        self._set_phase(HunterPhase.WATCHING, on_progress)
        logger.info(
            "WATCH / REFRESH interval=%ss discovered=%s",
            self._refresh_interval_s,
            self.store.status().discovered,
        )
        while not self._stop:
            self._interruptible_sleep(self._refresh_interval_s)
            if self._stop:
                break
            self.refresh_once(on_progress)
            if not self._stop:
                self._set_phase(HunterPhase.WATCHING, on_progress)
        self._set_phase(HunterPhase.STOPPED, on_progress)
        return self.status()

    def refresh_once(
        self,
        on_progress: ProgressCallback | None = None,
    ) -> ListingScanStatus:
        """Check network + world bbox for new cameras. Does not replay grid jobs."""

        self._set_phase(HunterPhase.REFRESHING, on_progress)
        logger.info("listing catalog refresh start discovered=%s", self.store.status().discovered)
        errors = 0
        errors += 0 if self._refresh_network() else 1
        if self._stop:
            return self.status()
        errors += 0 if self._refresh_world_bbox() else 1
        if errors:
            self._set_phase(HunterPhase.ERROR, on_progress)
            logger.warning(
                "listing catalog refresh had %s error(s); catalog kept, will retry",
                errors,
            )
        else:
            logger.info(
                "listing catalog refresh done discovered=%s new_records=%s",
                self.store.status().discovered,
                self.store.new_records,
            )
        return self.status()

    def _run_initial_scan(self, on_progress: ProgressCallback | None) -> None:

        self._set_phase(HunterPhase.INITIAL_SCAN, on_progress)
        logger.info("INITIAL SCAN start")
        while not self._stop:
            pending = self.store.pending_jobs()
            if not pending:
                break
            self._process_pending(pending, on_progress)
            if self._stop:
                break
            self.store.ensure_jobs(self._jobs)
            pending = self.store.pending_jobs()
            if not pending:
                break
            if self._failed_retry_pause_s:
                self._interruptible_sleep(self._failed_retry_pause_s)

    def _process_pending(
        self,
        pending: list[ListingJob],
        on_progress: ProgressCallback | None,
    ) -> None:

        for index, job in enumerate(pending):
            if self._stop:
                break
            try:
                cameras = self._fetch_job(job)
                added = self.store.add_cameras(cameras)
                self.store.mark_processed(job.id)
                logger.info(
                    "listing catalog job %s: got=%s new=%s discovered=%s",
                    job.id,
                    len(cameras),
                    added,
                    self.store.status().discovered,
                )
            except Exception as exc:
                logger.exception("listing catalog job failed: %s", job.id)
                self.store.mark_failed(job.id, f"{type(exc).__name__}: {exc}")
            self._emit_progress(on_progress)
            if self._request_pause_s and index + 1 < len(pending) and not self._stop:
                self._interruptible_sleep(self._request_pause_s)

    def _refresh_network(self) -> bool:

        try:
            payload = self._network_fetcher()
            cameras = cameras_from_payload(payload, source=SOURCE_NETWORK)
            added = self.store.add_cameras(cameras)
            logger.info("listing catalog refresh network new=%s", added)
            return True
        except Exception:
            logger.exception("listing catalog refresh network failed")
            return False

    def _refresh_world_bbox(self) -> bool:

        try:
            payload = self._bbox_fetcher(dict(WORLD_BBOX))
            cameras = cameras_from_payload(payload, source=SOURCE_BBOX)
            added = self.store.add_cameras(cameras)
            logger.info("listing catalog refresh world bbox new=%s", added)
            return True
        except Exception:
            logger.exception("listing catalog refresh world bbox failed")
            return False

    def _fetch_job(self, job: ListingJob) -> list:
        if job.kind == "network":
            payload = self._network_fetcher()
            return cameras_from_payload(payload, source=SOURCE_NETWORK)
        if job.kind == "bbox":
            payload = self._bbox_fetcher(dict(job.params))
            return cameras_from_payload(payload, source=SOURCE_BBOX)
        raise ValueError(f"Unknown listing catalog job kind: {job.kind}")

    def _set_phase(
        self,
        phase: HunterPhase,
        on_progress: ProgressCallback | None = None,
    ) -> None:

        self.phase = phase
        self._emit_progress(on_progress)

    def _emit_progress(self, on_progress: ProgressCallback | None) -> None:

        if on_progress is None:
            return
        on_progress(self.status())

    def _interruptible_sleep(self, seconds: float) -> None:

        if seconds <= 0 or self._stop:
            return
        self._stop_event.wait(timeout=seconds)
