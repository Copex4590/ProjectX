# ============================================================================
# Project X
# Vessel Photo Registry
# ============================================================================

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from storage import active_cache_path
from vessels.photo_record import PhotoRecord


def vessel_photos_dir() -> Path:
    """Return the active vessel photo cache directory."""

    override = os.environ.get("PROJECTX_VESSEL_PHOTOS_DIR", "").strip()

    if override:
        return Path(override).expanduser().resolve()

    return active_cache_path("vessel_photos")


VESSEL_PHOTOS_DIR = vessel_photos_dir()
PHOTO_DATABASE_FILE = VESSEL_PHOTOS_DIR / "photos.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vessel_photos (
    mmsi INTEGER PRIMARY KEY,
    imo TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    local_file TEXT NOT NULL DEFAULT '',
    remote_url TEXT NOT NULL DEFAULT '',
    thumbnail TEXT NOT NULL DEFAULT '',
    copyright TEXT NOT NULL DEFAULT '',
    photographer TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_UPSERT_SQL = """
INSERT INTO vessel_photos (
    mmsi,
    imo,
    source,
    local_file,
    remote_url,
    thumbnail,
    copyright,
    photographer,
    created_at,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(mmsi) DO UPDATE SET
    imo = excluded.imo,
    source = excluded.source,
    local_file = excluded.local_file,
    remote_url = excluded.remote_url,
    thumbnail = excluded.thumbnail,
    copyright = excluded.copyright,
    photographer = excluded.photographer,
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


class PhotoRegistry:

    def __init__(self, db_path: Path | str | None = None):

        self._db_path = Path(db_path or PHOTO_DATABASE_FILE)
        self._lock = Lock()
        self._ensure_schema()

    @property
    def storage_dir(self) -> Path:

        return self._db_path.parent

    def get(self, mmsi: int | str) -> PhotoRecord | None:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return None

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM vessel_photos WHERE mmsi = ?",
                    (normalized_mmsi,),
                ).fetchone()

        if row is None:
            return None

        return PhotoRecord.from_row(row)

    def has(self, mmsi: int | str) -> bool:

        return self.get(mmsi) is not None

    def register(self, record: PhotoRecord) -> PhotoRecord:

        normalized_mmsi = _normalize_mmsi(record.mmsi)

        if normalized_mmsi is None:
            raise ValueError("Photo record requires a valid MMSI")

        now = datetime.now()
        existing = self.get(normalized_mmsi)

        payload = PhotoRecord(
            mmsi=normalized_mmsi,
            imo=record.safe_text(record.imo),
            source=record.safe_text(record.source),
            local_file=record.safe_text(record.local_file),
            remote_url=record.safe_text(record.remote_url),
            thumbnail=record.safe_text(record.thumbnail),
            copyright=record.safe_text(record.copyright),
            photographer=record.safe_text(record.photographer),
            created_at=existing.created_at if existing else (record.created_at or now),
            updated_at=now,
        )

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    _UPSERT_SQL,
                    (
                        payload.mmsi,
                        payload.imo,
                        payload.source,
                        payload.local_file,
                        payload.remote_url,
                        payload.thumbnail,
                        payload.copyright,
                        payload.photographer,
                        _format_timestamp(payload.created_at),
                        _format_timestamp(payload.updated_at),
                    ),
                )
                connection.commit()

                row = connection.execute(
                    "SELECT * FROM vessel_photos WHERE mmsi = ?",
                    (normalized_mmsi,),
                ).fetchone()

        if row is None:
            return payload

        return PhotoRecord.from_row(row)

    def remove(self, mmsi: int | str) -> PhotoRecord | None:

        normalized_mmsi = _normalize_mmsi(mmsi)

        if normalized_mmsi is None:
            return None

        existing = self.get(normalized_mmsi)

        if existing is None:
            return None

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM vessel_photos WHERE mmsi = ?",
                    (normalized_mmsi,),
                )
                connection.commit()

        return existing

    def all(self) -> list[PhotoRecord]:

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM vessel_photos ORDER BY mmsi"
                ).fetchall()

        return [PhotoRecord.from_row(row) for row in rows]

    def count(self) -> int:

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT COUNT(*) AS total FROM vessel_photos"
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


photo_registry = PhotoRegistry()
