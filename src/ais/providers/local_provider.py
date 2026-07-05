# ============================================================================
# Project X
# Local AIS Provider
# ============================================================================

from __future__ import annotations

from ais.providers.provider import AISProvider, AISProviderType, AISTestResult
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from engines.ais.ais_catcher_launcher import is_port_open


class LocalAISProvider(AISProvider):

    provider_type = AISProviderType.LOCAL

    @property
    def display_name(self) -> str:

        return "Local AIS receiver"

    def test(
        self,
        *,
        host: str = "",
        port: int | str = 0,
        **_kwargs,
    ) -> AISTestResult:

        resolved_host = str(host or AIS_CATCHER_HOST).strip() or AIS_CATCHER_HOST

        try:
            resolved_port = int(port or AIS_CATCHER_PORT)
        except (TypeError, ValueError):
            resolved_port = AIS_CATCHER_PORT

        if resolved_port <= 0 or resolved_port > 65535:
            return AISTestResult(
                success=False,
                message="Please enter a valid port number.",
            )

        if is_port_open(resolved_host, resolved_port, timeout=3.0):
            return AISTestResult(
                success=True,
                message="Connection successful",
            )

        return AISTestResult(
            success=False,
            message="Local AIS receiver is not reachable.",
        )
