# ============================================================================
# Project X — Sample Info Plugin (SAVE-212 demo)
# ============================================================================

from __future__ import annotations

from plugins.api import PluginAPI
from plugins.interface import Plugin
from plugins.metadata import PluginMetadata


class SampleInfoPlugin(Plugin):
    """Minimal sample plugin used to exercise enable/disable and metadata UI."""

    def metadata(self) -> PluginMetadata:

        return PluginMetadata(
            id="sample.info",
            name="Sample Info Plugin",
            version="1.0.0",
            author="Project X",
            description=(
                "Demonstration plugin for the SAVE-212 Plugin Framework. "
                "Does not replace built-in AIS, Camera, or Database modules."
            ),
            api_version="1.0.0",
            entry="plugin:SampleInfoPlugin",
        )

    def on_load(self, api: PluginAPI) -> None:

        api.get_logger("sample.info").debug(
            "Sample Info Plugin loaded (host %s %s)",
            api.app_name,
            api.app_version,
        )

    def on_enable(self, api: PluginAPI) -> None:

        api.get_logger("sample.info").info("Sample Info Plugin enabled")

    def on_disable(self, api: PluginAPI) -> None:

        api.get_logger("sample.info").info("Sample Info Plugin disabled")
