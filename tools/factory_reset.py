#!/usr/bin/env python3
# ============================================================================
# Project X — Development Factory Reset
# ============================================================================
#
# Removes user-generated runtime data so the next launch matches a fresh
# installation. Application code, bundled resources, and database schema
# definitions are left untouched.
#
# Usage (from repository root):
#   python tools/factory_reset.py
#   python tools/factory_reset.py --dry-run
#   python tools/factory_reset.py --yes
#

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"
DEV_CONFIG_DIR = SRC_DIR / "config"

DEFAULT_PLAYBACK_JSON = {
    "mode": "automatic",
    "preferred_backend": "mpv",
    "custom_executable": "",
    "custom_arguments": [],
}

DEFAULT_CAMERA_PACKS_STATE_JSON = {
    "enabled_packs": [],
}

DEV_CONFIG_FILES_TO_REMOVE = (
    "preferences.json",
    "observation_points.json",
    "cameras.json",
    "ais_api_key.txt",
)

FROZEN_CONFIG_FILES_TO_REMOVE = DEV_CONFIG_FILES_TO_REMOVE + (
    "camera_packs_state.json",
)

LEGACY_DEV_DATABASES = (
    SRC_DIR / "alerts" / "alerts.db",
    SRC_DIR / "timeline" / "timeline.db",
    SRC_DIR / "database" / "vessels.db",
)

DATA_DATABASES = (
    "alerts.db",
    "timeline.db",
    "vessels.db",
)

DATA_RUNTIME_FILES = (
    "obs_freeze.trace",
)

DATA_DIRS_TO_CLEAR = (
    DATA_DIR / "Hajók",
    DATA_DIR / "vessel_photos",
)

HOME = Path.home()

FROZEN_USER_DIRS = (
    HOME / ".local" / "share" / "projectx",
    HOME / ".local" / "share" / "Project X",
)

CACHE_DIRS = (
    HOME / ".cache" / "Project X",
    HOME / ".cache" / "projectx",
)

LEGACY_AIS_KEY = HOME / "duna-monitor" / "api_key.txt"


class ResetAction:
    def __init__(self, kind: str, path: Path, detail: str = "") -> None:
        self.kind = kind
        self.path = path
        self.detail = detail


def _require_repo_root() -> None:
    if not (SRC_DIR / "main.py").is_file():
        print(
            "ERROR: Expected Project X repository layout (src/main.py missing).",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2) + "\n"


def _collect_actions() -> list[ResetAction]:
    actions: list[ResetAction] = []

    for name in DEV_CONFIG_FILES_TO_REMOVE:
        actions.append(ResetAction("delete", DEV_CONFIG_DIR / name))

    actions.append(
        ResetAction(
            "write",
            DEV_CONFIG_DIR / "camera_packs" / "state.json",
            _json_text(DEFAULT_CAMERA_PACKS_STATE_JSON),
        )
    )
    actions.append(
        ResetAction(
            "write",
            DEV_CONFIG_DIR / "playback.json",
            _json_text(DEFAULT_PLAYBACK_JSON),
        )
    )

    for path in LEGACY_DEV_DATABASES:
        actions.append(ResetAction("delete", path))

    for name in DATA_DATABASES:
        actions.append(ResetAction("delete", DATA_DIR / name))

    for name in DATA_RUNTIME_FILES:
        actions.append(ResetAction("delete", DATA_DIR / name))

    for directory in DATA_DIRS_TO_CLEAR:
        if not directory.is_dir():
            continue

        for child in sorted(directory.iterdir()):
            if child.name == ".gitkeep":
                continue
            actions.append(ResetAction("delete", child))

    frozen_config = HOME / ".local" / "share" / "projectx" / "config"
    for name in FROZEN_CONFIG_FILES_TO_REMOVE:
        actions.append(ResetAction("delete", frozen_config / name))

    frozen_data = HOME / ".local" / "share" / "projectx" / "data"
    if frozen_data.is_dir():
        for path in sorted(frozen_data.rglob("*"), reverse=True):
            actions.append(ResetAction("delete", path))
        actions.append(ResetAction("delete", frozen_data))

    for directory in FROZEN_USER_DIRS:
        if directory.is_dir():
            actions.append(ResetAction("delete", directory))

    for directory in CACHE_DIRS:
        if directory.is_dir():
            actions.append(ResetAction("delete", directory))

    if LEGACY_AIS_KEY.is_file():
        actions.append(ResetAction("delete", LEGACY_AIS_KEY))

    return actions


def _existing_actions(actions: list[ResetAction]) -> list[ResetAction]:
    existing: list[ResetAction] = []

    for action in actions:
        if action.kind == "write":
            current = action.path.read_text(encoding="utf-8") if action.path.is_file() else ""
            if current != action.detail:
                existing.append(action)
            continue

        if action.path.exists() or action.path.is_symlink():
            existing.append(action)

    return existing


def _format_action(action: ResetAction) -> str:
    if action.kind == "write":
        return f"reset  {action.path}"
    return f"delete {action.path}"


def _apply_action(action: ResetAction, *, dry_run: bool) -> None:
    if dry_run:
        return

    if action.kind == "write":
        action.path.parent.mkdir(parents=True, exist_ok=True)
        action.path.write_text(action.detail, encoding="utf-8")
        return

    if action.path.is_dir() and not action.path.is_symlink():
        shutil.rmtree(action.path)
        return

    action.path.unlink(missing_ok=True)


def _projectx_running() -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", r"(ProjectX|projectx|src/main\.py)"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False

    return bool(result.stdout.strip())


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reset Project X user data to a fresh-installation state "
            "(development utility)."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without making changes.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    args = parser.parse_args(argv)

    _require_repo_root()

    actions = _existing_actions(_collect_actions())

    if not actions:
        print("Nothing to reset — Project X is already in a clean state.")
        return 0

    print("Project X factory reset (development only)")
    print(f"Repository: {REPO_ROOT}")
    print()
    print("The following user-generated data will be removed or reset:")
    for action in actions:
        print(f"  {_format_action(action)}")
    print()
    print("Application code, bundled resources, translations, and icons are kept.")
    print()

    if _projectx_running():
        print(
            "WARNING: Project X appears to be running. "
            "Close the application before resetting to avoid files being recreated."
        )
        print()

    if args.dry_run:
        print("Dry run complete — no changes were made.")
        return 0

    if not args.yes and not _confirm("Proceed?"):
        print("Cancelled.")
        return 1

    for action in actions:
        _apply_action(action, dry_run=False)

    for directory in DATA_DIRS_TO_CLEAR:
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    print("Factory reset complete.")
    print("Launch Project X to start from a fresh installation state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
