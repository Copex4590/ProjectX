"""Shared filesystem helpers for unit tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

_TEST_WORKSPACE_ROOT = Path(__file__).resolve().parent / ".projectx-test-workspace"


def isolated_temp_dir() -> tempfile.TemporaryDirectory[str]:
    """Create a writable temp directory outside system temp locations."""

    _TEST_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(_TEST_WORKSPACE_ROOT))
