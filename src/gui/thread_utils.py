# ============================================================================
# Project X
# QThread helpers (SAVE-202)
# ============================================================================

from __future__ import annotations

import logging

from PySide6.QtCore import QThread

logger = logging.getLogger(__name__)


def stop_qthread(
    thread: QThread | None,
    *,
    timeout_ms: int = 3000,
    label: str = "QThread",
) -> None:
    """Request quit and wait; log if the worker outlives the timeout."""

    if thread is None:
        return

    if not thread.isRunning():
        return

    thread.requestInterruption()
    thread.quit()

    if thread.wait(timeout_ms):
        return

    logger.warning(
        "%s did not stop within %d ms — terminating",
        label,
        timeout_ms,
    )
    thread.terminate()
    thread.wait(1000)
