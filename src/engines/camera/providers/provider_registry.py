# ============================================================================
# Project X
# Provider Registry
# ============================================================================

from threading import Lock

from .base_provider import CameraProvider
from models.camera import Camera


class ProviderRegistry:

    def __init__(self):

        self._providers: list[tuple[int, CameraProvider]] = []
        self._lock = Lock()

    def register(
        self,
        provider: CameraProvider,
        *,
        priority: int = 0,
    ):

        with self._lock:

            self._remove_provider(provider)

            self._providers.append((priority, provider))
            self._providers.sort(
                key=lambda entry: (-entry[0], entry[1].name),
            )

    def unregister(self, provider: CameraProvider) -> bool:

        with self._lock:
            return self._remove_provider(provider)

    def _remove_provider(self, provider: CameraProvider) -> bool:

        before = len(self._providers)

        self._providers = [
            entry
            for entry in self._providers
            if entry[1] is not provider
        ]

        return len(self._providers) != before

    def unregister_by_name(self, provider_name: str) -> bool:

        with self._lock:

            before = len(self._providers)
            target = provider_name.strip().lower()

            self._providers = [
                entry
                for entry in self._providers
                if entry[1].name.lower() != target
            ]

            return len(self._providers) != before

    def get_provider(self, camera: Camera) -> CameraProvider | None:

        with self._lock:

            for _, provider in self._providers:
                if provider.supports(camera):
                    return provider

        return None

    def list_providers(self) -> list[CameraProvider]:

        with self._lock:
            return [provider for _, provider in self._providers]

    def clear(self):

        with self._lock:
            self._providers.clear()

    def count(self) -> int:

        with self._lock:
            return len(self._providers)


provider_registry = ProviderRegistry()
