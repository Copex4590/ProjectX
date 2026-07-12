# Release Approval Checklist

Final gate before creating a **GitHub Release** or publishing to the public website.  
Complete after platform RC tests and automated verification.

**Release version:** _______________  
**Approval date:** _______________  
**Approver(s):** _______________

---

## A. Build and artifacts

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-01 | Linux artifacts built | `ProjectX.deb`, `ProjectX.AppImage` in `release/linux/` | | |
| A-02 | Windows artifact built | `ProjectX-Setup.exe` in `release/windows/` | | |
| A-03 | `prepare_release.sh` completed | Website copies synced | | |
| A-04 | `./scripts/verify_release.sh` | Exit 0, no FAIL | | |
| A-05 | `./scripts/verify_linux_release.sh` | Exit 0 | | |
| A-06 | `scripts\verify_windows_installer.bat` | PASS (Windows build host) | | |

**Critical:** A-01, A-04

---

## B. Checksums and integrity

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-07 | `release/linux/SHA256SUMS` | Matches `.deb` and `.AppImage` | | |
| A-08 | `release/windows/SHA256SUMS` | Matches `.exe` | | |
| A-09 | Website mirror checksums | Identical to `release/` copies | | |

**Critical:** A-07

---

## C. Metadata alignment

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-10 | `release/manifest.json` version | Matches `src/version.py` | | |
| A-11 | `website/releases.json` | Synced with manifest | | |
| A-12 | Release notes present | `release/notes/` + `website/releases/{latest}.md` | | |
| A-13 | Linux primary download | `ProjectX.deb` (not AppImage) | | |
| A-14 | Stable artifact filenames | No versioned filenames in URLs | | |

**Critical:** A-10, A-13

---

## D. Manual QA completion

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-15 | Linux RC test report filed | RUN ID: | | |
| A-16 | Linux RC outcome | PASS or CONDITIONAL PASS | | |
| A-17 | Windows RC test report filed | RUN ID: | | |
| A-18 | Windows RC outcome | PASS or CONDITIONAL PASS | | |
| A-19 | No open BLOCKER issues | Count: 0 | | |
| A-20 | No open HIGH without deferral | Count: 0 or deferred list attached | | |

**Critical:** A-15, A-16, A-17, A-18, A-19

---

## E. GitHub Release readiness

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-21 | Git tag created | `v{VERSION}` | | |
| A-22 | Release notes pasted | From `release/notes/` | | |
| A-23 | Attachments complete | All platform binaries + SHA256SUMS | | |
| A-24 | No developer-only assets | No `installer/linux/` zip, no source installer | | |

**Critical:** A-23, A-24

---

## F. Website and downloads

| ID | Check | Expected | Result | Notes |
|----|-------|----------|--------|-------|
| A-25 | `./website/verify_releases.sh` | PASS | | |
| A-26 | `./scripts/validate_public_download.sh` | PASS (if website hosts files) | | |
| A-27 | Primary download HTTP 200 | Linux `.deb`, Windows `.exe` | | |
| A-28 | No public `install.sh` links | End-user path is binary only | | |

---

## Deferral register (CONDITIONAL PASS only)

| Issue ID | Severity | Summary | Release note entry | Approved by |
|----------|----------|---------|-------------------|-------------|
| | | | | |

---

## Approval decision

| Decision | Select one |
|----------|------------|
| **APPROVED — publish release** | ☐ |
| **CONDITIONAL — publish with known issues** | ☐ |
| **REJECTED — do not publish** | ☐ |

**Rejection reason (if applicable):**  
_______________________________________________

**Signatures:**

| Role | Name | Date |
|------|------|------|
| Release owner | | |
| Linux QA | | |
| Windows QA | | |

---

## Reference

Publication and rejection rules: [PASS-FAIL-CRITERIA.md](PASS-FAIL-CRITERIA.md)
