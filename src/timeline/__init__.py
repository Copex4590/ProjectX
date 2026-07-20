from timeline.timeline_manager import TimelineManager
from timeline.timeline_recorder import (
    EVENT_POSITION_UPDATE,
    TimelineRecorder,
)
from timeline.timeline_record import TimelineRecord
from timeline.timeline_registry import TimelineRegistry
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "EVENT_POSITION_UPDATE",
    "TIMELINE_DATABASE_FILE",
    "TimelineManager",
    "TimelineRecorder",
    "TimelineRecord",
    "TimelineRegistry",
    "timeline_manager",
    "timeline_recorder",
    "timeline_registry",
]


def __getattr__(name: str):
    if name == "timeline_manager":
        return lazy_submodule_export(__name__, name)
    if name == "timeline_recorder":
        return lazy_submodule_export(__name__, name)
    if name == "timeline_registry":
        return lazy_submodule_export(__name__, name)
    if name == "TIMELINE_DATABASE_FILE":
        from timeline.timeline_registry import timeline_database_file

        return timeline_database_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
