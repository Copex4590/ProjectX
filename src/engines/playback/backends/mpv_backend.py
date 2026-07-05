# ============================================================================
# Project X
# MPV Backend
# ============================================================================

import os
import subprocess

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.backend import PlaybackBackend, PlaybackBackendStatus
from engines.playback.mpv_launch import (
    MPVLaunchConfiguration,
    attach_launch_configuration,
    build_mpv_launch_configuration,
    get_launch_configuration,
)
from engines.playback.session import PlaybackSession, PlaybackState
from playback.preferences import load_playback_preferences

_SUPPORTED_PROVIDERS = frozenset({"hls", "rtsp"})


class MPVBackend(PlaybackBackend):

    def __init__(self):

        self._active_session: PlaybackSession | None = None
        self._process: subprocess.Popen | None = None

    @property
    def name(self) -> str:

        return "mpv"

    def supports(self, provider_session: ProviderSession) -> bool:

        provider_name = self._provider_name(provider_session)
        protocol = self._provider_protocol(provider_session)
        stream_url = str(provider_session.stream_url).strip()

        if not stream_url:
            return False

        return (
            provider_name in _SUPPORTED_PROVIDERS
            or protocol in _SUPPORTED_PROVIDERS
        )

    def prepare(self, provider_session: ProviderSession) -> PlaybackSession | None:

        if not self.supports(provider_session):
            return None

        preferences = load_playback_preferences()
        executable = preferences.custom_executable.strip() or "mpv"

        launch_configuration = build_mpv_launch_configuration(
            provider_session,
            executable=executable,
            extra_arguments=list(preferences.custom_arguments),
        )

        if launch_configuration is None:
            return None

        session = PlaybackSession(
            provider_session=provider_session,
            backend_name=self.name,
            state=PlaybackState.PREPARED,
            metadata=attach_launch_configuration(
                {
                    "prepared_by": self.name,
                    "playback_prepared": True,
                },
                launch_configuration,
            ),
        )

        self._active_session = session
        return session

    def start(self, session: PlaybackSession) -> PlaybackSession:

        launch_configuration = get_launch_configuration(session)

        if launch_configuration is None:
            return session.with_state(
                PlaybackState.ERROR,
                message="MPV launch configuration is missing",
            )

        try:
            environment = os.environ.copy()
            environment.update(launch_configuration.environment)

            popen_kwargs = {
                "env": environment,
            }

            if launch_configuration.working_directory:
                popen_kwargs["cwd"] = launch_configuration.working_directory

            self._process = subprocess.Popen(
                launch_configuration.command(),
                **popen_kwargs,
            )

        except Exception as error:
            self._process = None
            return session.with_state(
                PlaybackState.ERROR,
                message=f"Failed to launch MPV playback: {error}",
            )

        started = session.with_state(
            PlaybackState.STARTED,
            message="MPV playback launched",
            launch_ready=True,
            process_id=self._process.pid,
        )

        self._active_session = started
        return started

    def stop(self, session: PlaybackSession) -> PlaybackSession:

        self._terminate_process()

        stopped = session.with_state(
            PlaybackState.STOPPED,
            message="MPV session stopped",
            launch_ready=False,
        )

        if self._active_session and self._active_session.session_id == session.session_id:
            self._active_session = None

        return stopped

    def _terminate_process(self):

        if self._process is None:
            return

        if self._process.poll() is None:
            self._process.terminate()

            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)

        self._process = None

    def status(self, session: PlaybackSession) -> PlaybackBackendStatus:

        launch_configuration = get_launch_configuration(session)
        message = str(session.metadata.get("message", ""))

        if launch_configuration is not None and not message:
            message = "MPV launch configuration prepared"

        return PlaybackBackendStatus(
            state=session.state,
            backend_name=self.name,
            session_id=session.session_id,
            message=message,
        )

    def launch_configuration(
        self,
        session: PlaybackSession,
    ) -> MPVLaunchConfiguration | None:

        return get_launch_configuration(session)
