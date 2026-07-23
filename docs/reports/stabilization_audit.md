# Project X — Stabilization Audit (SAVE-201)

**Branch:** `release/0.3.1-alpha.1`  
**Scope:** `src/**/*.py` pattern scan  
**Mode:** Report only — no code changes in this audit pass.

## Summary counts

| Pattern | Count |
|--------|------:|
| `TODO` | 0 |
| `FIXME` | 0 |
| `NotImplemented` | 10 |
| `except:` | 0 |
| `except Exception` | 35 |
| `pass` | 19 |
| `print(` | 48 |

Notes:
- No `TODO` / `FIXME` markers found in `src/`.
- No bare `except:` found in `src/`.
- `pass` includes intentional empty class bodies and narrow `except (...): pass` handlers.
- `print(` is concentrated in HybridEngine (production) and unused `hybrid_engine_v2`.

## Findings by file

### `src/ais/providers/aisstream_provider.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 104 | `except Exception` | `except Exception as e:` |

### `src/ais/providers/provider.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 54 | `NotImplemented` | `raise NotImplementedError` |
| 58 | `NotImplemented` | `raise NotImplementedError` |

### `src/app/application.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 124 | `except Exception` | `except Exception:` |

### `src/camera/stream_test.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 91 | `pass` | `pass` |

### `src/cameras/loader.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 17 | `pass` | `pass` |

### `src/database/vessel_sync.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 211 | `except Exception` | `except Exception:` |
| 212 | `pass` | `pass` |

### `src/engines/ais/ais_rtl_client.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 49 | `pass` | `pass` |

### `src/engines/ais/aisstream_engine.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 76 | `except Exception` | `except Exception:` |
| 102 | `except Exception` | `except Exception:` |

### `src/engines/ais/runtime_provider.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 28 | `NotImplemented` | `raise NotImplementedError` |
| 32 | `NotImplemented` | `raise NotImplementedError` |
| 36 | `NotImplemented` | `raise NotImplementedError` |

### `src/engines/camera/camera_engine.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 12 | `print(` | `print("Camera Engine started.")` |
| 16 | `print(` | `print("Camera Engine stopped.")` |

### `src/engines/camera/diagnostics/diagnostics_engine.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 253 | `except Exception` | `except Exception:` |
| 295 | `except Exception` | `except Exception:` |
| 296 | `pass` | `pass` |

### `src/engines/playback/backends/mpv_backend.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 108 | `except Exception` | `except Exception as error:` |

### `src/engines/rtl/hybrid_engine.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 72 | `except Exception` | `except Exception:` |
| 145 | `except Exception` | `except Exception:` |
| 231 | `print(` | `print("🛑 Hybrid Engine stopped")` |
| 237 | `print(` | `print(f"🧹 Removed {removed} ship(s) outside reference coverage")` |
| 251 | `except Exception` | `except Exception:` |
| 252 | `pass` | `pass` |
| 259 | `except Exception` | `except Exception:` |
| 260 | `pass` | `pass` |
| 267 | `print(` | `print(f"📁 Új hajó dosszié létrehozva: {name}")` |
| 540 | `print(` | `print()` |
| 541 | `print(` | `print("════════════════════════════════════")` |
| 542 | `print(` | `print(f"🚢 {name}")` |
| 543 | `print(` | `print(f"📏 Távolság : {round(distance, 2)} km-re {direction}")` |
| 544 | `print(` | `print(f"🧭 {heading}")` |
| 546 | `print(` | `print(f"⚡ {sog:.1f} csomó")` |
| 547 | `print(` | `print(f"🕒 {current_time} [{source}]")` |
| 548 | `print(` | `print("════════════════════════════════════")` |
| 571 | `print(` | `print("⏳ Waiting for observation reference point before AISStream...")` |
| 579 | `print(` | `print("⏳ AISStream disabled or missing API key...")` |
| 586 | `print(` | `print("📡 AISStream kapcsolat...")` |
| 606 | `print(` | `print("✅ AISStream kapcsolódva")` |
| 619 | `print(` | `print("🔄 Observation area changed — resubscribing AISStream...")` |
| 649 | `print(` | `print(f"📻 AIS név: {mmsi} -> {meta_name}")` |
| 681 | `print(` | `print(f"🟢 AISStream név: {mmsi} -> {name}")` |
| 706 | `except Exception` | `except Exception as e:` |
| 709 | `print(` | `print("❌ AISStream hiba:", e)` |
| 739 | `print(` | `print("🚢 Hybrid Duna Monitor")` |
| 740 | `print(` | `print("📡 Kapcsolódás AIS-catcherhez...")` |
| 758 | `print(` | `print("✅ Kapcsolódva")` |
| 763 | `print(` | `print("📡 Várakozás hajóadatokra...")` |
| 804 | `print(` | `print(f"📻 RÁDIÓ NÉV: {mmsi} -> {ship_name}")` |
| 850 | `except Exception` | `except Exception as e:` |
| 851 | `print(` | `print("⚠️ RTL hiba:", e)` |

