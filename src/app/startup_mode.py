# ============================================================================
# Project X
# Startup Mode Decision (SAVE-107-C5)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from preferences.preferences_manager import preferences_manager
from storage import configured_data_root, legacy_data_exists, requires_data_root_setup


class StartupMode(str, Enum):
    """Primary startup path selected before the main window loads."""

    FIRST_RUN_SETUP = "first_run_setup"
    LEGACY_UPGRADE = "legacy_upgrade"
    NORMAL = "normal"


@dataclass(frozen=True)
class StartupPlan:
    """Resolved startup path and follow-up wizard requirements."""

    mode: StartupMode
    needs_data_root_wizard: bool = False
    needs_observation_wizard: bool = False

    @property
    def needs_legacy_upgrade(self) -> bool:
        return self.mode is StartupMode.LEGACY_UPGRADE

    @property
    def show_splash(self) -> bool:
        return self.mode is not StartupMode.FIRST_RUN_SETUP


def determine_startup_mode() -> StartupPlan:
    """Return the single startup path the application should execute."""

    existing_user = is_existing_user()
    has_observations = has_observation_points()

    if should_offer_legacy_upgrade(existing_user=existing_user):
        return StartupPlan(mode=StartupMode.LEGACY_UPGRADE)

    needs_data_root = needs_data_root_wizard(existing_user=existing_user)

    if needs_data_root or (not existing_user and not has_observations):
        return StartupPlan(
            mode=StartupMode.FIRST_RUN_SETUP,
            needs_data_root_wizard=needs_data_root,
            needs_observation_wizard=not has_observations,
        )

    return StartupPlan(mode=StartupMode.NORMAL)


def needs_deferred_storage_layout() -> bool:
    """Return True when storage layout must wait for the data root wizard."""

    return needs_data_root_wizard(existing_user=is_existing_user())


def is_existing_user() -> bool:
    """Return True when the installation should not be treated as first-run."""

    preferences = preferences_manager.get()

    if preferences.has_data_directory():
        return True

    if preferences.first_run_completed:
        return True

    if preferences.legacy_migration_deferred:
        return True

    if has_observation_points():
        return True

    if legacy_data_exists():
        return True

    return False


def has_observation_points() -> bool:

    if configured_data_root() is None and requires_data_root_setup():
        return False

    from observation.observation_manager import (
        file_contains_observation_points,
        observation_points_file,
    )

    return file_contains_observation_points(observation_points_file())


def needs_data_root_wizard(*, existing_user: bool | None = None) -> bool:
    """Return True when the first-run data location wizard should appear."""

    if configured_data_root() is not None:
        return False

    if existing_user if existing_user is not None else is_existing_user():
        return False

    return requires_data_root_setup()


def should_offer_legacy_upgrade(*, existing_user: bool | None = None) -> bool:
    """Return True when the legacy data upgrade dialog should appear."""

    preferences = preferences_manager.get()

    if preferences.has_data_directory() or preferences.legacy_migration_deferred:
        return False

    if not legacy_data_exists():
        return False

    if not has_observation_points():
        return False

    _ = existing_user
    return True
