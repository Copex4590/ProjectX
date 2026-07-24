# CHANGELOG — SAVE-236

## Internet State Propagation (UX)

- ConnectionPanel treats **Internet** as the master link for dependent providers.
- When Internet goes 🔴, internet-dependent rows (AISStream, API, and future peers in `INTERNET_DEPENDENT_CONNECTIONS`) switch to 🔴 immediately — no wait for websocket timeout.
- When Internet returns 🟢, dependents stay 🔴 until their own live status is working again (e.g. AISStream websocket reconnect).
- Connection Notice popups still follow each provider’s **real** status (`_real_statuses`); Internet loss does not emit false AISStream lost/restored dialogs.
- Websocket reconnect logic is unchanged; only panel visuals are gated by Internet.