### `src/engines/rtl/hybrid_engine_v2.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 80 | `except Exception` | `except Exception:` |
| 97 | `except Exception` | `except Exception:` |
| 98 | `pass` | `pass` |
| 107 | `print(` | `print("🛑 Hybrid Engine stopped")` |
| 113 | `except Exception` | `except Exception:` |
| 114 | `pass` | `pass` |
| 121 | `print(` | `print(f"📁 Új hajó dosszié létrehozva: {name}")` |
| 393 | `print(` | `print()` |
| 394 | `print(` | `print("════════════════════════════════════")` |
| 395 | `print(` | `print(f"🚢 {name}")` |
| 396 | `print(` | `print(f"📏 Távolság : {round(distance, 2)} km-re {direction}")` |
| 397 | `print(` | `print(f"🧭 {heading}")` |
| 399 | `print(` | `print(f"⚡ {sog:.1f} csomó")` |
| 400 | `print(` | `print(f"🕒 {current_time} [{source}]")` |
| 401 | `print(` | `print("════════════════════════════════════")` |
| 416 | `print(` | `print("📡 AISStream kapcsolat...")` |
| 429 | `print(` | `print("✅ AISStream kapcsolódva")` |
| 454 | `print(` | `print(f"📻 AIS név: {mmsi} -> {meta_name}")` |
| 486 | `print(` | `print(f"🟢 AISStream név: {mmsi} -> {name}")` |
| 511 | `except Exception` | `except Exception as e:` |
| 514 | `print(` | `print("❌ AISStream hiba:", e)` |
| 521 | `except Exception` | `except Exception:` |
| 522 | `pass` | `pass` |
| 532 | `print(` | `print("🚢 Hybrid Duna Monitor")` |
| 533 | `print(` | `print("📡 Kapcsolódás AIS-catcherhez...")` |
| 538 | `print(` | `print("✅ Kapcsolódva")` |
| 549 | `print(` | `print("📡 Várakozás hajóadatokra...")` |
| 590 | `print(` | `print(f"📻 RÁDIÓ NÉV: {mmsi} -> {ship_name}")` |
| 636 | `except Exception` | `except Exception as e:` |
| 637 | `print(` | `print("⚠️ RTL hiba:", e)` |

### `src/engines/timeline/arrival_departure_engine.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 173 | `except Exception` | `except Exception:` |
| 174 | `pass` | `pass` |

### `src/events/eventbus.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 52 | `except Exception` | `except Exception:` |

### `src/gui/aiswizard.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 216 | `pass` | `pass` |

### `src/gui/providers/__init__.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 44 | `except Exception` | `except Exception:` |

### `src/gui/providers/provider_window.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 166 | `NotImplemented` | `raise NotImplementedError` |
| 170 | `NotImplemented` | `raise NotImplementedError` |
| 174 | `NotImplemented` | `raise NotImplementedError` |
| 178 | `NotImplemented` | `raise NotImplementedError` |
| 182 | `NotImplemented` | `raise NotImplementedError` |

### `src/gui/systemhealthpage.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 141 | `pass` | `pass` |

### `src/gui/widgets/camerapreviewpanel.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 208 | `except Exception` | `except Exception:` |

### `src/inspector/inspector.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 76 | `except Exception` | `except Exception as error:` |
| 94 | `except Exception` | `except Exception as error:` |
| 122 | `except Exception` | `except Exception as error:` |
| 151 | `except Exception` | `except Exception as error:` |
| 199 | `except Exception` | `except Exception as error:` |
| 234 | `except Exception` | `except Exception as error:` |
| 260 | `except Exception` | `except Exception as error:` |

### `src/logbook/xlsx_generator.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 89 | `pass` | `pass` |

### `src/playback/live_camera_workflow.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 43 | `except Exception` | `except Exception:` |
| 144 | `except Exception` | `except Exception:` |
| 145 | `pass` | `pass` |
| 150 | `except Exception` | `except Exception:` |
| 151 | `pass` | `pass` |

### `src/rtl/reception_monitor.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 95 | `pass` | `pass` |

### `src/system_health/report.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 30 | `pass` | `pass` |

### `src/timeline/timeline_recorder.py`

| Line | Pattern | Snippet |
|-----:|---------|---------|
| 182 | `except Exception` | `except Exception:` |
| 183 | `pass` | `pass` |

