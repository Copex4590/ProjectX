# SAVE-230 — Release readiness audit

## Summary

Full-tree release-readiness audit after startup / lifecycle / progressive-loading work. Overall score **74/100**. Linux Alpha **PASS\*** (rebuild packages first). Full dual-platform public release **FAIL** (Windows binary missing + stale Linux artifacts).

## Safe cleanups (verified)

- Stop MainWindow from importing unused `inspector` for version metadata
- Remove superseded `DeferredDataLoader` API
- Stop exporting unused AIS engine stubs from `engines.ais`
- Fix AppStream license to MIT; stamp `PROJECTX_BUILD` on Linux release builds
- Drop junk `map.html.save`; correct metainfo path in Linux installer docs

## Deliverables

- `docs/reports/SAVE-230_release_readiness_audit.md`
- Canvas: `SAVE-230-release-readiness.canvas.tsx`
