#!/usr/bin/env bash
# ============================================================================
# Project X — Public release verification (SAVE-078)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"
PORT="${PORT:-8766}"
FAILED=0
WARNINGS=0
SERVER_PID=""

cleanup() {
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

fail() {
    echo "[FAIL] $*"
    FAILED=1
}

warn() {
    echo "[WARN] $*"
    WARNINGS=$((WARNINGS + 1))
}

ok() {
    echo "[OK] $*"
}

echo "============================================================"
echo "Project X — Public Release Verification (SAVE-078)"
echo "============================================================"
echo ""

echo "--- Release folder structure ---"
for path in \
    release/manifest.json \
    release/README.md \
    release/windows \
    release/linux \
    release/notes; do
    [[ -e "$ROOT/$path" ]] && ok "Present: $path" || fail "Missing: $path"
done

echo ""
echo "--- Release notes ---"
for note in release/notes/0.3.0-alpha.md release/notes/0.3.0-alpha-full.md; do
    [[ -f "$ROOT/$note" ]] && ok "Present: $note" || fail "Missing: $note"
done

echo ""
echo "--- Manifest and website config ---"
"$PYTHON" - <<'PY'
import json
import sys
from pathlib import Path

root = Path(".")
failed = False

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

manifest = load(root / "release" / "manifest.json")
website = load(root / "website" / "releases.json")

checks = [
    ("version vs windows.version", manifest["version"], website["windows"]["version"]),
    ("website_version vs latest", manifest["website_version"], website["latest"]),
    ("release_date", manifest["release_date"], website["release_date"]),
    ("windows file", manifest["packages"]["windows"]["file"], website["windows"]["file"]),
    ("linux file", manifest["packages"]["linux"]["primary"]["file"], website["linux"]["file"]),
]

for label, left, right in checks:
    if left == right:
        print(f"[OK] {label}: {left}")
    else:
        print(f"[FAIL] {label}: manifest={left!r} website={right!r}")
        failed = True

secondary = manifest["packages"]["linux"].get("secondary", {}).get("file")
website_secondary = website["linux"].get("secondary_file")
if secondary and website_secondary and secondary == website_secondary:
    print(f"[OK] linux secondary file: {secondary}")
elif secondary and not website_secondary:
    print(f"[WARN] manifest secondary file not listed in website/releases.json")
else:
    if secondary != website_secondary:
        print(f"[FAIL] linux secondary mismatch: manifest={secondary!r} website={website_secondary!r}")
        failed = True

required_manifest_keys = ["version", "release_date", "packages", "checksum_files", "release_notes", "minimum_os", "build"]
for key in required_manifest_keys:
    if key in manifest:
        print(f"[OK] manifest key present: {key}")
    else:
        print(f"[FAIL] manifest missing key: {key}")
        failed = True

sys.exit(1 if failed else 0)
PY
if [[ $? -ne 0 ]]; then FAILED=1; fi

echo ""
echo "--- Windows release artifact ---"
WIN_FILE="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("release/manifest.json").read_text(encoding="utf-8"))["packages"]["windows"]["file"])
PY
)"
WIN_RELEASE="$ROOT/release/windows/$WIN_FILE"
WIN_WEBSITE="$ROOT/website/downloads/windows/$WIN_FILE"

if [[ -f "$WIN_RELEASE" ]]; then
    ok "Windows installer present: release/windows/$WIN_FILE"
    if [[ -f "$WIN_WEBSITE" ]]; then
        ok "Website Windows download present: website/downloads/windows/$WIN_FILE"
        if cmp -s "$WIN_RELEASE" "$WIN_WEBSITE"; then
            ok "Windows release and website copies match"
        else
            fail "Windows website copy differs from release/windows/ (run ./scripts/prepare_release.sh)"
        fi
    else
        warn "Website Windows download missing: website/downloads/windows/$WIN_FILE"
    fi
else
    warn "Windows installer not built yet: release/windows/$WIN_FILE"
fi

echo ""
echo "--- Release artifacts ---"
ARTIFACT_PATHS=()
while IFS= read -r line; do
    ARTIFACT_PATHS+=("$line")
done < <("$PYTHON" - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path("release/manifest.json").read_text(encoding="utf-8"))
paths = []
win = manifest["packages"]["windows"]
paths.append(str(Path(win["directory"]) / win["file"]))
primary = manifest["packages"]["linux"]["primary"]
paths.append(str(Path(primary["directory"]) / primary["file"]))
secondary = manifest["packages"]["linux"].get("secondary")
if secondary:
    paths.append(str(Path(secondary["directory"]) / secondary["file"]))
for path in paths:
    print(path)
PY
)

