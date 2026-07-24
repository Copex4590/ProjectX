# ============================================================================
# Project X — Deferred background page loading (SAVE-228)
# ============================================================================
"""Load expensive page payloads off the GUI thread.

``DeferredDataLoader`` runs a callable on a ``QThread``, delivers the result
back to the owner widget, and ignores stale results when the owner is destroyed
or a newer load superseded the job.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import QLabel, QWidget
from shiboken6 import isValid

from gui.theme import ThemeColors
from gui.thread_utils import stop_qthread
from i18n import tr

logger = logging.getLogger(__name__)

LoaderFn = Callable[[], Any]


class _DeferredWorker(QThread):
    """Background worker that emits ``(payload, generation)``."""

    finished_with_generation = Signal(object, int)
    failed_with_generation = Signal(str, int)

    def __init__(self, loader: LoaderFn, generation: int, parent: QObject | None = None):
        super().__init__(parent)
        self._loader = loader
        self._generation = generation

    def run(self) -> None:

        try:
            if self.isInterruptionRequested():
                return
            payload = self._loader()
            if self.isInterruptionRequested():
                return
            self.finished_with_generation.emit(payload, self._generation)
        except Exception as exc:
            logger.exception("Deferred page load failed")
            self.failed_with_generation.emit(str(exc) or type(exc).__name__, self._generation)


class DeferredDataLoader(QObject):
    """One-at-a-time background loader owned by a page widget."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, owner: QWidget):
        super().__init__(owner)
        self._owner = owner
        self._generation = 0
        self._worker: _DeferredWorker | None = None
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def start(self, loader: LoaderFn, *, force: bool = False) -> bool:
        """Start ``loader`` in a worker thread.

        Returns ``True`` if a new job was started. When ``force`` is False and a
        job is already running, returns ``False`` (no duplicate). When ``force``
        is True, the in-flight generation is invalidated and a new job starts.
        """

        if self._busy and not force:
            return False

        if self._busy and force:
            self.cancel(stop_worker=False)

        self._generation += 1
        generation = self._generation
        self._busy = True

        worker = _DeferredWorker(loader, generation, self)
        worker.finished_with_generation.connect(
            self._on_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.failed_with_generation.connect(
            self._on_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()
        return True

    def cancel(self, *, stop_worker: bool = True) -> None:
        """Invalidate in-flight results; optionally stop the worker thread."""

        self._generation += 1
        self._busy = False
        worker = self._worker
        self._worker = None
        if stop_worker and worker is not None:
            stop_qthread(worker, label="DeferredDataLoader")

    def _accepts(self, generation: int) -> bool:

        if generation != self._generation:
            return False
        owner = self._owner
        if owner is None or not isValid(owner):
            return False
        return True

    def _on_finished(self, payload: object, generation: int) -> None:

        if not self._accepts(generation):
            return
        self._busy = False
        self._worker = None
        self.finished.emit(payload)

    def _on_failed(self, message: str, generation: int) -> None:

        if not self._accepts(generation):
            return
        self._busy = False
        self._worker = None
        self.failed.emit(message)


def make_loading_label(parent: QWidget | None = None) -> QLabel:
    """Compact status line used while deferred data is loading."""

    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"color: {ThemeColors.TextSecondary}; font-size: 10pt; padding: 4px;"
    )
    label.hide()
    label.setText(tr("Loading…"))
    return label
