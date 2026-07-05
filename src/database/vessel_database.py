# ============================================================================
# Project X
# Vessel Database
# ============================================================================

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from models.vessel_record import VesselRecord

from app.paths import runtime_data_path

VESSEL_DATABASE_FILE = Path(
    os.environ.get(
        "PROJECTX_VESSEL_DATABASE_FILE",
        str(runtime_data_path("vessels.db")),
    )
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vessels (
    mmsi INTEGER PRIMARY KEY,
    imo TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    callsign TEXT NOT NULL DEFAULT '',
    ship_type TEXT NOT NULL DEFAULT '',
    flag TEXT NOT NULL DEFAULT '',
    length REAL,
    width REAL,
    draft REAL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_UPSERT_SQL = """
INSERT INTO vessels (
    mmsi,
    imo,
    name,
    callsign,
    ship_type,
    flag,
    length,
    width,
    draft,
    first_seen,
    last_seen,
    created_at,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(mmsi) DO UPDATE SET
    imo = excluded.imo,
    name = excluded.name,
    callsign = excluded.callsign,
    ship_type = excluded.ship_type,
    flag = excluded.flag,
    length = excluded.length,
    width = excluded.width,
    draft = excluded.draft,
    last_seen = excluded.last_seen,
    updated_at = excluded.updated_at
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


class VesselDatabase:

    def __init__(self, db_path: Path | str | None = None):

        self._db_path = Path(db_path or VESSEL_DATABASE_FILE)
        self._lock = Lock()
        self._ensure_schema()

    def get(self, mmsi: int | str) -> VesselRecord | None:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return None

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM vessels WHERE mmsi = ?",
                    (normalized_mmsi,),
                ).fetchone()

        if row is None:
            return None

        return VesselRecord.from_row(row)

    def upsert(self, record: VesselRecord) -> VesselRecord:

        normalized_mmsi = _normalize_mmsi(record.mmsi)

        if normalized_mmsi is None:
            raise ValueError("Vessel record requires a valid MMSI")

        now = datetime.now()
        payload = VesselRecord(
            mmsi=normalized_mmsi,
            imo=record.safe_text(record.imo),
            name=record.safe_text(record.name),
            callsign=record.safe_text(record.callsign),
            ship_type=record.safe_text(record.ship_type),
            flag=record.safe_text(record.flag),
            length=record.length,
            width=record.width,
            draft=record.draft,
            first_seen=record.first_seen or now,
            last_seen=record.last_seen or now,
            created_at=record.created_at or now,
            updated_at=record.updated_at or now,
        )

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    _UPSERT_SQL,
                    (
                        payload.mmsi,
                        payload.imo,
                        payload.name,
                        payload.callsign,
                        payload.ship_type,
                        payload.flag,
                        payload.length,
                        payload.width,
                        payload.draft,
                        _format_timestamp(payload.first_seen),
                        _format_timestamp(payload.last_seen),
                        _format_timestamp(payload.created_at),
                        _format_timestamp(payload.updated_at),
                    ),
                )
                connection.commit()

                row = connection.execute(
                    "SELECT * FROM vessels WHERE mmsi = ?",
                    (normalized_mmsi,),
                ).fetchone()

        if row is None:
            return payload

        return VesselRecord.from_row(row)

    def all(self) -> list[VesselRecord]:

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM vessels ORDER BY mmsi"
                ).fetchall()

        return [VesselRecord.from_row(row) for row in rows]

    def count(self) -> int:

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT COUNT(*) AS total FROM vessels"
                ).fetchone()

        if row is None:
            return 0

        return int(row["total"])

    def _ensure_schema(self) -> None:

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            with self._connect() as connection:
                connection.execute(_SCHEMA_SQL)
                connection.commit()

    def _connect(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection


vessel_database = VesselDatabase()
