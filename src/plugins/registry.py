# ============================================================================
# Project X
# Plugin Framework — registry (SAVE-212)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock

from plugins.interface import Plugin
from plugins.metadata import PluginMetadata


class PluginState(str, Enum):

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginRecord:
    metadata: PluginMetadata
    state: PluginState = PluginState.DISCOVERED
    enabled: bool = False
    instance: Plugin | None = None
    error: str = ""
    dependency_errors: list[str] = field(default_factory=list)

    @property
    def plugin_id(self) -> str:

        return self.metadata.id


class PluginRegistry:
    """In-memory catalog of discovered / loaded plugins."""

    def __init__(self) -> None:

        self._lock = RLock()
        self._records: dict[str, PluginRecord] = {}

    def clear(self) -> None:

        with self._lock:
            self._records.clear()

    def register(self, metadata: PluginMetadata) -> PluginRecord:

        if not metadata.id:
            raise ValueError("Plugin metadata requires a non-empty id")

        with self._lock:
            existing = self._records.get(metadata.id)
            if existing is not None:
                existing.metadata = metadata
                return existing

            record = PluginRecord(metadata=metadata)
            self._records[metadata.id] = record
            return record

    def get(self, plugin_id: str) -> PluginRecord | None:

        with self._lock:
            return self._records.get(str(plugin_id).strip())

    def all(self) -> list[PluginRecord]:

        with self._lock:
            return sorted(
                self._records.values(),
                key=lambda item: (item.metadata.name.lower(), item.metadata.id),
            )

    def ids(self) -> list[str]:

        with self._lock:
            return list(self._records.keys())

    def set_instance(self, plugin_id: str, instance: Plugin | None) -> None:

        with self._lock:
            record = self._records.get(plugin_id)
            if record is None:
                return
            record.instance = instance
            if instance is not None and record.state == PluginState.DISCOVERED:
                record.state = PluginState.LOADED

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:

        with self._lock:
            record = self._records.get(plugin_id)
            if record is None:
                return
            record.enabled = bool(enabled)
            if record.state != PluginState.ERROR:
                record.state = (
                    PluginState.ENABLED if enabled else PluginState.DISABLED
                )

    def set_error(
        self,
        plugin_id: str,
        message: str,
        *,
        dependency_errors: list[str] | None = None,
    ) -> None:

        with self._lock:
            record = self._records.get(plugin_id)
            if record is None:
                return
            record.error = str(message or "").strip()
            if dependency_errors is not None:
                record.dependency_errors = list(dependency_errors)
            if record.error or record.dependency_errors:
                record.state = PluginState.ERROR

    def clear_error(self, plugin_id: str) -> None:

        with self._lock:
            record = self._records.get(plugin_id)
            if record is None:
                return
            record.error = ""
            record.dependency_errors = []
            if record.enabled:
                record.state = PluginState.ENABLED
            elif record.instance is not None:
                record.state = PluginState.DISABLED
            else:
                record.state = PluginState.DISCOVERED
