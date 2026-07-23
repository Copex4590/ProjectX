# ============================================================================
# Project X
# Plugin Framework — PluginManager (SAVE-212)
# ============================================================================

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from app.paths import plugins_dir, runtime_data_path
from plugins.api import PluginAPI
from plugins.loader import PluginLoader
from plugins.metadata import PLUGIN_API_VERSION, PluginMetadata
from plugins.registry import PluginRecord, PluginRegistry, PluginState
from plugins.versioning import Version, compare_versions, satisfies_requirement

logger = logging.getLogger(__name__)

PLUGIN_STATE_FILE = Path(
    os.environ.get(
        "PROJECTX_PLUGINS_STATE_FILE",
        str(runtime_data_path("plugins_state.json")),
    )
)


@dataclass(frozen=True)
class PluginActionResult:
    success: bool
    message: str
    plugin_id: str = ""


class PluginManager:
    """Discover, load, enable/disable plugins with dependency checks."""

    def __init__(
        self,
        *,
        plugins_root: Path | None = None,
        state_path: Path | None = None,
        loader: PluginLoader | None = None,
        registry: PluginRegistry | None = None,
        api: PluginAPI | None = None,
    ) -> None:

        self._lock = RLock()
        self._plugins_root = Path(plugins_root) if plugins_root else None
        self._state_path = Path(state_path) if state_path else PLUGIN_STATE_FILE
        self._loader = loader or PluginLoader()
        self._registry = registry or PluginRegistry()
        self._api = api or PluginAPI()
        self._enabled_ids: set[str] = set()
        self._initialized = False

    @property
    def api(self) -> PluginAPI:

        return self._api

    @property
    def registry(self) -> PluginRegistry:

        return self._registry

    @property
    def plugins_root(self) -> Path:

        return self._plugins_root or plugins_dir()

    def initialize(self) -> None:
        """Load persisted enablement, discover packages, apply previous enables."""

        with self._lock:
            if self._initialized:
                self.refresh()
                return

            self._load_state()
            self._discover_and_register()
            self._initialized = True
            self._apply_persisted_enables()

    def refresh(self) -> list[PluginRecord]:
        """Re-scan the plugins directory without dropping enabled instances."""

        with self._lock:
            self._discover_and_register()
            return self._registry.all()

    def list_plugins(self) -> list[PluginRecord]:

        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._registry.all()

    def get_plugin(self, plugin_id: str) -> PluginRecord | None:

        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._registry.get(plugin_id)

    def enable(self, plugin_id: str) -> PluginActionResult:

        with self._lock:
            if not self._initialized:
                self.initialize()

            plugin_id = str(plugin_id).strip()
            record = self._registry.get(plugin_id)
            if record is None:
                return PluginActionResult(
                    False,
                    f"Plugin not found: {plugin_id}",
                    plugin_id,
                )

            if record.enabled and record.state == PluginState.ENABLED:
                return PluginActionResult(True, "Already enabled", plugin_id)

            errors = self._check_dependencies(record.metadata)
            if errors:
                self._registry.set_error(
                    plugin_id,
                    "Dependency check failed",
                    dependency_errors=errors,
                )
                return PluginActionResult(
                    False,
                    "; ".join(errors),
                    plugin_id,
                )

            api_error = self._check_api_version(record.metadata)
            if api_error:
                self._registry.set_error(plugin_id, api_error)
                return PluginActionResult(False, api_error, plugin_id)

            try:
                instance = record.instance
                if instance is None:
                    instance = self._loader.load_plugin(record.metadata)
                    instance.on_load(self._api)
                    self._registry.set_instance(plugin_id, instance)

                assert instance is not None
                instance.on_enable(self._api)
            except Exception as error:
                logger.exception("Failed to enable plugin %s", plugin_id)
                message = str(error)
                self._registry.set_error(plugin_id, message)
                return PluginActionResult(False, message, plugin_id)

            self._registry.clear_error(plugin_id)
            self._registry.set_enabled(plugin_id, True)
            self._enabled_ids.add(plugin_id)
            self._persist_state()
            return PluginActionResult(True, "Plugin enabled", plugin_id)

    def disable(self, plugin_id: str) -> PluginActionResult:

        with self._lock:
            if not self._initialized:
                self.initialize()

            plugin_id = str(plugin_id).strip()
            record = self._registry.get(plugin_id)
            if record is None:
                return PluginActionResult(
                    False,
                    f"Plugin not found: {plugin_id}",
                    plugin_id,
                )

            if not record.enabled and record.state in (
                PluginState.DISABLED,
                PluginState.DISCOVERED,
                PluginState.LOADED,
            ):
                self._enabled_ids.discard(plugin_id)
                self._persist_state()
                return PluginActionResult(True, "Already disabled", plugin_id)

            dependents = self._enabled_dependents(plugin_id)
            if dependents:
                names = ", ".join(dependents)
                return PluginActionResult(
                    False,
                    f"Cannot disable: required by {names}",
                    plugin_id,
                )

            try:
                if record.instance is not None:
                    record.instance.on_disable(self._api)
            except Exception as error:
                logger.exception("Failed to disable plugin %s", plugin_id)
                message = str(error)
                self._registry.set_error(plugin_id, message)
                return PluginActionResult(False, message, plugin_id)

            self._registry.clear_error(plugin_id)
            self._registry.set_enabled(plugin_id, False)
            self._enabled_ids.discard(plugin_id)
            self._persist_state()
            return PluginActionResult(True, "Plugin disabled", plugin_id)

    def shutdown(self) -> None:

        with self._lock:
            for record in self._registry.all():
                if record.instance is None:
                    continue
                try:
                    if record.enabled:
                        record.instance.on_disable(self._api)
                    record.instance.on_unload(self._api)
                except Exception:
                    logger.exception("Error unloading plugin %s", record.plugin_id)
                self._registry.set_instance(record.plugin_id, None)
                self._registry.set_enabled(record.plugin_id, False)
            self._initialized = False

    def _discover_and_register(self) -> None:

        root = self.plugins_root
        root.mkdir(parents=True, exist_ok=True)

        for metadata in self._loader.discover(root):
            self._registry.register(metadata)

            # Keep enablement flag from persisted state when rediscovering
            if metadata.id in self._enabled_ids:
                record = self._registry.get(metadata.id)
                if record is not None and not record.enabled:
                    # Will be applied by enable path; mark intended
                    pass

    def _apply_persisted_enables(self) -> None:

        for plugin_id in sorted(self._enabled_ids):
            result = self.enable(plugin_id)
            if not result.success:
                logger.warning(
                    "Could not restore plugin %s: %s",
                    plugin_id,
                    result.message,
                )

    def _check_api_version(self, metadata: PluginMetadata) -> str:
        """Plugins may target the same major API version."""

        required = Version.parse(metadata.api_version)
        host = Version.parse(PLUGIN_API_VERSION)

        if required.major != host.major:
            return (
                f"Incompatible plugin API {metadata.api_version} "
                f"(host {PLUGIN_API_VERSION})"
            )

        if compare_versions(metadata.api_version, PLUGIN_API_VERSION) > 0:
            return (
                f"Plugin requires newer API {metadata.api_version} "
                f"(host {PLUGIN_API_VERSION})"
            )

        return ""

    def _check_dependencies(self, metadata: PluginMetadata) -> list[str]:

        errors: list[str] = []

        for dep_id, requirement in metadata.dependencies.items():
            record = self._registry.get(dep_id)
            if record is None:
                errors.append(f"Missing dependency: {dep_id}")
                continue

            if not satisfies_requirement(record.metadata.version, requirement):
                errors.append(
                    f"Dependency {dep_id} {record.metadata.version} "
                    f"does not satisfy {requirement}"
                )
                continue

            if not record.enabled:
                errors.append(f"Dependency not enabled: {dep_id}")

        return errors

    def _enabled_dependents(self, plugin_id: str) -> list[str]:

        dependents: list[str] = []
        for record in self._registry.all():
            if not record.enabled:
                continue
            if plugin_id in record.metadata.dependencies:
                dependents.append(record.metadata.id)
        return dependents

    def _load_state(self) -> None:

        path = self._state_path
        if not path.exists():
            self._enabled_ids = set()
            return

        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load plugin state from %s", path)
            self._enabled_ids = set()
            return

        enabled = payload.get("enabled") if isinstance(payload, dict) else None
        if isinstance(enabled, dict):
            self._enabled_ids = {
                str(key).strip()
                for key, value in enabled.items()
                if str(key).strip() and bool(value)
            }
        elif isinstance(enabled, list):
            self._enabled_ids = {
                str(item).strip() for item in enabled if str(item).strip()
            }
        else:
            self._enabled_ids = set()

    def _persist_state(self) -> None:

        path = self._state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "enabled": {plugin_id: True for plugin_id in sorted(self._enabled_ids)},
        }

        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")


plugin_manager = PluginManager()
