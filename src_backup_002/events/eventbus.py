# ============================================================================
# Project X
# Event Bus
# Version : 1.0.0
# ============================================================================

from collections import defaultdict
from typing import Callable


class EventBus:

    def __init__(self):

        self._listeners = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable):

        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):

        if callback in self._listeners[event_name]:
            self._listeners[event_name].remove(callback)

    def publish(self, event_name: str, *args, **kwargs):

        for callback in self._listeners[event_name]:
            callback(*args, **kwargs)

    def clear(self):

        self._listeners.clear()


eventbus = EventBus()
