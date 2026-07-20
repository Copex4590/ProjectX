# ============================================================================
# Project X
# Vessel Timeline Manager
# ============================================================================

from storage.lazy_singleton import LazySingleton, lazy_module_getattr
from timeline.timeline_record import TimelineRecord
from timeline.timeline_registry import TimelineRegistry


class TimelineManager:

    def __init__(self, registry: TimelineRegistry | None = None):

        self._registry = registry

    def _registry_instance(self) -> TimelineRegistry:

        if self._registry is None:
            from timeline.timeline_registry import get_timeline_registry

            self._registry = get_timeline_registry()

        return self._registry

    def append(self, record: TimelineRecord) -> TimelineRecord:

        return self._registry_instance().append(record)

    def history(self, mmsi: int | str) -> list[TimelineRecord]:

        return self._registry_instance().history(mmsi)

    def latest(self, mmsi: int | str) -> TimelineRecord | None:

        return self._registry_instance().latest(mmsi)

    def count(self) -> int:

        return self._registry_instance().count()

    def all(self) -> list[TimelineRecord]:

        return self._registry_instance().all()


get_timeline_manager = LazySingleton(TimelineManager)


def __getattr__(name: str):
    return lazy_module_getattr(
        name,
        module_name=__name__,
        export_name="timeline_manager",
        getter=get_timeline_manager,
    )
