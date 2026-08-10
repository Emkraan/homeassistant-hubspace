<p align="center">
  <img src="https://raw.githubusercontent.com/Emkraan/homeassistant-hubspace/main/.github/homeassistant-hubspace.png" alt="Hubspace" width="120" />
</p>

<h1 align="center">Hubspace Integration for Home Assistant</h1>

<p align="center">
  Control Hubspace (Afero IoT) lights, fans, switches, locks, valves, thermostats, portable ACs, and security systems from Home Assistant - built from scratch for reliability.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-blue.svg?style=for-the-badge" alt="HACS Custom"></a>
  <a href="https://github.com/Emkraan/homeassistant-hubspace/releases"><img src="https://img.shields.io/github/v/release/Emkraan/homeassistant-hubspace?include_prereleases&style=for-the-badge" alt="Latest release"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white" alt="HA 2025.1+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License"></a>
</p>

<div align="center">

⚠️ 🚨 **This is an unofficial integration and is not affiliated with or endorsed by Hubspace, Afero, or The Home Depot.** 🚨 ⚠️

</div>

---

## Table of contents

- [Why this integration](#why-this-integration)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Automations](#automations)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Credits & attribution](#credits--attribution)
- [License](#license)

---

## Why this integration

Home Assistant already has a community Hubspace integration
(`jdeath/Hubspace-Homeassistant`). This is a separate, from-scratch build -
not a fork - focused specifically on the reliability gaps in real-world use:
devices that go unavailable and never recover, one flaky device taking every
other device down with it, opaque setup failures, and commands that appear
to work then silently revert a few seconds later. See
[How it works](#how-it-works) for the specifics.

## Features

- **Per-device availability** - a single device dropping off Wi-Fi (or
  vanishing from Afero's API during a Home-Depot-side backend migration)
  goes `unavailable` on its own. A shared cloud hiccup doesn't take every
  device down with it.
- **Self-healing** - a device that reconnects to Wi-Fi/power but stays
  unresponsive is recovered automatically: a background check forces a
  fresh discovery refresh, escalating to a full automatic reload if a
  device is still stuck after repeated attempts. No manual "reload
  integration" needed.
- **Stale-data tolerance** - brief Afero cloud outages replay the
  last-known-good state for a configurable grace period instead of
  instantly flapping every entity to unavailable.
- **Automatic re-authentication** - token refresh runs proactively with a
  safety margin; a dead refresh token now correctly falls back to a full
  login instead of repeating the same failed request.
- **Multi-zone lights supported natively** - dual-channel/color+white
  fixtures show up as separate light entities per zone.
- **Full device coverage** - lights, fans, switches (including multi-outlet
  power strips), locks, valves, thermostats, portable ACs, and security
  systems (panel + zone sensors + keypad).
- **UI configuration** - add the integration from Settings → Devices &
  Services. Supports MFA/one-time-passcode accounts and re-authentication
  when your password changes.

## Requirements

| Requirement | Details |
|---|---|
| Home Assistant | 2025.1.0 or newer |
| Hubspace account | Email + password used in the Hubspace app |
| Network | Outbound HTTPS to Afero's cloud API (`api2.afero.net`, `accounts.hubspaceconnect.com`) |

## Installation

### Via HACS (recommended)

Click the badge below to open HACS and add this repository in one step:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Emkraan&repository=homeassistant-hubspace&category=integration)

Or manually:

1. In Home Assistant, open **HACS → Integrations**.
2. Menu (⋮) → **Custom repositories**.
3. Add the repo URL: `https://github.com/Emkraan/homeassistant-hubspace`
4. Category: **Integration**. Click **Add**.
5. Install **Hubspace** from the list.
6. Restart Home Assistant.
7. **Settings → Devices & Services → Add Integration → Hubspace** and follow the prompts.

> **Migrating from `jdeath/Hubspace-Homeassistant`?** Both integrations use
> the same `hubspace` domain by design (this replaces it, rather than
> running alongside it). Remove the old `custom_components/hubspace` before
> installing this one, then re-add the integration and sign in again.

### Manual

1. Copy this repository's `custom_components/hubspace/` folder into `<config>/custom_components/hubspace/`.
2. Restart Home Assistant.
3. Add the integration from the UI as above.

## Configuration

Sign in with the same email and password you use in the Hubspace app. If
your account has two-factor authentication enabled, you'll be prompted for
the one-time code on the next screen.

Options (Settings → Devices & Services → Hubspace → Configure):

| Option | Default | Purpose |
|---|---|---|
| State polling interval | 30s | How often device state is refreshed. Floored at 2s - Afero rate-limits aggressively. |
| Device discovery interval | 3600s | How often the full device list is re-fetched (cheap deltas use the interval above; this is the expensive full-metadata call). |
| Keep last-known data during brief cloud outages | On | Ride out short Afero cloud blips without flapping entities to unavailable. |
| Stale-data grace period | 10 min | How long to tolerate a cloud outage before entities do go unavailable. |

## Entities

Entity availability depends on the specific device's own capabilities as
reported by Afero - not every field below exists on every model.

| Platform | Devices | Notes |
|---|---|---|
| `light` | Lights, including multi-zone/dual-channel fixtures | On/off, brightness, RGB color, color temperature (Kelvin), effects |
| `fan` | Ceiling/standalone fans | On/off, speed, direction, comfort-breeze preset |
| `switch` | Outlets, transformers, generic switches | One entity per toggleable instance (multi-outlet strips get one per outlet) |
| `lock` | Smart locks | Lock/unlock, with locking/unlocking transitional states |
| `valve` | Water timers/valves | One entity per zone instance |
| `climate` | Thermostats, portable ACs | HVAC mode, fan mode (thermostats), target temperature / range |
| `alarm_control_panel` | Security system panels | Arm home/away, disarm (PIN), manual trigger |
| `binary_sensor` | Any device with an alert-style state | Errors, motion, humidity threshold, security zone open/tamper, etc. |
| `sensor` | Any device with a telemetry value | Battery %, Wi-Fi RSSI, power (W), voltage (V) |
| `number` | Device-specific numeric settings | e.g. auto-off timer, alarm exit delay |
| `select` | Device-specific option pickers | e.g. alarm chime/siren sound and volume, fan speed step |

Exhaust fans are a special case: Afero exposes their toggle, fan speed, and
light as separate `switch`/`fan`/`light` entities rather than one combined
device - this mirrors how Afero's own API models them, not a limitation of
this integration.

## Automations

```yaml
# Turn on the porch light at sunset
automation:
  - alias: "Porch light at sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.porch_light
        data:
          brightness_pct: 60
```

```yaml
# Notify if a security zone opens while armed away
automation:
  - alias: "Zone opened while armed away"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_sensor
        to: "on"
    condition:
      - condition: state
        entity_id: alarm_control_panel.home_security_panel
        state: armed_away
    action:
      - service: notify.mobile_app
        data:
          message: "Front door opened while armed away"
```

```yaml
# Auto-close a valve after 15 minutes
automation:
  - alias: "Auto-close garden valve"
    trigger:
      - platform: state
        entity_id: valve.garden_zone_1
        to: "open"
        for: "00:15:00"
    action:
      - service: valve.close_valve
        target:
          entity_id: valve.garden_zone_1
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Setup fails with "unknown error" | Afero's login page changed, or a genuinely unexpected response | Enable debug logging (below) and check the log for the actual exception; open an issue with the redacted log |
| One device is `unavailable`, others are fine | That specific device stopped reporting (Wi-Fi drop, or removed from your Afero account) | Check the device in the Hubspace app; if it's really gone, remove it in HA too |
| Every device is `unavailable` at once | Afero's cloud is down or your account's connection was lost | Check whether the Hubspace app itself works right now; if not, this is an upstream outage, not a bug here |
| A command seems to revert a few seconds after you set it | Historically the most common Hubspace complaint - a stale poll response overwriting an optimistic update | This integration only applies poll-response fields matching a command it just sent, specifically to prevent this; if you still see it, please file a bug with debug logs |
| Setup asks for a one-time code every time | Your account has MFA enabled | Enter the current code from your authenticator/email each time you set up or re-authenticate |
| A device shows the wrong entity type (e.g. a dimmer showing as a plain switch) | Afero's own device metadata doesn't always self-describe correctly | File a feature request with the device's raw payload (see the issue template) |

Debug logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.hubspace: debug
```

## How it works

Hubspace runs entirely on Afero's cloud (`iot_class: cloud_polling` - there
is no local control path). Authentication is OAuth2 Authorization
Code + PKCE against a Keycloak identity provider
(`accounts.hubspaceconnect.com`), performed the same way the official app
does it. Access tokens last only 118 seconds; this integration refreshes
proactively with a safety margin rather than waiting for a request to fail.

Every device exposes a set of "functions" (its capability schema) and
"states" (current values), keyed by `(functionClass, functionInstance)` -
e.g. a combo fixture's power state might be keyed `power` /
`light-power` vs `power` / `fan-power`. State is fetched on two cadences: a
cheap per-device delta poll (30s default) and a more expensive full
discovery poll (hourly default) that picks up new/removed devices.

## Credits & attribution

The cloud protocol client is vendored from
[`aioafero`](https://github.com/Expl0dingBanana/aioafero) by Chris Dohmen
(MIT License) - see
[`custom_components/hubspace/aioafero/NOTICE.md`](custom_components/hubspace/aioafero/NOTICE.md)
for the exact local patches on top of upstream. Everything above that layer
(config flow, coordinator, entity platforms) is written fresh for this
integration.

## License

MIT - see [LICENSE](LICENSE). The vendored `aioafero` client retains its
own MIT copyright; see the Credits & attribution section above.
