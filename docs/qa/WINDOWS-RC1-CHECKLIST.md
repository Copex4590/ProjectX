# Windows RC1 Test Checklist

Reusable Release Candidate test checklist for **Windows 10/11 x64**.  
Artifact: **`ProjectX-Setup.exe`**.

**Test run ID:** `PX-QA-RUN-{VERSION}-{NNN}`  
**Severity reference:** [SEVERITY.md](SEVERITY.md)  
**Pass/fail rules:** [PASS-FAIL-CRITERIA.md](PASS-FAIL-CRITERIA.md)

---

## Test environment

| Field | Value |
|-------|-------|
| Version under test | |
| Test run ID | |
| Tester | |
| Date | |
| OS | e.g. Windows 11 23H2 |
| Architecture | x64 |
| Artifact source | GitHub Release / staging URL |
| Artifact SHA256 verified | Yes / No |
| Clean VM recommended | Yes |

---

## Pre-test — remove previous install

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-01 | Uninstall existing Project X via Settings → Apps | Not listed after uninstall | | |
| W-02 | Confirm `{ProgramFiles}\Project X` removed | Folder absent | | |
| W-03 | Download `ProjectX-Setup.exe` from official release channel | File present locally | | |
| W-04 | Optional: verify with `SHA256SUMS` | Checksum matches | | |

---

## Install — installer UX

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-05 | Run `ProjectX-Setup.exe` | Inno Setup wizard opens | | |
| W-06 | Product name | **Project X** | | |
| W-07 | Install location | `{autopf}\Project X` (64-bit Program Files) | | |
| W-08 | Optional tasks visible | Desktop shortcut, Launch after install | | |
| W-09 | Complete install | Installation succeeds | | |
| W-10 | UAC prompt | Handled; install completes | | |

**Critical:** W-05, W-09

---

## Post-install — shortcuts

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-11 | Start Menu | **Project X** shortcut with icon | | |
| W-12 | Start Menu launch | Application starts | | |
| W-13 | Desktop shortcut (if task selected) | Shortcut present and works | | |

**Critical:** W-12

---

## First launch and wizard

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-14 | First launch | GUI opens without error dialog | | |
| W-15 | First Run Wizard | Wizard appears and can be completed | | |
| W-16 | Dashboard / map smoke test | Map view loads (network permitting) | | |
| W-17 | Close application | Clean exit | | |

**Critical:** W-14, W-15

---

## Restart and relaunch

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-18 | Reboot Windows | Normal boot | | |
| W-19 | Launch from Start Menu | App starts normally | | |
| W-20 | Launch from desktop (if installed) | App starts normally | | |

**Critical:** W-18, W-19

---

## Uninstall

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-21 | Uninstall via Settings → Apps | Uninstall completes | | |
| W-22 | Program Files | `{ProgramFiles}\Project X` removed | | |
| W-23 | Start Menu shortcut | Removed | | |
| W-24 | Desktop shortcut | Removed (if was created) | | |
| W-25 | User data | `%APPDATA%\Project X\` **preserved** (policy) | | |

**Critical:** W-21, W-22

---

## Optional — silent install (automated parity)

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-30 | `scripts\verify_windows_installer.bat` on build machine | PASS | | |
| W-31 | Silent install: `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` | Installs without UI | | |
| W-32 | Silent uninstall | Directory removed | | |

---

## Optional — SmartScreen / signing

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| W-40 | SmartScreen on first run | Warning may appear (unsigned — document if MEDIUM) | | |

---

## Test run summary

| Metric | Value |
|--------|-------|
| Critical steps PASS | /7 |
| Total steps PASS | /25 (excluding optional) |
| Open BLOCKER | |
| Open HIGH | |
| **Outcome** | PASS / CONDITIONAL PASS / FAIL |

**Next:** Complete [RELEASE-TEST-REPORT-TEMPLATE.md](RELEASE-TEST-REPORT-TEMPLATE.md)

---

## Issue logging quick guide

| Symptom | Type | Typical severity |
|---------|------|----------------|
| Installer fails | INS | BLOCKER |
| Wrong product name in Add/Remove Programs | UX | HIGH |
| Crash on startup | BUG | BLOCKER |
| Wizard broken | BUG | BLOCKER |
| SmartScreen warning | UX | MEDIUM (if documented) |
| Start Menu entry remains after uninstall | INS | HIGH |
