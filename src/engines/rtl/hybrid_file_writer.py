# ============================================================================
# Project X
# HybridEngine background filesystem writer (SAVE-203)
# ============================================================================

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any

logger = logging.getLogger(__name__)

_STOP = object()

CSV_HEADER = (
    "Időpont;"
    "Távolság;"
    "Haladási irány;"
    "Sebesség;"
    "Célállomás + ETA;"
    "Hívójel;"
    "Merülés;"
    "MMSI;"
    "Hajótípus;"
    "Hossz;"
    "Szélesség\n"
)


@dataclass
class _RadarExportState:
    ships: dict[str, dict[str, Any]] = field(default_factory=dict)
    dirty: set[str] = field(default_factory=set)
    last_full_kml_at: float = 0.0
    base_dir: Path | None = None


class HybridFileWriter:
    """All HybridEngine disk IO runs on this worker — never on AIS/RTL threads."""

    FULL_KML_INTERVAL_S = 30.0

    def __init__(self) -> None:

        self._queue: Queue[Any] = Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop_requested = False
        self._radar = _RadarExportState()
        self._pending_cache: tuple[Path, dict[str, str]] | None = None

    def start(self) -> None:

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="HybridFileWriter",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:

        self._stop_requested = True
        self._queue.put(_STOP)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.warning("HybridFileWriter did not stop within %.1fs", timeout)

    def enqueue(self, job: dict[str, Any]) -> None:

        if self._stop_requested:
            return
        self.start()
        self._queue.put(job)

    def _worker_loop(self) -> None:

        while True:
            try:
                job = self._queue.get(timeout=0.25)
            except Empty:
                self._flush_pending_cache()
                if self._stop_requested:
                    return
                continue

            try:
                if job is _STOP:
                    self._flush_pending_cache()
                    self._flush_radar(force_full_kml=True)
                    return
                self._handle_job(job)
            except Exception:
                logger.exception("HybridFileWriter job failed: %s", job)
            finally:
                if job is not _STOP:
                    self._queue.task_done()

    def _handle_job(self, job: dict[str, Any]) -> None:

        kind = job.get("kind")

        if kind == "ensure_folder":
            self._ensure_folder(Path(job["ship_dir"]))
        elif kind == "append_csv":
            ship_dir = Path(job["ship_dir"])
            self._ensure_folder(ship_dir)
            with (ship_dir / "adatlap.csv").open("a", encoding="utf-8") as handle:
                handle.write(job["row"])
        elif kind == "append_deli":
            path = Path(job["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(job["row"])
        elif kind == "write_hajo":
            path = Path(job["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(job["text"], encoding="utf-8")
        elif kind == "save_cache":
            self._pending_cache = (Path(job["path"]), dict(job["ship_names"]))
        elif kind == "radar_upsert":
            self._radar.base_dir = Path(job["base_dir"])
            mmsi = str(job["mmsi"])
            self._radar.ships[mmsi] = job["payload"]
            self._radar.dirty.add(mmsi)
        elif kind == "radar_remove":
            mmsi = str(job["mmsi"])
            self._radar.ships.pop(mmsi, None)
            self._radar.dirty.add(mmsi)
        elif kind == "radar_flush":
            self._radar.base_dir = Path(job["base_dir"])
            self._flush_radar(force_full_kml=bool(job.get("force_full_kml")))
        else:
            logger.warning("Unknown HybridFileWriter job kind: %s", kind)

    def _ensure_folder(self, ship_dir: Path) -> None:

        created = not ship_dir.exists()
        ship_dir.mkdir(parents=True, exist_ok=True)
        csv_file = ship_dir / "adatlap.csv"
        if not csv_file.exists():
            csv_file.write_text(CSV_HEADER, encoding="utf-8")
            if created:
                logger.info("Created ship folder: %s", ship_dir.name)

    def _flush_pending_cache(self) -> None:

        pending = self._pending_cache
        if pending is None:
            return
        self._pending_cache = None
        path, ship_names = pending
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(ship_names, handle, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            logger.exception("Failed to save ship cache to %s", path)

    def _flush_radar(self, *, force_full_kml: bool = False) -> None:

        base_dir = self._radar.base_dir
        if base_dir is None:
            return

        dirty = set(self._radar.dirty)
        if not dirty and not force_full_kml:
            return

        self._radar.dirty.clear()
        base_dir.mkdir(parents=True, exist_ok=True)

        # Incremental delta for external consumers.
        delta = [
            self._radar.ships[mmsi]
            for mmsi in dirty
            if mmsi in self._radar.ships
        ]
        removed = [mmsi for mmsi in dirty if mmsi not in self._radar.ships]
        try:
            with (base_dir / "radar_delta.json").open("w", encoding="utf-8") as handle:
                json.dump(
                    {"upsert": delta, "remove": removed, "ts": datetime.now().isoformat(timespec="seconds")},
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
        except Exception:
            logger.exception("Failed to write radar_delta.json")

        # Compact full snapshot (no pretty-indent) — only ships still present.
        snapshot = list(self._radar.ships.values())
        try:
            with (base_dir / "radar.json").open("w", encoding="utf-8") as handle:
                json.dump(snapshot, handle, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            logger.exception("Failed to write radar.json")

        # Compact top-10 text board.
        try:
            ranked = sorted(snapshot, key=lambda item: float(item.get("distance", 0)))[:10]
            lines = ["RADAR", ""]
            for ship in ranked:
                lines.append(
                    f"{str(ship.get('name', ''))[:20]:20} "
                    f"{float(ship.get('distance', 0)):.2f} km "
                    f"{ship.get('direction', '')}"
                )
            (base_dir / "radar.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            logger.exception("Failed to write radar.txt")

        now = time_monotonic()
        if force_full_kml or (now - self._radar.last_full_kml_at) >= self.FULL_KML_INTERVAL_S:
            self._radar.last_full_kml_at = now
            self._write_full_kml(base_dir, snapshot)
        elif dirty:
            self._write_delta_kml(base_dir, delta)

    def _write_full_kml(self, base_dir: Path, snapshot: list[dict[str, Any]]) -> None:

        try:
            parts = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
            ]
            for ship in snapshot:
                parts.append(self._kml_placemark(ship))
            parts.append("</Document></kml>")
            (base_dir / "radar.kml").write_text("\n".join(parts), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write radar.kml")

    def _write_delta_kml(self, base_dir: Path, delta: list[dict[str, Any]]) -> None:

        if not delta:
            return
        try:
            parts = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
            ]
            for ship in delta:
                parts.append(self._kml_placemark(ship))
            parts.append("</Document></kml>")
            (base_dir / "radar_delta.kml").write_text("\n".join(parts), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write radar_delta.kml")

    @staticmethod
    def _kml_placemark(ship: dict[str, Any]) -> str:

        return (
            f"<Placemark><name>{ship.get('name', '')}</name>"
            f"<description>MMSI: {ship.get('mmsi', '')}"
            f"&#10;Távolság: {ship.get('distance', '')} km"
            f"&#10;Irány: {ship.get('direction', '')}"
            f"&#10;Forrás: {ship.get('source', '')}</description>"
            f"<Point><coordinates>{ship.get('lon', 0)},{ship.get('lat', 0)},0"
            f"</coordinates></Point></Placemark>"
        )


def time_monotonic() -> float:

    import time

    return time.monotonic()


hybrid_file_writer = HybridFileWriter()
