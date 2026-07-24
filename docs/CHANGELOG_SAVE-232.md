# SAVE-232 — Event pipeline consolidation

## Summary

All live `ship.updated` traffic now publishes only from `HybridAisEngine`. UI pages (Dashboard, Map, Analytics, Vessel Details, Timeline) receive coalesced updates exclusively through `EventBridge`. Analytics polling timer removed.

## Deliverable

See `docs/reports/SAVE-232_event_pipeline.md`.
