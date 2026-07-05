# ============================================================================
# Project X
# Event Bus
# ============================================================================

import logging
from collections import defaultdict
from threading import Lock
from typing import Callable

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

        with self._lock:
            listeners = tuple(self._listeners.get(event_name, ()))

        for callback in listeners:
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.exception(
                    "EventBus handler failed for '%s' -> %s",
                    event_name,
                    callback.__qualname__,
                )

    def listener_count(self, event_name: str):

        with self._lock:
            return len(self._listeners.get(event_name, ()))

    def clear(self):

        with self._lock:
            self._listeners.clear()


eventbus = EventBus()
