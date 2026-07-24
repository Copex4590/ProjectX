# SAVE-229 — Progressive Data Pipeline

**Verdict: PASS**

## Before / After

| Metric | SAVE-228 (before) | SAVE-229 (after) |
|--------|-------------------|------------------|
| First paint strategy | Wait for full fetch, then chunked UI fill | First batch/phase painted ASAP |
| vessel_database activate() | ~9–15 ms | **0.6 ms** |
| vessel_database TTFV | n/a (full payload first) | **44.0 ms** |
| vessel_database total load | background full load | **163.7 ms** (37 batches, ~192 rows/batch) |
| vessel_database UI pulses during load | present | **3** |
| vessel_database cached revisit | ~0–24 ms | **0.0 ms** |
| timeline activate() | ~9–15 ms | **0.4 ms** |
| timeline TTFV | n/a (full payload first) | **118.6 ms** |
| timeline total load | background full load | **2316.4 ms** (288 batches, ~199 rows/batch) |
| timeline UI pulses during load | present | **23** |
| timeline cached revisit | ~0–24 ms | **0.0 ms** |
| statistics activate() | ~9–15 ms | **0.3 ms** |
| statistics TTFV | n/a (full payload first) | **204.4 ms** |
| statistics total load | background full load | **2328.2 ms** (2 batches, ~1 rows/batch) |
| statistics UI pulses during load | present | **27** |
| statistics cached revisit | ~0–24 ms | **0.0 ms** |
| analytics activate() | ~9–15 ms | **0.4 ms** |
| analytics TTFV | n/a (full payload first) | **259.6 ms** |
| analytics total load | background full load | **2451.3 ms** (2 batches, ~1 rows/batch) |
| analytics UI pulses during load | present | **25** |
| analytics cached revisit | ~0–24 ms | **0.0 ms** |

## Memory

- Traced delta: **74.45 MB**
- Traced peak: **140.06 MB**

## Lifecycle

- EventBus remaining listeners (approx): **0**
- Extra threads after close: **`VesselDatabaseSyncScheduler`** (app-level daemon; not a page-load leak)

## Checks

- First data appears quickly (TTFV recorded)
- UI pulses continue during load (event loop alive)
- Duplicate loaders blocked
- Cancel on page leave
- Cached revisits instant
- Sorting/filtering preserved (timeline smoke)
