# ============================================================================
# Project X
# Vessel Timeline Playback Engine (SAVE-214)
# ============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import RLock

from PySide6.QtCore import QObject, QTimer, Signal

from events import eventbus
from models.ship import Ship
from timeline import EVENT_POSITION_UPDATE
from timeline.timeline_manager import timeline_manager
from timeline.timeline_record import TimelineRecord

logger = logging.getLogger(__name__)

EVENT_PLAYBACK_MODE = "vessel.playback.mode"
EVENT_PLAYBACK_POSITION = "vessel.playback.position"

PLAYBACK_RATES = (1, 2, 5, 10)
_BASE_TICK_MS = 500
_MAX_SAMPLES = 5000


class PlaybackMode(str, Enum):

    LIVE = "live"
    PAUSED = "paused"
    PLAYING = "playing"


@dataclass(frozen=True)
class PlaybackSample:
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float | None = None
    course: float | None = None
    heading: float | None = None
    source: str = ""


def _valid_coord(lat: float | None, lon: float | None) -> bool:

    if lat is None or lon is None:
        return False
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return False
    if lat_f == 0.0 and lon_f == 0.0:
        return False
    return -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0


class VesselPlaybackEngine(QObject):
    """Per-selected-vessel chronological trail storage and playback."""

    mode_changed = Signal(str)
    samples_changed = Signal()
    index_changed = Signal(int, int)
    position_changed = Signal(object)
    rate_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._lock = RLock()
        self._mmsi: int | None = None
        self._samples: list[PlaybackSample] = []
        self._index = 0
        self._mode = PlaybackMode.LIVE
        self._rate = 1

        self._timer = QTimer(self)
        self._timer.setInterval(_BASE_TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    @property
    def mmsi(self) -> int | None:

        return self._mmsi

    @property
    def mode(self) -> PlaybackMode:

        return self._mode

    @property
    def rate(self) -> int:

        return self._rate

    @property
    def index(self) -> int:

        return self._index

    @property
    def sample_count(self) -> int:

        with self._lock:
            return len(self._samples)

    def is_live(self) -> bool:

        return self._mode == PlaybackMode.LIVE

    def is_playback_active(self) -> bool:

        return self._mode in (PlaybackMode.PAUSED, PlaybackMode.PLAYING)

    def samples(self) -> list[PlaybackSample]:

        with self._lock:
            return list(self._samples)

    def current_sample(self) -> PlaybackSample | None:

        with self._lock:
            if not self._samples:
                return None
            index = max(0, min(self._index, len(self._samples) - 1))
            return self._samples[index]

    def trail_points(self) -> list[tuple[float, float]]:

        with self._lock:
            return [(sample.latitude, sample.longitude) for sample in self._samples]

    def clear(self) -> None:

        self._timer.stop()
        with self._lock:
            self._mmsi = None
            self._samples = []
            self._index = 0
            self._mode = PlaybackMode.LIVE
        self.samples_changed.emit()
        self.index_changed.emit(0, 0)
        self.mode_changed.emit(PlaybackMode.LIVE.value)
        self.position_changed.emit(None)
        eventbus.publish(EVENT_PLAYBACK_MODE, mode=PlaybackMode.LIVE.value, mmsi=None)

    def bind_vessel(self, mmsi: int | None, ship: Ship | None = None) -> None:

        if mmsi is None:
            self.clear()
            return

        try:
            resolved = int(mmsi)
        except (TypeError, ValueError):
            self.clear()
            return

        self._timer.stop()
        with self._lock:
            self._mmsi = resolved
            self._samples = self._build_samples(resolved, ship)
            self._index = max(0, len(self._samples) - 1)
            self._mode = PlaybackMode.LIVE

        self.samples_changed.emit()
        self.index_changed.emit(self._index, len(self._samples))
        self.mode_changed.emit(PlaybackMode.LIVE.value)
        self.position_changed.emit(None)
        eventbus.publish(
            EVENT_PLAYBACK_MODE,
            mode=PlaybackMode.LIVE.value,
            mmsi=resolved,
        )

    def append_live_ship(self, ship: Ship) -> None:
        """Extend trail while following live AIS for the selected vessel."""

        if ship is None:
            return

        with self._lock:
            if self._mmsi is None or int(ship.mmsi) != self._mmsi:
                return
            if not _valid_coord(ship.lat, ship.lon):
                return

            sample = PlaybackSample(
                timestamp=ship.last_seen or datetime.now(),
                latitude=float(ship.lat),
                longitude=float(ship.lon),
                speed=float(ship.speed) if ship.speed is not None else None,
                course=float(ship.course) if ship.course is not None else None,
                heading=float(ship.heading) if ship.heading is not None else None,
                source=str(ship.source or ""),
            )

            if self._samples:
                last = self._samples[-1]
                if (
                    abs(last.latitude - sample.latitude) < 0.00001
                    and abs(last.longitude - sample.longitude) < 0.00001
                ):
                    return

            self._samples.append(sample)
            if len(self._samples) > _MAX_SAMPLES:
                overflow = len(self._samples) - _MAX_SAMPLES
                self._samples = self._samples[overflow:]
                self._index = max(0, self._index - overflow)

            if self._mode == PlaybackMode.LIVE:
                self._index = len(self._samples) - 1

        self.samples_changed.emit()
        self.index_changed.emit(self._index, len(self._samples))

    def set_rate(self, rate: int) -> None:

        try:
            resolved = int(rate)
        except (TypeError, ValueError):
            resolved = 1

        if resolved not in PLAYBACK_RATES:
            resolved = 1

        self._rate = resolved
        self._timer.setInterval(max(50, int(_BASE_TICK_MS / resolved)))
        self.rate_changed.emit(resolved)

    def play(self) -> None:

        if self.sample_count == 0:
            return

        with self._lock:
            if self._index >= len(self._samples) - 1:
                self._index = 0
            self._mode = PlaybackMode.PLAYING

        self._timer.setInterval(max(50, int(_BASE_TICK_MS / max(1, self._rate))))
        self._timer.start()
        self._emit_position()
        self.mode_changed.emit(PlaybackMode.PLAYING.value)
        eventbus.publish(
            EVENT_PLAYBACK_MODE,
            mode=PlaybackMode.PLAYING.value,
            mmsi=self._mmsi,
        )

    def pause(self) -> None:

        self._timer.stop()
        with self._lock:
            if self._mode == PlaybackMode.LIVE and not self._samples:
                return
            self._mode = PlaybackMode.PAUSED

        self._emit_position()
        self.mode_changed.emit(PlaybackMode.PAUSED.value)
        eventbus.publish(
            EVENT_PLAYBACK_MODE,
            mode=PlaybackMode.PAUSED.value,
            mmsi=self._mmsi,
        )

    def toggle_play_pause(self) -> None:

        if self._mode == PlaybackMode.PLAYING:
            self.pause()
        else:
            self.play()

    def seek_fraction(self, fraction: float) -> None:

        with self._lock:
            if not self._samples:
                return
            clamped = max(0.0, min(1.0, float(fraction)))
            self._index = int(round(clamped * (len(self._samples) - 1)))
            if self._mode == PlaybackMode.LIVE:
                self._mode = PlaybackMode.PAUSED

        if self._mode == PlaybackMode.PLAYING:
            pass
        else:
            self._timer.stop()
            self.mode_changed.emit(self._mode.value)
            eventbus.publish(
                EVENT_PLAYBACK_MODE,
                mode=self._mode.value,
                mmsi=self._mmsi,
            )

        self.index_changed.emit(self._index, self.sample_count)
        self._emit_position()

    def seek_index(self, index: int) -> None:

        with self._lock:
            if not self._samples:
                return
            self._index = max(0, min(int(index), len(self._samples) - 1))
            if self._mode == PlaybackMode.LIVE:
                self._mode = PlaybackMode.PAUSED

        if self._mode != PlaybackMode.PLAYING:
            self._timer.stop()
            self.mode_changed.emit(self._mode.value)

        self.index_changed.emit(self._index, self.sample_count)
        self._emit_position()

    def go_live(self) -> None:

        self._timer.stop()
        with self._lock:
            self._mode = PlaybackMode.LIVE
            if self._samples:
                self._index = len(self._samples) - 1

        self.index_changed.emit(self._index, self.sample_count)
        self.position_changed.emit(None)
        self.mode_changed.emit(PlaybackMode.LIVE.value)
        eventbus.publish(
            EVENT_PLAYBACK_MODE,
            mode=PlaybackMode.LIVE.value,
            mmsi=self._mmsi,
        )

    def _on_tick(self) -> None:

        with self._lock:
            if self._mode != PlaybackMode.PLAYING or not self._samples:
                self._timer.stop()
                return

            if self._index >= len(self._samples) - 1:
                self._mode = PlaybackMode.PAUSED
                self._timer.stop()
                done = True
            else:
                self._index += 1
                done = False

        self.index_changed.emit(self._index, self.sample_count)
        self._emit_position()

        if done:
            self.mode_changed.emit(PlaybackMode.PAUSED.value)
            eventbus.publish(
                EVENT_PLAYBACK_MODE,
                mode=PlaybackMode.PAUSED.value,
                mmsi=self._mmsi,
            )

    def _emit_position(self) -> None:

        sample = self.current_sample()
        self.position_changed.emit(sample)
        if sample is not None:
            eventbus.publish(
                EVENT_PLAYBACK_POSITION,
                mmsi=self._mmsi,
                latitude=sample.latitude,
                longitude=sample.longitude,
                index=self._index,
            )

    def _build_samples(
        self,
        mmsi: int,
        ship: Ship | None,
    ) -> list[PlaybackSample]:

        samples: list[PlaybackSample] = []
        seen: set[tuple[float, float, str]] = set()

        try:
            records = timeline_manager.history(mmsi)
        except Exception:
            logger.exception("Failed to load timeline history for %s", mmsi)
            records = []

        for record in records:
            if not _valid_coord(record.latitude, record.longitude):
                continue
            # Prefer position updates; still accept A/D points with coordinates.
            event_type = str(record.event_type or "")
            if event_type and event_type not in (
                EVENT_POSITION_UPDATE,
                "ARRIVAL",
                "DEPARTURE",
            ):
                continue

            sample = self._from_record(record)
            key = (
                round(sample.latitude, 5),
                round(sample.longitude, 5),
                sample.timestamp.isoformat(timespec="seconds"),
            )
            if key in seen:
                continue
            seen.add(key)
            samples.append(sample)

        if ship is not None and getattr(ship, "history", None):
            # Seed denser recent crumbs without timestamps when DB is sparse.
            for lat, lon in list(ship.history):
                if not _valid_coord(lat, lon):
                    continue
                key = (round(float(lat), 5), round(float(lon), 5), "")
                if key in seen:
                    continue
                seen.add(key)
                samples.append(
                    PlaybackSample(
                        timestamp=datetime.now(),
                        latitude=float(lat),
                        longitude=float(lon),
                        source="history",
                    )
                )

        if ship is not None and _valid_coord(ship.lat, ship.lon):
            sample = PlaybackSample(
                timestamp=ship.last_seen or datetime.now(),
                latitude=float(ship.lat),
                longitude=float(ship.lon),
                speed=float(ship.speed) if ship.speed is not None else None,
                course=float(ship.course) if ship.course is not None else None,
                heading=float(ship.heading) if ship.heading is not None else None,
                source=str(ship.source or "live"),
            )
            key = (
                round(sample.latitude, 5),
                round(sample.longitude, 5),
                sample.timestamp.isoformat(timespec="seconds"),
            )
            if key not in seen:
                samples.append(sample)

        samples.sort(key=lambda item: item.timestamp)
        if len(samples) > _MAX_SAMPLES:
            samples = samples[-_MAX_SAMPLES:]
        return samples

    @staticmethod
    def _from_record(record: TimelineRecord) -> PlaybackSample:

        return PlaybackSample(
            timestamp=record.timestamp,
            latitude=float(record.latitude),
            longitude=float(record.longitude),
            speed=float(record.speed) if record.speed is not None else None,
            course=float(record.course) if record.course is not None else None,
            heading=float(record.heading) if record.heading is not None else None,
            source=str(record.source or ""),
        )


vessel_playback_engine = VesselPlaybackEngine()
