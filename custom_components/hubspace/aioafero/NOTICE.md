# Third-party notice

This directory (`custom_components/hubspace/aioafero/`) is vendored from
[`aioafero`](https://github.com/Expl0dingBanana/aioafero) by Chris Dohmen
(`Expl0dingBanana`), licensed under the MIT License (see `LICENSE` in this
directory for the full text and copyright notice).

Vendored from commit `c8ca65dc5adce6bf8a47edf96eab13e4f4d18496` (`main`,
2026-07-25; `pyproject.toml` declares version `7.0.10`). It is copied in
rather than depended on as a PyPI package so reliability issues can be fixed
directly and there is no external package to break on a Home Assistant
update - per Emkraan's standing "HA Integration Build From Scratch" policy.

## Local patches on top of upstream

All patches below are marked inline with an `Emkraan hardening:` comment at
the change site, so a future upstream version bump is a reviewable diff.

- **`v1/auth.py`** (2026-07-27): `AferoAuth.token()` did not clear
  `self._token_data` before its own internal retry when a refresh-token
  exchange raised `InvalidAuth`. The retry re-entered with the *same* dead
  token still set, so `is_expired` was still `True` and it repeated the
  identical doomed refresh grant instead of ever falling through to
  `perform_initial_login()` (a full username/password login) - the retry
  path was a no-op that always raised on the second attempt. Fixed by
  setting `self._token_data = None` before retrying. Also added a
  `TOKEN_REFRESH_MARGIN` (20s) so `is_expired` trips before the hard 118s
  cutoff instead of exactly at it, closing an in-flight-request race.
- **`v1/__init__.py`** (2026-07-27): `AferoBridgeV1.request()` only retried
  on HTTP 429/503/504 and did not retry on 500/502, and any connection-level
  failure (`aiohttp.ClientError`, timeout) from the request itself propagated
  immediately with zero retry, outside the backoff loop entirely. Both are
  exactly the shape of upstream-reported "500 Internal Server Error and
  Connection timeouts when fetching states" failures. Folded both into the
  existing retry/backoff loop.
- **`v1/controllers/event.py`** (2026-07-27): `EventStream.__device_polling`
  (the ~30s state-poll loop) swallowed every exception with only a log line
  and no event emitted, so a sustained state-poll outage left every device
  frozen on stale data forever with zero signal to subscribers - the
  discovery loop (hourly) already emitted `DISCONNECTED`/`RECONNECTED` on
  the same class of failure, but the far-more-frequent state loop did not.
  Added the same consecutive-failure tracking and `DISCONNECTED`/
  `RECONNECTED` emission to the state-poll loop.

- **All files** (2026-07-28, critical): every internal cross-module import
  in this vendored tree used upstream's original **absolute** form
  (`from aioafero.device import ...`, `from aioafero.v1.models import ...`,
  etc.), which only resolves correctly when `aioafero` is genuinely
  installed as its own top-level package - never true here, since it's
  vendored under `custom_components.hubspace.aioafero`. Two failure modes,
  both confirmed live: (a) on any environment with **no** leftover
  `aioafero` PyPI package already installed, every one of these imports
  raises `ModuleNotFoundError: No module named 'aioafero'` and the whole
  integration fails to load; (b) on an environment that happens to have a
  **real, unpatched** `aioafero` installed already (e.g. a leftover
  dependency from the community `jdeath/Hubspace-Homeassistant` integration
  this repo replaces), those absolute imports silently resolve to that
  *external, unpatched* copy instead of this vendored one - the HA-side
  `HubspaceCoordinator` in the parent package still imports `EventType` etc.
  via its own correct relative import into *this* vendored tree, so the two
  ends of the same event stream ended up holding two distinct `EventType`
  enum classes; every `event_type == EventType.X` comparison in the
  coordinator silently evaluated `False`, `_last_seen` was never populated,
  and every entity showed `unavailable` forever despite the devices being
  online and controllable in the official Hubspace app. Rewrote every
  `from aioafero...` import in this tree to the correctly-scoped relative
  form (`from .`/`from ..`/`from ...` depending on file depth) so the
  vendored package is fully self-contained regardless of what else is
  installed in the Python environment. Verified by importing every module
  under a bare `custom_components.hubspace` package layout with only the
  three real runtime dependencies (`aiohttp`, `beautifulsoup4`,
  `securelogging`) installed - no other tests here caught this because
  `py_compile`/`ruff` check syntax, not whether imports actually resolve.

## Integration-support addition (not a reliability patch)

- **`v1/__init__.py`**: added `AferoBridgeV1.controllers_by_name`, a small
  read-only property returning initialized controllers keyed by their bridge
  attribute name (`"lights"`, `"fans"`, etc.). The generic HA platforms
  (`sensor.py`, `binary_sensor.py`, `number.py`, `select.py` in the parent
  `custom_components/hubspace/` package) need to walk every controller type
  without hardcoding the list and need the name back to re-fetch a live
  resource via `getattr(bridge, name)` on each update. Purely additive -
  does not change any existing method's behavior.

Everything else (the OAuth2/PKCE + scripted Keycloak login flow, the
`(functionClass, functionInstance)` state model, the command-echo
suppression in `v1/controllers/base.py`'s `update()`, the discovery/state
polling split, and the per-device-type controller/model architecture) is
unmodified from upstream and should be treated as correct - do not
re-implement it.
