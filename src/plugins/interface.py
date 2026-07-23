# ============================================================================
# Project X
# Plugin Framework — plugin interface (SAVE-212)
# ============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plugins.api import PluginAPI
    from plugins.metadata import PluginMetadata


class Plugin(ABC):
    """Base class for installable Project X plugins."""

    @abstractmethod
    def metadata(self) -> "PluginMetadata":
        """Return static plugin metadata (id, version, author, …)."""

    def on_load(self, api: "PluginAPI") -> None:
        """Called once after the plugin class is instantiated."""

    def on_enable(self, api: "PluginAPI") -> None:
        """Called when the plugin is enabled."""

    def on_disable(self, api: "PluginAPI") -> None:
        """Called when the plugin is disabled."""

    def on_unload(self, api: "PluginAPI") -> None:
        """Called before the plugin is discarded from memory."""
