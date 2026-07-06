#!/usr/bin/env bash
# ============================================================================
# Project X — Verify Windows release artifact (Linux host / post-prepare)
# ============================================================================
# Authoritative installer path: release/windows/ProjectX-Setup.exe
# Website mirror: website/downloads/windows/ProjectX-Setup.exe

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"
CHECKSUM_DIR="${ROOT}/release/checksums"
FAILED=0

read_names() {
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

fail() {
    echo "[FAIL] $*"
    FAILED=1
}

ok() {
    echo "[OK] $*"
}

echo "Verifying Windows release artifact..."
read_names

if [[ ! -f "$WIN_RELEASE" ]]; then
    fail "Windows installer not found: $WIN_RELEASE (run scripts\\build_windows.bat on Windows)"
    echo ""
    echo "Verification failed."
    exit 1
fi

ok "Release artifact present: ${WIN_RELEASE#${ROOT}/}"

if [[ ! -f "$WIN_WEBSITE" ]]; then
    fail "Website download copy missing: $WIN_WEBSITE (run ./scripts/prepare_release.sh)"
else
    ok "Website download copy present: ${WIN_WEBSITE#${ROOT}/}"
    if cmp -s "$WIN_RELEASE" "$WIN_WEBSITE"; then
        ok "Release and website copies are identical"
    else
        fail "Website copy differs from release/windows/ (re-run ./scripts/prepare_release.sh)"
    fi
fi

COMBINED_SUMS="${CHECKSUM_DIR}/SHA256SUMS"
if [[ -f "$COMBINED_SUMS" ]]; then
    ok "SHA256SUMS present: ${COMBINED_SUMS#${ROOT}/}"
    grep -Fq "$(basename "$WIN_RELEASE")" "$COMBINED_SUMS" && ok "SHA256SUMS lists Windows installer" || fail "SHA256SUMS missing Windows installer entry"
else
    fail "SHA256SUMS missing: $COMBINED_SUMS"
fi

SIDEcar="${CHECKSUM_DIR}/$(basename "$WIN_RELEASE").sha256"
if [[ -f "$SIDEcar" ]]; then
    ok "Per-file checksum: $(basename "$SIDEcar")"
    expected="$(awk '{print $1}' "$SIDEcar")"
    actual="$(sha256sum "$WIN_RELEASE" | awk '{print $1}')"
    if [[ "$expected" == "$actual" ]]; then
        ok "Checksum matches Windows installer"
    else
        fail "Checksum mismatch for Windows installer"
    fi
else
    fail "Missing checksum sidecar: ${SIDEcar#${ROOT}/}"
fi

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo "Windows release verification complete."
    echo "Run scripts\\verify_windows_installer.bat on Windows for install/uninstall tests."
    exit 0
fi

echo "Verification failed."
exit 1
