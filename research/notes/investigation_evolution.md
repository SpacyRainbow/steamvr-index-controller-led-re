# How the Investigation Evolved

This document tracks the major shifts in understanding across the project,
in the format: what was originally believed, what evidence changed that
belief, what was discovered instead, and the updated conclusion. This is
deliberately separate from the polished `docs/` reference material, which
states current best understanding without necessarily showing its own
history.

---

## 1. Firmware extraction difficulty

**Originally believed:** firmware extraction might require hardware-level
techniques (voltage-glitching the nRF52840's APPROTECT flash-read
protection), based on general knowledge that embedded VR controller
firmware is sometimes protected. Background research was done on this
technique specifically to prepare for it ([`docs/02_background.md`](../../docs/02_background.md)).

**Evidence:** a plain `zlib.decompress()` call against the `.fw` files
found directly inside the SteamVR installation directory succeeded
immediately, with no protection encountered at all.

**Later discovery:** the firmware format has zero confidentiality
protection — only a data-integrity CRC, discovered much later
([`docs/05_firmware_layout.md`](../../docs/05_firmware_layout.md)), which protects against corruption during
flashing, not against reading.

**Updated conclusion:** the entire hardware-extraction contingency was
unnecessary. This freed essentially all of the project's time budget for
protocol/firmware analysis instead.

---

## 2. What the wired connection actually provides

**Originally believed:** uncertain whether the wired USB connection to the
controller was a full-featured HID link or a charge-only connection.

**Evidence:** a haptic-pulse command write succeeded
([`scripts/test_haptic_sanity_check.py`](../../scripts/test_haptic_sanity_check.py)), and subsequent full HID report
descriptor enumeration ([`scripts/dump_hid_descriptors.py`](../../scripts/dump_hid_descriptors.py)) found a rich set
of Input/Output/Feature reports across three interfaces.

**Updated conclusion:** the wired connection is a genuine, full-featured
USB HID link, making live protocol investigation viable without needing
wireless/dongle-based access.

---

## 3. The nature of the "Debug" interface

**Originally believed:** no specific expectation — this was discovered,
not hypothesized in advance. The closest prior expectation (from
`nairol/LighthouseRedox` precedent) was that undocumented functionality, if
any existed, would be reachable via extra command bytes on the *existing*
standard HID reports (a multiplexed command channel, analogous to Report ID
255 on the older Vive wand), not via an entirely separate, additional HID
interface.

**Evidence:** systematic `SET_FEATURE` testing of toggle-sized Feature
reports found that report `0x12` set to `0x01` causes the device to reset
and expose a genuinely new, 4th USB HID interface named "Debug."

**Updated conclusion:** the actual architecture is richer than the prior
LighthouseRedox-informed hypothesis — a dedicated debug/diagnostic
interface, not just extra command bytes on the normal channel. This
directly enabled everything from Experiment 2 onward
([`docs/13_experiments.md`](../../docs/13_experiments.md)).

---

## 4. Whether the debug shell can write config values

**Originally believed:** once the `config` command was found to display
live values including `led_driver_current_*`, it seemed likely a
corresponding write syntax (`config set ...` or similar) would exist,
mirroring how the shell's other commands (e.g. `set_gpio_level`) pair a
`get`/`set` form.

**Evidence:** every tried write syntax silently no-op'd, in clear behavioral
contrast to commands that genuinely validate arguments (`set_gpio_level`
correctly errors on bad input).

