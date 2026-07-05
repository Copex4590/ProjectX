#!/usr/bin/env bash
# ============================================================================
# Project X — Prepare public release folder (SAVE-078)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"

WINDOWS_RELEASE_DIR="$ROOT/release/windows"
WINDOWS_WEBSITE_DIR="$ROOT/website/downloads/windows"
WINDOWS_INSTALLER_NAME="ProjectX-Setup.exe"
WINDOWS_INSTALLER_CANONICAL="$WINDOWS_RELEASE_DIR/$WINDOWS_INSTALLER_NAME"
WINDOWS_INSTALLER_WEBSITE="$WINDOWS_WEBSITE_DIR/$WINDOWS_INSTALLER_NAME"

echo "============================================================"
echo "Project X — Prepare Public Release"
echo "============================================================"

mkdir -p \
    "$WINDOWS_RELEASE_DIR" \
    "$ROOT/release/linux" \
    "$ROOT/release/checksums" \
    "$ROOT/release/notes" \
    "$WINDOWS_WEBSITE_DIR" \
    "$ROOT/website/downloads/linux"

echo "Syncing release notes..."
cp -f "$ROOT/website/releases/0.3-alpha.md" "$ROOT/release/notes/0.3.0-alpha.md"
cp -f "$ROOT/docs/RELEASE_NOTES_0.3_ALPHA.md" "$ROOT/release/notes/0.3.0-alpha-full.md"
echo "[OK] release/notes/ updated"

sync_artifact() {
    local src="$1"
    local dest="$2"
    if [[ -f "$src" ]]; then
        cp -f "$src" "$dest"
        echo "[OK] Synced $(basename "$dest")"
    fi
}

echo "Syncing website download copies..."
for file in "$WINDOWS_RELEASE_DIR"/*; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    sync_artifact "$file" "$WINDOWS_WEBSITE_DIR/$(basename "$file")"
done
for file in "$ROOT/release/linux"/*; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    sync_artifact "$file" "$ROOT/website/downloads/linux/$(basename "$file")"
done

if [[ -f "$WINDOWS_INSTALLER_CANONICAL" ]]; then
    echo "[OK] Canonical Windows installer: $WINDOWS_INSTALLER_CANONICAL"
else
    echo "[WARN] Canonical Windows installer missing: $WINDOWS_INSTALLER_CANONICAL"
fi

echo "Generating checksums..."
bash "$ROOT/scripts/generate_release_checksums.sh"

BUILD_PYTHON="$("$PYTHON" - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:2])))
PY
)"

echo "Updating manifest build metadata (python_used_for_build=${BUILD_PYTHON})..."
"$PYTHON" - <<PY
import json
from pathlib import Path

manifest_path = Path("${ROOT}/release/manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["build"]["python_used_for_build"] = "${BUILD_PYTHON}"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("[OK] release/manifest.json updated")
PY

echo ""
echo "Release preparation complete."
echo "Next: ./scripts/verify_release.sh"
