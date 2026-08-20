# ============================================================================
# Project X
# In-process Camera Hunter discovery session (vendored camera_hunter)
# ============================================================================
"""Owns DiscoveryEngine + Hunter HlsPlayer for one live camera page URL.

Does not import the Hunter GUI, does not start a second QApplication, and
does not persist CameraResult URLs. Referer / User-Agent stay inside the
Hunter playback chain.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def camera_result_stream_url(result: object) -> str:
    """CameraResult.camera_source_url → PX stream URL. No persistence."""

    return str(getattr(result, "camera_source_url", None) or "").strip()


def camera_result_provider_type(result: object) -> str:
    """Map Hunter source_type onto PX Camera.provider_type values only."""

    raw = getattr(result, "source_type", None)
    value = getattr(raw, "value", raw)
    text = str(value or "").strip().lower()
    if text == "hls":
        return "hls"
    if text == "mjpeg":
        return "mjpeg"
    if text in {"still_image", "refreshing_image"}:
        return "http"
    return "hls"


class HunterLiveSession(QObject):
    """Process-wide in-process Hunter discovery + HlsPlayer host."""

    live_ready = Signal(object)
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None, *, headless: bool = False) -> None:

        super().__init__(parent)
        self._engine = None
        self._player = None
        self._result = None
        self._headless = bool(headless)

    @property
    def result(self) -> object | None:

        return self._result

    @property
    def is_busy(self) -> bool:

        engine = self._engine
        return bool(engine is not None and engine.is_busy)

    @property
    def is_active(self) -> bool:

        if self._result is not None:
            return True
        if self.is_busy:
            return True
        player = self._player
        return bool(player is not None and (player.has_video or player.is_playing))

    def player_widget(self) -> QWidget | None:

        player = self._player
        if player is None:
            return None
        return player.widget

    def ensure(self) -> None:
        """Create DiscoveryEngine + HlsPlayer after QApplication exists."""

        if self._engine is not None:
            return

        from camera_hunter.engine import DiscoveryEngine
        from camera_hunter.engine.hls_player import HlsPlayer

        self._player = HlsPlayer(self)
        self._engine = DiscoveryEngine(self, headless=self._headless)
        self._engine.set_live_player(self._player)
        if self._headless:
            from PySide6.QtCore import Qt

            widget = self._player.widget
            widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._engine.live_ready.connect(self._on_engine_live_ready)
        self._engine.status.connect(self.status.emit)
        self._engine.finished.connect(self._on_engine_finished)
        logger.info("Hunter live session ready (in-process DiscoveryEngine)")

    def discover(self, page_url: str) -> bool:
        """Start non-interactive discovery for a camera page URL."""

        url = (page_url or "").strip()
        if not url:
            self.failed.emit("Camera page URL is empty.")
            return False

        self.ensure()
        if self._engine is None:
            self.failed.emit("Discovery engine is not available.")
            return False
        if self._engine.is_busy:
            self.failed.emit("Discovery already running.")
            return False

        self._result = None
        # interactive=True keeps LIVE playback: non-interactive settle calls
        # _collect_and_finish → _stop_live_player. This is not listing/embed_view.
        self._engine.discover(url, interactive=True)
        return True

    def stop(self) -> None:
        """Stop playback and drop an in-flight interactive session immediately."""

        engine = self._engine
        if engine is not None and engine.is_busy:
            engine.abort_in_flight()
        player = self._player
        if player is not None:
            player.stop()
        self._result = None

    def _on_engine_live_ready(self, result: object) -> None:

        self._result = result
        url = camera_result_stream_url(result)
        provider = camera_result_provider_type(result)
        logger.info(
            "Hunter live_ready provider=%s url=%s",
            provider,
            url or "-",
        )
        self.live_ready.emit(result)

    def _on_engine_finished(self, result: object) -> None:

        if self._result is not None:
            return
        error = getattr(result, "error", None)
        message = str(error).strip() if error else ""
        if not message:
            message = "Discovery finished without a live camera."
        self.failed.emit(message)


hunter_live_session = HunterLiveSession()
