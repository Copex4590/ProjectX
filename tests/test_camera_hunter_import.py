# ============================================================================
# Project X
# Camera Hunter vendor import smoke (no discovery / GUI / playback)
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_camera_result_import():
    from camera_hunter.models import CameraResult

    assert CameraResult is not None


def test_discovery_engine_import():
    from camera_hunter.engine import DiscoveryEngine

    assert DiscoveryEngine is not None


def test_listing_hunter_cli_import():
    from camera_hunter.app.listing_hunter import main
    from camera_hunter.listing_hunter import main as entry_main

    assert main is not None
    assert entry_main is main or callable(entry_main)


def test_catalog_validator_cli_import():
    from camera_hunter.app.catalog_validator import main
    from camera_hunter.catalog_validator import main as entry_main

    assert main is not None
    assert callable(entry_main)


def test_validated_preview_cli_import():
    from camera_hunter.app.validated_preview import main
    from camera_hunter.validated_preview import main as entry_main

    assert main is not None
    assert callable(entry_main)
