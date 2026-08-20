# ============================================================================
# Project X
# Vendored Hunter HLS fallback: next accepted candidate after pre-LIVE fail
# ============================================================================

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from camera_hunter.engine.discovery import DiscoveryEngine
from camera_hunter.engine.hls_capture import HlsCaptureResult
from camera_hunter.engine.session import HunterSession, HunterState
from camera_hunter.models import CameraSource, SourceType

PAGE = "https://cams.example.com/view"
CAM_A = "https://cdn.example.com/live/cam-a/playlist.m3u8"
CAM_B = "https://cdn.example.com/live/cam-b/playlist.m3u8"
CAM_C = "https://cdn.example.com/live/cam-c/playlist.m3u8"


class _FakeEngine:
    """Bind production helper methods without constructing QWebEngine."""

    _arm_next_accepted_hls = DiscoveryEngine._arm_next_accepted_hls
    _on_hls_capture_finished = DiscoveryEngine._on_hls_capture_finished
    _handle_earthcam_validation_failure = DiscoveryEngine._handle_earthcam_validation_failure
    _on_player_playback_failed = DiscoveryEngine._on_player_playback_failed

    def __init__(self) -> None:
        self._session = HunterSession()
        self._hls_failed_urls: set[str] = set()
        self._live_hls_url: str | None = None
        self._pending_live_src: CameraSource | None = None
        self._live_sources: dict[tuple[str, SourceType], CameraSource] = {}
        self._live_headers: dict[str, str] = {}
        self._busy = True
        self._capture_inflight = True
        self._armed: list[str] = []
        self._validated: list[tuple[str, int]] = []
        self._probe_starts = 0
        self._player_stops = 0
        self._probe_timer = self
        self._live_player = None
        self._session.activate_camera_page(PAGE)
        self._session.mark_discovery_active()

    def start(self) -> None:
        self._probe_starts += 1

    def _stop_live_player(self) -> None:
        self._player_stops += 1

    def _arm_live_playback(self, src: CameraSource) -> None:
        self._pending_live_src = src
        self._live_hls_url = src.url
        self._armed.append(src.url)

    def _start_hls_validation(self, src: CameraSource, generation: int) -> None:
        self._validated.append((src.url, generation))

    def _recover_live_source(self, *, reason: str) -> None:
        raise AssertionError(f"pre-LIVE fallback must not recover: {reason}")


def _hls_src(url: str) -> CameraSource:
    return CameraSource(
        url=url,
        source_type=SourceType.HLS,
        mime_type="application/vnd.apple.mpegurl",
        discovery_source="NETWORK REQUEST",
        source_page=PAGE,
        found_after=PAGE,
        discovered_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
    )


def _accept(engine: _FakeEngine, *urls: str, armed: str | None = None) -> None:
    gen = engine._session.generation
    for url in urls:
        src = _hls_src(url)
        engine._live_sources[(url, SourceType.HLS)] = src
        assert engine._session.add_hls_candidate(url, gen) is True
    if armed is not None:
        engine._live_hls_url = armed
        engine._pending_live_src = engine._live_sources[(armed, SourceType.HLS)]


def _failed_cap(url: str) -> HlsCaptureResult:
    cap = HlsCaptureResult(hls_url=url, error="HTTP 404")
    cap.hls_fetch = False
    cap.segment = False
    cap.video_frame = False
    return cap


def test_fallback_arms_next_accepted_candidate():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, armed=CAM_A)

    assert engine._arm_next_accepted_hls(CAM_A) is True

    assert engine._live_hls_url == CAM_B
    assert engine._armed == [CAM_B]
    assert engine._validated == [(CAM_B, engine._session.generation)]
    assert CAM_A in engine._hls_failed_urls
    assert CAM_B not in engine._hls_failed_urls


def test_fallback_skips_failed_and_arms_third():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, CAM_C, armed=CAM_A)

    assert engine._arm_next_accepted_hls(CAM_A) is True
    assert engine._live_hls_url == CAM_B
    assert engine._arm_next_accepted_hls(CAM_B) is True

    assert engine._live_hls_url == CAM_C
    assert engine._armed == [CAM_B, CAM_C]
    assert engine._validated == [
        (CAM_B, engine._session.generation),
        (CAM_C, engine._session.generation),
    ]
    assert engine._hls_failed_urls == {CAM_A, CAM_B}


