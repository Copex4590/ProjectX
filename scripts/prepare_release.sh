#!/usr/bin/env bash
# ============================================================================
# Project X — Prepare public release folder (SAVE-078)
# ============================================================================
# Authoritative Windows installer: release/windows/ProjectX-Setup.exe
# Website mirror: website/downloads/windows/ProjectX-Setup.exe

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"

read_manifest() {
    WIN_FILE="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path("release/manifest.json").read_text(encoding="utf-8"))
print(manifest["packages"]["windows"]["file"])
PY
)"
    WIN_RELEASE="${ROOT}/release/windows/${WIN_FILE}"
    WIN_WEBSITE="${ROOT}/website/downloads/windows/${WIN_FILE}"
}

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

read_manifest

echo "Syncing release notes..."
cp -f "$ROOT/website/releases/0.3-alpha.md" "$ROOT/release/notes/0.3.0-alpha.md"
cp -f "$ROOT/docs/RELEASE_NOTES_0.3_ALPHA.md" "$ROOT/release/notes/0.3.0-alpha-full.md"
echo "[OK] release/notes/ updated"

sync_artifact() {
    local src="$1"
    local dest="$2"
    cp -f "$src" "$dest"
    echo "[OK] Synced $(basename "$dest")"
}

echo "Syncing Windows release artifact..."
if [[ ! -f "$WIN_RELEASE" ]]; then
    echo "[FAIL] Windows installer missing: $WIN_RELEASE"
    echo "       Build on Windows: scripts\\build_windows.bat"
    exit 1
fi
echo "[OK] Windows installer present: ${WIN_RELEASE#${ROOT}/}"
sync_artifact "$WIN_RELEASE" "$WIN_WEBSITE"
if ! cmp -s "$WIN_RELEASE" "$WIN_WEBSITE"; then
    echo "[FAIL] Website copy differs from release/windows/"
    exit 1
fi
echo "[OK] Website copy verified: ${WIN_WEBSITE#${ROOT}/}"

echo "Syncing Linux release artifacts..."
LINUX_SYNCED=0
for file in "$ROOT/release/linux"/*; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    sync_artifact "$file" "$ROOT/website/downloads/linux/$(basename "$file")"
    LINUX_SYNCED=$((LINUX_SYNCED + 1))
done
if [[ "$LINUX_SYNCED" -eq 0 ]]; then
    echo "[WARN] No Linux artifacts under release/linux/ (run ./scripts/build_linux_release.sh)"
fi

echo "Generating checksums..."
bash "$ROOT/scripts/generate_release_checksums.sh"

if [[ ! -f "$ROOT/release/checksums/SHA256SUMS" ]]; then
    echo "[FAIL] Checksum generation did not produce release/checksums/SHA256SUMS"
    exit 1
fi
grep -Fq "$(basename "$WIN_RELEASE")" "$ROOT/release/checksums/SHA256SUMS" || {
    echo "[FAIL] SHA256SUMS missing Windows installer entry"
    exit 1
}
echo "[OK] SHA256SUMS includes Windows installer"

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
echo "Next: ./scripts/verify_windows_release.sh"
echo "Next: ./scripts/verify_release.sh"
