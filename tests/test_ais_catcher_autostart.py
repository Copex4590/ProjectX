#!/usr/bin/env python3
# ============================================================================
# Project X — AIS-Catcher auto-start / endpoint regression tests
# ============================================================================

from __future__ import annotations

import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engines.ais import ais_catcher_launcher as launcher
from engines.rtl.hybrid_engine import (
    RTL_CATCHER_RETRY_MIN_S,
    RTL_CATCHER_UNAVAILABLE_LOG_INTERVAL_S,
    HybridEngine,
)


def test_build_ais_catcher_args_overrides_default_port():

    with patch.object(launcher, "AIS_CATCHER_ARGS", ["-d:0", "-o", "5", "-S", "10110"]):
        assert launcher.build_ais_catcher_args(port=19999) == [
            "-d:0",
            "-o",
            "5",
            "-S",
            "19999",
        ]


def test_build_ais_catcher_args_handles_compact_dash_s():

    with patch.object(launcher, "AIS_CATCHER_ARGS", ["-d:0", "-S10110"]):
        assert launcher.build_ais_catcher_args(port=20202) == [
            "-d:0",
            "-S",
            "20202",
        ]


def test_ensure_already_running_does_not_relaunch():

    with (
        patch.object(launcher, "is_port_open", return_value=True) as port_open,
        patch.object(launcher.subprocess, "Popen") as popen,
    ):
        assert launcher.ensure_ais_catcher_ready(host="127.0.0.1", port=10110) is True
        port_open.assert_called_with("127.0.0.1", 10110)
        popen.assert_not_called()


def test_ensure_starts_with_custom_host_port():

    exe = Path("/tmp/fake-AIS-catcher")
    calls: list[tuple] = []

    def fake_port_open(host, port, timeout=1.0):
        # Closed before launch; open after Popen.
        return bool(calls)

    def fake_popen(command, **_kwargs):
        calls.append(tuple(command))
        return MagicMock()

    with (
        patch.object(launcher, "is_port_open", side_effect=fake_port_open),
        patch.object(launcher, "wait_for_port", return_value=True),
        patch.object(launcher.subprocess, "Popen", side_effect=fake_popen),
        patch.object(Path, "is_file", return_value=True),
    ):
        assert (
            launcher.ensure_ais_catcher_ready(
                host="127.0.0.1",
                port=19999,
                executable=exe,
            )
            is True
        )

    assert len(calls) == 1
    assert calls[0][0] == str(exe)
    assert calls[0][-2:] == ("-S", "19999")


def test_ensure_launcher_failure_returns_false():

    with (
        patch.object(launcher, "is_port_open", return_value=False),
        patch.object(Path, "is_file", return_value=True),
        patch.object(
            launcher.subprocess,
            "Popen",
            side_effect=OSError("boom"),
        ),
    ):
        assert launcher.ensure_ais_catcher_ready(host="localhost", port=10110) is False


def test_ensure_missing_executable_returns_false():

    with (
        patch.object(launcher, "is_port_open", return_value=False),
        patch.object(Path, "is_file", return_value=False),
        patch.object(launcher.subprocess, "Popen") as popen,
    ):
        assert launcher.ensure_ais_catcher_ready() is False
        popen.assert_not_called()


def _engine_stub() -> HybridEngine:
    engine = HybridEngine.__new__(HybridEngine)
    engine.running = True
    engine._rtl_active = True
    engine._rtl_catcher_retry_s = RTL_CATCHER_RETRY_MIN_S
    engine._rtl_catcher_last_warning_at = 0.0
    engine._rtl_client = None
    return engine


def test_should_auto_start_requires_rtl_auto_connect_and_pref():

    engine = _engine_stub()

    with (
        patch.object(engine, "_rtl_enabled", return_value=True),
        patch(
            "engines.rtl.hybrid_engine._ais_connection_preferences",
            return_value=(True, True, 1.0, 60.0, 10.0),
        ),
        patch(
            "engines.rtl.hybrid_engine.preferences_manager.get",
            return_value=MagicMock(rtl_auto_start_ais_catcher=True),
        ),
    ):
        assert engine._should_auto_start_ais_catcher() is True

    with (
        patch.object(engine, "_rtl_enabled", return_value=True),
        patch(
            "engines.rtl.hybrid_engine._ais_connection_preferences",
            return_value=(True, True, 1.0, 60.0, 10.0),
        ),
        patch(
            "engines.rtl.hybrid_engine.preferences_manager.get",
            return_value=MagicMock(rtl_auto_start_ais_catcher=False),
        ),
    ):
        assert engine._should_auto_start_ais_catcher() is False

    with (
        patch.object(engine, "_rtl_enabled", return_value=False),
        patch(
            "engines.rtl.hybrid_engine._ais_connection_preferences",
            return_value=(True, True, 1.0, 60.0, 10.0),
        ),
        patch(
            "engines.rtl.hybrid_engine.preferences_manager.get",
            return_value=MagicMock(rtl_auto_start_ais_catcher=True),
        ),
    ):
        assert engine._should_auto_start_ais_catcher() is False


def test_wait_for_catcher_already_up_skips_ensure():

    engine = _engine_stub()
    with (
        patch("engines.rtl.hybrid_engine.is_port_open", return_value=True),
        patch("engines.rtl.hybrid_engine.ensure_ais_catcher_ready") as ensure,
    ):
        assert engine._wait_for_ais_catcher("localhost", 10110) is True
        ensure.assert_not_called()


