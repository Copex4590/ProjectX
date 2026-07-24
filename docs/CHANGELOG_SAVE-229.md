# SAVE-229 — Progressive Data Pipeline

## Summary

Timeline, Vessel Database, Statistics, and Analytics now stream data to the GUI in batches instead of waiting for a complete dataset. The first batch/phase paints immediately; remaining data continues in configurable batches while the UI stays responsive.

## Architecture

- `gui/progressive_pipeline.py` — `ProgressiveDataPipeline`, `progressive_batch_size()`, metrics
- Batch size via `PROJECTX_PROGRESSIVE_BATCH_SIZE` (default **200**)
- Timeline / Vessel DB: SQL `LIMIT` first page, then in-memory batch slices
- Statistics / Analytics: vessels/fleet-first phase, then full timeline-backed snapshot
- Refresh keeps the previous cache visible and replaces it **atomically** on success
- `hideEvent` cancels in-flight loads when leaving the page
- Duplicate loaders refused unless `force=True`
- Cached revisits skip reload (`_data_ready`)

## Instrumentation

- Time to first visible row (TTFV)
- Total load time
- Batch count / rows per batch
- UI pulse count during load (event-loop liveness)

## Verification — **PASS**

See `docs/reports/SAVE-229_progressive_report.md`.

| Page | TTFV | Total | Batches |
|------|------|-------|---------|
| Vessel Database | ~44 ms | ~164 ms | 37 |
| Timeline | ~119 ms | ~2.3 s | 288 |
| Statistics | ~204 ms | ~2.3 s | 2 phases |
| Analytics | ~260 ms | ~2.5 s | 2 phases |

Cached revisits ~0 ms. EventBus listeners 0 after shutdown. No QObject lifetime issues observed.
