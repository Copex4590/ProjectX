# CHANGELOG — SAVE-236.5

## Release Blocker Stabilization

1. **AIS Providers panel ↔ Connection Panel sync**  
   Shared `connectivity.internet_state` drives AISStream display. Internet down → 🔴; restore while reconnecting → 🔴 Csatlakozás...; green only on real websocket `connected`.

2. **AISStream authentication UX**  
   HTTP 401/403 → durable `auth_error` status, no reconnect spam. Clear HU/EN message. New API key resumes connect automatically.

3. **RTL host/port single source of truth**  
   `HybridEngine.rtl_worker` reads `preferences.ais_local_host` / `ais_local_port` (no hardcoded `localhost:10110` on the live path). Wrong port → 🔴 Nincs kapcsolat.
