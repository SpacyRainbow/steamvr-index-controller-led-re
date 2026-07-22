# 09 — LED Policy: Known States and Behaviors

This document summarizes what is known about the Index Controller's LED
*policy* — the rules governing which color/behavior is shown for which
device state — as distinct from the *mechanism* (`docs/07_led_architecture.md`)
that applies whatever color the policy decides on. For the detailed research
log of the (unsuccessful, as of this writing) attempt to locate the policy
decision code itself, see `docs/16_charging_led_research.md`.

## Observed states and colors

**Correction (see note below the table):** an earlier version of this
document, and several other documents in this repository, stated or
implied that blue was a color "the controller never normally shows" and
therefore a good target for a demonstration patch. **This was wrong** —
per the user's direct, first-hand knowledge of Index Controller behavior,
blue (solid and blinking) is a normal, existing LED state, used for
USB/host connection status and pairing. This is corrected throughout the
repository; see the correction note in `docs/14_failed_attempts.md`.

| State | Observed/reported color | How known | Confidence |
|---|---|---|---|
| Powered on, not charging (normal use) | Green | Direct visual observation by the human tester, multiple times across the project | 100% (visually confirmed, repeatedly) |
| Charging (connected to USB, battery below full) | Orange | Inferred from firmware log strings (`" PM -> charging\n"`, `"charge term"` etc. — see `docs/16_charging_led_research.md`) and general Index Controller knowledge; **not independently visually confirmed during this project's live testing** | 50% (consistent with general knowledge, not independently re-verified live in this project) |
| Charged / charge terminated (on charger, battery full) | White | The live `battery` debug shell command reported `state: charge term` while connected and at 100% charge; general knowledge holds this state displays white | 50% (state confirmed live via telemetry; the *color* not independently reconfirmed visually) |
| No connection to PC | Believed to be off, or a distinct idle state | Reported by the user from direct experience; not investigated in this project's firmware analysis yet | Unconfirmed by this project (user-reported) |
| Connecting to PC | Blue (solid, believed) | Reported by the user from direct experience | Unconfirmed by this project (user-reported) |
| Pairing mode | Blue, blinking | Reported by the user from direct experience | Unconfirmed by this project (user-reported) |
| Error / low battery (if distinct) | Possibly red — the user listed red among the "for sure" colors, but did not specify which state it maps to | Reported by the user from direct experience | Unconfirmed by this project (user-reported), state mapping unknown |
| Boot self-test | Multiple colors, cycling | Directly observed by the human tester immediately after two separate firmware flashes ("during the powerup, it did cycle through a few colors") | 100% (directly observed, twice) |
| Forced black (patched firmware) | Off | Directly observed by the human tester after applying the Layer-1 code patch (`docs/15_firmware_patching.md`) | 100% (directly observed) |

**The user has directly confirmed the full known color set is: green, red,
blue, white, orange** ("The for sure colors are green red blue white
orange"). This is the strongest available evidence on the *palette*, even
though several state-to-color mappings above remain unconfirmed by this
project's own instrumentation. Treat the "How known" / confidence columns
literally — several rows are user-reported knowledge, not something this
project's firmware analysis has independently traced or visually verified.

**Important caveat (unchanged from before):** the "orange = charging" and
"white = charged" mappings are carried over from general community/user
knowledge, not independently re-verified by direct observation within this
project. This project's own live testing confirmed the *existence* of
distinct charging-related device states via telemetry (the `battery`
command's `state:` field, and firmware log strings referencing
`"not charging"`, `"pre charging"`, `"fast charging"`, `"charge term"` —
four distinct textual states) but did not, within the time invested,
directly watch the physical LED transition through orange and white while
simultaneously confirming which telemetry state each color corresponded to.
**This is flagged as important follow-up verification work** — see
`docs/18_future_work.md`.

## Implication for the connection-state hypothesis (new, see `docs/16_charging_led_research.md`)

Blue being a real, existing state for PC/host connection and pairing is an
important clue for the open charging-LED research problem
(`docs/16_charging_led_research.md`): it means the firmware almost
certainly tracks a **connection-state** concept (no connection / connecting
/ paired) as something at least partly *separate* from the
**charging-state** concept (`docs/06_firmware_symbols.md` §6.5's `+0xc`
enum) this project has been tracing. The user's follow-up feature request
— disable the LED only while connected to SteamVR, revert to stock
behavior otherwise — targets this connection-state concept specifically,
which may be simpler to locate than the charging enum, since it is
plausibly closer to a binary condition (paired/tracking vs. not) than the
multi-way charging state machine. See `docs/16_charging_led_research.md`
"Connection-state hypothesis" for the investigation of this new angle.

## Known charging-related firmware states (from string evidence)

The decompressed firmware contains exactly four charging-state strings,
found via a full string search (`docs/16_charging_led_research.md` documents
the search):

```
"not charging"
"pre charging"
"fast charging"
"charge term"
```

These are almost certainly the human-readable labels for an internal
enumerated charging-state variable (a `uint8_t` or similar, read at struct
offset `+0xc` relative to a per-controller "PM" struct pointer — see the
disassembly excerpt in `docs/16_charging_led_research.md`). Whether this
same enumerated value is what the LED policy reads to decide color is
**plausible but not confirmed** — no code was found that reads this specific
field and also touches the LED call graph.

## Boot self-test

Both times the controller's firmware was replaced via the official update
tool and the device rebooted, the human tester observed the LED cycling
through multiple colors briefly before settling into a steady state. This
is strong independent evidence that the firmware's LED subsystem genuinely
supports multiple arbitrary colors (corroborating the driver-level evidence
in `docs/08_lp5562_driver.md`), and is presumed to be a factory/production
self-test routine exercising each LED channel — this is a reasonable
inference, not a confirmed fact (no code implementing this specific
sequence was located or disassembled).

One relevant data point: this boot color-cycle was still observed **after**
flashing a firmware build with `led_driver_current_*` values forced to `0`
(§ `docs/15_firmware_patching.md` Experiment 6/`indexcontroller_app_LEDTEST_v0.fw`).
This suggests the self-test sequence either uses a hardcoded brightness
level that bypasses the `led_driver_current_*` calibration values entirely,
or occurs early enough in boot that the patched config value hadn't yet been
applied when the self-test ran. Neither explanation was confirmed by
tracing the actual self-test code (its location was not found).

## The "glow" concept

The string `"glow not supported\n"` and several LED-setting entry points
that reference a "glow pattern ID" field (`docs/06_firmware_symbols.md`
§6.3, `0x41d6b4`) suggest the firmware architecture supports (or once
supported, on different hardware) fade/breathe/pulse animation patterns
distinct from a simple static color. On the test unit used in this project,
every code path that attempted to use a "glow" pattern printed
`"glow not supported"` and fell back to a plain static color set. This
strongly suggests glow/pattern support is either disabled by configuration
or genuinely unimplemented for this specific hardware/firmware combination.
Not further investigated.

## What is explicitly NOT known

- The exact code location that reads the charging-state enum and issues the
  corresponding LED color request (the central open question — see
  `docs/16_charging_led_research.md`).
- The exact 24-bit RGB(W) values used for "orange" and "white" states (no
  literal color constant matching plausible orange/white values was ever
  located in the firmware image, despite a targeted search — see
  `docs/14_failed_attempts.md`).
- Whether "ready" (green) is a true default/idle state, or itself the
  result of an explicit policy decision equivalent in structure to
  charging/charged.
- Whether pairing, low-battery, or error states have distinct LED behavior
  (no evidence gathered either way).
