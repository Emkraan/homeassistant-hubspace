# Changelog

## 2026.7.2-beta (2026-07-28)

**Critical fix: entities stuck permanently `unavailable`.** The vendored
`aioafero` tree used upstream's original absolute imports
(`from aioafero.xxx import ...`), which only work when `aioafero` is a real
top-level package — never true here. On a clean install with no leftover
`aioafero` PyPI package, this breaks the integration outright
(`ModuleNotFoundError`). On an install with a leftover `aioafero` from the
community integration this replaces, those imports silently resolved to
that external, unpatched copy instead — splitting the event stream across
two different `EventType` classes and permanently breaking every entity's
`unavailable` check, even for devices confirmed online in the official
Hubspace app. Rewrote every internal import in the vendored tree to be
properly relative; see
`custom_components/hubspace/aioafero/NOTICE.md` for the full explanation.

**If you installed `2026.7.0-beta` or `2026.7.1-beta` and your devices show
unavailable, update to this version — no need to remove/re-add in HACS,
just install the update and restart Home Assistant.**

## 2026.7.1-beta (2026-07-27)

Re-cut as a fresh tag/release. The `2026.7.0-beta` tag was deleted and
recreated pointing at a different commit after a same-day `hacs.json` fix —
HACS's own release-indexing pipeline got confused by the tag move and cached
a stale ref, causing installs to 404. No functional changes from
`2026.7.0-beta` beyond this version bump; if you have `2026.7.0-beta`
tracked in HACS, remove the repository and re-add it fresh rather than
updating in place.

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
