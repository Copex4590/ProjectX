#!/usr/bin/env bash
# ============================================================================
# Project X — Remove PyInstaller build artifacts
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Removing build artifacts under ${ROOT}..."

rm -rf build/ dist/ .install-test/
rm -f "$ROOT/src/resources/build_stamp"

find "$ROOT/src" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$ROOT/scripts" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

echo "Clean complete."
