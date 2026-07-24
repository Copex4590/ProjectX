# CHANGELOG — SAVE-235

## Alpha UX stabilization

- Connection loss/restore popups: body-only text, no title, sticky until Close, per-connection “Don’t show again”.
- Right connection panel: remove Database; status icons ⚪ / 🟢 / 🔴 for Internet, AISStream, RTL, GPS, Camera, API.
- Preferences: `connection_notice_suppressed` map; automatic reconnect and panel colors continue when popups are suppressed.
- Connection UX no longer uses alert banners: removed `ais.status` → `AIS_LOST` → desktop banner path; Connection Notice is exclusive.
- Camera panel 🟢 requires an enabled camera whose stream host is actually reachable (not merely enabled).
- Alpha UX: Professional Alerts desktop banners suppressed (`DesktopBannerSink.ENABLED_FOR_ALPHA = False`); timeline / AlertManager / Alert Center pipeline unchanged.
