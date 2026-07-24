# ============================================================================
# Project X
# Shared Internet online flag (SAVE-236 / SAVE-236.5)
# ============================================================================

from __future__ import annotations

from threading import Lock

_lock = Lock()
_online = True


def is_internet_online() -> bool:
    """Last probed Internet reachability (ConnectionPanel is the writer)."""

    with _lock:
        return _online


def set_internet_online(online: bool) -> bool:
    """Update shared Internet flag. Returns True when the value changed."""

    global _online

    online = bool(online)
    with _lock:
        if _online == online:
            return False
        _online = online
        return True
