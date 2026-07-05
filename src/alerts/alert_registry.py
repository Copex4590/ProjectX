# ============================================================================
# Project X
# Alert Registry
# ============================================================================

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from alerts.alert_event import AlertEvent
from alerts.alert_rule import AlertRule

_ALERTS_DIR = Path(__file__).resolve().parent

ALERT_DATABASE_FILE = Path(
    os.environ.get(
        "PROJECTX_ALERT_DATABASE_FILE",
        str(_ALERTS_DIR / "alerts.db"),
    )
)

_RULES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    conditions TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_EVENTS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    mmsi INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}'
)
"""

_RULES_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_alert_rules_event_type
ON alert_rules (event_type, enabled)
"""

_EVENTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_alert_events_rule_timestamp
ON alert_events (rule_id, timestamp)
"""

_INSERT_RULE_SQL = """
INSERT INTO alert_rules (
    name,
    enabled,
    priority,
    event_type,
    conditions,
    created_at,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE_RULE_SQL = """
UPDATE alert_rules SET
    name = ?,
    enabled = ?,
    priority = ?,
    event_type = ?,
    conditions = ?,
    updated_at = ?
WHERE id = ?
"""

_INSERT_EVENT_SQL = """
INSERT INTO alert_events (
    rule_id,
    mmsi,
    event_type,
    timestamp,
    severity,
    message,
    metadata
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return datetime.now().isoformat(timespec="seconds")

    return value.isoformat(timespec="seconds")


class AlertRegistry:

    def __init__(self, db_path: Path | str | None = None):

        self._db_path = Path(db_path or ALERT_DATABASE_FILE)
        self._lock = Lock()
        self._ensure_schema()

    def register_rule(self, rule: AlertRule) -> AlertRule:

        now = datetime.now()
        payload = AlertRule(
            id=rule.id,
            name=rule.safe_text(rule.name) or "Unnamed Rule",
            enabled=bool(rule.enabled),
            priority=int(rule.priority),
            event_type=rule.safe_text(rule.event_type).upper(),
            conditions=dict(rule.conditions or {}),
            created_at=rule.created_at or now,
            updated_at=now,
        )

        with self._lock:
            with self._connect() as connection:
                if payload.id is None:
                    cursor = connection.execute(
                        _INSERT_RULE_SQL,
                        (
                            payload.name,
                            int(payload.enabled),
                            payload.priority,
                            payload.event_type,
                            payload.conditions_json(),
                            _format_timestamp(payload.created_at),
                            _format_timestamp(payload.updated_at),
                        ),
                    )
                    rule_id = int(cursor.lastrowid)
                else:
                    connection.execute(
                        _UPDATE_RULE_SQL,
                        (
                            payload.name,
                            int(payload.enabled),
                            payload.priority,
                            payload.event_type,
                            payload.conditions_json(),
                            _format_timestamp(payload.updated_at),
                            payload.id,
                        ),
                    )
                    rule_id = payload.id

                connection.commit()

                row = connection.execute(
                    "SELECT * FROM alert_rules WHERE id = ?",
                    (rule_id,),
                ).fetchone()

        if row is None:
            payload.id = rule_id
            return payload

        return AlertRule.from_row(row)

    def remove_rule(self, rule_id: int) -> bool:

        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM alert_rules WHERE id = ?",
                    (int(rule_id),),
                )
                connection.commit()

        return cursor.rowcount > 0

    def rules(self) -> list[AlertRule]:

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM alert_rules
                    ORDER BY priority DESC, id ASC
                    """
                ).fetchall()

        return [AlertRule.from_row(row) for row in rows]

    def append_event(self, event: AlertEvent) -> AlertEvent:

        payload = AlertEvent(
            rule_id=int(event.rule_id),
            mmsi=int(event.mmsi),
            event_type=event.safe_text(event.event_type).upper(),
            timestamp=event.timestamp or datetime.now(),
            severity=event.safe_text(event.severity) or "info",
            message=event.safe_text(event.message),
            metadata=dict(event.metadata or {}),
        )

        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    _INSERT_EVENT_SQL,
                    (
                        payload.rule_id,
                        payload.mmsi,
                        payload.event_type,
                        _format_timestamp(payload.timestamp),
                        payload.severity,
                        payload.message,
                        payload.metadata_json(),
                    ),
                )
                connection.commit()
                event_id = int(cursor.lastrowid)

                row = connection.execute(
                    "SELECT * FROM alert_events WHERE id = ?",
                    (event_id,),
                ).fetchone()

        if row is None:
            payload.id = event_id
            return payload

        return AlertEvent.from_row(row)

    def events(self) -> list[AlertEvent]:

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM alert_events
                    ORDER BY timestamp DESC, id DESC
                    """
                ).fetchall()

        return [AlertEvent.from_row(row) for row in rows]

    def _ensure_schema(self) -> None:

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            with self._connect() as connection:
                connection.execute(_RULES_SCHEMA_SQL)
                connection.execute(_EVENTS_SCHEMA_SQL)
                connection.execute(_RULES_INDEX_SQL)
                connection.execute(_EVENTS_INDEX_SQL)
                connection.commit()

    def _connect(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection


alert_registry = AlertRegistry()
