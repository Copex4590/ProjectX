# Project X — TODO

## SAVE-031 — Circular import: CameraManager ↔ Diagnostics

**Status:** Open  
**Discovered during:** SAVE-030 (0.2 RC1 stabilization)  
**Priority:** High

### Issue

Importing `engines.camera.diagnostics` (or `engines.camera` package) can hang or take
excessively long during application startup and headless verification. Investigation
during SAVE-030 suggests a **possible circular import** between:

- `cameras.manager` / `CameraManager` (via `camera_selection_engine`)
- `engines.camera.diagnostics` (via `diagnostics_engine` → `provider_registry` → `engines.camera.providers`)
- `engines.camera` package `__init__.py` (imports both `diagnostics` and `providers`)

### Observed behavior

- `from cameras import camera_manager` — loads quickly
- `import engines.camera.diagnostics` — can block indefinitely in some import orders
- `import engines.camera.providers` — slow (~15s) or may block depending on load order
- Headless verification scripts that import diagnostics after cameras may hang

### Suspected chain

```
engines.camera.__init__
  → diagnostics → diagnostics_engine
    → provider_registry → engines.camera.providers
  → camera_selection_engine
    → cameras.manager → cameras (pack_manager reload)
```

### Scope for SAVE-031

- [ ] Confirm circular import with import profiling
- [ ] Break the cycle without changing CameraManager architecture, providers, or diagnostics logic
- [ ] Lazy-load `provider_registry` / `backend_registry` in `diagnostics_engine` if appropriate
- [ ] Re-order or defer imports in `engines.camera.__init__.py`
- [ ] Add import-order regression test
- [ ] Re-enable full headless verification

### Do NOT

- Modify HybridEngine, CameraManager architecture, CameraSelectionEngine, providers, or Playback Framework as part of the quick fix unless strictly required for import resolution
