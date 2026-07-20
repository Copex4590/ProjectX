# ============================================================================
# Project X
# AIS Manager
# ============================================================================

from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Lock

from ais.providers import get_provider, normalize_provider_type, provider_display_name
from ais.providers.provider import AISTestResult
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from events import eventbus
from preferences import preferences_manager

from storage.deferred_paths import deferred_config_path
from storage.lazy_singleton import LazySingleton, lazy_module_getattr

logger = logging.getLogger(__name__)


def ais_api_key_file() -> Path:
    """Return the active AIS API key file path."""

    return deferred_config_path("PROJECTX_AIS_API_KEY_FILE", "ais_api_key.txt")


class AISManager:

    def __init__(self):

        self._lock = Lock()
        self._ais_status = "offline"
        self._rtl_status = "offline"
        self._started = False

    def start(self) -> None:

        if self._started:
            return

        eventbus.subscribe("ais.status", self._on_ais_status)
        eventbus.subscribe("rtl.status", self._on_rtl_status)
        self._started = True

    def ais_connection_status(self) -> str:

        with self._lock:
            return self._ais_status

    def rtl_connection_status(self) -> str:

        with self._lock:
            return self._rtl_status

    def is_configured(self) -> bool:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        if provider.value == "later":
            return False

        return bool(preferences.ais_configured)

    def is_connected(self) -> bool:

        preferences = preferences_manager.get()
        provider = normalize_provider_type(preferences.ais_provider)

        with self._lock:
            if provider.value == "aisstream":
                return self._ais_status == "connected"

            if provider.value == "local":
                return self._rtl_status == "connected"

            if provider.value == "hybrid":
                return (
                    self._ais_status == "connected"
                    and self._rtl_status == "connected"
                )

        return False

    def provider_name(self) -> str:

        preferences = preferences_manager.get()
        return provider_display_name(preferences.ais_provider)

    def test_current(self):

        preferences = preferences_manager.get()
        return self.test_configuration(
            provider_type=preferences.ais_provider,
            api_key=preferences.aisstream_api_key,
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
        )

    def test_configuration(
        self,
        *,
        provider_type: str,
        api_key: str = "",
        host: str = "",
        port: int = 0,
    ):

        provider = get_provider(provider_type)

        if provider is None:
            return AISTestResult(
                success=True,
                message="AIS source skipped.",
            )

        return provider.test(
            api_key=api_key,
            host=host or AIS_CATCHER_HOST,
            port=port or AIS_CATCHER_PORT,
        )

    def save_configuration(
        self,
        *,
        provider_type: str,
        api_key: str = "",
        host: str = "",
        port: int = 0,
        configured: bool = True,
    ) -> None:

        preferences_manager.set_ais_configuration(
            provider_type=provider_type,
            api_key=api_key,
            host=host,
            port=port,
            configured=configured,
        )
        self._sync_api_key_file(api_key)

    def _sync_api_key_file(self, api_key: str) -> None:

        key = str(api_key or "").strip()
        api_key_file = ais_api_key_file()

        if not key:
            try:
                if api_key_file.exists():
                    api_key_file.unlink()
            except OSError:
                logger.warning(
                    "Failed to remove AIS API key file: %s",
                    api_key_file,
                )
            return

        api_key_file.parent.mkdir(parents=True, exist_ok=True)
        api_key_file.write_text(key + "\n", encoding="utf-8")

    def _on_ais_status(self, status: str = "", **kwargs) -> None:

        normalized = str(status or "offline")

        with self._lock:
            previous = self._ais_status
            self._ais_status = normalized

        if previous != normalized:
            logger.info("AIS connection status: %s -> %s", previous, normalized)

    def _on_rtl_status(self, status: str = "", **kwargs) -> None:

        with self._lock:
            self._rtl_status = str(status or "offline")


get_ais_manager = LazySingleton(AISManager)


def __getattr__(name: str):
    if name == "AIS_API_KEY_FILE":
        return ais_api_key_file()
    return lazy_module_getattr(
        name,
        module_name=__name__,
        export_name="ais_manager",
        getter=get_ais_manager,
    )
