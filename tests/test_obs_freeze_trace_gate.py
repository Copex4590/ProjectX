# ============================================================================
# Project X — SAVE-P0 obs_freeze_trace gate
# ============================================================================

from __future__ import annotations

import pytest


@pytest.fixture
def trace_module():
    import debug.obs_freeze_trace as mod

    return mod


def test_trace_disabled_by_default(trace_module, monkeypatch, tmp_path):
    monkeypatch.delenv("PROJECTX_OBS_FREEZE_TRACE", raising=False)
    monkeypatch.setattr(trace_module, "_TRACE_PATH", tmp_path / "obs_freeze.trace")
    trace_module._SEQ = 0

    assert trace_module.is_trace_enabled() is False

    with trace_module.trace_block("unit"):
        pass

    trace_module.trace_event("should-not-write")
    trace_module.reset_trace_log()
    trace_module.begin_delete_trace_session("x")

    assert not (tmp_path / "obs_freeze.trace").exists()


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " On "])
def test_trace_enabled_writes_file(trace_module, monkeypatch, tmp_path, value):
    monkeypatch.setenv("PROJECTX_OBS_FREEZE_TRACE", value)
    path = tmp_path / "obs_freeze.trace"
    monkeypatch.setattr(trace_module, "_TRACE_PATH", path)
    trace_module._SEQ = 0

    assert trace_module.is_trace_enabled() is True

    trace_module.trace_event("hello")

    assert path.exists()
    assert "hello" in path.read_text(encoding="utf-8")


def test_trace_slot_returns_original_when_disabled(trace_module, monkeypatch):
    monkeypatch.delenv("PROJECTX_OBS_FREEZE_TRACE", raising=False)

    def original():
        return 42

    assert trace_module.trace_slot("label", original) is original
