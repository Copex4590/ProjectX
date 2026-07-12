# QA Severity Classification

All issues found during RC testing must be assigned one of four severity levels. Severity drives **publish / reject** decisions (see [PASS-FAIL-CRITERIA.md](PASS-FAIL-CRITERIA.md)).

---

## Severity levels

### BLOCKER

**Definition:** Prevents RC publication. End users cannot install, launch, or use core functionality; or causes data loss / security exposure.

**Examples:**

- Installer fails on a supported clean OS
- Application will not start after install
- Terminal/console window appears for GUI launch (Linux `.deb` / Windows `.exe`)
- First Run Wizard cannot complete
- Download artifact 404 or checksum mismatch on official channel
- Uninstall leaves broken system state (orphaned services, unremovable package)
- Critical crash on startup with default configuration

**Response:** Fix required before any public release. RC **must be rejected**.

---

### HIGH

**Definition:** Major functionality broken or severely degraded for typical users; workaround difficult or undocumented.

**Examples:**

- Dashboard map does not load on clean install
- Menu entry missing after `.deb` install (primary Linux path)
- Wrong application name shown in Software Manager / Add/Remove Programs
- Silent install script fails in CI verification
- AppImage or portable path completely non-functional

**Response:** Fix before publication unless explicitly deferred with documented workaround and product owner sign-off. **Default: reject RC.**

---

### MEDIUM

**Definition:** Noticeable problem that does not block core workflow; reasonable workaround exists.

**Examples:**

- Desktop shortcut not removed on uninstall (menu entry OK)
- Secondary download path (AppImage) missing optional integration
- Non-critical UI glitch in wizard
- SmartScreen warning on Windows (unsigned binary — known limitation if documented)
- Icon slightly blurry at one size only

**Response:** May ship in RC/Alpha with issue logged and release-note entry. **Must not accumulate more than 3 open MEDIUM issues without review.**

---

### LOW

**Definition:** Cosmetic, documentation, or edge-case issue; no impact on install → launch → core use.

**Examples:**

- Typo in release notes (not in installer UI)
- AppStream hint warning during AppImage build (no user impact)
- Dev-only script mentioned in non-public doc
- Minor alignment in About dialog

**Response:** Fix when convenient; does not block publication.

---

## Severity vs issue type

| Issue type | Typical severities |
|------------|-------------------|
| **BUG** | BLOCKER, HIGH, MEDIUM |
| **UX** | HIGH, MEDIUM, LOW |
| **INS** | BLOCKER, HIGH, MEDIUM |

Installer failures that block install are almost always **BLOCKER** (`INS` or `BUG`).

---

## Escalation rules

| Condition | Action |
|-----------|--------|
| Any open **BLOCKER** | RC rejected |
| Any open **HIGH** without deferral approval | RC rejected |
| 3+ open **MEDIUM** | Release approval meeting required |
| **LOW** only | RC may proceed |

---

## Deferral (HIGH / MEDIUM only)

To ship with a non-blocker unfixed:

1. Log issue ID (`PX-QA-*`)
2. Document in release notes under **Known issues**
3. Record **Deferral approved by:** name + date on [RELEASE-APPROVAL-CHECKLIST.md](RELEASE-APPROVAL-CHECKLIST.md)
4. Set target fix version

**BLOCKER issues cannot be deferred.**

---

## Status values

| Status | Meaning |
|--------|---------|
| `OPEN` | Not fixed |
| `FIXED` | Fixed in current RC build |
| `VERIFIED` | Fix confirmed in QA re-run |
| `DEFERRED` | Accepted for this release (not BLOCKER) |
| `DUPLICATE` | Same as existing ID |
| `WONTFIX` | Accepted permanent limitation |
| `INVALID` | Not reproducible / not an issue |
