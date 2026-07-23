# ============================================================================
# Project X — temporary GUI freeze instrumentation (BUG-TEST-003)
#
# Disabled by default (SAVE-P0). Enable with:
#   PROJECTX_OBS_FREEZE_TRACE=1
# Accepted truthy values: 1, true, yes, on (case-insensitive).
# ============================================================================

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Callable, TypeVar

from app.paths import runtime_data_path

_LOGGER = logging.getLogger("obs_freeze.trace")
_LOGGER.setLevel(logging.INFO)

if not _LOGGER.handlers:
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s: %(message)s")
    )
    _LOGGER.addHandler(_stream_handler)
    _LOGGER.propagate = False

_TRACE_PATH = runtime_data_path("obs_freeze.trace")
_LOCK = threading.Lock()
_SEQ = 0

F = TypeVar("F", bound=Callable)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_trace_enabled() -> bool:
    """Return True only when PROJECTX_OBS_FREEZE_TRACE is explicitly enabled."""

    value = os.environ.get("PROJECTX_OBS_FREEZE_TRACE", "").strip().lower()
    return value in _TRUTHY


def trace_path() -> str:

    return str(_TRACE_PATH)


def reset_trace_log() -> None:

    if not is_trace_enabled():
        return

    global _SEQ

    with _LOCK:
        _SEQ = 0
        _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TRACE_PATH.write_text("", encoding="utf-8")

    trace_event("=== OBS_FREEZE TRACE RESET ===")
    trace_event(f"trace_file={_TRACE_PATH}")


def begin_delete_trace_session(point_id: str) -> None:

    if not is_trace_enabled():
        return

    reset_trace_log()
    trace_event(f"=== DELETE TRACE SESSION point_id={point_id} ===")


def trace_event(label: str) -> None:

    if not is_trace_enabled():
        return

    global _SEQ

    with _LOCK:
        _SEQ += 1
        seq = _SEQ

    thread = threading.current_thread().name
    ts = time.monotonic()
    message = f"[{seq:06d}] t={ts:.6f} thr={thread} {label}"
    line = f"{message}\n"

    with _LOCK:
        _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _TRACE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()

    _LOGGER.info(message)


def trace_enter(label: str) -> None:

    trace_event(f"ENTER {label}")


def trace_exit(label: str) -> None:

    trace_event(f"EXIT {label}")


@contextmanager
def trace_block(label: str):

    if not is_trace_enabled():
        yield
        return

    trace_enter(label)

    try:
        yield
    finally:
        trace_exit(label)


def trace_call(label: str, fn: Callable, *args, **kwargs):

    if not is_trace_enabled():
        return fn(*args, **kwargs)

    trace_enter(label)

    try:
        return fn(*args, **kwargs)
    finally:
        trace_exit(label)


def trace_slot(label: str, fn: Callable) -> Callable:

    if not is_trace_enabled():
        return fn

    def wrapper(*args, **kwargs):

        trace_enter(label)

        try:
            return fn(*args, **kwargs)
        finally:
            trace_exit(label)

    return wrapper


def trace_timer_callback(label: str, fn: Callable) -> Callable:

    if not is_trace_enabled():
        return fn

    def wrapper():

        trace_enter(label)

        try:
            fn()
        finally:
            trace_exit(label)

    return wrapper


def schedule_traced_single_shot(delay_ms: int, label: str, fn: Callable) -> None:

    from PySide6.QtCore import QTimer

    if not is_trace_enabled():
        QTimer.singleShot(delay_ms, fn)
        return

    trace_event(f"SCHEDULE QTimer.singleShot delay_ms={delay_ms} label={label}")
    QTimer.singleShot(delay_ms, trace_timer_callback(label, fn))
