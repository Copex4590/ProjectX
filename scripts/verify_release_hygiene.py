#!/usr/bin/env python3
# ============================================================================
# Project X — Release packaging hygiene verification
# ============================================================================

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_CONFIG = ROOT / "src" / "config"

DEVELOPER_PATH_PATTERN = re.compile(
    r"/home/zoli|/home/[A-Za-z0-9_-]+/ProjectX|/home/[A-Za-z0-9_-]+/Project X"
)

RUNTIME_CONFIG_ARTIFACTS = (
    SRC_CONFIG / "migration_state.json",
)

BUNDLED_CONFIG_JSON = (
    SRC_CONFIG / "preferences.json.example",
    SRC_CONFIG / "cameras.json.example",
    SRC_CONFIG / "observation_points.json.example",
    SRC_CONFIG / "playback.json",
    SRC_CONFIG / "camera_packs" / "state.json",
)


def _import_verify_data_tree():
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    import verify_data_tree_clean as module

    return module


def verify_data_tree() -> list[str]:
    module = _import_verify_data_tree()
    violations = module.find_violations()

    if violations:
        return [
            f"data/{path.relative_to(module.ROOT / 'data')}"
            for path in violations
        ]

    return []


def verify_runtime_config_artifacts() -> list[str]:
    errors: list[str] = []

    for path in RUNTIME_CONFIG_ARTIFACTS:
        if path.is_file():
            errors.append(
                f"{path.relative_to(ROOT)} must not be present for release builds "
                "(runtime artifact; remove or relocate before packaging)."
            )

    return errors


def verify_bundled_config_paths() -> list[str]:
    errors: list[str] = []

    for path in BUNDLED_CONFIG_JSON:
        if not path.is_file():
            errors.append(f"Missing bundled config template: {path.relative_to(ROOT)}")
            continue

        text = path.read_text(encoding="utf-8")

        if DEVELOPER_PATH_PATTERN.search(text):
            errors.append(
                f"{path.relative_to(ROOT)} contains developer-specific paths."
            )

    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(verify_data_tree())
    errors.extend(verify_runtime_config_artifacts())
    errors.extend(verify_bundled_config_paths())

    if errors:
        print("ERROR: Release hygiene verification failed:", file=sys.stderr)

        for message in errors:
            print(f"  - {message}", file=sys.stderr)

        print(
            "\nRun scripts/clean_data_tree.py and remove runtime config artifacts "
            "under src/config/ before building a release.",
            file=sys.stderr,
        )
        return 1

    print("Release hygiene verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
