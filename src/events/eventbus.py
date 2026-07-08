# ============================================================================
# Project X
# Event Bus
# ============================================================================

import logging
from collections import defaultdict
from threading import Lock
from typing import Callable

from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit

logger = logging.getLogger(__name__)


class EventBus:

    def __init__(self):

        self._listeners = defaultdict(list)
        self._lock = Lock()

    def subscribe(self, event_name: str, callback: Callable):

        with self._lock:

            if callback not in self._listeners[event_name]:
                self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):

        with self._lock:

            if callback in self._listeners[event_name]:
                self._listeners[event_name].remove(callback)

    def publish(self, event_name: str, *args, **kwargs):

        with trace_block(f"EventBus.publish event={event_name}"):
            with self._lock:
                listeners = tuple(self._listeners.get(event_name, ()))

            for callback in listeners:
                label = (
                    f"EventBus.publish.{event_name}"
                    f"->{getattr(callback, '__qualname__', repr(callback))}"
                )
                trace_enter(label)

                try:
                    callback(*args, **kwargs)
                except Exception:
                    logger.exception(
                        "EventBus handler failed for '%s' -> %s",
                        event_name,
                        callback.__qualname__,
                    )
                finally:
                    trace_exit(label)

    def listener_count(self, event_name: str):

        with self._lock:
            return len(self._listeners.get(event_name, ()))

    def clear(self):

        with self._lock:
            self._listeners.clear()


eventbus = EventBus()
