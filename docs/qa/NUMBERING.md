# QA Numbering System

Every test run and issue gets a **unique, permanent ID**. IDs are never reused, even if an issue is closed or a release is cancelled.

---

## Format

```
PX-QA-{TYPE}-{VERSION}-{NNN}
```

| Part | Meaning | Example |
|------|---------|---------|
| `PX` | Project X | Fixed prefix |
| `QA` | Quality assurance domain | Fixed |
| `{TYPE}` | Category (see below) | `RUN`, `BUG`, `UX`, `INS` |
| `{VERSION}` | Release under test | `0.3.0-alpha`, `0.4.0-beta` |
| `{NNN}` | Sequential number per type per version | `001`, `002`, … `999` |

**Examples:**

- `PX-QA-RUN-0.3.0-alpha-001` — first QA test run for 0.3.0-alpha
- `PX-QA-BUG-0.3.0-alpha-003` — third confirmed bug in that release cycle
- `PX-QA-UX-0.3.0-alpha-001` — first UX issue logged
- `PX-QA-INS-0.3.0-alpha-002` — second installer/packaging issue

---

## Issue types

| Type code | Full name | Use when |
|-----------|-----------|----------|
| **RUN** | Test run | Each execution of an RC checklist (Linux, Windows, or combined) |
| **BUG** | Bug | Application crashes, data loss, incorrect functional behaviour |
| **UX** | UX issue | Confusing labels, wrong menu name, poor copy, icon problems, wizard flow |
| **INS** | Installer issue | Install/uninstall failure, missing shortcut, wrong package metadata, checksum mismatch |

**Rule:** If unsure between BUG and UX, use **UX** for display/copy/integration issues and **BUG** for crashes or broken core behaviour.

---

## Assignment rules

1. **One RUN ID per checklist execution session** — e.g. Linux RC on VM A = one RUN; Windows RC on VM B = another RUN (or combine in one report with two RUN IDs).
2. **Increment NNN independently per TYPE per VERSION** — `BUG-001` and `UX-001` can coexist.
3. **Cross-release carry-over** — when an issue persists into the next version, open a **new ID** for the new version and reference the old ID in the description: `Carried from PX-QA-BUG-0.3.0-alpha-002`.
4. **Do not renumber** closed or invalid issues; mark status `WONTFIX`, `DUPLICATE`, or `INVALID` instead.

---

## Where to record IDs

| Location | Content |
|----------|---------|
| [RELEASE-TEST-REPORT-TEMPLATE.md](RELEASE-TEST-REPORT-TEMPLATE.md) | Test run ID, issue table |
| GitHub Issues (optional) | Title prefix: `[PX-QA-BUG-0.3.0-alpha-001]` |
| Release notes (if shipping known issue) | Reference ID for traceability |

---

## Test run naming convention

Recommended RUN description:

```
PX-QA-RUN-{VERSION}-{NNN} — {Platform} RC1 — {Tester} — {YYYY-MM-DD}
```

Example:

```
PX-QA-RUN-0.3.0-alpha-001 — Linux RC1 — Mint 22 VM — 2026-07-12
```

---

## Quick reference table

| I need to… | ID pattern |
|------------|------------|
| Start a new test session | `PX-QA-RUN-{VERSION}-{NNN}` |
| Log a crash | `PX-QA-BUG-{VERSION}-{NNN}` |
| Log wrong menu title / icon | `PX-QA-UX-{VERSION}-{NNN}` |
| Log .deb / .exe install failure | `PX-QA-INS-{VERSION}-{NNN}` |
