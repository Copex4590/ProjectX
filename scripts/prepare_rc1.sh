#!/usr/bin/env bash
# ============================================================================
# Project X — Assemble Release Candidate RC1 package (SAVE-080)
# Copies all public release files into release/RC1/ for publication audit.
# Does not modify application functionality.
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RC1="$ROOT/release/RC1"
PYTHON="${PROJECTX_PYTHON:-python3}"

echo "============================================================"
echo "Project X — Prepare RC1 Release Package (SAVE-080)"
echo "============================================================"

rm -rf "$RC1"
mkdir -p \
    "$RC1/notes" \
    "$RC1/windows" \
    "$RC1/linux" \
    "$RC1/website-downloads/windows" \
    "$RC1/website-downloads/linux"

copy_if_exists() {
    local src="$1"
    local dest="$2"
    if [[ -f "$src" ]]; then
        cp -f "$src" "$dest"
        echo "[OK] Copied $(basename "$dest")"
        return 0
    fi
    echo "[SKIP] Missing: $src"
    return 1
}

echo "Copying manifest and website config..."
cp -f "$ROOT/release/manifest.json" "$RC1/manifest.json"
cp -f "$ROOT/website/releases.json" "$RC1/releases.json"

echo "Copying release notes..."
cp -f "$ROOT/release/notes/0.3.0-alpha.md" "$RC1/notes/0.3.0-alpha.md"
cp -f "$ROOT/release/notes/0.3.0-alpha-full.md" "$RC1/notes/0.3.0-alpha-full.md"
cp -f "$ROOT/website/releases/0.3-alpha.md" "$RC1/notes/website-0.3-alpha.md"

echo "Copying release artifacts (including per-platform SHA256SUMS)..."
for f in "$ROOT/release/windows"/*; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "README.md" ]] && continue
    cp -f "$f" "$RC1/windows/"
    echo "[OK] Windows: $(basename "$f")"
done
for f in "$ROOT/release/linux"/*; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "README.md" ]] && continue
    cp -f "$f" "$RC1/linux/"
    echo "[OK] Linux: $(basename "$f")"
done

echo "Copying website download mirrors..."
for f in "$ROOT/website/downloads/windows"/*; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "README.md" ]] && continue
    cp -f "$f" "$RC1/website-downloads/windows/"
    echo "[OK] Website Windows: $(basename "$f")"
done
for f in "$ROOT/website/downloads/linux"/*; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "README.md" ]] && continue
    cp -f "$f" "$RC1/website-downloads/linux/"
    echo "[OK] Website Linux: $(basename "$f")"
done

"$PYTHON" - <<'PY'
import json
from datetime import date
from pathlib import Path

rc1 = Path("release/RC1")
manifest = json.loads((rc1 / "manifest.json").read_text(encoding="utf-8"))

expected = {
    "windows": manifest["packages"]["windows"]["file"],
    "linux_primary": manifest["packages"]["linux"]["primary"]["file"],
    "linux_secondary": manifest["packages"]["linux"]["secondary"]["file"],
}

present = {}
for key, name in expected.items():
    if key == "windows":
        path = rc1 / "windows" / name
    else:
        path = rc1 / "linux" / name
    present[key] = path.exists()

notes = sorted(p.name for p in (rc1 / "notes").glob("*") if p.is_file())

lines = [
    "# Project X RC1 Package Inventory",
    "",
    f"**Assembled:** {date.today().isoformat()}",
    f"**Version:** {manifest['version']} (website: {manifest['website_version']})",
    "",
    "## Expected artifacts",
    "",
    "| Artifact | Expected path | Present |",
    "|----------|---------------|---------|",
]
for key, name in expected.items():
    sub = "windows" if key == "windows" else "linux"
    status = "yes" if present[key] else "no"
    lines.append(f"| {name} | `{sub}/` | {status} |")

lines.append("| SHA256SUMS | `linux/` | yes |" if (rc1 / "linux" / "SHA256SUMS").exists() else "| SHA256SUMS | `linux/` | no |")
lines.append("| SHA256SUMS | `windows/` | yes |" if (rc1 / "windows" / "SHA256SUMS").exists() else "| SHA256SUMS | `windows/` | no |")

lines += [
    "",
    "## Checksums",
    "",
    "Per-platform `SHA256SUMS` files live alongside binaries under `linux/` and `windows/`.",
]

lines += ["", "## Release notes", ""]
lines.extend(f"- `{n}`" for n in notes)

(rc1 / "INVENTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("[OK] Wrote release/RC1/INVENTORY.md")
PY

echo ""
echo "RC1 package assembled at: release/RC1/"
echo "Next: review RC1_REPORT.md and run verification scripts."
