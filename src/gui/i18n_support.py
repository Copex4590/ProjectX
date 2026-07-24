# ============================================================================
# Project X
# GUI Localization Support
# ============================================================================
"""Bind UI refresh callbacks to language changes without dangling slots.

``language_manager`` is a process-wide singleton. Connecting a bare lambda to
``language_changed`` keeps a strong reference to a bound method and is *not*
tied to the QObject lifetime — so ``WA_DeleteOnClose`` dialogs (e.g.
ObservationWizard) stay registered after the C++ object is gone and raise:

    RuntimeError: Internal C++ object (...) already deleted

The binder parents a small helper QObject to the widget/dialog that owns the
refresh method. When that owner is destroyed, Qt destroys the helper and
disconnects its slots automatically. Calls also guard with ``isValid``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject
from shiboken6 import isValid

from i18n import language_manager

logger = logging.getLogger(__name__)


class _LanguageRefreshBinding(QObject):
    """Owns one language_changed → refresh_method connection for ``parent``."""

    def __init__(self, owner: QObject, refresh_method: Callable[[], None]):
        super().__init__(owner)
        self._refresh_method = refresh_method
        language_manager.language_changed.connect(self._on_language_changed)

    def _on_language_changed(self, _code: str) -> None:

        owner = self.parent()
        if owner is None or not isValid(owner) or not isValid(self):
            return

        try:
            self._refresh_method()
        except RuntimeError:
            # C++ counterpart already deleted (race with teardown).
            logger.debug(
                "Skipped language refresh on deleted object %r",
                owner,
                exc_info=True,
            )


def bind_language_refresh(refresh_method: Callable[[], None]) -> None:
    """Register ``refresh_method`` for future language changes.

    Prefer bound methods on a ``QObject`` (``self.refresh_translations``).
    Those are unregistered automatically when the owner is destroyed.
    """

    owner = getattr(refresh_method, "__self__", None)

    if isinstance(owner, QObject):
        _LanguageRefreshBinding(owner, refresh_method)
        return

    # Rare non-QObject callable: keep previous behaviour (caller must manage life).
    language_manager.language_changed.connect(
        lambda _code, method=refresh_method: method()
    )
