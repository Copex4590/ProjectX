# PASS / FAIL Criteria and Publication Gates

Defines when a Release Candidate **passes**, **fails**, may be **published**, or **must be rejected**.

---

## Checklist item results

| Result | Symbol | Meaning |
|--------|--------|---------|
| **PASS** | ✓ | Behaviour matches expected result exactly |
| **FAIL** | ✗ | Behaviour does not match; log an issue ID |
| **N/A** | — | Step not applicable to this platform or release scope |
| **SKIP** | ○ | Intentionally not run (document reason) |

A skipped critical step without approved reason counts as **FAIL**.

---

## Test run outcomes

| Outcome | Condition |
|---------|-----------|
| **PASS** | All **critical** steps PASS; no open BLOCKER or HIGH issues |
| **CONDITIONAL PASS** | All critical steps PASS; only MEDIUM/LOW open with documented deferrals |
| **FAIL** | Any critical step FAIL; or any open BLOCKER; or any open HIGH without deferral |

---

## Critical steps (must PASS)

### Linux ([LINUX-RC1-CHECKLIST.md](LINUX-RC1-CHECKLIST.md))

| Step ID | Requirement |
|---------|-------------|
| L-06 | Package name: **Project X** |
| L-07 | Description: **Professional Maritime Monitoring Platform** |
| L-10 | Installation succeeds |
| L-13 | Menu name: **Project X** |
| L-15 | Terminal does **not** appear on launch |
| L-16 | First Run Wizard completes |
| L-19 | Launch from applications menu works |
| L-22 | Menu entry removed after uninstall |

### Windows ([WINDOWS-RC1-CHECKLIST.md](WINDOWS-RC1-CHECKLIST.md))

| Step ID | Requirement |
|---------|-------------|
| W-06 | Product name: **Project X** |
| W-09 | Installation succeeds |
| W-12 | Start Menu shortcut works |
| W-14 | Application launches without error |
| W-15 | First Run Wizard completes |
| W-18 | Launch from Start Menu after reboot |
| W-21 | Uninstall removes Program Files entry |

### Release approval ([RELEASE-APPROVAL-CHECKLIST.md](RELEASE-APPROVAL-CHECKLIST.md))

| Step ID | Requirement |
|---------|-------------|
| A-01 | All platform artifacts built |
| A-04 | `verify_release.sh` — no FAIL |
| A-07 | Checksums match artifacts |
| A-10 | GitHub Release assets match manifest |
| A-12 | Both platform RC test runs PASS or CONDITIONAL PASS |

---

## Automated verification gate

Before manual RC testing, these must complete:

| Script | Platform | Gate |
|--------|----------|------|
| `./scripts/verify_linux_release.sh` | Linux | Exit 0 |
| `scripts\verify_windows_installer.bat` | Windows | Exit 0 |
| `./scripts/verify_release.sh` | Both | Exit 0 (WARN allowed for optional paths) |
| `./scripts/validate_public_download.sh` | Website | Exit 0 before public website publish |

Manual RC testing uses **GitHub Release or staging artifacts**, not developer tree installs.

---

## When a Release Candidate MAY be published

All of the following must be true:

1. **Build complete** — `ProjectX.deb`, `ProjectX.AppImage`, `ProjectX-Setup.exe`, per-platform `SHA256SUMS` exist and match manifest.
2. **Automated verify PASS** — no FAIL from verification scripts required for publication.
3. **Linux RC test run** — outcome PASS or CONDITIONAL PASS; test report filed with RUN ID.
4. **Windows RC test run** — outcome PASS or CONDITIONAL PASS; test report filed with RUN ID.
5. **Release approval checklist** — signed off on [RELEASE-APPROVAL-CHECKLIST.md](RELEASE-APPROVAL-CHECKLIST.md).
6. **No open BLOCKER** issues.
7. **No open HIGH** issues unless formally deferred.
8. **GitHub Release** — tag, notes, and binary attachments match `release/manifest.json`.
9. **Website** — download URLs return HTTP 200 for primary artifacts (if website hosts files).

**Alpha / RC1 note:** First public Alpha may publish with documented known limitations (e.g. unsigned Windows binary) if severity is MEDIUM or LOW and listed in release notes.

---

## When a release MUST be rejected

Reject immediately if **any** of the following is true:

| # | Rejection trigger |
|---|-------------------|
| R1 | Any **BLOCKER** issue open |
| R2 | Any **HIGH** issue open without written deferral |
| R3 | Any **critical step** (Linux, Windows, or Approval) result FAIL |
| R4 | Checksum mismatch between artifact and `SHA256SUMS` |
| R5 | Wrong version or wrong file attached to GitHub Release |
| R6 | Primary Linux download not `ProjectX.deb` or primary path broken |
| R7 | Application requires terminal for normal GUI launch |
| R8 | First Run Wizard broken on clean install (both platforms if releasing both) |
| R9 | Install succeeds but application binary missing or not executable |
| R10 | Public link to developer-only `installer/linux/install.sh` as end-user path |

**After rejection:** increment build, fix issues, assign new RUN ID, re-run full RC cycle.

---

## CONDITIONAL PASS rules

Allowed only when:

- Zero BLOCKER, zero HIGH
- All critical steps PASS
- MEDIUM issues ≤ 3 and each listed in release notes with PX-QA ID
- Approver signs RELEASE-APPROVAL checklist with deferral section completed

---

## Sign-off authority

| Release type | Minimum approver |
|--------------|------------------|
| Alpha / RC | Release owner + one platform tester |
| Beta / Stable | Release owner + Linux tester + Windows tester |

Record names and dates in the Release Test Report.
