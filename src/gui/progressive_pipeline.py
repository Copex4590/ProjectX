# ============================================================================
# Project X — Progressive data pipeline (SAVE-229)
# ============================================================================
"""Stream page datasets to the GUI in batches instead of waiting for a full load.

``ProgressiveDataPipeline`` runs a producer on a ``QThread``, emits each batch
as soon as it is ready, then delivers the assembled payload on completion.
Stale generations are ignored; duplicate loaders are refused unless ``force``.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from gui.thread_utils import stop_qthread

logger = logging.getLogger(__name__)

DEFAULT_PROGRESSIVE_BATCH_SIZE = 200
_ENV_BATCH_SIZE = "PROJECTX_PROGRESSIVE_BATCH_SIZE"

ProducerFn = Callable[[], Iterable[Any]]
AssembleFn = Callable[[list[Any]], Any]


def progressive_batch_size(default: int = DEFAULT_PROGRESSIVE_BATCH_SIZE) -> int:
    """Configurable batch size (env ``PROJECTX_PROGRESSIVE_BATCH_SIZE``)."""

    raw = os.environ.get(_ENV_BATCH_SIZE)
    if raw is None or not str(raw).strip():
        return max(1, int(default))
    try:
        value = int(str(raw).strip())
    except ValueError:
        return max(1, int(default))
    return max(1, min(value, 10_000))


@dataclass
class ProgressiveLoadMetrics:
    """Instrumentation captured for one progressive load cycle."""

    time_to_first_visible_ms: float | None = None
    total_load_ms: float | None = None
    batch_count: int = 0
    rows_per_batch: int = 0
    total_rows: int = 0
    ui_pulses_during_load: int = 0
    started_at: float = field(default_factory=time.perf_counter)
    first_batch_at: float | None = None
    finished_at: float | None = None

    def mark_first_batch(self) -> None:

        if self.first_batch_at is None:
            self.first_batch_at = time.perf_counter()

    def mark_first_visible(self) -> None:

        if self.time_to_first_visible_ms is not None:
            return
        self.time_to_first_visible_ms = (
            time.perf_counter() - self.started_at
        ) * 1000.0

    def finalize(self) -> None:

        self.finished_at = time.perf_counter()
        self.total_load_ms = (self.finished_at - self.started_at) * 1000.0
        if self.batch_count > 0 and self.total_rows > 0:
            self.rows_per_batch = max(1, round(self.total_rows / self.batch_count))


def _batch_row_count(batch: Any) -> int:

    if batch is None:
        return 0
    if isinstance(batch, list):
        return len(batch)
    if isinstance(batch, dict):
        if batch.get("meta"):
            return 0
        for key in ("records", "rows", "items"):
            value = batch.get(key)
            if isinstance(value, list):
                return len(value)
        return 1
    return 1


class _ProgressiveWorker(QThread):
    """Background worker that streams batches then the assembled payload."""

    batch_with_generation = Signal(object, int, int)  # batch, index, generation
    finished_with_generation = Signal(object, int)  # assembled, generation
    failed_with_generation = Signal(str, int)

    def __init__(
        self,
        producer: ProducerFn,
        assemble: AssembleFn,
        generation: int,
        metrics: ProgressiveLoadMetrics,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._producer = producer
        self._assemble = assemble
        self._generation = generation
        self._metrics = metrics

    def run(self) -> None:

        batches: list[Any] = []
        try:
            iterator: Iterator[Any] = iter(self._producer())
            index = 0
            while True:
                if self.isInterruptionRequested():
                    return
                try:
                    batch = next(iterator)
                except StopIteration:
                    break
                if self.isInterruptionRequested():
                    return
                batches.append(batch)
                self._metrics.batch_count += 1
                self._metrics.total_rows += _batch_row_count(batch)
                self._metrics.mark_first_batch()
                self.batch_with_generation.emit(batch, index, self._generation)
                index += 1

            if self.isInterruptionRequested():
                return
            assembled = self._assemble(batches)
            if self.isInterruptionRequested():
                return
            self.finished_with_generation.emit(assembled, self._generation)
        except Exception as exc:
            logger.exception("Progressive page load failed")
            self.failed_with_generation.emit(
                str(exc) or type(exc).__name__,
                self._generation,
            )


def _default_assemble(batches: list[Any]) -> Any:
    """Flatten list batches; otherwise return the batch list as-is."""

    if not batches:
        return []
    if all(isinstance(batch, list) for batch in batches):
        assembled: list[Any] = []
        for batch in batches:
            assembled.extend(batch)
        return assembled
    return batches


class ProgressiveDataPipeline(QObject):
    """One-at-a-time progressive loader owned by a page widget."""

    batch_ready = Signal(object, int)  # batch, index
    finished = Signal(object)  # assembled payload
    failed = Signal(str)

    def __init__(self, owner: QWidget):
        super().__init__(owner)
        self._owner = owner
        self._generation = 0
        self._worker: _ProgressiveWorker | None = None
        self._busy = False
        self._metrics: ProgressiveLoadMetrics | None = None
        self.last_metrics: ProgressiveLoadMetrics | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def metrics(self) -> ProgressiveLoadMetrics | None:
        return self._metrics

    def start(
        self,
        producer: ProducerFn,
        *,
        force: bool = False,
        assemble: AssembleFn | None = None,
    ) -> bool:
        """Start streaming ``producer`` batches on a worker thread.

        Returns ``True`` if a new job started. When ``force`` is False and a
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
        self._metrics = ProgressiveLoadMetrics()
        self.last_metrics = self._metrics

        worker = _ProgressiveWorker(
            producer,
            assemble or _default_assemble,
            generation,
            self._metrics,
            self,
        )
        worker.batch_with_generation.connect(
            self._on_batch,
            Qt.ConnectionType.QueuedConnection,
        )
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
        if self._metrics is not None and self._metrics.total_load_ms is None:
            self._metrics.finalize()
        worker = self._worker
        self._worker = None
        if stop_worker and worker is not None:
            stop_qthread(worker, label="ProgressiveDataPipeline")

    def note_ui_pulse(self) -> None:
        """Count an event-loop pulse while a load is in flight (responsiveness)."""

        if self._busy and self._metrics is not None:
            self._metrics.ui_pulses_during_load += 1

    def note_first_visible(self) -> None:
        """Record time-to-first-visible-row once the GUI shows the first batch."""

        if self._metrics is not None:
            self._metrics.mark_first_visible()

    def _accepts(self, generation: int) -> bool:

        if generation != self._generation:
            return False
        owner = self._owner
        if owner is None or not isValid(owner):
            return False
        return True

    def _on_batch(self, batch: object, index: int, generation: int) -> None:

        if not self._accepts(generation):
            return
        self.batch_ready.emit(batch, index)

    def _on_finished(self, payload: object, generation: int) -> None:

        if not self._accepts(generation):
            return
        if self._metrics is not None:
            self._metrics.finalize()
        self._busy = False
        self._worker = None
        self.finished.emit(payload)

    def _on_failed(self, message: str, generation: int) -> None:

        if not self._accepts(generation):
            return
        if self._metrics is not None:
            self._metrics.finalize()
        self._busy = False
        self._worker = None
        self.failed.emit(message)
