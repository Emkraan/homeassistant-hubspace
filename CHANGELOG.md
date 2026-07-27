# Changelog

## 2026.7.0-beta (2026-07-27)

Initial release. A from-scratch Home Assistant integration for Hubspace
(Afero IoT), built to replace the community `jdeath/Hubspace-Homeassistant`
integration with better reliability.

- Full config flow: email/password sign-in, OTP/MFA support, reauthentication.
- Vendors and hardens the `aioafero` cloud client (see
  `custom_components/hubspace/aioafero/NOTICE.md` for the exact patches):
  proactive token refresh with a safety margin, a fixed reauth-retry bug,
  broader retry coverage for Afero's own intermittent 500s and connection
  timeouts, and connectivity signaling on the state-poll loop that previously
  failed silently.
- Per-device availability: one device dropping off Wi-Fi (or vanishing from
  the API during a Home-Depot-side migration) goes unavailable on its own —
  it doesn't take every other device down with it.
- Configurable stale-data tolerance: brief cloud hiccups replay the last
  known good state instead of instantly flapping every entity to
  unavailable.
- Platforms: `light` (including multi-zone/dual-channel fixtures), `fan`,
  `switch`, `lock`, `valve`, `climate` (thermostats + portable ACs),
  `alarm_control_panel` (+ zone/keypad sensors), `sensor`, `binary_sensor`,
  `number`, `select`.
