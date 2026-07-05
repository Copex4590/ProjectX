# ============================================================================
# Project X
# Subsystem Status
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SubsystemState(str, Enum):

    WORKING = "working"
    WARNING = "warning"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


class SubsystemAction(str, Enum):

    NONE = ""
    CONFIGURE = "configure"
    TEST = "test"
    DIAGNOSTICS = "diagnostics"
    OPEN_SETTINGS = "open_settings"
    OPEN_DASHBOARD = "open_dashboard"
    OPEN_MAP = "open_map"
    SETUP = "setup"


@dataclass(frozen=True)
class SubsystemHealth:

    subsystem_key: str
    state: SubsystemState
    message_key: str
    message_args: dict[str, object] = field(default_factory=dict)
    action: SubsystemAction = SubsystemAction.NONE
    detail: str = ""


@dataclass(frozen=True)
class SystemHealthReport:

    subsystems: tuple[SubsystemHealth, ...]
    has_errors: bool = False
    has_warnings: bool = False

    @classmethod
    def from_subsystems(cls, subsystems: list[SubsystemHealth]) -> SystemHealthReport:

        has_errors = any(
            item.state == SubsystemState.ERROR for item in subsystems
        )
        has_warnings = any(
            item.state == SubsystemState.WARNING for item in subsystems
        )

        return cls(
            subsystems=tuple(subsystems),
            has_errors=has_errors,
            has_warnings=has_warnings,
        )
