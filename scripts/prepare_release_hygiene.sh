#!/usr/bin/env bash
# ============================================================================
# Project X — Prepare repository tree for release packaging
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-}"

if [[ -z "$PYTHON" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

echo "Resetting data/ tree to release placeholders..."
"$PYTHON" "$ROOT/scripts/clean_data_tree.py"

echo "Removing developer runtime config artifacts from src/config/..."
rm -f "$ROOT/src/config/migration_state.json"

echo "Verifying release hygiene..."
"$PYTHON" "$ROOT/scripts/verify_release_hygiene.py"

echo "Release hygiene preparation complete."
