# ============================================================================
# Project X — Vessel voyage / observed-route store
#
# Canonical voyage state for destination, ETA, and (when sourced) departure.
# Observed route points come from the existing timeline POSITION_UPDATE stream —
# not invented ports, not a parallel AIS ingest path.
#
# User-facing Voyage (Utazás) never shows raw GPS / observed-track summaries.
# Route is only explicit intermediate stops from a trusted source.
#
# Flow:
#   HybridAisEngine → ShipRegistry.add → voyage_store.observe(ship)
#   UI / Analytics ← voyage_store.get_state / ui_fields / get_observed_route
# ============================================================================

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

from app.paths import runtime_data_path
from geo.port_catalog import port_catalog
from models.ship import Ship
from timeline.timeline_manager import timeline_manager
from timeline.timeline_recorder import EVENT_POSITION_UPDATE

# Departure/route sources that must never drive user-facing Voyage fields.
_UNRELIABLE_SOURCES = frozenset(
    {
        "",
        "inferred",
        "guess",
        "guessed",
        "observed",
        "track",
        "observed track",
        "ais-history",
        "ais_history",
        "gps",
        "history",
        # Live AIS feeds do not carry a trustworthy departure / itinerary.
        "aisstream",
        "ais",
        "rtl",
        "rtl-sdr",
        "hybrid",
    }
)

