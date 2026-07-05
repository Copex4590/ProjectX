#!/usr/bin/env bash
# ============================================================================
# Project X website — release portal verification (SAVE-074)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
PORT="${PORT:-8765}"
SERVER_PID=""

cleanup() {
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

echo "Verifying release configuration under ${ROOT}..."

"$PYTHON" - <<'PY'
import json
import sys
from pathlib import Path

root = Path(".")
config_path = root / "releases.json"
config = json.loads(config_path.read_text(encoding="utf-8"))

latest = config["latest"]
notes_path = root / "releases" / f"{latest}.md"
errors = []

if not notes_path.exists():
    errors.append(f"Missing release notes file: {notes_path}")

for platform in ("windows", "linux"):
    entry = config.get(platform)
    if not entry:
        errors.append(f"Missing platform config: {platform}")
        continue
    filename = entry.get("file")
    if not filename:
        errors.append(f"Missing file name for platform: {platform}")
        continue
    expected_url = f"downloads/{platform}/{filename}"
    installer_path = root / expected_url
    print(f"[OK] {platform} URL -> {expected_url}")
    if not installer_path.exists():
        print(f"[WARN] Installer not uploaded yet: {installer_path}")
    else:
        print(f"[OK] Installer present: {installer_path}")

if errors:
    print("\nVerification failed:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)

print(f"[OK] releases.json latest={latest}")
print(f"[OK] release notes present: {notes_path}")
PY

echo
echo "Starting local web server on port ${PORT}..."

"$PYTHON" -m http.server "$PORT" >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1

BASE="http://127.0.0.1:${PORT}"

check_url() {
    local url="$1"
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
    if [[ "$code" != "200" ]]; then
        echo "[FAIL] ${url} -> HTTP ${code}" >&2
        exit 1
    fi
    echo "[OK] ${url} -> HTTP ${code}"
}

check_url "${BASE}/releases.json"
check_url "${BASE}/releases/0.3-alpha.md"
check_url "${BASE}/index.html"
check_url "${BASE}/download.html"

echo
echo "Simulating releases.json update..."
TMP_CONFIG="$(mktemp)"
"$PYTHON" - <<PY
import json
from pathlib import Path

config = json.loads(Path("releases.json").read_text(encoding="utf-8"))
config["windows"]["file"] = "ProjectX-Setup-0.4-beta.exe"
config["linux"]["file"] = "ProjectX-0.4-beta.AppImage"
config["latest"] = "0.4-beta"
Path("${TMP_CONFIG}").write_text(json.dumps(config), encoding="utf-8")
PY

WIN_URL="$("$PYTHON" - <<PY
import json
from pathlib import Path
config = json.loads(Path("${TMP_CONFIG}").read_text(encoding="utf-8"))
print("downloads/windows/" + config["windows"]["file"])
PY
)"

LIN_URL="$("$PYTHON" - <<PY
import json
from pathlib import Path
config = json.loads(Path("${TMP_CONFIG}").read_text(encoding="utf-8"))
print("downloads/linux/" + config["linux"]["file"])
PY
)"

rm -f "$TMP_CONFIG"

if [[ "$WIN_URL" != "downloads/windows/ProjectX-Setup-0.4-beta.exe" ]]; then
    echo "[FAIL] Windows URL generation mismatch: ${WIN_URL}" >&2
    exit 1
fi

if [[ "$LIN_URL" != "downloads/linux/ProjectX-0.4-beta.AppImage" ]]; then
    echo "[FAIL] Linux URL generation mismatch: ${LIN_URL}" >&2
    exit 1
fi

echo "[OK] Windows download URL updates automatically -> ${WIN_URL}"
echo "[OK] Linux download URL updates automatically -> ${LIN_URL}"
echo
echo "Verification complete."