ARTIFACTS_PRESENT=0
for rel in "${ARTIFACT_PATHS[@]}"; do
    if [[ -f "$ROOT/$rel" ]]; then
        ok "Artifact present: $rel"
        ARTIFACTS_PRESENT=$((ARTIFACTS_PRESENT + 1))
    else
        warn "Artifact not built yet: $rel"
    fi
done

echo ""
echo "--- Checksums ---"
for sums_path in release/linux/SHA256SUMS release/windows/SHA256SUMS; do
    if [[ -f "$ROOT/$sums_path" ]]; then
        ok "Checksum file present: $sums_path"
    else
        warn "Checksum file missing: $sums_path (run ./scripts/generate_release_checksums.sh)"
    fi
done

CHECK_OK=1
verify_sums_file() {
    local sums_file="$1"
    local artifact_dir="$2"
    [[ -f "$sums_file" ]] || return 0
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        local hash base artifact actual
        hash="$(awk '{print $1}' <<< "$line")"
        base="$(awk '{print $NF}' <<< "$line")"
        artifact="${artifact_dir}/${base}"
        [[ -f "$artifact" ]] || continue
        actual="$(sha256sum "$artifact" | awk '{print $1}')"
        if [[ "$hash" == "$actual" ]]; then
            ok "Checksum matches: $base"
        else
            fail "Checksum mismatch: $base"
            CHECK_OK=0
        fi
    done < "$sums_file"
}

verify_sums_file "$ROOT/release/linux/SHA256SUMS" "$ROOT/release/linux"
verify_sums_file "$ROOT/release/windows/SHA256SUMS" "$ROOT/release/windows"
[[ "$CHECK_OK" -eq 1 && "$ARTIFACTS_PRESENT" -gt 0 ]] || true

echo ""
echo "--- Website download paths ---"
"$PYTHON" - <<'PY'
import json
from pathlib import Path

root = Path(".")
website = json.loads((root / "website" / "releases.json").read_text(encoding="utf-8"))
manifest = json.loads((root / "release" / "manifest.json").read_text(encoding="utf-8"))
failed = False

def check(platform, filename, website_dir):
    path = root / website_dir / filename
    if path.exists():
        print(f"[OK] Website download ready: {path}")
    else:
        print(f"[WARN] Website download missing: {path}")
    return path

check("windows", website["windows"]["file"], manifest["packages"]["windows"]["website_directory"])
check("linux", website["linux"]["file"], manifest["packages"]["linux"]["primary"]["website_directory"])
secondary = website["linux"].get("secondary_file")
if secondary:
    check("linux", secondary, manifest["packages"]["linux"]["secondary"]["website_directory"])
linux_sums = root / manifest["packages"]["linux"]["primary"]["website_directory"] / "SHA256SUMS"
if linux_sums.exists():
    print(f"[OK] Website download ready: {linux_sums}")
else:
    print(f"[WARN] Website download missing: {linux_sums}")
PY

echo ""
echo "--- Website HTTP smoke test ---"
if command -v curl >/dev/null 2>&1; then
    "$PYTHON" -m http.server "$PORT" --directory "$ROOT/website" >/dev/null 2>&1 &
    SERVER_PID=$!
    sleep 1
    for url in \
        "http://127.0.0.1:${PORT}/releases.json" \
        "http://127.0.0.1:${PORT}/download.html" \
        "http://127.0.0.1:${PORT}/releases/0.3-alpha.md"; do
        code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
        if [[ "$code" == "200" ]]; then
            ok "HTTP $code $url"
        else
            fail "HTTP $code $url"
        fi
    done

    WIN_DL="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("website/releases.json").read_text(encoding="utf-8"))
print("downloads/windows/" + c["windows"]["file"])
PY
)"
    if [[ -f "$ROOT/website/$WIN_DL" ]]; then
        code="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/${WIN_DL}")"
        if [[ "$code" == "200" ]]; then
            ok "HTTP $code http://127.0.0.1:${PORT}/${WIN_DL}"
        else
            fail "HTTP $code Windows download URL (expected 200): ${WIN_DL}"
        fi
    fi
else
    warn "curl not available; skipped website HTTP smoke test"
fi

echo ""
echo "============================================================"
if [[ "$FAILED" -eq 0 ]]; then
    echo "RELEASE VERIFICATION: PASS"
    if [[ "$WARNINGS" -gt 0 ]]; then
        echo "Warnings: $WARNINGS (expected before platform builds are uploaded)"
    fi
    echo ""
    echo "Repository structure is ready for first public Alpha release."
    echo "Build Windows/Linux packages, run prepare_release.sh, then publish."
    exit 0
fi

echo "RELEASE VERIFICATION: FAIL"
exit 1
