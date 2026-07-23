# ============================================================================
# Project X
# Plugin Framework (SAVE-212)
# ============================================================================

from plugins.api import PluginAPI
from plugins.interface import Plugin
from plugins.loader import PluginLoader
from plugins.manager import PluginActionResult, PluginManager, plugin_manager
from plugins.metadata import PLUGIN_API_VERSION, PluginMetadata
from plugins.registry import PluginRecord, PluginRegistry, PluginState
from plugins.versioning import Version, compare_versions, satisfies_requirement

__all__ = [
    "PLUGIN_API_VERSION",
    "Plugin",
    "PluginAPI",
    "PluginActionResult",
    "PluginLoader",
    "PluginManager",
    "PluginMetadata",
    "PluginRecord",
    "PluginRegistry",
    "PluginState",
    "Version",
    "compare_versions",
    "plugin_manager",
    "satisfies_requirement",
]
