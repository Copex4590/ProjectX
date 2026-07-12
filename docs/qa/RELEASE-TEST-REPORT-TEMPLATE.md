# Release Test Report — Template

Copy this file for each QA cycle. Save as:  
`docs/qa/reports/PX-QA-RUN-{VERSION}-{NNN}.md` (recommended) or store externally.

---

## Report header

| Field | Value |
|-------|-------|
| **Test run ID** | PX-QA-RUN-{VERSION}-{NNN} |
| **Release version** | |
| **Report date** | YYYY-MM-DD |
| **Tester(s)** | |
| **Platform(s) tested** | Linux / Windows / Both |
| **Artifact source** | GitHub Release tag / CI / local staging |
| **Git commit / tag** | |

---

## Executive summary

**Overall outcome:** PASS / CONDITIONAL PASS / FAIL  

**Recommendation:** PUBLISH / REJECT / FIX AND RE-TEST  

One-paragraph summary:

> _Example: Linux RC1 PASS on Mint 22 VM. Windows RC1 CONDITIONAL PASS — SmartScreen warning logged as PX-QA-UX-0.3.0-alpha-001 (MEDIUM, deferred). No blockers._

---

## Environment

### Linux (if tested)

| Field | Value |
|-------|-------|
| OS | |
| VM / hardware | |
| `.deb` SHA256 | |
| Checklist used | [LINUX-RC1-CHECKLIST.md](LINUX-RC1-CHECKLIST.md) |

### Windows (if tested)

| Field | Value |
|-------|-------|
| OS | |
| VM / hardware | |
| `.exe` SHA256 | |
| Checklist used | [WINDOWS-RC1-CHECKLIST.md](WINDOWS-RC1-CHECKLIST.md) |

---

## Automated verification results

| Script | Date | Result | Log reference |
|--------|------|--------|---------------|
| `verify_linux_release.sh` | | PASS / FAIL | |
| `verify_windows_installer.bat` | | PASS / FAIL | |
| `verify_release.sh` | | PASS / FAIL | |
| `validate_public_download.sh` | | PASS / FAIL / N/A | |

---

## Manual checklist results

### Linux critical steps

| Step ID | Description | Result | Issue ID |
|---------|-------------|--------|----------|
| L-06 | Package name shown | **Project X** | | |
| L-07 | Description correct | | |
| L-10 | Install succeeds | | |
| L-13 | Menu name Project X | | |
| L-15 | No terminal on launch | | |
| L-16 | First Run Wizard OK | | |
| L-19 | Launch from menu | | |
| L-22 | Menu removed on uninstall | | |

### Windows critical steps

| Step ID | Description | Result | Issue ID |
|---------|-------------|--------|----------|
| W-06 | Product name Project X | | |
| W-09 | Install succeeds | | |
| W-12 | Start Menu works | | |
| W-14 | Launch OK | | |
| W-15 | First Run Wizard OK | | |
| W-18 | Reboot OK | | |
| W-19 | Start Menu after reboot | | |
| W-21 | Uninstall OK | | |

---

## Issues found

| Issue ID | Type | Severity | Step | Summary | Status |
|----------|------|----------|------|---------|--------|
| PX-QA-BUG- | BUG | | | | OPEN |
| PX-QA-UX- | UX | | | | OPEN |
| PX-QA-INS- | INS | | | | OPEN |

_Add rows as needed. Severity definitions: [SEVERITY.md](SEVERITY.md)_

---

## Issue details (repeat per issue)

### {ISSUE-ID}

| Field | Value |
|-------|-------|
| Type | BUG / UX / INS |
| Severity | BLOCKER / HIGH / MEDIUM / LOW |
| Platform | Linux / Windows / Both |
| Checklist step | e.g. L-15 |
| Status | OPEN / FIXED / VERIFIED / DEFERRED |

**Steps to reproduce:**

1. 
2. 
3. 

**Expected:**

**Actual:**

**Screenshots / logs:**

**Fix version (if fixed):**

---

## Configuration policy verification

| Platform | User data preserved on uninstall | Result |
|----------|----------------------------------|--------|
| Linux `~/.local/share/projectx/` | Yes (policy) | |
| Windows `%APPDATA%\Project X\` | Yes (policy) | |

---

## Metrics

| Metric | Linux | Windows |
|--------|-------|---------|
| Checklist items PASS | /25 | /25 |
| Critical steps PASS | /8 | /7 |
| BLOCKER count | | |
| HIGH count | | |
| MEDIUM count | | |
| LOW count | | |

---

## Release approval linkage

| Field | Value |
|-------|-------|
| Approval checklist completed | Yes / No |
| Approver | |
| Approval decision | APPROVED / CONDITIONAL / REJECTED |
| GitHub Release URL | |

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tester | | | |
| Release owner | | | |

---

## Appendix — raw notes

_Free-form observations, timing, environment quirks._

```

```
