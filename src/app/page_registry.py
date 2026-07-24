# ============================================================================
# Project X — Lazy page registry
# ============================================================================
"""Deferred construction of MainWindow stack pages.

Dashboard is created eagerly. Every other page is a lightweight placeholder
until first navigation, then constructed once and reused.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

PageFactory = Callable[[], QWidget]
PageBinder = Callable[[QWidget], None]


@dataclass(frozen=True, slots=True)
class PageSpec:
    """Describe one stack slot."""

    index: int
    attr_name: str
    factory: PageFactory
    binder: PageBinder | None = None
    eager: bool = False


class _PagePlaceholder(QWidget):
    """Empty stand-in that keeps stack indices stable before first open."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(f"pagePlaceholder_{title}")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)


class PageRegistry:
    """Own stack placeholders and materialize real pages on demand."""

    def __init__(self, host: Any, stack: QStackedWidget):
        self._host = host
        self._stack = stack
        self._specs: dict[int, PageSpec] = {}
        self._by_attr: dict[str, PageSpec] = {}
        self._loaded: dict[int, QWidget] = {}
        self._placeholders: dict[int, QWidget] = {}
        self._initialized: set[int] = set()
        # Diagnostics for stabilization / tests (create / initialize / activate).
        self.create_counts: dict[str, int] = {}
        self.initialize_counts: dict[str, int] = {}
        self.activate_counts: dict[str, int] = {}
        self.binder_counts: dict[str, int] = {}

    def register(self, spec: PageSpec) -> None:
        if spec.index in self._specs:
            raise ValueError(f"Duplicate page index {spec.index}")
        if spec.attr_name in self._by_attr:
            raise ValueError(f"Duplicate page attr {spec.attr_name}")

        self._specs[spec.index] = spec
        self._by_attr[spec.attr_name] = spec

        if spec.eager:
            page = self._materialize(spec)
            return

        placeholder = _PagePlaceholder(spec.attr_name)
        self._placeholders[spec.index] = placeholder
        self._stack.addWidget(placeholder)
        setattr(self._host, spec.attr_name, None)

    def count(self) -> int:
        return len(self._specs)

    def is_loaded(self, index: int) -> bool:
        return index in self._loaded

    def get_loaded(self, index: int | None = None, *, attr: str | None = None) -> QWidget | None:
        if attr is not None:
            spec = self._by_attr.get(attr)
            if spec is None:
                return None
            index = spec.index
        if index is None:
            return None
        return self._loaded.get(index)

    def loaded_pages(self) -> list[QWidget]:
        return [self._loaded[i] for i in sorted(self._loaded)]

    def ensure(self, index: int) -> QWidget:
        """Return the real page, creating once; call activate() on every visit."""

        loaded = self._loaded.get(index)
        if loaded is not None:
            self._activate(index, loaded)
            return loaded

        spec = self._specs.get(index)
        if spec is None:
            raise KeyError(f"Unknown page index {index}")

        return self._materialize(spec)

    def ensure_attr(self, attr_name: str) -> QWidget:
        spec = self._by_attr.get(attr_name)
        if spec is None:
            raise KeyError(f"Unknown page attr {attr_name}")
        return self.ensure(spec.index)

    def _create(self, spec: PageSpec) -> QWidget:
        logger.info("Lazy page create: %s (index=%s)", spec.attr_name, spec.index)
        self.create_counts[spec.attr_name] = self.create_counts.get(spec.attr_name, 0) + 1
        return spec.factory()

    def _initialize(self, index: int, page: QWidget, attr_name: str) -> None:
        if index in self._initialized:
            return
        self._initialized.add(index)
        initialize = getattr(page, "initialize", None)
        if callable(initialize):
            initialize()
            self.initialize_counts[attr_name] = (
                self.initialize_counts.get(attr_name, 0) + 1
            )

    def _activate(self, index: int, page: QWidget) -> None:
        spec = self._specs[index]
        activate = getattr(page, "activate", None)
        if callable(activate):
            activate()
            self.activate_counts[spec.attr_name] = (
                self.activate_counts.get(spec.attr_name, 0) + 1
            )

    def _materialize(self, spec: PageSpec) -> QWidget:
        if spec.index in self._loaded:
            page = self._loaded[spec.index]
            self._activate(spec.index, page)
            return page

        page = self._create(spec)
        placeholder = self._placeholders.get(spec.index)
        stack_index = spec.index

        if spec.eager:
            self._stack.addWidget(page)
        elif placeholder is not None:
            # Replace placeholder in-place to preserve indices.
            self._stack.insertWidget(stack_index, page)
            self._stack.removeWidget(placeholder)
            placeholder.deleteLater()
            del self._placeholders[spec.index]
        else:
            self._stack.insertWidget(stack_index, page)

        self._loaded[spec.index] = page
        setattr(self._host, spec.attr_name, page)

        self._initialize(spec.index, page, spec.attr_name)

        if spec.binder is not None:
            spec.binder(page)
            self.binder_counts[spec.attr_name] = (
                self.binder_counts.get(spec.attr_name, 0) + 1
            )

        self._activate(spec.index, page)

        logger.info("Lazy page ready: %s", spec.attr_name)
        return page
