# ============================================================================
# Project X
# Lazy Singleton Helper
# ============================================================================

from __future__ import annotations

import importlib
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class LazySingleton(Generic[T]):
    """Construct a singleton on first access instead of at module import."""

    __slots__ = ("_factory", "_instance")

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._instance: T | None = None

    def __call__(self) -> T:
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def reset(self) -> None:
        """Drop the cached singleton so the next access creates a fresh instance."""

        self._instance = None


def lazy_module_getattr(
    name: str,
    *,
    module_name: str,
    export_name: str,
    getter: LazySingleton[Any],
) -> Any:
    """Resolve singleton exports and delegate module-level API access.

    When a package contains both ``logbook_recorder.py`` and a lazy singleton
    export named ``logbook_recorder``, ``from logbook import logbook_recorder``
    binds the submodule. Delegating unresolved attributes to the singleton keeps
    legacy call sites such as ``logbook_recorder.start()`` working without eager
    initialization at import time.
    """

    if name == export_name:
        return getter()

    factory = getter._factory
    if not hasattr(factory, name):
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

    return getattr(getter(), name)


def lazy_submodule_export(package_name: str, export_name: str) -> Any:
    """Return the lazy singleton submodule for a package export.

    Package ``__getattr__`` hooks must return the submodule (not the singleton
    instance) so import-time access stays lazy and module-level API delegation
    works for legacy call sites such as ``logbook_recorder.start()``.
    """

    return importlib.import_module(f"{package_name}.{export_name}")
