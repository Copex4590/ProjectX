#!/usr/bin/env bash
# ============================================================================
# Project X — Linux PyInstaller build
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-}"
PREPARE_ONLY=0

usage() {
    cat <<EOF
Project X Linux build

Usage: $0 [options]

Options:
  --prepare-only   Fetch bundled assets and verify paths; do not run PyInstaller
  -h, --help       Show this help

Environment:
  PROJECTX_PYTHON   Python interpreter (default: .venv/bin/python or python3)
  PROJECTX_BUILD    Build label written into the bundle (optional)
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

ensure_build_python() {
    if [[ -n "$PYTHON" ]]; then
        return
    fi

    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
        return
    fi

    require_command python3
    echo "Creating build virtual environment at ${ROOT}/.venv ..."
    python3 -m venv "$ROOT/.venv"
    PYTHON="$ROOT/.venv/bin/python"
}

prepare_assets() {
    if [[ ! -f "$ROOT/src/resources/map/cesium/Cesium.js" ]]; then
        echo "Fetching Cesium assets..."
        require_command curl
        bash "$ROOT/scripts/fetch_cesium.sh"
    fi

    for asset in projectx-logo.png projectx.ico; do
        if [[ ! -f "$ROOT/src/resources/branding/$asset" ]]; then
            echo "Generating branding assets..."
            "$PYTHON" "$ROOT/scripts/generate_branding_assets.py"
            break
        fi
    done
}

verify_data_tree() {
    echo "Preparing release hygiene..."
    bash "$ROOT/scripts/prepare_release_hygiene.sh"
}

verify_paths() {
    echo "Verifying runtime path resolution..."

    "$PYTHON" - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))

from app import paths

assert paths.bundle_dir().exists(), "bundle_dir missing"
assert paths.resource_path("translations", "en.json").exists(), "en.json missing"
assert paths.resource_path("map", "cesium", "Cesium.js").exists(), "Cesium.js missing"
assert paths.resource_path("branding", "projectx-logo.png").exists(), "logo missing"
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

install_build_deps() {
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$ROOT/requirements.txt" pyinstaller
}

run_pyinstaller() {
    echo "Running PyInstaller for Linux..."
    "$PYTHON" -m PyInstaller --noconfirm "$ROOT/installer/projectx.spec"
    echo "Linux bundle written to: $ROOT/dist/projectx/"
    "$PYTHON" "$ROOT/scripts/verify_bundle_no_data.py"
}

if [[ -z "$PYTHON" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

prepare_assets
verify_data_tree
verify_paths

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
    echo "Prepare-only complete."
    exit 0
fi

ensure_build_python
install_build_deps
run_pyinstaller
