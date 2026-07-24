# SAVE-223 — CHANGELOG (short)

## Fixed
- MainWindow no longer inherits ~950px+ minimum height from Sidebar / MapPage content
- Window can resize within detected monitor work areas (incl. 1366×768)

## Changed (layout only — no visual redesign)
- **Sidebar:** navigation buttons in `QScrollArea`; `minimumSizeHint` height = 0
- **MapPage:** right-hand panels in vertical `QScrollArea`; page min height = 0
- **ConnectionPanel:** does not force MainWindow min height
- **Pages host:** `_FlexibleStackedWidget` ignores child minimum sizes
- **MainWindow:** explicit reasonable `setMinimumSize(800, 500)`

## Unchanged
- Window Geometry Manager (SAVE-222) not modified
