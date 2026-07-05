# ============================================================================
# Project X
# Vessel Photo Provider Registry
# ============================================================================

from threading import Lock

from vessels.photo_record import PhotoRecord
from vessels.providers.base_provider import VesselPhotoProvider


class ProviderRegistry:

    def __init__(self):

        self._providers: list[tuple[int, VesselPhotoProvider]] = []
        self._lock = Lock()

    def register(
        self,
        provider: VesselPhotoProvider,
        *,
        priority: int = 0,
    ) -> None:

        with self._lock:

            self._remove_provider(provider)

            self._providers.append((priority, provider))
            self._providers.sort(
                key=lambda entry: (-entry[0], entry[1].name()),
            )

    def unregister(self, provider: VesselPhotoProvider) -> bool:

        with self._lock:
            return self._remove_provider(provider)

    def unregister_by_name(self, provider_name: str) -> bool:

        with self._lock:

            before = len(self._providers)
            target = provider_name.strip().lower()

            self._providers = [
                entry
                for entry in self._providers
                if entry[1].name().lower() != target
            ]

            return len(self._providers) != before

    def providers(self) -> list[VesselPhotoProvider]:

        with self._lock:
            return [provider for _, provider in self._providers]

    def get_provider(self, name: str) -> VesselPhotoProvider | None:

        target = name.strip().lower()

        with self._lock:

            for _, provider in self._providers:
                if provider.name().lower() == target:
                    return provider

        return None

    def find_provider(self, record: PhotoRecord) -> VesselPhotoProvider | None:

        with self._lock:

            for _, provider in self._providers:
                if provider.supports(record):
                    return provider

        return None

    def clear(self) -> None:

        with self._lock:
            self._providers.clear()

    def count(self) -> int:

        with self._lock:
            return len(self._providers)

    def _remove_provider(self, provider: VesselPhotoProvider) -> bool:

        before = len(self._providers)

        self._providers = [
            entry
            for entry in self._providers
            if entry[1] is not provider
        ]

        return len(self._providers) != before


provider_registry = ProviderRegistry()


def _register_default_providers() -> None:

    from vessels.providers.local_provider import LocalProvider
    from vessels.providers.marinetraffic_provider import MarineTrafficProvider
    from vessels.providers.vesselfinder_provider import VesselFinderProvider

    provider_registry.register(LocalProvider(), priority=100)
    provider_registry.register(MarineTrafficProvider(), priority=50)
    provider_registry.register(VesselFinderProvider(), priority=40)


_register_default_providers()
