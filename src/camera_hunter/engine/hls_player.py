"""Real HLS playback via QMediaPlayer + local header proxy.

Not a JPEG pipeline. Overlay should hide only after video_started.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoFrame
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget

from camera_hunter.engine.hls_diag import diag
from camera_hunter.engine.hls_proxy import HlsProxy


def _enum_name(value: object) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    return str(value)


class HlsPlayer(QObject):
    """Play an M3U8 URL continuously. Reconnects on player errors, not Hunter health."""

    video_started = Signal()
    buffering = Signal()
    playback_failed = Signal(str)
    playback_stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proxy = HlsProxy()
        self._url = ""
        self._headers: dict[str, str] = {}
        self._started = False
        self._retries = 0
        self._want_play = False
        self._frame_logs = 0

        self._video = QVideoWidget()
        self._video.setStyleSheet("background-color: #0a0e16;")
        self._video.hide()

        self._audio = QAudioOutput(self)
        self._audio.setMuted(True)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        sink = self._player.videoSink()
        if sink is not None:
            sink.videoFrameChanged.connect(self._on_video_frame)
            sink.videoSizeChanged.connect(self._on_video_size)

        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_play)
        diag("player_created", has_sink=self._player.videoSink() is not None)

    @property
    def widget(self) -> QWidget:
        return self._video

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def has_video(self) -> bool:
        return self._started

    @property
    def current_url(self) -> str:
        return self._url

    def play(self, url: str, headers: dict[str, str] | None = None) -> None:
        url = (url or "").strip()
        if not url:
            diag("player_play_empty_url")
            return
        same = url == self._url and self._want_play and self._started
        self._url = url
        self._headers = dict(headers or {})
        self._want_play = True
        self._retries = 0
        if same and self.is_playing:
            diag("player_play_skip_same", url=url)
            return
        self._started = False
        self._frame_logs = 0
        self._video.show()
        local = self._proxy.set_upstream(url, self._headers)
        diag(
            "player_set_source",
            upstream_m3u8=url,
            local_m3u8=local,
            header_keys=sorted(self._headers),
            referer=self._headers.get("Referer"),
            widget_visible=self._video.isVisible(),
            widget_size=f"{self._video.width()}x{self._video.height()}",
        )
        self._player.stop()
        self._player.setSource(QUrl(local))
        self._player.play()
        diag(
            "player_play_called",
            local_m3u8=local,
            media_status=_enum_name(self._player.mediaStatus()),
            playback_state=_enum_name(self._player.playbackState()),
            error=_enum_name(self._player.error()),
            error_string=self._player.errorString(),
        )

    def stop(self) -> None:
        self._want_play = False
        self._retry_timer.stop()
        self._started = False
        prev = self._url
        self._url = ""
        self._player.stop()
        self._player.setSource(QUrl())
        self._video.hide()
        self._proxy.stop()
        diag("player_stop", previous_url=prev)
        self.playback_stopped.emit()

    def _retry_play(self) -> None:
        if not self._want_play or not self._url:
            return
        local = self._proxy.set_upstream(self._url, self._headers)
        diag("player_retry", url=self._url, retries=self._retries, local_m3u8=local)
        self._player.stop()
        self._player.setSource(QUrl(local))
        self._player.play()

    @Slot(QVideoFrame)
    def _on_video_frame(self, frame: QVideoFrame) -> None:
        if not self._want_play or self._started:
            return
        valid = frame is not None and frame.isValid()
        size = frame.size() if valid else None
        if self._frame_logs < 8:
            self._frame_logs += 1
            diag(
                "player_video_frame",
                valid=valid,
                width=size.width() if size is not None else 0,
                height=size.height() if size is not None else 0,
            )
        if frame is None or not frame.isValid():
            return
        size = frame.size()
        if size.width() < 2 or size.height() < 2:
            return
        self._mark_started()

    def _on_video_size(self) -> None:
        if not self._want_play or self._started:
            return
        sink = self._player.videoSink()
        if sink is None:
            return
        size = sink.videoSize()
        if size.width() < 2 or size.height() < 2:
            return
        self._mark_started()

    def _mark_started(self) -> None:
        if self._started:
            return
        self._started = True
        self._retries = 0
        self._video.show()
        self._video.raise_()
        diag("player_video_started", url=self._url)
        self.video_started.emit()

    def _on_error(self, *args: object) -> None:
        if not self._want_play:
            return
        text = " ".join(str(a) for a in args if a)
        diag(
            "player_error",
            error=text or "playback error",
            media_status=_enum_name(self._player.mediaStatus()),
            playback_state=_enum_name(self._player.playbackState()),
            error_enum=_enum_name(self._player.error()),
            error_string=self._player.errorString(),
            url=self._url,
        )
        self.playback_failed.emit(text or "playback error")
        self._schedule_retry()

    def _on_state(self, state: object) -> None:
        if not self._want_play:
            return
        diag(
            "player_playback_state",
            state=_enum_name(state),
            media_status=_enum_name(self._player.mediaStatus()),
            error=_enum_name(self._player.error()),
            error_string=self._player.errorString(),
            started=self._started,
        )
        if state == QMediaPlayer.PlaybackState.StoppedState and not self._started:
            self._schedule_retry()

    def _on_status(self, status: object) -> None:
        if not self._want_play:
            return
        diag(
            "player_media_status",
            media_status=_enum_name(status),
            playback_state=_enum_name(self._player.playbackState()),
            error=_enum_name(self._player.error()),
            error_string=self._player.errorString(),
            url=self._url,
        )
        if status == QMediaPlayer.MediaStatus.BufferingMedia:
            self.buffering.emit()
        elif status == QMediaPlayer.MediaStatus.StalledMedia:
            self.buffering.emit()
            self._schedule_retry()
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._schedule_retry()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            diag("player_invalid_media", error_string=self._player.errorString(), url=self._url)
            self.playback_failed.emit("invalid media")
            self._schedule_retry()

    def _schedule_retry(self) -> None:
        if not self._want_play or self._retry_timer.isActive():
            return
        self._retries += 1
        delay = min(400 * (2 ** min(self._retries, 4)), 4000)
        diag("player_schedule_retry", retries=self._retries, delay_ms=delay, url=self._url)
        self._retry_timer.start(delay)
