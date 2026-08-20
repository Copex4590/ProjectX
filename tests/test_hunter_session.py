# ============================================================================
# Project X
# Hunter live session mapping + import smoke
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cameras.hunter_session import (
    camera_result_provider_type,
    camera_result_stream_url,
)


def test_camera_result_stream_url_maps_source():
    result = SimpleNamespace(camera_source_url="https://cdn.example.com/live.m3u8")
    assert camera_result_stream_url(result) == "https://cdn.example.com/live.m3u8"


def test_camera_result_provider_type_hls():
    result = SimpleNamespace(source_type=SimpleNamespace(value="hls"))
    assert camera_result_provider_type(result) == "hls"


def test_hunter_session_module_has_no_hunter_gui_import():
    import cameras.hunter_session as module

    assert "camera_hunter.ui" not in sys.modules
    assert "camera_hunter.app.main" not in sys.modules
    assert module.hunter_live_session._engine is None
    assert module.hunter_live_session._headless is False


def test_ensure_passes_headless_into_discovery_engine():
    from unittest.mock import MagicMock, patch

    from cameras.hunter_session import HunterLiveSession

    session = HunterLiveSession(headless=True)
    fake_player = MagicMock()
    fake_player.widget = MagicMock()
    fake_engine = MagicMock()
    with patch(
        "camera_hunter.engine.hls_player.HlsPlayer",
        return_value=fake_player,
    ):
        with patch(
            "camera_hunter.engine.DiscoveryEngine",
            return_value=fake_engine,
        ) as engine_cls:
            session.ensure()
    engine_cls.assert_called_once()
    assert engine_cls.call_args.kwargs.get("headless") is True
    fake_player.widget.setAttribute.assert_called()


def test_stop_then_discover_replaces_busy_live_session():
    """Victoria/live stays busy until stop(); the next camera must start, not reject."""

    from cameras.hunter_session import HunterLiveSession

    session = HunterLiveSession()
    engine = SimpleNamespace(is_busy=True, abort_calls=0, finish_calls=0, discovered=None)

    def abort_in_flight():
        engine.abort_calls += 1
        engine.is_busy = False

    def finish_session(timed_out=False):
        engine.finish_calls += 1

    def discover(url, interactive=False):
        engine.discovered = (url, interactive)
        engine.is_busy = True

    engine.abort_in_flight = abort_in_flight
    engine.finish_session = finish_session
    engine.discover = discover
    session._engine = engine
    session._player = SimpleNamespace(stop=lambda: None)
    session._result = SimpleNamespace(
        camera_source_url="https://victoria.example/live.m3u8"
    )

    failed = []
    session.failed.connect(failed.append)

    session.stop()
    assert engine.abort_calls == 1
    assert engine.finish_calls == 0
    assert session.result is None
    assert engine.is_busy is False

    started = session.discover("http://www.citylive.hu/index.php/budapest-panoramic-view")
    assert started is True
    assert failed == []
    assert engine.discovered == (
        "http://www.citylive.hu/index.php/budapest-panoramic-view",
        True,
    )


def test_discover_rejects_when_busy_without_stop():
    from cameras.hunter_session import HunterLiveSession

    session = HunterLiveSession()
    engine = SimpleNamespace(is_busy=True, discovered=None)
    engine.discover = lambda url, interactive=False: setattr(
        engine, "discovered", (url, interactive)
    )
    session._engine = engine

    failed = []
    session.failed.connect(failed.append)

    started = session.discover("https://example.com/other")
    assert started is False
    assert engine.discovered is None
    assert failed == ["Discovery already running."]
