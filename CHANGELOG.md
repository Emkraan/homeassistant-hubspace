# Changelog

## 2026.8.10 (2026-08-10)

Repo standard compliance updates. No functional changes since 2026.7.3.

### Changed
- Migrated from Dependabot to Renovate for dependency updates.
- CI now uses the shared `ha-shared-workflows` reusable workflow.
- Exempted `renovate[bot]` from the readme-freshness gate.

## 2026.7.3 (2026-07-28)

First stable release. Same code as `2026.7.3-beta` below - promoted after
live end-to-end testing (login, all entity platforms, light control, and
the self-healing recovery path) against a real Hubspace account.

## 2026.7.3-beta (2026-07-28)

**Self-healing for unresponsive devices - no more manual reload.** Observed
live: a light reconnected to Wi-Fi and worked fine in the official Hubspace
app, but stayed uncontrollable through this integration - every *other*
device kept polling normally, so nothing tripped the whole-account
reconnect logic, and the only fix was reloading the integration by hand
(which works only because it forces a brand-new discovery pass). This
release automates that: a background watchdog checks every 90s for any
device that's gone stale and forces an out-of-band discovery refresh
(rate-limited to once every 2 minutes per stale batch); if a device is
still stale after 12 minutes despite refreshes, it escalates to a full,
automatic config-entry reload - the same recovery a user would otherwise
have to trigger by hand.

**Fixed a related resource leak:** `async_unload_entry` never actually shut
down the previous coordinator/bridge on reload, so every manual (or now
automatic) reload leaked the old bridge's background polling tasks running
orphaned in the background instead of stopping them. Now properly calls
`coordinator.async_shutdown()` on unload.

## 2026.7.2-beta (2026-07-28)

**Critical fix: entities stuck permanently `unavailable`.** The vendored
`aioafero` tree used upstream's original absolute imports
(`from aioafero.xxx import ...`), which only work when `aioafero` is a real
top-level package - never true here. On a clean install with no leftover
`aioafero` PyPI package, this breaks the integration outright
(`ModuleNotFoundError`). On an install with a leftover `aioafero` from the
community integration this replaces, those imports silently resolved to
that external, unpatched copy instead - splitting the event stream across
two different `EventType` classes and permanently breaking every entity's
`unavailable` check, even for devices confirmed online in the official
Hubspace app. Rewrote every internal import in the vendored tree to be
properly relative; see
`custom_components/hubspace/aioafero/NOTICE.md` for the full explanation.

**If you installed `2026.7.0-beta` or `2026.7.1-beta` and your devices show
unavailable, update to this version - no need to remove/re-add in HACS,
just install the update and restart Home Assistant.**

## 2026.7.1-beta (2026-07-27)

Re-cut as a fresh tag/release. The `2026.7.0-beta` tag was deleted and
recreated pointing at a different commit after a same-day `hacs.json` fix -
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
  the API during a Home-Depot-side migration) goes unavailable on its own -
  it doesn't take every other device down with it.
- Configurable stale-data tolerance: brief cloud hiccups replay the last
  known good state instead of instantly flapping every entity to
  unavailable.
- Platforms: `light` (including multi-zone/dual-channel fixtures), `fan`,
  `switch`, `lock`, `valve`, `climate` (thermostats + portable ACs),
  `alarm_control_panel` (+ zone/keypad sensors), `sensor`, `binary_sensor`,
  `number`, `select`.
