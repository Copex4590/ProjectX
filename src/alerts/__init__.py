from alerts.alert_event import AlertEvent, EvaluationEvent
from alerts.alert_manager import AlertManager
from alerts.alert_registry import AlertRegistry
from alerts.alert_rule import (
    RULE_TYPE_ARRIVAL,
    RULE_TYPE_CAMERA_LOST,
    RULE_TYPE_CAMERA_VISIBLE,
    RULE_TYPE_DEPARTURE,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_SPEED_OVER,
    SUPPORTED_RULE_TYPES,
    AlertRule,
)
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "ALERT_DATABASE_FILE",
    "AlertEvent",
    "AlertManager",
    "AlertRegistry",
    "AlertRule",
    "EvaluationEvent",
    "RULE_TYPE_ARRIVAL",
    "RULE_TYPE_CAMERA_LOST",
    "RULE_TYPE_CAMERA_VISIBLE",
    "RULE_TYPE_DEPARTURE",
    "RULE_TYPE_ENTER_REGION",
    "RULE_TYPE_EXIT_REGION",
    "RULE_TYPE_SPEED_OVER",
    "SUPPORTED_RULE_TYPES",
    "alert_manager",
    "alert_registry",
]


def __getattr__(name: str):
    if name == "alert_manager":
        return lazy_submodule_export(__name__, name)
    if name == "alert_registry":
        return lazy_submodule_export(__name__, name)
    if name == "ALERT_DATABASE_FILE":
        from alerts.alert_registry import alert_database_file

        return alert_database_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
