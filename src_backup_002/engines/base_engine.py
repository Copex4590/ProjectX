# ============================================================================
# Project X
# Base Engine
# ============================================================================

from abc import ABC, abstractmethod

from events import eventbus


class BaseEngine(ABC):

    def __init__(self, name: str):

        self.name = name
        self.running = False

    def start(self):

        if self.running:
            return

        self.running = True

        eventbus.publish(
            "engine.started",
            engine=self
        )

        self.on_start()

    def stop(self):

        if not self.running:
            return

        self.running = False

        eventbus.publish(
            "engine.stopped",
            engine=self
        )

        self.on_stop()

    @abstractmethod
    def on_start(self):
        ...

    @abstractmethod
    def on_stop(self):
        ...
