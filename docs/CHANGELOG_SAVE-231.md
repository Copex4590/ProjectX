# SAVE-231 — Camera framework consolidation

## Summary

Merged the legacy `src/camera` (user/OP) and `src/cameras` (catalog/packs) stacks into one `Camera` model, one `CameraManager`, and one registry. Wizard, dashboard, map selection/preview, HLS providers, and health/analytics all use the same path.

## Deliverable

See `docs/reports/SAVE-231_camera_consolidation.md` (architecture diagram, removed files, module tree, import report, PASS).
