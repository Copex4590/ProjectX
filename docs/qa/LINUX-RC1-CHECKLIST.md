# Linux RC1 Test Checklist

Reusable Release Candidate test checklist for **Linux Mint / Ubuntu / Debian x86_64**.  
Artifact: **`ProjectX.deb`** (primary). Optional: `ProjectX.AppImage` (portable path).

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
| OS | e.g. Linux Mint 22, Ubuntu 24.04 |
| Architecture | x86_64 |
| Artifact source | GitHub Release / staging URL |
| Artifact SHA256 verified | Yes / No |
| Clean VM / physical | |

---

## Pre-test — remove previous install

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-01 | Remove old `.deb`: `sudo dpkg -r projectx` | Package not installed | | |
| L-02 | Remove dev install if present: `installer/linux/uninstall.sh` | No `~/.local/share/applications/projectx.desktop` | | |
| L-03 | Confirm `/opt/projectx` absent | Path does not exist | | |
| L-04 | Download `ProjectX.deb` from official release channel | File present locally | | |

---

## Install — package manager UX

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-05 | Double-click `.deb` | GDebi or Software Install opens | | |
| L-06 | Package name shown | **Project X** | | |
| L-07 | Package description | **Professional Maritime Monitoring Platform** | | |
| L-08 | Package icon | Project X logo (not generic placeholder) | | |
| L-09 | Start install | Progress shown | | |
| L-10 | Enter password / authorize | Install completes successfully | | |

**Critical:** L-06, L-07, L-10

---

## Post-install — shortcuts and menu

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-11 | Desktop shortcut | `Project X.desktop` on user desktop (default ON) | | |
| L-12 | Applications menu entry | Project X visible with icon | | |
| L-13 | Menu display name | **Project X** | | |
| L-14 | Menu subtitle / comment | Professional Maritime Monitoring Platform (or equivalent) | | |

**Critical:** L-13

---

## First launch and wizard

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-15 | Launch application (first time) | GUI opens; **no terminal window** | | |
| L-16 | First Run Wizard | Wizard appears and can be completed | | |
| L-17 | Close application | Clean exit, no hung process | | |

**Critical:** L-15, L-16

---

## Restart and relaunch

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-18 | Reboot system | Normal boot | | |
| L-19 | Launch from applications menu | App starts; no terminal | | |
| L-20 | Launch from desktop shortcut | App starts; no terminal | | |

**Critical:** L-19

---

## Uninstall

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-21 | Uninstall via Software Manager or `sudo dpkg -r projectx` | Uninstall succeeds | | |
| L-22 | Applications menu | Project X entry **gone** | | |
| L-23 | Desktop shortcut | `Project X.desktop` **removed** | | |
| L-24 | User configuration | `~/.local/share/projectx/` **preserved** (policy) | | |
| L-25 | System paths | `/opt/projectx` absent; `/usr/bin/projectx` absent | | |

**Critical:** L-22

---

## Optional — portable AppImage path

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-30 | Download `ProjectX.AppImage` | File present | | |
| L-31 | Mark executable and run | App launches | | |
| L-32 | Menu integration | No automatic menu entry (by design) | | |
| L-33 | Delete AppImage | No system install remnants | | |

---

## Optional — integrity

| ID | Step | Expected | Result | Issue ID |
|----|------|----------|--------|----------|
| L-40 | `sha256sum -c SHA256SUMS` | Both Linux artifacts OK | | |

---

## Test run summary

| Metric | Value |
|--------|-------|
| Critical steps PASS | /8 |
| Total steps PASS | /25 (excluding optional) |
| Open BLOCKER | |
| Open HIGH | |
| **Outcome** | PASS / CONDITIONAL PASS / FAIL |

**Next:** Complete [RELEASE-TEST-REPORT-TEMPLATE.md](RELEASE-TEST-REPORT-TEMPLATE.md)

---

## Issue logging quick guide

| Symptom | Type | Typical severity |
|---------|------|----------------|
| Install fails | INS | BLOCKER |
| Wrong package title | UX | HIGH |
| Terminal on launch | BUG | BLOCKER |
| Wizard broken | BUG | BLOCKER |
| Icon blurry | UX | MEDIUM |
| Desktop shortcut remains after uninstall | INS | MEDIUM |
