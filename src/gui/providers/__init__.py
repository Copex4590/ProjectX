# ============================================================================
# Project X
# Provider Windows
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ais.providers import AISProviderType, normalize_provider_type
from core.logger import logger
from gui.providers.aisstream_window import AISStreamWindow
from gui.providers.generic_provider_window import GenericProviderWindow
from gui.providers.provider_window import ProviderWindow
from gui.providers.rtl_window import RTLWindow

_PROVIDER_WINDOWS = {
    AISProviderType.AISSTREAM: AISStreamWindow,
    AISProviderType.LOCAL: RTLWindow,
    AISProviderType.MARINE_TRAFFIC: GenericProviderWindow,
    AISProviderType.AISHUB: GenericProviderWindow,
}

_open_windows: dict[AISProviderType, ProviderWindow] = {}


def _focus_provider_window(window: QWidget) -> None:

    window.show()
    window.raise_()
    window.activateWindow()


def refresh_open_provider_windows(*_args, **_kwargs) -> None:

    from shiboken6 import isValid

    for window in list(_open_windows.values()):
        if not isValid(window):
            continue

        try:
            window.refresh_state()
        except Exception:
            logger.exception("Failed to refresh open provider window")


def open_provider_window(provider_id: str, parent=None) -> None:

    provider = normalize_provider_type(provider_id)
    window_class = _PROVIDER_WINDOWS.get(provider)

    if window_class is None:
        logger.info("Provider window not available: %s", provider_id)
        return

    existing = _open_windows.get(provider)

    if existing is not None:
        existing.refresh_state()
        _focus_provider_window(existing)
        return

    window = window_class(provider.value, parent)
    _open_windows[provider] = window
    window.destroyed.connect(lambda *_args, key=provider: _open_windows.pop(key, None))
    _focus_provider_window(window)
