#!/usr/bin/env bash
# ============================================================================
# Project X — Prepare public release folder (SAVE-078)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"

echo "============================================================"
echo "Project X — Prepare Public Release"
echo "============================================================"

mkdir -p \
    "$ROOT/release/windows" \
    "$ROOT/release/linux" \
    "$ROOT/release/checksums" \
    "$ROOT/release/notes" \
    "$ROOT/website/downloads/windows" \
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
for file in "$ROOT/release/windows"/*; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    sync_artifact "$file" "$ROOT/website/downloads/windows/$(basename "$file")"
done
for file in "$ROOT/release/linux"/*; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    sync_artifact "$file" "$ROOT/website/downloads/linux/$(basename "$file")"
done

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
