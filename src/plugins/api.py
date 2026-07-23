# ============================================================================
# Project X
# Plugin Framework — Plugin API (SAVE-212)
# ============================================================================

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from version import PROJECT_NAME, PROJECT_VERSION

from plugins.metadata import PLUGIN_API_VERSION


class PluginAPI:
    """
    Host services exposed to plugins.

    Intentionally small and stable — built-in AIS / Camera / Database modules
    are not exposed as plugins yet (SAVE-212).
    """

    def __init__(self) -> None:

        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    @property
    def api_version(self) -> str:

        return PLUGIN_API_VERSION

    @property
    def app_name(self) -> str:

        return PROJECT_NAME

    @property
    def app_version(self) -> str:

        return PROJECT_VERSION

    def get_logger(self, name: str) -> logging.Logger:

        plugin_name = str(name or "plugin").strip() or "plugin"
        return logging.getLogger(f"plugins.{plugin_name}")

    def register_hook(self, hook_name: str, callback: Callable[..., Any]) -> None:

        key = str(hook_name or "").strip()
        if not key or not callable(callback):
            return

        self._hooks.setdefault(key, []).append(callback)

    def unregister_hook(self, hook_name: str, callback: Callable[..., Any]) -> None:

        key = str(hook_name or "").strip()
        callbacks = self._hooks.get(key)
        if not callbacks:
            return

        self._hooks[key] = [item for item in callbacks if item is not callback]
        if not self._hooks[key]:
            self._hooks.pop(key, None)

    def emit_hook(self, hook_name: str, **payload: Any) -> list[Any]:

        key = str(hook_name or "").strip()
        results: list[Any] = []

        for callback in list(self._hooks.get(key, [])):
            try:
                results.append(callback(**payload))
            except Exception:
                logging.getLogger(__name__).exception(
                    "Plugin hook %s failed",
                    key,
                )

        return results
