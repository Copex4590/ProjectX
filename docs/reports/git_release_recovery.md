# SAVE-207 — Git Release Recovery

**Branch:** `release/0.3.1-alpha.1`  
**Date:** 2026-07-23  
**Goal:** Remove `data/obs_freeze.trace` (~714 MB) from release-branch history so GitHub push can succeed.  
**Force-push:** **not executed** (operator must run the push command below).  
**Commits created by SAVE-207:** **none**.

---

## 1. Audit — large files

Largest blobs observed before rewrite (repo-wide object scan):

| Size (bytes) | Path |
|-------------:|------|
| 747 957 899 | `data/obs_freeze.trace` (**blocker**) |
| ~402 548 | older `data/obs_freeze.trace` revisions |
| ~246 065 | older `data/obs_freeze.trace` revisions |
| ~5 909 848 | `src/resources/map/cesium/Cesium.js` (other history; not the push blocker) |

### Commits that touched `data/obs_freeze.trace` (pre-rewrite)

| Commit | Subject | Note |
|--------|---------|------|
| `30d1ab6` | SAVE-200 Baseline before Performance Initiative | **Introduced 713 MB growth** (`246065 → 747957899`); **only file in that commit** |
| `d3b3dd6` | SAVE-102 Phase 1 - Project X Design System | Smaller trace blob among other files |
| `fc19762` | SAVE-100 Pre-cleanup snapshot | Smaller trace blob among other files |

Also present on other refs (not rewritten): `stabilization/0.3.1-alpha`, some stash-like commits. **`main` does not contain `30d1ab6`.**

Working tree still has a local `data/obs_freeze.trace` (~714 MB) for debugging; it is now **gitignored**.

---

## 2. What changed (local only)

1. **Backup ref created:** `backup/pre-save207-release-0.3.1-alpha.1` → old tip `a1901e652f41b35e0423d1f8c9027078fad61574`
2. **History rewritten** on `release/0.3.1-alpha.1` with:
   ```bash
   FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
     --index-filter 'git rm --cached --ignore-unmatch data/obs_freeze.trace' \
     --prune-empty \
     release/0.3.1-alpha.1
   ```
3. **`.gitignore` updated (working tree only, not committed):**
   - `data/obs_freeze.trace`
   - `**/obs_freeze.trace`
4. **Verified:** `git rev-list --objects release/0.3.1-alpha.1` contains **no** `obs_freeze.trace` path.
5. **New tip:** `885a2c8c6d790880556c59ccf56290b559d4f30e` (`SAVE-206 Refresh Linux release checksums`)

`refs/original/refs/heads/release/0.3.1-alpha.1` still points at the pre-rewrite tip (filter-branch safety net).

---

## 3. Rewritten commits (message → SHA)

All meaningful SAVE commits retained with new SHAs. **SAVE-200 was pruned** because after removing `data/obs_freeze.trace` it had an empty tree delta (that commit only enlarged the forbidden file).

| Subject | Old SHA | New SHA |
|---------|---------|---------|
| `SAVE-206 Refresh Linux release checksums` | `a1901e652f41` | `885a2c8c6d79` |
| `SAVE-205 Release Finalization` | `57645274deac` | `1c8a2e962cc5` |
| `SAVE-204 Release Candidate Audit` | `f03690b382d1` | `0c9f71124202` |
| `SAVE-203 High Priority Release Stabilization` | `388b4930a57b` | `3bd0f73387c1` |
| `SAVE-202 Critical Release Stabilization` | `dad5319d424e` | `d904a6f1f8f7` |
| `SAVE-201 – Release Stabilization Phase 1` | `46b663f7fdf1` | `80396c3921a8` |
| `SAVE-P0 – Gate obs_freeze_trace` | `87b27dca7a2e` | `7e68f30780be` |
| `SAVE-200 Baseline before Performance Initiative` | `30d1ab6b3996` | **PRUNED** (empty after strip) |
| `SAVE-103 - Safe filename handling` | `817f141c6c75` | `7a4c328d8c92` |
| `SAVE-105 - Hybrid Engine hot path optimization` | `9949e9803d0b` | `adca17159474` |
| `SAVE-106 - GUI Refresh Optimization` | `d7fef890ac43` | `a98fa1284d2e` |

Every other commit on the release lineage was rewritten with a new object ID; messages and non-trace file contents preserved. Ancestors that previously carried smaller `obs_freeze.trace` blobs no longer contain that path.

---

## 4. Exact commands (already run locally)

```bash
# 0) Ensure on release branch
cd /home/zoli/ProjectX
git checkout release/0.3.1-alpha.1

# 1) Backup old tip
git branch backup/pre-save207-release-0.3.1-alpha.1 HEAD

# 2) Strip path from entire release-branch ancestry
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --index-filter 'git rm --cached --ignore-unmatch data/obs_freeze.trace' \
  --prune-empty \
  release/0.3.1-alpha.1

# 3) Verify absence
git rev-list --objects release/0.3.1-alpha.1 | grep 'obs_freeze\.trace' || echo 'NONE'

# 4) .gitignore (working tree — not committed per SAVE-207)
#    entries: data/obs_freeze.trace and **/obs_freeze.trace
```

Optional local GC (after you are satisfied; drops unreachable pre-rewrite objects later):

```bash
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## 5. Required push command (operator — not executed)

If the branch **does not exist yet** on `origin`:

```bash
git push -u origin release/0.3.1-alpha.1
```

If the branch **already exists** on `origin` with the old history (contains the 713 MB blob), a force-with-lease is required:

```bash
git push --force-with-lease origin release/0.3.1-alpha.1
```

**SAVE-207 did not run any push.**

Recommended follow-up **after** a successful push (new commit; outside this SAVE):

```bash
git add .gitignore
git commit -m "$(cat <<'EOF'
SAVE-207 Ignore obs_freeze.trace runtime artifact

EOF
)"
git push origin release/0.3.1-alpha.1
```

---

## 6. Rollback procedure

Restore the pre-rewrite tip from the backup branch:

```bash
git checkout release/0.3.1-alpha.1
git reset --hard backup/pre-save207-release-0.3.1-alpha.1
# equivalent tip also at:
#   refs/original/refs/heads/release/0.3.1-alpha.1  (a1901e652f41…)
```

If a force-push already updated the remote, rollback remote as well (destructive):

```bash
git push --force-with-lease origin backup/pre-save207-release-0.3.1-alpha.1:release/0.3.1-alpha.1
```

---

## 7. Notes / remaining risks

- `stabilization/0.3.1-alpha` still points at pre-rewrite history that may contain the large blob — do not push that ref without a similar strip.
- Local disk may still hold the old blob until `refs/original` is deleted and `git gc` runs.
- Cesium and other large-but-acceptable assets were not removed.

---

## READY TO FORCE PUSH
