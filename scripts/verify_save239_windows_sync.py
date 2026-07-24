#!/usr/bin/env python3
# SAVE-239 — Windows installer sync smoke (offline)
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "sync_windows_installer.py"


def load():
    spec = importlib.util.spec_from_file_location("sync_windows_installer", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    failures: list[str] = []
    mod = load()

    if mod.release_tag("0.3.1-beta") != "v0.3.1-beta":
        failures.append("tag prefix")
    if mod.release_tag("v0.3.1-beta") != "v0.3.1-beta":
        failures.append("tag already prefixed")

    parsed = mod.parse_sums(
        "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789  ProjectX-Setup.exe\n"
    )
    if "ProjectX-Setup.exe" not in parsed:
        failures.append("parse_sums missing name")

    with tempfile.TemporaryDirectory() as tmp:
        installer = Path(tmp) / "ProjectX-Setup.exe"
        installer.write_bytes(b"demo-installer")
        digest = mod.sha256_file(installer)
        sums = Path(tmp) / "SHA256SUMS"
        sums.write_text(f"{digest}  ProjectX-Setup.exe\n", encoding="utf-8")
        # Monkeypatch paths
        mod.WINDOWS_DIR = Path(tmp)
        try:
            mod.verify_installer_checksum(installer, sums)
        except SystemExit as exc:
            failures.append(f"checksum verify exited: {exc}")

        # Mismatch must fail
        sums.write_text(
            "0" * 64 + "  ProjectX-Setup.exe\n",
            encoding="utf-8",
        )
        raised = False
        try:
            mod.verify_installer_checksum(installer, sums)
        except SystemExit:
            raised = True
        if not raised:
            failures.append("mismatch should fail")

    version = mod.release_version()
    if version != "0.3.1-beta":
        failures.append(f"manifest version unexpected: {version}")
    repo = mod.detect_github_repo()
    if "/" not in repo:
        failures.append(f"repo detect failed: {repo}")

    if failures:
        print("SAVE-239 FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("SAVE-239 smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