**Updated conclusion:** the plaintext shell is read-mostly for this
category of data; a different mechanism (ultimately, full firmware
flashing) was needed to actually write values. This is documented as a
confirmed dead end ([`docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md)) rather than an unresolved
question — the negative result itself was a useful, load-bearing finding
that redirected the project's approach.

---

## 5. The role of `led_driver_current_*`

**Originally believed:** these four values, being the only clearly
LED-named entries in the live config table, were assumed to be *the*
primary lever for controlling LED appearance — i.e., that patching them
would be sufficient to prove (or disprove) software LED control.

**Evidence:** patching them to `0` produced dramatic dimming but not full
black; patching to `255` produced no clearly perceptible change at all.
Both results were genuine, confirmed effects (the values were verified to
have actually changed via live readback), just not the complete story.

**Later discovery:** deeper static analysis of the LED write pipeline
([`docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md) §6.3, [`docs/07_led_architecture.md`](../../docs/07_led_architecture.md) Layer 1)
revealed these values are a *multiplicative calibration/scaling* stage
applied to an already-determined base color, not the sole determinant of
output. The actual base color is set elsewhere in the pipeline (and, for
policy-determined states like "charging," by code not yet located — see
item 7 below).

**Updated conclusion:** `led_driver_current_*` is real and useful (proven
effective), but the project's strongest, most unambiguous result required
patching the color-computation pipeline directly ([`docs/13_experiments.md`](../../docs/13_experiments.md)
Experiment 7), not just the calibration values. This distinction — between
"a value that affects LED output" and "the value that determines LED
output" — became a central organizing idea for the rest of the
investigation.

---

## 6. Confidence in manual disassembly vs. the need for proper tooling

**Originally believed:** early LED-pipeline tracing was done via manual
capstone-based linear disassembly ([`scripts/disasm_config.py`](../../scripts/disasm_config.py)), and
initial findings (including a specific "indirect call / vtable" pattern)
were trusted at face value.

**Evidence:** once a full Ghidra installation was set up
([`tools/ghidra_setup.md`](../../tools/ghidra_setup.md)) and used to properly decompile the same region,
it revealed that the earlier "vtable" pattern had been **misattributed to
the wrong function** — a genuine function-boundary error from manual
linear scanning, not a wrong interpretation of correct data.

**Updated conclusion:** manual disassembly without independently-verified
function boundaries is meaningfully error-prone for this firmware's dense,
VFP-heavy code style, in a way that cost real investigation time before
being caught. This is documented explicitly as a methodological lesson
([`docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md)), and the recommendation for any future work
on this codebase is to prefer Ghidra (or equivalent) over manual scanning
for anything beyond small, well-isolated code snippets.

---

## 7. What "finding the LED policy" actually requires

**Originally believed (going into the follow-up "selective patch"
request):** assumed this was primarily a call-graph tracing problem —
"find who calls the color-setting function with the 'charging' color" —
solvable with the same techniques (Ghidra reference analysis, brute-force
call-site search) that had successfully resolved every earlier question in
the project.

**Evidence:** all three independent, individually-reliable call-graph
search techniques (Ghidra's reference manager, an exhaustive brute-force
scan of every possible direct-call instruction encoding, and a raw
stored-pointer search) consistently found **zero** callers of the relevant
Layer-3 functions. Separately, tracing forward from the power-management
task's own charging-state-transition code showed it does not call into the
LED subsystem at all.

**Updated conclusion:** the connection is very likely not a direct call at
all, but a shared-state relationship across an RTOS task boundary (one
task writes a status variable, a different task reads it independently) —
a structurally different, and generally harder, class of reverse-
engineering problem than everything solved earlier in the project. This
reframing is the project's current stopping point and is documented in
full in [`docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md), with the corresponding
retargeted recommendations (live USB capture, data-flow analysis rather
than call-graph search) in [`docs/18_future_work.md`](../../docs/18_future_work.md).

---

## Summary: what this evolution shows

The investigation's early phases (extraction, HID discovery, protocol
reverse engineering, footer-CRC reverse engineering, the first successful
patch) each followed a pattern of "form a hypothesis, test it directly
against real hardware or real firmware bytes, get a clear answer, move
on" — and that pattern worked repeatedly and well. The final open question
(selective, charging-aware LED control) is qualitatively different: the
evidence gathered so far does not point at a specific, findable piece of
code, but at an architectural boundary (RTOS task/shared-state) that this
project's available techniques were not equipped to cross. Recognizing that
distinction — rather than continuing to apply the same call-graph-tracing
techniques indefinitely — is itself one of this project's findings, not
just a limitation.
