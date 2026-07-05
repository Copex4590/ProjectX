# ============================================================================
# Project X
# Vessel Timeline Registry
# ============================================================================

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from timeline.timeline_record import TimelineRecord

_TIMELINE_DIR = Path(__file__).resolve().parent

TIMELINE_DATABASE_FILE = Path(
    os.environ.get(
        "PROJECTX_TIMELINE_DATABASE_FILE",
        str(_TIMELINE_DIR / "timeline.db"),
    )
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vessel_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mmsi INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    speed REAL,
    course REAL,
    heading REAL,
    source TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}'
)
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_vessel_timeline_mmsi_timestamp
ON vessel_timeline (mmsi, timestamp)
"""

_INSERT_SQL = """
INSERT INTO vessel_timeline (
    mmsi,
    timestamp,
    event_type,
    latitude,
    longitude,
    speed,
    course,
    heading,
    source,
    metadata
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return datetime.now().isoformat(timespec="seconds")

    return value.isoformat(timespec="seconds")


def _normalize_mmsi(mmsi: int | str | None) -> int | None:

    if mmsi is None:
        return None

    try:
        normalized = int(mmsi)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None

    return normalized


class TimelineRegistry:

    def __init__(self, db_path: Path | str | None = None):

        self._db_path = Path(db_path or TIMELINE_DATABASE_FILE)
        self._lock = Lock()
        self._ensure_schema()

    def append(self, record: TimelineRecord) -> TimelineRecord:

        normalized_mmsi = _normalize_mmsi(record.mmsi)

        if normalized_mmsi is None:
            raise ValueError("Timeline record requires a valid MMSI")

        payload = TimelineRecord(
            mmsi=normalized_mmsi,
            timestamp=record.timestamp or datetime.now(),
            event_type=record.safe_text(record.event_type),
            latitude=record.latitude,
            longitude=record.longitude,
            speed=record.speed,
            course=record.course,
            heading=record.heading,
            source=record.safe_text(record.source),
            metadata=dict(record.metadata or {}),
        )

        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    _INSERT_SQL,
                    (
                        payload.mmsi,
                        _format_timestamp(payload.timestamp),
                        payload.event_type,
                        payload.latitude,
                        payload.longitude,
                        payload.speed,
                        payload.course,
                        payload.heading,
                        payload.source,
                        payload.metadata_json(),
                    ),
                )
                connection.commit()
                record_id = int(cursor.lastrowid)

                row = connection.execute(
                    "SELECT * FROM vessel_timeline WHERE id = ?",
                    (record_id,),
                ).fetchone()

        if row is None:
            payload.id = record_id
            return payload

        return TimelineRecord.from_row(row)

    def history(self, mmsi: int | str) -> list[TimelineRecord]:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return []

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM vessel_timeline
                    WHERE mmsi = ?
                    ORDER BY timestamp ASC, id ASC
                    """,
                    (normalized_mmsi,),
                ).fetchall()

        return [TimelineRecord.from_row(row) for row in rows]

    def latest(self, mmsi: int | str) -> TimelineRecord | None:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return None

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT * FROM vessel_timeline
                    WHERE mmsi = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT 1
                    """,
                    (normalized_mmsi,),
                ).fetchone()

        if row is None:
            return None

        return TimelineRecord.from_row(row)

    def count(self) -> int:

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT COUNT(*) AS total FROM vessel_timeline"
                ).fetchone()

        if row is None:
            return 0

        return int(row["total"])

    def all(self) -> list[TimelineRecord]:

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM vessel_timeline
                    ORDER BY timestamp DESC, id DESC
                    """
                ).fetchall()

        return [TimelineRecord.from_row(row) for row in rows]

    def _ensure_schema(self) -> None:

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            with self._connect() as connection:
                connection.execute(_SCHEMA_SQL)
                connection.execute(_INDEX_SQL)
                connection.commit()

    def _connect(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection


timeline_registry = TimelineRegistry()