VOYAGE_DATABASE_FILE = Path(
    os.environ.get(
        "PROJECTX_VOYAGE_DATABASE_FILE",
        str(runtime_data_path("voyage.db")),
    )
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vessel_voyage_state (
    mmsi INTEGER PRIMARY KEY,
    destination TEXT NOT NULL DEFAULT '',
    eta TEXT NOT NULL DEFAULT '',
    departure_port TEXT NOT NULL DEFAULT '',
    departure_source TEXT NOT NULL DEFAULT '',
    route_stops TEXT NOT NULL DEFAULT '[]',
    route_source TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vessel_route_meta (
    mmsi INTEGER PRIMARY KEY,
    point_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT '',
    ended_at TEXT NOT NULL DEFAULT '',
    start_lat REAL,
    start_lon REAL,
    end_lat REAL,
    end_lon REAL,
    summary TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_mmsi(mmsi: int | str | None) -> int | None:
    if mmsi is None:
        return None
    try:
        value = int(mmsi)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def _clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _source_reliable(source: str) -> bool:
    return _clean_text(source).lower() not in _UNRELIABLE_SOURCES


def _parse_route_stops(raw) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        text = _clean_text(raw)
        if not text:
            return ()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            return tuple(parts)
        if not isinstance(parsed, list):
            return ()
        items = parsed
    out: list[str] = []
    for item in items:
        name = _clean_text(item)
        if name and name not in out:
            out.append(name)
    return tuple(out)


def _dumps_route_stops(stops: tuple[str, ...] | list[str]) -> str:
    return json.dumps(list(stops), ensure_ascii=False)


@dataclass(frozen=True)
class VoyageState:
    mmsi: int
    destination: str = ""
    eta: str = ""
    departure_port: str = ""
    departure_source: str = ""
    route_stops: tuple[str, ...] = ()
    route_source: str = ""
    source: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class VoyageUiFields:
    """Human-facing Voyage fields — never raw track coordinates."""

    departure_port: str = ""
    route: str = ""
    destination: str = ""
    eta: str = ""


@dataclass(frozen=True)
class ObservedRoute:
    """Coverage-limited observed track derived from timeline positions."""

    mmsi: int
    point_count: int = 0
    started_at: str = ""
    ended_at: str = ""
    start_lat: float | None = None
    start_lon: float | None = None
    end_lat: float | None = None
    end_lon: float | None = None
    summary: str = ""
    points: tuple[tuple[datetime, float, float], ...] = ()

    @property
    def available(self) -> bool:
        return self.point_count >= 2 and bool(self.summary)


class VoyageStore:
    """Persistent voyage fields + observed-route cache (timeline-backed)."""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = Path(db_path or VOYAGE_DATABASE_FILE)
        self._lock = Lock()
        self._connection: sqlite3.Connection | None = None
        self._route_refresh_at: dict[int, float] = {}
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
        return self._connection

    def _ensure_schema(self) -> None:
        with self._lock:
            connection = self._conn()
            connection.executescript(_SCHEMA_SQL)
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(vessel_voyage_state)")
            }
            if "route_stops" not in columns:
                connection.execute(
                    "ALTER TABLE vessel_voyage_state "
                    "ADD COLUMN route_stops TEXT NOT NULL DEFAULT '[]'"
                )
            if "route_source" not in columns:
                connection.execute(
                    "ALTER TABLE vessel_voyage_state "
                    "ADD COLUMN route_source TEXT NOT NULL DEFAULT ''"
                )
            connection.commit()

    def observe(self, ship: Ship) -> VoyageState | None:
        """Merge non-empty voyage fields from a live Ship into durable state.

        Never invents departure_port. Empty AIS fields do not erase a previously
        stored non-empty destination/ETA/departure.
        """

        mmsi = _normalize_mmsi(getattr(ship, "mmsi", None))
        if mmsi is None:
            return None

        destination = _clean_text(getattr(ship, "destination", ""))
        eta = _clean_text(getattr(ship, "eta", ""))
        departure = _clean_text(getattr(ship, "departure_port", ""))
        source = _clean_text(getattr(ship, "source", ""))
        now = _now_iso()

        with self._lock:
            connection = self._conn()
            row = connection.execute(
                "SELECT * FROM vessel_voyage_state WHERE mmsi = ?",
                (mmsi,),
            ).fetchone()

            prev_dest = _clean_text(row["destination"]) if row else ""
            prev_eta = _clean_text(row["eta"]) if row else ""
            prev_dep = _clean_text(row["departure_port"]) if row else ""
            prev_dep_src = _clean_text(row["departure_source"]) if row else ""
            prev_route = _parse_route_stops(row["route_stops"]) if row else ()
            prev_route_src = _clean_text(row["route_source"]) if row else ""
            prev_source = _clean_text(row["source"]) if row else ""

            new_dest = destination or prev_dest
            new_eta = eta or prev_eta
            # Only accept an explicit departure value from the Ship payload.
            if departure:
                new_dep = departure
                new_dep_src = source or "explicit"
            else:
                new_dep = prev_dep
                new_dep_src = prev_dep_src
            new_route = prev_route
            new_route_src = prev_route_src
            new_source = source or prev_source

            connection.execute(
                """
                INSERT INTO vessel_voyage_state (
                    mmsi, destination, eta, departure_port, departure_source,
                    route_stops, route_source, source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi) DO UPDATE SET
                    destination = excluded.destination,
                    eta = excluded.eta,
                    departure_port = excluded.departure_port,
                    departure_source = excluded.departure_source,
                    route_stops = excluded.route_stops,
                    route_source = excluded.route_source,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    mmsi,
                    new_dest,
                    new_eta,
                    new_dep,
                    new_dep_src,
                    _dumps_route_stops(new_route),
                    new_route_src,
                    new_source,
                    now,
                ),
            )
            connection.commit()

        # Refresh observed-route cache from timeline (throttled; durable).
        last = self._route_refresh_at.get(mmsi, 0.0)
        now_monotonic = time.monotonic()
        if now_monotonic - last >= 15.0:
            self._route_refresh_at[mmsi] = now_monotonic
            self.refresh_observed_route(mmsi)
        return self.get_state(mmsi)

    def get_state(self, mmsi: int | str) -> VoyageState | None:
        normalized = _normalize_mmsi(mmsi)
        if normalized is None:
            return None
        with self._lock:
            row = self._conn().execute(
                "SELECT * FROM vessel_voyage_state WHERE mmsi = ?",
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        keys = set(row.keys())
        return VoyageState(
            mmsi=int(row["mmsi"]),
            destination=_clean_text(row["destination"]),
            eta=_clean_text(row["eta"]),
            departure_port=_clean_text(row["departure_port"]),
            departure_source=_clean_text(row["departure_source"]),
            route_stops=_parse_route_stops(
                row["route_stops"] if "route_stops" in keys else "[]"
            ),
            route_source=_clean_text(
                row["route_source"] if "route_source" in keys else ""
            ),
            source=_clean_text(row["source"]),
            updated_at=_clean_text(row["updated_at"]),
        )

    def set_departure_port(
        self,
        mmsi: int | str,
        departure_port: str,
        *,
        source: str,
    ) -> VoyageState | None:
        """Explicit departure ingest (future provider / manual). No inference."""

        normalized = _normalize_mmsi(mmsi)
        port = _clean_text(departure_port)
        src = _clean_text(source)
        if normalized is None or not port or not _source_reliable(src):
            return None

        ship = Ship(mmsi=normalized, departure_port=port, source=src)
        return self.observe(ship)

    def set_route_stops(
        self,
        mmsi: int | str,
        stops: list[str] | tuple[str, ...],
        *,
        source: str,
    ) -> VoyageState | None:
        """Explicit intermediate ports only. GPS track is never a route."""

        normalized = _normalize_mmsi(mmsi)
        src = _clean_text(source)
        cleaned = _parse_route_stops(stops)
        if normalized is None or not cleaned or not _source_reliable(src):
            return None

        now = _now_iso()
        with self._lock:
            connection = self._conn()
            row = connection.execute(
                "SELECT * FROM vessel_voyage_state WHERE mmsi = ?",
                (normalized,),
            ).fetchone()
            destination = _clean_text(row["destination"]) if row else ""
            eta = _clean_text(row["eta"]) if row else ""
            departure = _clean_text(row["departure_port"]) if row else ""
            dep_src = _clean_text(row["departure_source"]) if row else ""
            prev_source = _clean_text(row["source"]) if row else ""
            connection.execute(
                """
                INSERT INTO vessel_voyage_state (
                    mmsi, destination, eta, departure_port, departure_source,
                    route_stops, route_source, source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi) DO UPDATE SET
                    route_stops = excluded.route_stops,
                    route_source = excluded.route_source,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized,
                    destination,
                    eta,
                    departure,
                    dep_src,
                    _dumps_route_stops(cleaned),
                    src,
                    prev_source or src,
                    now,
                ),
            )
            connection.commit()
        return self.get_state(normalized)

    def label_place(
        self,
        lat: float,
        lon: float,
        *,
        max_km: float = 3.0,
    ) -> str:
        """Resolve coordinates via the global port catalog when a hit exists."""

        return port_catalog.label_near(lat, lon, max_km=max_km)

    def ui_fields(
        self,
        mmsi: int | str,
        *,
        ship: Ship | None = None,
    ) -> VoyageUiFields:
        """Voyage values safe for the user-facing Vessel Card."""

        state = self.get_state(mmsi)
        destination = _clean_text(getattr(ship, "destination", "") if ship else "")
        eta = _clean_text(getattr(ship, "eta", "") if ship else "")
        if state is not None:
            destination = destination or state.destination
            eta = eta or state.eta

        departure = ""
        if ship is not None:
            ship_dep = _clean_text(getattr(ship, "departure_port", ""))
            ship_src = _clean_text(getattr(ship, "source", ""))
            if ship_dep and _source_reliable(ship_src):
                departure = ship_dep
        if (
            not departure
            and state is not None
            and state.departure_port
            and _source_reliable(state.departure_source)
        ):
            departure = state.departure_port

        route = ""
        if (
            state is not None
            and state.route_stops
            and _source_reliable(state.route_source)
        ):
            route = " → ".join(state.route_stops)

        return VoyageUiFields(
            departure_port=departure,
            route=route,
            destination=destination,
            eta=eta,
        )

    def build_observed_route(self, mmsi: int | str) -> ObservedRoute:
        """Derive MMSI route from timeline POSITION_UPDATE records."""

        normalized = _normalize_mmsi(mmsi)
        if normalized is None:
            return ObservedRoute(mmsi=0)

        records = timeline_manager.history(normalized)
        points: list[tuple[datetime, float, float]] = []
        for record in records:
            if str(record.event_type or "") != EVENT_POSITION_UPDATE:
                continue
            try:
                lat = float(record.latitude)
                lon = float(record.longitude)
            except (TypeError, ValueError):
                continue
            if lat == 0.0 and lon == 0.0:
                continue
            points.append((record.timestamp, lat, lon))

        if len(points) < 2:
            summary = ""
            started = ended = ""
            start_lat = start_lon = end_lat = end_lon = None
        else:
            first = points[0]
            last = points[-1]
            started = first[0].strftime("%Y-%m-%d %H:%M:%S")
            ended = last[0].strftime("%Y-%m-%d %H:%M:%S")
            start_lat, start_lon = first[1], first[2]
            end_lat, end_lon = last[1], last[2]
            summary = (
                f"{len(points)} pts · {started} → {ended} · "
                f"{start_lat:.5f},{start_lon:.5f} → {end_lat:.5f},{end_lon:.5f} "
                f"(observed track)"
            )

        return ObservedRoute(
            mmsi=normalized,
            point_count=len(points),
            started_at=started if len(points) >= 2 else "",
            ended_at=ended if len(points) >= 2 else "",
            start_lat=start_lat if len(points) >= 2 else None,
            start_lon=start_lon if len(points) >= 2 else None,
            end_lat=end_lat if len(points) >= 2 else None,
            end_lon=end_lon if len(points) >= 2 else None,
            summary=summary,
            points=tuple(points),
        )

    def refresh_observed_route(self, mmsi: int | str) -> ObservedRoute:
        route = self.build_observed_route(mmsi)
        if route.mmsi <= 0:
            return route
        with self._lock:
            self._conn().execute(
                """
                INSERT INTO vessel_route_meta (
                    mmsi, point_count, started_at, ended_at,
                    start_lat, start_lon, end_lat, end_lon,
                    summary, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi) DO UPDATE SET
                    point_count = excluded.point_count,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    start_lat = excluded.start_lat,
                    start_lon = excluded.start_lon,
                    end_lat = excluded.end_lat,
                    end_lon = excluded.end_lon,
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
                """,
                (
                    route.mmsi,
                    route.point_count,
                    route.started_at,
                    route.ended_at,
                    route.start_lat,
                    route.start_lon,
                    route.end_lat,
                    route.end_lon,
                    route.summary,
                    _now_iso(),
                ),
            )
            self._conn().commit()
        return route

    def get_observed_route(self, mmsi: int | str) -> ObservedRoute:
        """Return cached summary; rebuild from timeline if cache missing."""

        normalized = _normalize_mmsi(mmsi)
        if normalized is None:
            return ObservedRoute(mmsi=0)

        with self._lock:
            row = self._conn().execute(
                "SELECT * FROM vessel_route_meta WHERE mmsi = ?",
                (normalized,),
            ).fetchone()

        if row is None or int(row["point_count"] or 0) < 2:
            return self.refresh_observed_route(normalized)

        return ObservedRoute(
            mmsi=normalized,
            point_count=int(row["point_count"] or 0),
            started_at=_clean_text(row["started_at"]),
            ended_at=_clean_text(row["ended_at"]),
            start_lat=row["start_lat"],
            start_lon=row["start_lon"],
            end_lat=row["end_lat"],
            end_lon=row["end_lon"],
            summary=_clean_text(row["summary"]),
        )

    def destination_counts(self, limit: int = 10) -> list[tuple[str, int]]:
        """Persisted destinations for analytics (not live-only)."""

        with self._lock:
            rows = self._conn().execute(
                """
                SELECT destination, COUNT(*) AS n
                FROM vessel_voyage_state
                WHERE TRIM(destination) != ''
                GROUP BY destination
                ORDER BY n DESC, destination ASC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [(_clean_text(row["destination"]), int(row["n"])) for row in rows]


voyage_store = VoyageStore()
