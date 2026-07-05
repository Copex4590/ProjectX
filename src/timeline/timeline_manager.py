# ============================================================================
# Project X
# Vessel Timeline Manager
# ============================================================================

from timeline.timeline_record import TimelineRecord
from timeline.timeline_registry import (
    TIMELINE_DATABASE_FILE,
    TimelineRegistry,
    timeline_registry,
)


class TimelineManager:

    def __init__(self, registry: TimelineRegistry | None = None):

        self._registry = registry or timeline_registry

    def append(self, record: TimelineRecord) -> TimelineRecord:

        return self._registry.append(record)

    def history(self, mmsi: int | str) -> list[TimelineRecord]:

        return self._registry.history(mmsi)

    def latest(self, mmsi: int | str) -> TimelineRecord | None:

        return self._registry.latest(mmsi)

    def count(self) -> int:

        return self._registry.count()

    def all(self) -> list[TimelineRecord]:

        return self._registry.all()


timeline_manager = TimelineManager()
