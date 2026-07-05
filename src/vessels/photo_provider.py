# ============================================================================
# Project X
# Vessel Photo Provider
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Lock

from vessels.photo_record import PhotoRecord


@dataclass(frozen=True)
class PhotoProviderStatus:

    provider_name: str = ""
    message: str = ""
    ready: bool = True
    metadata: dict = field(default_factory=dict)


class PhotoProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def supports(self, mmsi: int, imo: str = "") -> bool:
        ...

    def describe(self, mmsi: int, imo: str = "") -> PhotoProviderStatus:

        return PhotoProviderStatus(
            provider_name=self.name,
            message="Provider ready",
            ready=True,
        )

    def build_record(
        self,
        mmsi: int,
        imo: str = "",
        *,
        source: str = "",
    ) -> PhotoRecord | None:

        if not self.supports(mmsi, imo):
            return None

        return PhotoRecord(
            mmsi=int(mmsi),
            imo=str(imo or "").strip(),
            source=source or self.name,
        )


class PhotoProviderRegistry:

    def __init__(self):

        self._providers: list[tuple[int, PhotoProvider]] = []
        self._lock = Lock()

    def register(
        self,
        provider: PhotoProvider,
        *,
        priority: int = 0,
    ) -> None:

        with self._lock:

            self._remove_provider(provider)

            self._providers.append((priority, provider))
            self._providers.sort(
                key=lambda entry: (-entry[0], entry[1].name),
            )

    def unregister(self, provider: PhotoProvider) -> bool:

        with self._lock:
            return self._remove_provider(provider)

    def _remove_provider(self, provider: PhotoProvider) -> bool:

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

    def find_provider(
        self,
        mmsi: int,
        imo: str = "",
    ) -> PhotoProvider | None:

        with self._lock:

            for _, provider in self._providers:
                if provider.supports(mmsi, imo):
                    return provider

        return None

    def list_providers(self) -> list[PhotoProvider]:

        with self._lock:
            return [provider for _, provider in self._providers]

    def clear(self) -> None:

        with self._lock:
            self._providers.clear()

    def count(self) -> int:

        with self._lock:
            return len(self._providers)


photo_provider_registry = PhotoProviderRegistry()
