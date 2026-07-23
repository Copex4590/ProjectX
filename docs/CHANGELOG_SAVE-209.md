# SAVE-209 — CHANGELOG (short)

## Added
- Automatic Vessel Database Synchronization for Database Manager backend
- Auto Sync scheduler (Idle / Running / Error)
- Persisted Last Sync + Auto Sync ON/OFF (`data/vessel_db_sync_state.json`)
- Next Sync calculation from interval
- Manual Sync (background worker)
- Progress callback hook + EventBus events (`vessel_db.sync.*`)
- Online provider hook (`OnlineVesselSyncProvider`) for later enrichment

## Notes
- UI unchanged (SAVE-208 Manager page)
- Local sync reconciles ShipRegistry → SQLite via existing VesselSync
