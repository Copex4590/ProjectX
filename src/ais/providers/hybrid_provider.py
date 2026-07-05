# ============================================================================
# Project X
# Hybrid AIS Provider
# ============================================================================

from __future__ import annotations

from ais.providers.aisstream_provider import AISStreamProvider
from ais.providers.local_provider import LocalAISProvider
from ais.providers.provider import AISProvider, AISProviderType, AISTestResult


class HybridAISProvider(AISProvider):

    provider_type = AISProviderType.HYBRID

    def __init__(self):

        self._aisstream = AISStreamProvider()
        self._local = LocalAISProvider()

    @property
    def display_name(self) -> str:

        return "Hybrid"

    def test(
        self,
        *,
        api_key: str = "",
        host: str = "",
        port: int | str = 0,
        **_kwargs,
    ) -> AISTestResult:

        stream_result = self._aisstream.test(api_key=api_key)

        if not stream_result.success:
            return stream_result

        local_result = self._local.test(host=host, port=port)

        if not local_result.success:
            return local_result

        return AISTestResult(
            success=True,
            message="Connection successful",
        )
