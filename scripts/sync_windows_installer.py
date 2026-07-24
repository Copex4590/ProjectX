#!/usr/bin/env python3
# ============================================================================
# Project X — Cross-platform Windows installer sync (SAVE-239)
# ============================================================================
"""Publish / fetch ``ProjectX-Setup.exe`` via GitHub Releases (version-aware).

Commands:
  publish  — upload local installer + SHA256SUMS to the version release (idempotent)
  fetch    — ensure local installer exists (download if missing, verify SHA256)

Version tag: ``v`` + ``release/manifest.json`` → ``version`` (e.g. ``v0.3.1-beta``).

Environment:
  PROJECTX_SKIP_WINDOWS_PUBLISH=1  — skip publish (local-only Windows builds)
  PROJECTX_GITHUB_REPO             — override ``owner/repo`` (default from git remote / manifest)
  PROJECTX_WINDOWS_INSTALLER_URL   — direct HTTPS override for fetch (optional)
  GH_TOKEN / gh auth               — required for publish and for private downloads
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "release" / "manifest.json"
WINDOWS_DIR = ROOT / "release" / "windows"
INSTALLER_NAME = "ProjectX-Setup.exe"
SUMS_NAME = "SHA256SUMS"


def _die(message: str, *, code: int = 1) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(code)


def _info(message: str) -> None:
    print(f"[OK] {message}")


def _warn(message: str) -> None:
    print(f"[WARN] {message}")


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        _die(f"Missing manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def release_version(manifest: dict | None = None) -> str:
    data = manifest or load_manifest()
    version = str(data.get("version") or "").strip()
    if not version:
        _die("release/manifest.json has empty version")
    return version


def release_tag(version: str | None = None) -> str:
    ver = version or release_version()
    return ver if ver.startswith("v") else f"v{ver}"


def installer_path() -> Path:
    manifest = load_manifest()
    name = str(
        manifest.get("packages", {}).get("windows", {}).get("file") or INSTALLER_NAME
    ).strip() or INSTALLER_NAME
    return WINDOWS_DIR / name


def sums_path() -> Path:
    return WINDOWS_DIR / SUMS_NAME


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_windows_sums(path: Path | None = None) -> Path:
    """Write release/windows/SHA256SUMS for the installer (idempotent)."""

    target = path or installer_path()
    if not target.is_file():
        _die(f"Cannot checksum missing installer: {target.relative_to(ROOT)}")

    WINDOWS_DIR.mkdir(parents=True, exist_ok=True)
    out = sums_path()
    digest = sha256_file(target)
    out.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    _info(f"Wrote {out.relative_to(ROOT)} ({digest[:12]}…)")
    return out


def parse_sums(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line)
        if not match:
            continue
        mapping[match.group(2).strip()] = match.group(1).lower()
    return mapping


def verify_installer_checksum(installer: Path, sums_file: Path | None = None) -> None:
    sums = sums_file or sums_path()
    if not sums.is_file():
        _warn(f"No {sums.relative_to(ROOT)} — skipping SHA256 verification")
        return

    expected_map = parse_sums(sums.read_text(encoding="utf-8"))
    expected = expected_map.get(installer.name)
    if not expected:
        _die(
            f"{sums.name} has no entry for {installer.name}. "
            "Regenerate checksums or re-publish the Windows installer."
        )
    actual = sha256_file(installer)
    if actual.lower() != expected.lower():
        _die(
            f"SHA256 mismatch for {installer.name}:\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}"
        )
    _info(f"SHA256 verified for {installer.name}")


def detect_github_repo(manifest: dict | None = None) -> str:
    override = os.environ.get("PROJECTX_GITHUB_REPO", "").strip()
    if override:
        return override

    data = manifest or load_manifest()
    github_url = str(data.get("github") or "").strip()
    match = re.search(r"github\.com[:/](?P<repo>[\w.-]+/[\w.-]+?)(?:\.git)?/?$", github_url)
    if match:
        return match.group("repo")

    try:
        remote = subprocess.check_output(
            ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        remote = ""
    match = re.search(r"github\.com[:/](?P<repo>[\w.-]+/[\w.-]+?)(?:\.git)?/?$", remote)
    if match:
        return match.group("repo")

    _die(
        "Cannot determine GitHub repo (owner/name).\n"
        "  Set PROJECTX_GITHUB_REPO=owner/repo or fix release/manifest.json github URL."
    )


def find_gh() -> str | None:
    return shutil.which("gh")


def require_gh() -> str:
    gh = find_gh()
    if not gh:
        _die(
            "GitHub CLI (gh) is not installed.\n"
            "  Install: https://cli.github.com/\n"
            "  Then authenticate: gh auth login\n"
            "  Or set GH_TOKEN with repo scope."
        )
    return gh


def gh_authenticated(gh: str) -> bool:
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return True
    try:
        subprocess.check_call(
            [gh, "auth", "status", "-h", "github.com"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def require_gh_auth(gh: str) -> None:
    if gh_authenticated(gh):
        return
    _die(
        "GitHub CLI is not authenticated.\n"
        "  Run: gh auth login -h github.com\n"
        "  Or export GH_TOKEN / GITHUB_TOKEN with access to the repository.\n"
        "  Without auth the Windows installer cannot be published or downloaded."
    )


def _gh(gh: str, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env.get("GITHUB_TOKEN") and not env.get("GH_TOKEN"):
        env["GH_TOKEN"] = env["GITHUB_TOKEN"]
    return subprocess.run(
        [gh, *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def release_exists(gh: str, repo: str, tag: str) -> bool:
    result = _gh(gh, ["release", "view", tag, "--repo", repo], check=False)
    return result.returncode == 0


def ensure_github_release(gh: str, repo: str, tag: str, version: str) -> None:
    if release_exists(gh, repo, tag):
        _info(f"GitHub release exists: {repo}@{tag}")
        return

    notes = ROOT / "release" / "notes" / f"{version}.md"
    title = f"Project X {version}"
    args = [
        "release",
        "create",
        tag,
        "--repo",
        repo,
        "--title",
        title,
    ]
    if notes.is_file():
        args.extend(["--notes-file", str(notes)])
    else:
        args.extend(["--notes", f"Project X {version} release assets."])

    # Tag may not exist yet — create release from current HEAD if needed.
    args.append("--target")
    try:
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        args.append(head)
    except (OSError, subprocess.CalledProcessError):
        args.append("HEAD")

    result = _gh(gh, args, check=False)
    if result.returncode != 0:
        _die(
            "Failed to create GitHub release "
            f"{repo}@{tag}.\n"
            f"  gh stderr: {(result.stderr or result.stdout or '').strip()}\n"
            "  Ensure you can push releases to this repository, then retry."
        )
    _info(f"Created GitHub release: {repo}@{tag}")


def cmd_publish() -> int:
    if os.environ.get("PROJECTX_SKIP_WINDOWS_PUBLISH", "").strip() in {
        "1",
        "true",
        "yes",
    }:
        _warn("PROJECTX_SKIP_WINDOWS_PUBLISH set — skipping GitHub publish")
        return 0

    installer = installer_path()
    if not installer.is_file():
        _die(
            f"Windows installer missing: {installer.relative_to(ROOT)}\n"
            "  Build on Windows first: scripts\\build_windows.bat"
        )

    write_windows_sums(installer)
    sums = sums_path()
    verify_installer_checksum(installer, sums)

    gh = require_gh()
    require_gh_auth(gh)
    manifest = load_manifest()
    version = release_version(manifest)
    tag = release_tag(version)
    repo = detect_github_repo(manifest)

    ensure_github_release(gh, repo, tag, version)

    result = _gh(
        gh,
        [
            "release",
            "upload",
            tag,
            str(installer),
            str(sums),
            "--repo",
            repo,
            "--clobber",
        ],
        check=False,
    )
    if result.returncode != 0:
        _die(
            f"Failed to upload Windows installer to {repo}@{tag}.\n"
            f"  gh stderr: {(result.stderr or result.stdout or '').strip()}\n"
            "  Check repository permissions (contents: write) and retry."
        )

    _info(f"Published {installer.name} + {SUMS_NAME} → {repo}@{tag}")
    print(
        f"Download URL: https://github.com/{repo}/releases/download/{tag}/{installer.name}"
    )
    return 0


def _download_url(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ProjectX-release-sync/SAVE-239"},
        )
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token and "github.com" in url:
            request.add_header("Authorization", f"Bearer {token}")
            request.add_header("Accept", "application/octet-stream")
        with urllib.request.urlopen(request, timeout=120) as response:
            with tmp.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        tmp.replace(dest)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _fetch_via_gh(gh: str, repo: str, tag: str, installer: Path) -> None:
    WINDOWS_DIR.mkdir(parents=True, exist_ok=True)
    result = _gh(
        gh,
        [
            "release",
            "download",
            tag,
            "--repo",
            repo,
            "--dir",
            str(WINDOWS_DIR),
            "--pattern",
            installer.name,
            "--pattern",
            SUMS_NAME,
            "--clobber",
        ],
        check=False,
    )
    if result.returncode != 0:
        _die(
            f"Could not download {installer.name} from GitHub release {repo}@{tag}.\n"
            f"  gh stderr: {(result.stderr or result.stdout or '').strip()}\n"
            "  Actionable steps:\n"
            f"    1. On Windows, build + publish: scripts\\build_windows.bat\n"
            f"       (uploads to release {tag})\n"
            f"    2. Confirm assets exist: gh release view {tag} --repo {repo}\n"
            "    3. Re-run ./scripts/prepare_release.sh\n"
            "  Or set PROJECTX_WINDOWS_INSTALLER_URL to a direct HTTPS installer URL."
        )


def cmd_fetch() -> int:
    installer = installer_path()
    version = release_version()
    tag = release_tag(version)
    repo = detect_github_repo()

    if installer.is_file():
        _info(f"Local installer present: {installer.relative_to(ROOT)}")
        if sums_path().is_file():
            verify_installer_checksum(installer)
        else:
            _warn("Local SHA256SUMS missing — installer kept as-is")
        return 0

    _warn(f"Local installer missing: {installer.relative_to(ROOT)}")
    print(f"Fetching version-aware asset for {version} (tag {tag})…")

    override = os.environ.get("PROJECTX_WINDOWS_INSTALLER_URL", "").strip()
    if override:
        try:
            _download_url(override, installer)
        except Exception as error:  # noqa: BLE001
            _die(f"PROJECTX_WINDOWS_INSTALLER_URL download failed: {error}")
        sums_url = os.environ.get("PROJECTX_WINDOWS_SHA256SUMS_URL", "").strip()
        if sums_url:
            try:
                _download_url(sums_url, sums_path())
            except Exception as error:  # noqa: BLE001
                _warn(f"SHA256SUMS URL download failed: {error}")
        if sums_path().is_file():
            verify_installer_checksum(installer)
        else:
            write_windows_sums(installer)
            _warn("No remote SHA256SUMS — wrote local checksum from downloaded file")
        _info(f"Fetched installer via PROJECTX_WINDOWS_INSTALLER_URL → {installer}")
        return 0

    gh = find_gh()
    if gh is None:
        url = f"https://github.com/{repo}/releases/download/{tag}/{installer.name}"
        sums_url = f"https://github.com/{repo}/releases/download/{tag}/{SUMS_NAME}"
        print(f"gh not found — trying public HTTPS: {url}")
        try:
            _download_url(url, installer)
        except Exception as error:  # noqa: BLE001
            _die(
                f"Windows installer missing locally and automatic download failed.\n"
                f"  Expected: {installer.relative_to(ROOT)}\n"
                f"  Version:  {version} (GitHub tag {tag})\n"
                f"  Repo:     {repo}\n"
                f"  Error:    {error}\n"
                "  Why: GitHub CLI (gh) is not installed, and the public release\n"
                "       asset was not reachable.\n"
                "  Fix:\n"
                "    • Install gh and run: gh auth login\n"
                f"    • Or publish from Windows: scripts\\build_windows.bat\n"
                f"      then confirm https://github.com/{repo}/releases/tag/{tag}\n"
                "    • Or set PROJECTX_WINDOWS_INSTALLER_URL to a direct URL"
            )
        try:
            _download_url(sums_url, sums_path())
        except Exception as error:  # noqa: BLE001
            _warn(f"SHA256SUMS not downloaded ({error})")
        if sums_path().is_file():
            verify_installer_checksum(installer)
        _info(f"Downloaded {installer.name} from public release {tag}")
        return 0

    require_gh_auth(gh)
    if not release_exists(gh, repo, tag):
        _die(
            f"GitHub release {repo}@{tag} does not exist yet.\n"
            "  The Linux prepare step cannot invent a Windows installer.\n"
            "  Fix:\n"
            "    1. On the Windows build machine run: scripts\\build_windows.bat\n"
            "       (publishes ProjectX-Setup.exe to this release tag)\n"
            f"    2. Verify: gh release view {tag} --repo {repo}\n"
            "    3. Re-run ./scripts/prepare_release.sh"
        )

    _fetch_via_gh(gh, repo, tag, installer)
    if not installer.is_file():
        _die(
            f"Download reported success but {installer.relative_to(ROOT)} is still missing.\n"
            f"  Check assets on https://github.com/{repo}/releases/tag/{tag}"
        )
    if sums_path().is_file():
        verify_installer_checksum(installer)
    else:
        _warn("Downloaded installer without SHA256SUMS — integrity not verified")
    _info(f"Fetched {installer.relative_to(ROOT)} from {repo}@{tag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SAVE-239 — sync Windows installer via GitHub Releases",
    )
    parser.add_argument(
        "command",
        choices=("publish", "fetch"),
        help="publish local installer to GitHub, or fetch if missing locally",
    )
    args = parser.parse_args(argv)

    if args.command == "publish":
        return cmd_publish()
    return cmd_fetch()


if __name__ == "__main__":
    raise SystemExit(main())
