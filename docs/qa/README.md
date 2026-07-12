# Project X — Release Candidate QA Framework

Permanent, reusable quality-assurance system for every Project X release.  
**Documentation only** — no application source changes.

---

## Purpose

This framework ensures every Release Candidate (RC) is tested the same way on **Linux** and **Windows**, issues are tracked with consistent IDs, and publication decisions are explicit and auditable.

Use it for Alpha, Beta, and stable releases. Replace `{VERSION}` with the release under test (e.g. `0.3.0-alpha`).

---

## Document index

| Document | Purpose |
|----------|---------|
| [NUMBERING.md](NUMBERING.md) | Unique IDs for test runs, bugs, UX, and installer issues |
| [SEVERITY.md](SEVERITY.md) | BLOCKER / HIGH / MEDIUM / LOW classification |
| [PASS-FAIL-CRITERIA.md](PASS-FAIL-CRITERIA.md) | PASS/FAIL rules, publish gate, mandatory rejection |
| [LINUX-RC1-CHECKLIST.md](LINUX-RC1-CHECKLIST.md) | Linux Mint / Debian RC test checklist |
| [WINDOWS-RC1-CHECKLIST.md](WINDOWS-RC1-CHECKLIST.md) | Windows RC test checklist |
| [RELEASE-APPROVAL-CHECKLIST.md](RELEASE-APPROVAL-CHECKLIST.md) | Final sign-off before GitHub Release |
| [RELEASE-TEST-REPORT-TEMPLATE.md](RELEASE-TEST-REPORT-TEMPLATE.md) | Fillable report after each QA run |

---

## Workflow (every release)

```
1. Build artifacts          →  scripts per RELEASE_PROCESS.md
2. Automated verification   →  verify_linux_release.sh, verify_windows_installer.bat, verify_release.sh
3. Assign test run ID       →  PX-QA-RUN-{VERSION}-{NNN}
4. Execute platform RC      →  LINUX-RC1-CHECKLIST / WINDOWS-RC1-CHECKLIST
5. Log issues               →  PX-QA-BUG / PX-QA-UX / PX-QA-INS
6. Complete test report     →  RELEASE-TEST-REPORT-TEMPLATE
7. Release approval         →  RELEASE-APPROVAL-CHECKLIST
8. Publish or reject        →  PASS-FAIL-CRITERIA
```

---

## Related repository docs

| Path | Role |
|------|------|
| `RELEASE_PROCESS.md` | Build, verify, GitHub Release workflow |
| `docs/LINUX_INSTALLER.md` | Linux package details |
| `docs/WINDOWS_INSTALLER.md` | Windows installer details |
| `docs/RC1-002-LINUX-MINT-PROTOCOL.md` | Example filled Linux Mint protocol (Hungarian) |

---

## Configuration policy (all platforms)

| Event | Behaviour | QA expectation |
|-------|-----------|----------------|
| Uninstall | Application binaries and shortcuts removed | PASS |
| User data | Preserved under platform user-data dir | **PASS — intentional** |
| Reinstall | Previous settings available | PASS |

| Platform | User data location |
|----------|-------------------|
| Linux | `~/.local/share/projectx/` |
| Windows | `%APPDATA%\Project X\` |

Full data wipe is manual only (documented in platform installer docs).

---

## Version history

| Save | Change |
|------|--------|
| SAVE-086 | Initial QA framework under `docs/qa/` |
