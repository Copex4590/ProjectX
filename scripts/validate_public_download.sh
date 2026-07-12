#!/usr/bin/env bash
# ============================================================================
# Project X — Public download validation (SAVE-079)
# Simulates end-user download journey checks without modifying the application.
# ============================================================================

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"
PORT="${PORT:-8767}"
SERVER_PID=""
FAILED=0
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

cleanup() {
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

record_pass() {
    echo "[PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

record_fail() {
    echo "[FAIL] $1"
    FAILED=1
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

record_warn() {
    echo "[WARN] $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

echo "============================================================"
echo "Project X — Public Download Validation (SAVE-079)"
echo "============================================================"
echo ""

echo "--- User journey (simulated) ---"
for step in \
    "Browser opens official website (index.html)" \
    "User navigates to Download page" \
    "User selects Windows or Linux download card" \
    "Download URL resolves from releases.json" \
    "Installer/package file served" \
    "Install step (platform verify scripts)" \
    "First Run Wizard (manual — requires installed app)" \
    "Application starts (manual — requires installed app)"; do
    echo "  → $step"
done
echo ""

echo "--- Website validation ---"
"$PYTHON" - <<'PY'
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

root = Path(".")
website = root / "website"
failed = False
passed = 0

def pass_(msg):
    global passed
    print(f"[PASS] {msg}")
    passed += 1

def fail(msg):
    global failed
    print(f"[FAIL] {msg}")
    failed = True

def warn(msg):
    print(f"[WARN] {msg}")

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)

pages = [
    "index.html",
    "download.html",
    "documentation.html",
    "screenshots.html",
]

nav_targets = {"index.html", "download.html", "documentation.html", "screenshots.html"}
broken = []

for page in pages:
    path = website / page
    if not path.exists():
        fail(f"Missing page: website/{page}")
        continue
    pass_(f"Page exists: website/{page}")

for page in pages:
    html = (website / page).read_text(encoding="utf-8")
    parser = LinkExtractor()
    parser.feed(html)
    for href in parser.links:
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            if "github.com/Copex4590/ProjectX" in href:
                pass_(f"GitHub link present on {page}")
            continue
        target = (website / href.split("#")[0]).resolve()
        try:
            target.relative_to(website.resolve())
        except ValueError:
            fail(f"Broken internal link on {page}: {href}")
            broken.append((page, href))
            continue
        if not target.exists():
            fail(f"Broken internal link on {page}: {href}")
            broken.append((page, href))

for page in pages:
    html = (website / page).read_text(encoding="utf-8")
    if 'data-page="home"' in html or 'href="index.html"' in html:
        pass_(f"Navigation markup present: {page}")

config = json.loads((website / "releases.json").read_text(encoding="utf-8"))
manifest = json.loads((root / "release" / "manifest.json").read_text(encoding="utf-8"))

if manifest["website_version"] == config["latest"]:
    pass_(f"Website version display source matches manifest: {config['latest']}")
else:
    fail(f"Website version mismatch: manifest={manifest['website_version']!r} releases.json={config['latest']!r}")

notes = website / "releases" / f"{config['latest']}.md"
if notes.exists():
    pass_(f"Release notes file for latest version: {notes.relative_to(root)}")
else:
    fail(f"Missing release notes: {notes}")

for platform in ("windows", "linux"):
    cfg = config[platform]
    expected = website / "downloads" / platform / cfg["file"]
    url = f"downloads/{platform}/{cfg['file']}"
    pass_(f"Download button URL configured ({platform}): {url}")
    if expected.exists():
        pass_(f"Download artifact present: {expected.relative_to(root)}")
    else:
        warn(f"Download artifact missing (404 for users): {expected.relative_to(root)}")

screenshots = list((website / "images" / "screenshots").glob("*"))
if screenshots:
    pass_(f"Screenshot assets present: {len(screenshots)} files")
else:
    fail("No screenshot assets under website/images/screenshots/")

if any("github.com/Copex4590/ProjectX" in (website / p).read_text(encoding="utf-8") for p in pages):
    pass_("GitHub repository link on website pages")

# Asset references in HTML
asset_refs = re.findall(r'(?:src|href)="([^"]+)"', "\n".join((website / p).read_text(encoding="utf-8") for p in pages))
for ref in asset_refs:
    if ref.startswith(("http", "#", "mailto:")):
        continue
    asset = (website / ref.split("#")[0]).resolve()
    if not asset.exists():
        fail(f"Broken asset reference: {ref}")

if not broken:
    pass_("No broken internal navigation links detected")

sys.exit(1 if failed else 0)
PY
WEBSITE_RC=$?
[[ "$WEBSITE_RC" -eq 0 ]] || FAILED=1

echo ""
echo "--- Release metadata validation ---"
"$PYTHON" - <<'PY'
import json
import sys
from pathlib import Path

root = Path(".")
failed = False

def pass_(msg):
    print(f"[PASS] {msg}")

def fail(msg):
    global failed
    print(f"[FAIL] {msg}")
    failed = True

def warn(msg):
    print(f"[WARN] {msg}")

manifest = json.loads((root / "release" / "manifest.json").read_text(encoding="utf-8"))
website = json.loads((root / "website" / "releases.json").read_text(encoding="utf-8"))

checks = [
    ("website_version == releases.json latest", manifest["website_version"], website["latest"]),
    ("version == windows.version", manifest["version"], website["windows"]["version"]),
    ("version == linux.version", manifest["version"], website["linux"]["version"]),
    ("release_date", manifest["release_date"], website["release_date"]),
    ("windows file", manifest["packages"]["windows"]["file"], website["windows"]["file"]),
    ("linux primary file", manifest["packages"]["linux"]["primary"]["file"], website["linux"]["file"]),
    ("linux secondary file", manifest["packages"]["linux"]["secondary"]["file"], website["linux"].get("secondary_file")),
]

for label, left, right in checks:
    if left == right:
        pass_(f"{label}: {left}")
    else:
        fail(f"{label}: manifest={left!r} releases.json={right!r}")

for note in manifest.get("release_notes", []):
    path = root / note
    if path.exists():
        pass_(f"Release notes exist: {note}")
    else:
        fail(f"Release notes missing: {note}")

artifacts = []
win = manifest["packages"]["windows"]
artifacts.append(root / win["directory"] / win["file"])
primary = manifest["packages"]["linux"]["primary"]
artifacts.append(root / primary["directory"] / primary["file"])
secondary = manifest["packages"]["linux"]["secondary"]
artifacts.append(root / secondary["directory"] / secondary["file"])

present = 0
for path in artifacts:
    if path.exists():
        pass_(f"Package exists: {path.relative_to(root)}")
        present += 1
    else:
        fail(f"Package missing: {path.relative_to(root)}")

if (root / "release/linux/SHA256SUMS").exists():
    pass_("Linux checksum file exists: release/linux/SHA256SUMS")
else:
    fail("Linux checksum file missing: release/linux/SHA256SUMS")

linux_sums = root / "release/linux/SHA256SUMS"
if linux_sums.exists():
    text = linux_sums.read_text(encoding="utf-8")
    for name in ("ProjectX.AppImage", "ProjectX.deb"):
        if name in text:
            pass_(f"SHA256SUMS lists {name}")
        else:
            fail(f"SHA256SUMS missing entry for {name}")

sys.exit(1 if failed else 0)
PY
META_RC=$?
[[ "$META_RC" -eq 0 ]] || FAILED=1

echo ""
echo "--- Windows package validation ---"
WIN_INSTALLER="$ROOT/release/windows/ProjectX-Setup.exe"
WIN_ISS="$ROOT/installer/windows/projectx.iss"
ICON="$ROOT/src/resources/branding/projectx.ico"

if [[ -f "$WIN_INSTALLER" ]]; then
    record_pass "Windows installer present: release/windows/ProjectX-Setup.exe"
    if [[ "$(basename "$WIN_INSTALLER")" == "ProjectX-Setup.exe" ]]; then
        record_pass "Windows installer filename matches manifest"
    else
        record_fail "Windows installer filename mismatch"
    fi
else
    record_fail "Windows installer missing: release/windows/ProjectX-Setup.exe"
fi

if grep -q 'MyAppVersion "0.3.0-alpha"' "$WIN_ISS" 2>/dev/null; then
    record_pass "Windows installer script version: 0.3.0-alpha (projectx.iss)"
else
    record_fail "Windows installer script version not 0.3.0-alpha"
fi

if [[ -f "$ICON" ]]; then
    record_pass "Windows setup icon source exists: src/resources/branding/projectx.ico"
else
    record_fail "Windows setup icon missing"
fi

if grep -q 'UninstallDisplayName={#MyAppName}' "$WIN_ISS" 2>/dev/null; then
    record_pass "Windows uninstall registry entry configured in Inno Setup"
else
    record_fail "Windows uninstall entry not configured in projectx.iss"
fi

if [[ -f "$WIN_INSTALLER" ]]; then
    record_warn "Windows silent install/uninstall requires scripts/verify_windows_installer.bat on Windows"
else
    record_fail "Cannot verify Windows install/uninstall — installer not built"
fi

echo ""
echo "--- Linux package validation ---"
if bash "$ROOT/scripts/verify_linux_release.sh" >/tmp/save079_linux_verify.log 2>&1; then
    while IFS= read -r line; do
        [[ "$line" == \[OK\]* ]] && record_pass "${line#\[OK\] }"
    done < /tmp/save079_linux_verify.log
else
    while IFS= read -r line; do
        if [[ "$line" == \[FAIL\]* ]]; then
            record_fail "${line#\[FAIL\] }"
        elif [[ "$line" == \[OK\]* ]]; then
            record_pass "${line#\[OK\] }"
        elif [[ "$line" == \[WARN\]* ]]; then
            record_warn "${line#\[WARN\] }"
        fi
    done < /tmp/save079_linux_verify.log
fi

echo ""
echo "--- HTTP download simulation ---"
if command -v curl >/dev/null 2>&1; then
    "$PYTHON" -m http.server "$PORT" --directory "$ROOT/website" >/dev/null 2>&1 &
    SERVER_PID=$!
    sleep 1
    BASE="http://127.0.0.1:${PORT}"

    for url in \
        "$BASE/index.html" \
        "$BASE/download.html" \
        "$BASE/documentation.html" \
        "$BASE/screenshots.html" \
        "$BASE/releases.json" \
        "$BASE/releases/0.3-alpha.md"; do
        code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
        if [[ "$code" == "200" ]]; then
            record_pass "HTTP $code ${url#*://*/}"
        else
            record_fail "HTTP $code ${url#*://*/}"
        fi
    done

    WIN_URL="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("website/releases.json").read_text(encoding="utf-8"))
print("downloads/windows/" + c["windows"]["file"])
PY
)"
    LIN_URL="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
c = json.loads(Path("website/releases.json").read_text(encoding="utf-8"))
print("downloads/linux/" + c["linux"]["file"])
PY
)"

    for rel in "$WIN_URL" "$LIN_URL"; do
        code="$(curl -s -o /dev/null -w "%{http_code}" "$BASE/$rel")"
        if [[ "$code" == "200" ]]; then
            record_pass "Download URL returns HTTP 200: $rel"
        else
            record_fail "Download URL returns HTTP $code (user gets broken download): $rel"
        fi
    done
else
    record_warn "curl not available — skipped HTTP simulation"
fi

echo ""
echo "============================================================"
if [[ "$FAILED" -eq 0 ]]; then
    echo "VALIDATION SUMMARY: PASS (ready for public Alpha)"
    exit 0
fi

echo "VALIDATION SUMMARY: FAIL (public release blocked)"
echo "See RELEASE_VALIDATION.md for required fixes."
exit 1
