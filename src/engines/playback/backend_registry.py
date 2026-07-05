# ============================================================================
# Project X
# Backend Registry
# ============================================================================

from threading import Lock

from engines.camera.providers.base_provider import ProviderSession
from engines.playback.backend import PlaybackBackend


class BackendRegistry:

    def __init__(self):

        self._backends: list[tuple[int, PlaybackBackend]] = []
        self._lock = Lock()

    def register(
        self,
        backend: PlaybackBackend,
        *,
        priority: int = 0,
    ):

        with self._lock:

            self.unregister(backend)

            self._backends.append((priority, backend))
            self._backends.sort(
                key=lambda entry: (-entry[0], entry[1].name),
            )

    def unregister(self, backend: PlaybackBackend) -> bool:

        with self._lock:

            before = len(self._backends)

            self._backends = [
                entry
                for entry in self._backends
                if entry[1] is not backend
            ]

            return len(self._backends) != before

    def unregister_by_name(self, backend_name: str) -> bool:

        with self._lock:

            before = len(self._backends)
            target = backend_name.strip().lower()

            self._backends = [
                entry
                for entry in self._backends
                if entry[1].name.lower() != target
            ]

            return len(self._backends) != before

    def get_backend(
        self,
        provider_session: ProviderSession,
    ) -> PlaybackBackend | None:

        with self._lock:

            for _, backend in self._backends:
                if backend.supports(provider_session):
                    return backend

        return None

    def available_backends(self) -> list[PlaybackBackend]:

        with self._lock:
            return [backend for _, backend in self._backends]

    def clear(self):

        with self._lock:
            self._backends.clear()

    def count(self) -> int:

        with self._lock:
            return len(self._backends)


backend_registry = BackendRegistry()
