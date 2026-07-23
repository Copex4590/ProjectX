# ============================================================================
# Project X
# Plugin Framework — loader (SAVE-212)
# ============================================================================

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path

from plugins.interface import Plugin
from plugins.metadata import PluginMetadata

logger = logging.getLogger(__name__)

MANIFEST_NAMES = ("plugin.json", "plugin.manifest.json")


class PluginLoader:
    """Discover plugin packages on disk and instantiate entry points."""

    def discover(self, root: Path) -> list[PluginMetadata]:

        root = Path(root)
        if not root.exists() or not root.is_dir():
            return []

        discovered: list[PluginMetadata] = []

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name == "__pycache__":
                continue

            metadata = self.load_manifest(child)
            if metadata is None:
                continue
            discovered.append(metadata)

        return discovered

    def load_manifest(self, plugin_dir: Path) -> PluginMetadata | None:

        plugin_dir = Path(plugin_dir)
        manifest_path = None

        for name in MANIFEST_NAMES:
            candidate = plugin_dir / name
            if candidate.is_file():
                manifest_path = candidate
                break

        if manifest_path is None:
            return None

        try:
            with manifest_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read plugin manifest: %s", manifest_path)
            return None

        metadata = PluginMetadata.from_dict(data, path=plugin_dir)
        if not metadata.id:
            logger.warning("Skipping plugin without id: %s", plugin_dir)
            return None

        return metadata

    def load_plugin(self, metadata: PluginMetadata) -> Plugin:
        """Import the entry module and construct the Plugin instance."""

        if metadata.path is None:
            raise FileNotFoundError(f"Plugin path missing for {metadata.id}")

        entry = metadata.entry.strip()
        if not entry or ":" not in entry:
            raise ValueError(
                f"Plugin {metadata.id} has invalid entry '{metadata.entry}' "
                "(expected module:Class)"
            )

        module_name, _, class_name = entry.partition(":")
        module_name = module_name.strip()
        class_name = class_name.strip()

        if not module_name or not class_name:
            raise ValueError(f"Plugin {metadata.id} has invalid entry '{entry}'")

        module_path = Path(metadata.path) / f"{module_name.replace('.', '/')}.py"
        if not module_path.is_file():
            # allow package-style entry: module/__init__.py not required for flat
            raise FileNotFoundError(
                f"Plugin module not found: {module_path} ({metadata.id})"
            )

        unique_name = f"projectx_plugin_{metadata.id.replace('.', '_')}_{module_name}"
        spec = importlib.util.spec_from_file_location(unique_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load plugin module: {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)

        plugin_cls = getattr(module, class_name, None)
        if plugin_cls is None:
            raise AttributeError(
                f"Plugin class '{class_name}' not found in {module_path}"
            )

        instance = plugin_cls()
        if not isinstance(instance, Plugin):
            raise TypeError(
                f"{class_name} in {metadata.id} must inherit plugins.interface.Plugin"
            )

        return instance
