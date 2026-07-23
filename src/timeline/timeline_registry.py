# ============================================================================
# Project X
# Vessel Timeline Registry (SAVE-203: WAL + persistent + batched inserts)
# ============================================================================

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from timeline.timeline_record import TimelineRecord

from app.paths import runtime_data_path

TIMELINE_DATABASE_FILE = Path(
    os.environ.get(
        "PROJECTX_TIMELINE_DATABASE_FILE",
        str(runtime_data_path("timeline.db")),
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
        self._connection: sqlite3.Connection | None = None
        self._ensure_schema()

    def append(self, record: TimelineRecord) -> TimelineRecord:

        return self.append_many([record])[0]

    def append_many(self, records: list[TimelineRecord]) -> list[TimelineRecord]:

        if not records:
            return []

        results: list[TimelineRecord] = []

        with self._lock:
            connection = self._conn()
            for record in records:
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
                payload.id = int(cursor.lastrowid)
                results.append(payload)

            connection.commit()

        return results

    def history(self, mmsi: int | str) -> list[TimelineRecord]:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return []

        with self._lock:
            rows = self._conn().execute(
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
            row = self._conn().execute(
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
            row = self._conn().execute(
                "SELECT COUNT(*) AS total FROM vessel_timeline"
            ).fetchone()

        if row is None:
            return 0

        return int(row["total"])

    def all(self) -> list[TimelineRecord]:

        with self._lock:
            rows = self._conn().execute(
                """
                SELECT * FROM vessel_timeline
                ORDER BY timestamp DESC, id DESC
                """
            ).fetchall()

        return [TimelineRecord.from_row(row) for row in rows]

    def _ensure_schema(self) -> None:

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            connection = self._conn()
            connection.execute(_SCHEMA_SQL)
            connection.execute(_INDEX_SQL)
            connection.commit()

    def _conn(self) -> sqlite3.Connection:

        if self._connection is not None:
            return self._connection

        connection = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        self._connection = connection
        return connection


timeline_registry = TimelineRegistry()
