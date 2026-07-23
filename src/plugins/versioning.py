# ============================================================================
# Project X
# Plugin Framework — version helpers (SAVE-212)
# ============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass


_VERSION_RE = re.compile(
    r"""
    ^\s*
    (?P<op>>=|<=|==|!=|>|<)?
    \s*
    (?P<version>\d+(?:\.\d+){0,3}(?:[-+][0-9A-Za-z.]+)?)
    \s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Version:
    major: int = 0
    minor: int = 0
    patch: int = 0
    suffix: str = ""

    @classmethod
    def parse(cls, value: str | None) -> "Version":

        text = str(value or "0").strip()
        if not text:
            return cls()

        # strip leading operators if present
        match = _VERSION_RE.match(text)
        if match:
            text = match.group("version")

        core, _, suffix = text.partition("-")
        if "+" in core:
            core = core.split("+", 1)[0]
        if "+" in suffix:
            suffix = suffix.split("+", 1)[0]

        parts = [part for part in core.split(".") if part != ""]
        numbers: list[int] = []
        for part in parts[:3]:
            try:
                numbers.append(int(part))
            except ValueError:
                numbers.append(0)

        while len(numbers) < 3:
            numbers.append(0)

        return cls(
            major=numbers[0],
            minor=numbers[1],
            patch=numbers[2],
            suffix=suffix.strip(),
        )

    def __str__(self) -> str:

        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.suffix:
            return f"{base}-{self.suffix}"
        return base

    def as_tuple(self) -> tuple[int, int, int, str]:

        return (self.major, self.minor, self.patch, self.suffix)


def compare_versions(left: str | Version, right: str | Version) -> int:
    """Return -1 / 0 / 1 for left < / == / > right (numeric core only)."""

    a = left if isinstance(left, Version) else Version.parse(str(left))
    b = right if isinstance(right, Version) else Version.parse(str(right))

    if a.as_tuple()[:3] < b.as_tuple()[:3]:
        return -1
    if a.as_tuple()[:3] > b.as_tuple()[:3]:
        return 1
    return 0


def satisfies_requirement(installed: str | Version, requirement: str) -> bool:
    """
    Check a single dependency requirement.

    Supported forms: ``1.2.3``, ``==1.2.3``, ``>=1.0``, ``<=2.0``, ``>1``, ``<3``, ``!=1.0``.
    Bare version means ``>=``.
    """

    text = str(requirement or "").strip()
    if not text:
        return True

    match = _VERSION_RE.match(text)
    if not match:
        # Unknown format — require exact string match via parse equality
        return compare_versions(installed, text) == 0

    op = match.group("op") or ">="
    required = Version.parse(match.group("version"))
    cmp = compare_versions(installed, required)

    if op == "==":
        return cmp == 0
    if op == "!=":
        return cmp != 0
    if op == ">=":
        return cmp >= 0
    if op == "<=":
        return cmp <= 0
    if op == ">":
        return cmp > 0
    if op == "<":
        return cmp < 0

    return cmp >= 0
