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

from storage import active_config_path

logger = logging.getLogger(__name__)

AIS_API_KEY_FILE = Path(
    os.environ.get(
        "PROJECTX_AIS_API_KEY_FILE",
        str(active_config_path("ais_api_key.txt")),
    )
)


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

        if not key:
            try:
                if AIS_API_KEY_FILE.exists():
                    AIS_API_KEY_FILE.unlink()
            except OSError:
                logger.warning(
                    "Failed to remove AIS API key file: %s",
                    AIS_API_KEY_FILE,
                )
            return

        AIS_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        AIS_API_KEY_FILE.write_text(key + "\n", encoding="utf-8")

    def _on_ais_status(self, status: str = "", **kwargs) -> None:

        with self._lock:
            self._ais_status = str(status or "offline")

    def _on_rtl_status(self, status: str = "", **kwargs) -> None:

        with self._lock:
            self._rtl_status = str(status or "offline")


ais_manager = AISManager()