def test_wait_for_catcher_auto_starts_when_down():

    engine = _engine_stub()
    with (
        patch(
            "engines.rtl.hybrid_engine.is_port_open",
            side_effect=[False, True],
        ),
        patch.object(engine, "_should_auto_start_ais_catcher", return_value=True),
        patch(
            "engines.rtl.hybrid_engine.ensure_ais_catcher_ready",
            return_value=True,
        ) as ensure,
    ):
        assert engine._wait_for_ais_catcher("127.0.0.1", 19999) is True
        ensure.assert_called_once_with(host="127.0.0.1", port=19999)


def test_wait_for_catcher_no_autostart_does_not_launch():

    engine = _engine_stub()
    with (
        patch("engines.rtl.hybrid_engine.is_port_open", return_value=False),
        patch.object(engine, "_should_auto_start_ais_catcher", return_value=False),
        patch("engines.rtl.hybrid_engine.ensure_ais_catcher_ready") as ensure,
        patch("engines.rtl.hybrid_engine.eventbus.publish"),
        patch("engines.rtl.hybrid_engine.time.sleep") as sleep,
    ):
        assert engine._wait_for_ais_catcher("localhost", 10110) is False
        ensure.assert_not_called()
        sleep.assert_called()


def test_wait_for_catcher_failure_backoff_and_throttled_warning(caplog):

    engine = _engine_stub()
    engine._rtl_catcher_last_warning_at = 0.0

    with (
        patch("engines.rtl.hybrid_engine.is_port_open", return_value=False),
        patch.object(engine, "_should_auto_start_ais_catcher", return_value=True),
        patch(
            "engines.rtl.hybrid_engine.ensure_ais_catcher_ready",
            return_value=False,
        ),
        patch("engines.rtl.hybrid_engine.eventbus.publish"),
        patch("engines.rtl.hybrid_engine.time.sleep"),
        caplog.at_level(logging.WARNING),
    ):
        assert engine._wait_for_ais_catcher("localhost", 10110) is False
        first_retry = engine._rtl_catcher_retry_s
        assert first_retry > RTL_CATCHER_RETRY_MIN_S

        # Immediate second call must not emit another warning (throttle).
        warning_count = sum(
            1
            for record in caplog.records
            if "AIS-Catcher unavailable" in record.getMessage()
        )
        assert warning_count == 1

        engine._rtl_catcher_last_warning_at = (
            time.monotonic() - RTL_CATCHER_UNAVAILABLE_LOG_INTERVAL_S - 1
        )
        assert engine._wait_for_ais_catcher("localhost", 10110) is False
        warning_count = sum(
            1
            for record in caplog.records
            if "AIS-Catcher unavailable" in record.getMessage()
        )
        assert warning_count == 2


def test_on_start_starts_aisstream_even_when_rtl_disabled():

    engine = HybridEngine.__new__(HybridEngine)
    engine.ais_thread = None
    engine.rtl_thread = None
    engine._runtime_lock = __import__("threading").Lock()
    engine._aisstream_active = False
    engine._rtl_active = False
    engine._resubscribe_requested = False
    engine._ws = None
    engine._rtl_client = None
    engine._rtl_reconnect_requested = False
    engine._rtl_catcher_retry_s = RTL_CATCHER_RETRY_MIN_S
    engine._rtl_catcher_last_warning_at = 0.0

    started: list[str] = []

    class FakeThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon
            self._alive = False

        def start(self):
            self._alive = True
            name = getattr(self.target, "__name__", "")
            started.append(name)

        def is_alive(self):
            return self._alive

    with (
        patch("engines.rtl.hybrid_engine.hybrid_file_writer.start"),
        patch.object(engine, "sync_enabled_providers"),
        patch("engines.rtl.hybrid_engine.eventbus.subscribe"),
        patch("engines.rtl.hybrid_engine.threading.Thread", FakeThread),
        patch.object(engine, "_rtl_enabled", return_value=False),
        patch("engines.rtl.hybrid_engine.ensure_ais_catcher_ready") as ensure,
    ):
        HybridEngine.on_start(engine)

    assert "aisstream_worker" in started
    assert "rtl_worker" in started
    ensure.assert_not_called()


def test_rtl_endpoint_uses_preferences():

    engine = _engine_stub()
    prefs = MagicMock(ais_local_host="10.0.0.5", ais_local_port=20202)
    with patch(
        "engines.rtl.hybrid_engine.preferences_manager.get",
        return_value=prefs,
    ):
        assert engine._rtl_endpoint() == ("10.0.0.5", 20202)


def test_rtl_manager_passes_prefs_endpoint_to_launcher():

    from rtl.rtl_manager import RTLManager

    manager = RTLManager()
    prefs = MagicMock(
        rtl_auto_start_ais_catcher=True,
        ais_local_host="192.168.1.9",
        ais_local_port=30303,
    )
    with (
        patch("rtl.rtl_manager.preferences_manager.get", return_value=prefs),
        patch("rtl.rtl_manager.ensure_ais_catcher_ready", return_value=True) as ensure,
    ):
        assert manager.ensure_ais_catcher() is True
        ensure.assert_called_once_with(host="192.168.1.9", port=30303)
