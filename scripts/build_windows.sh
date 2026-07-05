#!/usr/bin/env bash
# ============================================================================
# Project X — Windows PyInstaller build orchestration
# ============================================================================
#
# PyInstaller is not a cross-compiler. Native Windows binaries must be built
# with a Windows Python interpreter. From Linux, use one of:
#   - WSL + Windows Python (auto-detected under /mnt/c/Users/...)
#   - PROJECTX_WINDOWS_PYTHON=/path/to/python.exe
#   - Run this script on a Windows host (Git Bash / MSYS)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST_PYTHON="${PROJECTX_PYTHON:-}"
WINDOWS_PYTHON="${PROJECTX_WINDOWS_PYTHON:-}"
PREPARE_ONLY=0

usage() {
    cat <<EOF
Project X Windows build

Usage: $0 [options]

Options:
  --prepare-only   Fetch bundled assets and verify paths; do not run PyInstaller
  -h, --help       Show this help

Environment:
  PROJECTX_WINDOWS_PYTHON   Windows python.exe (required on Linux unless auto-detected in WSL)
  PROJECTX_PYTHON           Linux python3 used for asset prep and verification (default: python3 or .venv)
  PROJECTX_BUILD            Build label (optional)

Examples:
  # WSL on a Windows machine (auto-detect Windows Python):
  ./scripts/build_windows.sh

  # Linux with explicit Windows interpreter path:
  PROJECTX_WINDOWS_PYTHON='/mnt/c/Users/you/AppData/Local/Programs/Python/Python312/python.exe' \\
    ./scripts/build_windows.sh

  # Native Windows (Git Bash):
  ./scripts/build_windows.sh
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
}

detect_windows_python() {
    if [[ -n "$WINDOWS_PYTHON" ]]; then
        echo "$WINDOWS_PYTHON"
        return 0
    fi

    if is_windows_host; then
        if command -v py >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
        if command -v python >/dev/null 2>&1; then
            echo "python"
            return 0
        fi
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

    if is_windows_host; then
        echo "$path"
        return
    fi

    if command -v wslpath >/dev/null 2>&1; then
        wslpath -w "$path"
        return
    fi

    echo "$path"
}

run_pyinstaller_windows() {
    local win_python="$1"
    local spec_path root_win spec_win

    spec_path="$ROOT/installer/projectx.spec"
    root_win="$(to_windows_path "$ROOT")"
    spec_win="$(to_windows_path "$spec_path")"

    echo "Using Windows Python: $win_python"
    echo "Project root (Windows path): $root_win"

    "$win_python" -m pip install --upgrade pip
    "$win_python" -m pip install -r "$(to_windows_path "$ROOT/requirements.txt")" pyinstaller

    (
        cd "$ROOT"
        "$win_python" -m PyInstaller --noconfirm "$spec_win"
    )

    echo "Windows bundle written to: $ROOT/dist/projectx/"
    echo "Next step: compile installer/windows/projectx.iss with Inno Setup on Windows."
}

if [[ -z "$HOST_PYTHON" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        HOST_PYTHON="$ROOT/.venv/bin/python"
    else
        HOST_PYTHON="python3"
    fi
fi

prepare_assets
verify_paths

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
    echo "Prepare-only complete."
    exit 0
fi

if ! WINDOWS_PYTHON="$(detect_windows_python)"; then
    cat >&2 <<EOF
ERROR: No Windows Python interpreter found.

PyInstaller cannot produce native Windows executables from Linux alone.
Use one of these options:

  1. WSL on a Windows PC (this script auto-detects Windows Python under /mnt/c/Users/...)
  2. Set PROJECTX_WINDOWS_PYTHON to a Windows python.exe path
  3. Run this script on Windows (Git Bash / MSYS)
  4. Run asset preparation only: $0 --prepare-only

See BUILD_WINDOWS.md for the full workflow.
EOF
    exit 2
fi

run_pyinstaller_windows "$WINDOWS_PYTHON"
