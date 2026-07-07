#!/usr/bin/env bash
# ============================================================================
# Project X — Windows build helper (Linux / Git Bash)
# ============================================================================
#
# Primary Windows release workflow (SAVE-068):
#   Boot into native Windows and run:  scripts\build_windows.bat
#
# This shell script is for:
#   - Asset/path verification on Linux (--prepare-only)
#   - Optional WSL alternative (not recommended)
#
# PyInstaller is not a cross-compiler. Linux Python cannot produce Windows .exe.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST_PYTHON="${PROJECTX_PYTHON:-}"
WINDOWS_PYTHON="${PROJECTX_WINDOWS_PYTHON:-}"
PREPARE_ONLY=0

usage() {
    cat <<EOF
Project X Windows build helper (Linux / Git Bash)

Primary workflow on Windows:
  scripts\\build_windows.bat

This script:
  --prepare-only   Verify bundled assets and paths on Linux (no PyInstaller)
  (default)        WSL alternative only — requires Windows Python

Environment:
  PROJECTX_WINDOWS_PYTHON   Path to Windows python.exe (WSL alternative)
  PROJECTX_PYTHON           Linux Python for --prepare-only checks

See BUILD_WINDOWS.md for the dual-boot workflow.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prepare-only)
            PREPARE_ONLY=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

is_windows_host() {
    [[ "${OS:-}" == "Windows_NT" ]] || [[ "${MSYSTEM:-}" != "" ]]
}

is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null
}

prepare_assets() {
    if [[ ! -f "$ROOT/src/resources/map/leaflet/leaflet.js" ]]; then
        echo "Fetching Leaflet assets..."
        require_command curl
        bash "$ROOT/scripts/fetch_leaflet.sh"
    fi

    for asset in projectx-logo.png projectx.ico; do
        if [[ ! -f "$ROOT/src/resources/branding/$asset" ]]; then
            echo "Generating branding assets..."
            "$HOST_PYTHON" "$ROOT/scripts/generate_branding_assets.py"
            break
        fi
    done
}

verify_data_tree() {
    echo "Verifying data/ tree contains no runtime artifacts..."
    "$HOST_PYTHON" "$ROOT/scripts/verify_data_tree_clean.py"
}

verify_paths() {
    echo "Verifying runtime path resolution..."

    "$HOST_PYTHON" - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))

from app import paths

assert paths.resource_path("translations", "en.json").exists(), "en.json missing"
assert paths.resource_path("map", "leaflet", "leaflet.js").exists(), "leaflet.js missing"
assert paths.resource_path("branding", "projectx.ico").exists(), "projectx.ico missing"
assert paths.resource_path("map", "map.html").exists(), "map.html missing"

print("paths.py resolves bundled resources correctly.")
PY

    if command -v rg >/dev/null 2>&1; then
        local violations
        violations="$(rg -n '"/home/' "$ROOT/src" --glob '*.py' \
            | rg -v 'hybrid_engine\.py|aiscatcher\.py|ship_registry\.py|ais/parser' \
            || true)"

        if [[ -n "$violations" ]]; then
            echo "WARNING: Hardcoded Linux paths found outside excluded modules:" >&2
            echo "$violations" >&2
            exit 1
        fi

        echo "No disallowed hardcoded Linux paths detected."
    else
        echo "Skipped hardcoded-path scan (ripgrep not installed)."
    fi
}

detect_windows_python() {
    if [[ -n "$WINDOWS_PYTHON" ]]; then
        echo "$WINDOWS_PYTHON"
        return 0
    fi

    if is_windows_host; then
        echo "Use scripts\\build_windows.bat for native Windows builds." >&2
        return 1
    fi

    if is_wsl; then
        local candidate
        for candidate in /mnt/c/Users/*/AppData/Local/Programs/Python/Python*/python.exe; do
            if [[ -f "$candidate" ]]; then
                echo "$candidate"
                return 0
            fi
        done
    fi

    return 1
}

to_windows_path() {
    local path="$1"

    if command -v wslpath >/dev/null 2>&1; then
        wslpath -w "$path"
        return
    fi

    echo "$path"
}

run_pyinstaller_windows() {
    local win_python="$1"
    local spec_path spec_win

    spec_path="$ROOT/installer/projectx.spec"
    spec_win="$(to_windows_path "$spec_path")"

    echo "WSL alternative build using: $win_python"
    echo "Prefer native Windows: scripts\\build_windows.bat"

    "$win_python" -m pip install --upgrade pip
    "$win_python" -m pip install -r "$(to_windows_path "$ROOT/requirements.txt")" pyinstaller

    (
        cd "$ROOT"
        "$win_python" -m PyInstaller --noconfirm "$spec_win"
    )

    "$HOST_PYTHON" "$ROOT/scripts/verify_bundle_no_data.py"

    if [[ -f "$ROOT/dist/projectx/projectx.exe" ]]; then
        echo "Windows bundle written to: $ROOT/dist/projectx/"
    else
        echo "ERROR: dist/projectx/projectx.exe was not created." >&2
        exit 1
    fi
}

if [[ -z "$HOST_PYTHON" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        HOST_PYTHON="$ROOT/.venv/bin/python"
    else
        HOST_PYTHON="python3"
    fi
fi

prepare_assets
verify_data_tree
verify_paths

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
    echo "Prepare-only complete."
    echo "Next: boot into Windows and run scripts\\build_windows.bat"
    exit 0
fi

if is_windows_host; then
    cat >&2 <<EOF
ERROR: Use the native Windows build script instead:

  scripts\\build_windows.bat

See BUILD_WINDOWS.md
EOF
    exit 2
fi

if ! WINDOWS_PYTHON="$(detect_windows_python)"; then
    cat >&2 <<EOF
ERROR: No Windows Python interpreter found for the WSL alternative.

Recommended workflow (dual-boot):
  1. git pull on Windows
  2. scripts\\build_windows.bat

WSL alternative (optional):
  export PROJECTX_WINDOWS_PYTHON='/mnt/c/Users/you/AppData/Local/Programs/Python/Python312/python.exe'
  ./scripts/build_windows.sh

Asset checks only:
  ./scripts/build_windows.sh --prepare-only

See BUILD_WINDOWS.md
EOF
    exit 2
fi

run_pyinstaller_windows "$WINDOWS_PYTHON"
