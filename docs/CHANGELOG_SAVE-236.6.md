# CHANGELOG — SAVE-236.6

## Live RTL Configuration Reload

- Saving RTL Host/Port publishes `rtl.config.changed`.
- `HybridEngine` disconnects the live RTL socket and reconnects using the updated preferences — no app restart.
- AISStream / other providers are unchanged (event only fired from `save_local_configuration`).
