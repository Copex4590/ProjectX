# ============================================================================
# Project X
# MPV Launch Configuration
# ============================================================================

from dataclasses import dataclass, field

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.session import PlaybackSession

DEFAULT_MPV_ARGUMENTS = (
    "--profile=low-latency",
    "--hwdec=auto",
    "--cache=no",
    "--keep-open=no",
)

_LAUNCH_CONFIGURATION_KEY = "launch_configuration"


@dataclass(frozen=True)
class MPVLaunchConfiguration:

    executable: str
    url: str
    arguments: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    working_directory: str = ""

    def to_dict(self) -> dict:

        return {
            "executable": self.executable,
            "url": self.url,
            "arguments": list(self.arguments),
            "environment": dict(self.environment),
            "working_directory": self.working_directory,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MPVLaunchConfiguration":

        if not isinstance(data, dict):
            data = {}

        environment = data.get("environment", {})

        if not isinstance(environment, dict):
            environment = {}

        arguments = data.get("arguments", [])

        if not isinstance(arguments, list):
            arguments = []

        return cls(
            executable=str(data.get("executable", "mpv")).strip() or "mpv",
            url=str(data.get("url", "")).strip(),
            arguments=[str(item).strip() for item in arguments if str(item).strip()],
            environment={
                str(key): str(value)
                for key, value in environment.items()
            },
            working_directory=str(data.get("working_directory", "")).strip(),
        )

    def command(self) -> list[str]:

        command = [self.executable, *self.arguments]

        if self.url:
            command.append(self.url)

        return command


def build_mpv_launch_configuration(
    provider_session: ProviderSession,
    *,
    executable: str = "mpv",
    extra_arguments: list[str] | None = None,
    environment: dict[str, str] | None = None,
    working_directory: str = "",
) -> MPVLaunchConfiguration | None:

    stream_url = str(provider_session.stream_url).strip()

    if not stream_url:
        return None

    arguments = list(DEFAULT_MPV_ARGUMENTS)

    if extra_arguments:
        arguments.extend(
            str(item).strip()
            for item in extra_arguments
            if str(item).strip()
        )

    resolved_executable = str(executable).strip() or "mpv"

    return MPVLaunchConfiguration(
        executable=resolved_executable,
        url=stream_url,
        arguments=arguments,
        environment=dict(environment or {}),
        working_directory=str(working_directory).strip(),
    )


def attach_launch_configuration(
    metadata: dict,
    launch_configuration: MPVLaunchConfiguration,
) -> dict:

    merged = dict(metadata)
    merged[_LAUNCH_CONFIGURATION_KEY] = launch_configuration.to_dict()
    merged["launch_backend"] = "mpv"
    return merged


def get_launch_configuration(
    session: PlaybackSession,
) -> MPVLaunchConfiguration | None:

    data = session.metadata.get(_LAUNCH_CONFIGURATION_KEY)

    if not data:
        return None

    return MPVLaunchConfiguration.from_dict(data)
