# ============================================================================
# Project X
# Notification severity levels
# ============================================================================

from __future__ import annotations

from enum import Enum


class NotificationSeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