def test_fallback_false_when_no_usable_candidate():
    engine = _FakeEngine()
    _accept(engine, CAM_A, armed=CAM_A)

    assert engine._arm_next_accepted_hls(CAM_A) is False

    assert engine._live_hls_url is None
    assert engine._pending_live_src is None
    assert engine._armed == []
    assert engine._validated == []
    assert engine._player_stops == 1
    assert CAM_A in engine._hls_failed_urls


def test_late_failure_does_not_disarm_current_candidate():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, armed=CAM_A)
    assert engine._arm_next_accepted_hls(CAM_A) is True
    assert engine._live_hls_url == CAM_B
    stops_after_first = engine._player_stops
    armed_after_first = list(engine._armed)

    assert engine._arm_next_accepted_hls(CAM_A) is False

    assert engine._live_hls_url == CAM_B
    assert engine._armed == armed_after_first
    assert engine._player_stops == stops_after_first
    assert engine._pending_live_src is not None
    assert engine._pending_live_src.url == CAM_B


def test_failed_url_is_not_retried():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, CAM_C, armed=CAM_A)
    assert engine._arm_next_accepted_hls(CAM_A) is True
    assert engine._live_hls_url == CAM_B

    assert engine._arm_next_accepted_hls(CAM_B) is True

    assert engine._live_hls_url == CAM_C
    assert CAM_A not in engine._armed
    assert engine._validated == [
        (CAM_B, engine._session.generation),
        (CAM_C, engine._session.generation),
    ]
    assert CAM_A in engine._hls_failed_urls


def test_capture_finished_without_frame_uses_fallback():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, armed=CAM_A)

    engine._on_hls_capture_finished(
        engine._live_sources[(CAM_A, SourceType.HLS)],
        _failed_cap(CAM_A),
        engine._session.generation,
    )

    assert engine._capture_inflight is False
    assert engine._live_hls_url == CAM_B
    assert engine._armed == [CAM_B]
    assert engine._validated == [(CAM_B, engine._session.generation)]
    assert engine._probe_starts == 0


def test_capture_finished_without_next_candidate_keeps_probe():
    engine = _FakeEngine()
    _accept(engine, CAM_A, armed=CAM_A)

    engine._on_hls_capture_finished(
        engine._live_sources[(CAM_A, SourceType.HLS)],
        _failed_cap(CAM_A),
        engine._session.generation,
    )

    assert engine._live_hls_url is None
    assert engine._armed == []
    assert engine._probe_starts == 1
    assert engine._session.state != HunterState.FAILED


class _FakePlayer:
    def __init__(self, url: str, *, has_video: bool = False) -> None:
        self.current_url = url
        self.has_video = has_video


def test_pre_live_player_fail_arms_next_accepted_candidate():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, armed=CAM_A)
    engine._live_player = _FakePlayer(CAM_A, has_video=False)
    assert engine._session.state == HunterState.VALIDATING_HLS

    engine._on_player_playback_failed("ResourceError Could not open file")

    assert engine._live_hls_url == CAM_B
    assert engine._armed == [CAM_B]
    assert engine._validated == [(CAM_B, engine._session.generation)]
    assert engine._session.state != HunterState.FAILED
    assert CAM_A in engine._hls_failed_urls


def test_pre_live_player_fail_late_does_not_disarm_next():
    engine = _FakeEngine()
    _accept(engine, CAM_A, CAM_B, armed=CAM_A)
    assert engine._arm_next_accepted_hls(CAM_A) is True
    assert engine._live_hls_url == CAM_B
    engine._live_player = _FakePlayer(CAM_A, has_video=False)
    armed_after = list(engine._armed)
    stops_after = engine._player_stops

    engine._on_player_playback_failed("ResourceError stale")

    assert engine._live_hls_url == CAM_B
    assert engine._armed == armed_after
    assert engine._player_stops == stops_after
    assert engine._session.state != HunterState.FAILED
