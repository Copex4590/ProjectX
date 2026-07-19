# ============================================================================
# Project X
# Migration State Persistence (SAVE-107-B4)
# ============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from storage.bootstrap import bootstrap_config_path

MIGRATION_STATE_SCHEMA = 1
MIGRATION_STATE_FILENAME = "migration_state.json"


class MigrationPhase(str, Enum):
    PENDING = "pending"
    COPYING = "copying"
    VERIFYING = "verifying"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


def _utc_now_iso() -> str:

    return datetime.now(timezone.utc).isoformat()


@dataclass
class MigrationState:
    """Restart-safe migration progress persisted in the bootstrap profile."""

    migration_id: str
    phase: MigrationPhase
    destination_root: str
    source_inventory: dict
    copied_paths: list[str] = field(default_factory=list)
    destination_preexisting: bool = False
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    error: str | None = None
    schema_version: int = MIGRATION_STATE_SCHEMA

    def to_dict(self) -> dict:

        return {
            "schema_version": self.schema_version,
            "migration_id": self.migration_id,
            "phase": self.phase.value,
            "destination_root": self.destination_root,
            "source_inventory": dict(self.source_inventory),
            "copied_paths": list(self.copied_paths),
            "destination_preexisting": self.destination_preexisting,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MigrationState:

        if not isinstance(data, dict):
            data = {}

        phase_value = str(data.get("phase", MigrationPhase.PENDING.value)).strip().lower()

        try:
            phase = MigrationPhase(phase_value)
        except ValueError:
            phase = MigrationPhase.PENDING

        copied_paths = data.get("copied_paths", [])

        if not isinstance(copied_paths, list):
            copied_paths = []

        source_inventory = data.get("source_inventory", {})

        if not isinstance(source_inventory, dict):
            source_inventory = {}

        return cls(
            migration_id=str(data.get("migration_id", "")).strip() or str(uuid4()),
            phase=phase,
            destination_root=str(data.get("destination_root", "")).strip(),
            source_inventory=source_inventory,
            copied_paths=[str(item) for item in copied_paths if str(item).strip()],
            destination_preexisting=bool(data.get("destination_preexisting", False)),
            created_at=str(data.get("created_at", _utc_now_iso())),
            updated_at=str(data.get("updated_at", _utc_now_iso())),
            error=(
                str(data.get("error")).strip()
                if data.get("error") not in (None, "")
                else None
            ),
            schema_version=int(data.get("schema_version", MIGRATION_STATE_SCHEMA)),
        )

    @classmethod
    def new(
        cls,
        destination_root: Path,
        source_inventory: dict,
        *,
        destination_preexisting: bool,
    ) -> MigrationState:

        return cls(
            migration_id=str(uuid4()),
            phase=MigrationPhase.PENDING,
            destination_root=str(destination_root),
            source_inventory=dict(source_inventory),
            destination_preexisting=destination_preexisting,
        )

    def touch(self, *, phase: MigrationPhase | None = None, error: str | None = None) -> None:

        if phase is not None:
            self.phase = phase

        self.updated_at = _utc_now_iso()
        self.error = error


class MigrationStateStore:
    """Read/write migration_state.json from the bootstrap profile."""

    def __init__(self, path: Path | None = None) -> None:

        self._path = Path(path or bootstrap_config_path(MIGRATION_STATE_FILENAME))

    @property
    def path(self) -> Path:

        return self._path

    def load(self) -> MigrationState | None:

        if not self._path.is_file():
            return None

        try:
            with self._path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        state = MigrationState.from_dict(data)

        if not state.destination_root:
            return None

        return state

    def save(self, state: MigrationState) -> None:

        state.touch()
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, indent=2)
            handle.write("\n")

    def clear(self) -> None:

        if self._path.is_file():
            self._path.unlink()
