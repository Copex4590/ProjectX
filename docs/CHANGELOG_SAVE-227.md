# SAVE-227 — Lifecycle hooks (`initialize` / `activate`)

## Per-page work

| Page | `__init__` | `initialize()` (once) | `activate()` (every visit) |
|------|------------|----------------------|----------------------------|
| **Dashboard** | UI + button wiring | Language bind + translations | `refresh_configuration/observation/cameras` + diagnostics |
| **Map** | Layout shell, timers (unconnected), side panels | WebEngine via `MapController`, map signals, camera pack load, `VesselDetailsPanel.initialize()` | Personalization, observation points, `VesselDetailsPanel.activate()` |
| **Timeline** | UI + signal wiring | Language bind | `refresh()` (data + table) |
| **Analytics** | UI + timer object | Language bind + EventBus subscribe | `refresh()` + start live timer |
| **Statistics** | UI + timer object | Language bind | `refresh()` + restart auto-refresh if enabled |
| **Alert Center** | UI + timer object | Language bind + EventBus subscribe | `refresh()` + start timer |
| **Settings** | UI + signal wiring | Language bind | `reload_from_preferences()` |
| **Vessel Database** | UI + signal wiring | Language bind | `refresh()` |
| **Vessel Details** | UI sheet | Language bind + EventBus + `clear()` | `refresh()` if a vessel is selected |

## Verification (offscreen)

| Check | Result |
|-------|--------|
| `initialize()` count | **1** per page |
| `activate()` count | **≥2** after double navigation |
| `create()` count | **1** per page |
| MainWindow ctor | **~73 ms** (was ~67–91 ms post SAVE-224/226) |
| RSS after ctor | **~120 MB** (`ru_maxrss` 123364 KB) |
| First Timeline open | ~3926 ms (data load in `activate`, expected) |

## Notes

- Constructors no longer call `refresh()` / EventBus subscribe / WebEngine attach.
- Heavy data load remains on first **visit** via `activate()`, not at app startup (except Dashboard, which is eager).
