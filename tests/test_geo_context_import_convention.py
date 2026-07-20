#!/usr/bin/env python3
"""Guard against GeoContext namespace-shadowing imports."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "from observation import geo_context",
        re.compile(r"^\s*from\s+observation\s+import\s+geo_context\b"),
    ),
    (
        "import observation.geo_context as",
        re.compile(r"^\s*import\s+observation\.geo_context\s+as\s+"),
    ),
)

ALLOWLIST = {
    REPO_ROOT / "tests" / "test_geo_context.py": {
        "from observation import geo_context",
    },
}


def _scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    allowed = ALLOWLIST.get(path, set())

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for label, pattern in FORBIDDEN_PATTERNS:
            if label in allowed and pattern.search(line):
                continue

            if pattern.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {label}")

    return violations


class GeoContextImportConventionTests(unittest.TestCase):

    def test_no_ambiguous_geo_context_imports(self) -> None:

        roots = (
            REPO_ROOT / "src",
            REPO_ROOT / "tools",
            REPO_ROOT / "tests",
        )
        violations: list[str] = []

        for root in roots:
            for path in root.rglob("*.py"):
                violations.extend(_scan_file(path))

        self.assertEqual(
            violations,
            [],
            "Ambiguous GeoContext imports found:\n  "
            + "\n  ".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
