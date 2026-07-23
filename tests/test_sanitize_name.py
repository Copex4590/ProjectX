# ============================================================================
# Project X
# sanitize_name path-safety tests
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

from logbook.duna_format import sanitize_name


def test_sanitize_name_replaces_forward_slash():
    assert sanitize_name("F/VLE TAD") == "F VLE TAD"


def test_sanitize_name_replaces_backslash():
    assert sanitize_name("F\\VLE TAD") == "F VLE TAD"


def test_sanitize_name_replaces_os_separators():
    raw = f"ALPHA{os.sep}BETA"
    assert sanitize_name(raw) == "ALPHA BETA"
    if os.altsep:
        raw_alt = f"ALPHA{os.altsep}BETA"
        assert sanitize_name(raw_alt) == "ALPHA BETA"


def test_sanitize_name_still_strips_at_and_whitespace():
    assert sanitize_name("  @QUEEN  ") == "QUEEN"


def test_sanitize_name_collapses_spaces_from_separators():
    assert sanitize_name("A//B\\\\C") == "A B C"


def test_deli_hajok_path_stays_flat():
    deli_dir = Path("/home/zoli/rtl-monitor/deli_hajok")
    name = sanitize_name("F/VLE TAD")
    path = deli_dir / f"{name}.txt"
    assert path == Path("/home/zoli/rtl-monitor/deli_hajok/F VLE TAD.txt")
    assert path.parent == deli_dir
