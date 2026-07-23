# 16 — Charging-Aware Selective LED Patch: Open Research

**Status: open, unresolved as of this writing.** This document is the
detailed research log for the project's one substantial unresolved
question. It is written to let another engineer resume exactly where this
investigation stopped, without repeating the (considerable) work already
done.

## The goal

Produce a firmware patch that blanks the LED during normal
("ready"/actively-used) operation, while **preserving** the existing
charging (orange) and charged (white) status indication. This is a
refinement of the already-proven "always off" patch
([`docs/15_firmware_patching.md`](15_firmware_patching.md) Patch B, [`docs/13_experiments.md`](13_experiments.md)
Experiment 7), which is too blunt for this purpose since it disables the
LED unconditionally, including while charging.

## Why this is a fundamentally harder problem than the "always off" patch

The "always off" patch works because it targets a genuine choke point: one
low-level function through which every color request passes
([`docs/07_led_architecture.md`](07_led_architecture.md) Layer 1). A selective patch cannot target
that same choke point with a simple unconditional change — it needs the
patch to distinguish *which* state is requesting the color, which requires
locating the code that makes that distinction in the first place. That code
was not found. This section documents the trace, layer by layer, and
exactly where it stops.

## What was successfully traced (high confidence)

See [`docs/07_led_architecture.md`](07_led_architecture.md) and [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3
for full detail; summarized here:

- **Layer 1** (`0x41dbf0`, `0x419250`, `0x4232c4`): the hardware write
  pipeline. Fully understood, live-verified via the successful patch.
- **Layer 2** (`0x41d7ac`): the color-request wrapper. Cleanly decompiled
  with Ghidra; logic fully understood (checks a "was off" flag, applies the
  caller's requested color unconditionally).
- **Layer 3** (three functions in an unbounded code region spanning
  roughly `0x41d859`–`0x41dac4`): three direct callers of the Layer 2
  wrapper, found via Ghidra's reference manager once the correct function
  entry point (`0x41d7ac`, not the initially-assumed `0x41d7a8` — see
  [`docs/14_failed_attempts.md`](14_failed_attempts.md)) was identified. Two of these
  (`0x41d6fa`, `0x41d938`) read a color value from a caller-supplied struct
  field rather than a literal; the third (`0x41da90`) always passes a
  literal `color = 0`.

**The trace stops at Layer 3 → Layer 4**: no caller of any Layer 3 function
was found by any method attempted (see below), meaning the code that
actually decides *which* color value to put in that struct field for
*which* device state was not located.

## Methods attempted to find Layer 3's callers, and why each failed

All of the following were tried, in this order, against the same target
(finding what calls `0x41d6fa`, `0x41d938`, and `0x41da90`):

1. **Ghidra reference manager query** (`getReferencesTo`) — returned zero
   results for all three addresses.
2. **Exhaustive brute-force `BL`-instruction-encoding search** — computed
   the exact Thumb-2 `BL` instruction encoding for a call from every
   possible 2-byte-aligned address in the firmware to each target address,
   and searched for those exact bytes directly (bypassing disassembly
   entirely, so mis-alignment cannot hide a match). Zero results.
3. **Raw absolute-pointer search** — searched for the target addresses
   (with and without the Thumb bit set) stored anywhere as a literal 4-byte
   value, on the theory that they might be invoked via a function-pointer
   table rather than a direct call. Zero results. (See
   [`docs/14_failed_attempts.md`](14_failed_attempts.md) for the related, separately-documented
   "ownership tag" dead end encountered while investigating structures
   *inside* this Layer 3 region.)

All three methods are individually reliable (methods 1 and 2 in particular
leave essentially no room for a false negative from tooling limitations —
method 2 does not depend on Ghidra's analysis quality at all). Their
consistent failure is itself meaningful evidence, not merely "we didn't
look hard enough": **Layer 3's functions are not invoked via any
statically-discoverable mechanism this project could enumerate.**

Plausible explanations, none confirmed:
- They are genuinely unreachable/dead code in this specific firmware build
  (e.g., leftover from a different product variant or an earlier design
  that used per-LED struct-based dispatch, since superseded).
- They are invoked from a part of the firmware image not analyzed at all
  in this project (e.g., interrupt vector table entries set up via a
  mechanism distinct from ordinary function calls, or code reached only via
  runtime-computed addresses this project's static techniques cannot
  resolve without symbolic execution).
- They are invoked from outside the application firmware image entirely
  (e.g., from the bootloader or FPGA-adjacent code, which were not
  analyzed in this project at all — see [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.5
  "What is NOT yet mapped").

## The power-management task lead

A different approach was tried: instead of tracing *up* from the LED code,
search *down* from the known charging-state semantics. The decompressed
firmware contains firmware log strings unambiguously belonging to a
power-management state machine:

```
" PM -> charging\n"
"PM: charging from USB host; tracking on\n"
"PM: charging from USB adapter; tracking off\n"
"PM: charging -> on\n"
" PM: on, charging, or standby -> sleep\n"
"not charging"
"pre charging"
"fast charging"
"charge term"
```

The code region containing these strings (another large, Ghidra-unbounded
gap, manually read in full — preserved in
[`research/decompiler_notes/pm_gap_listing.txt`](../research/decompiler_notes/pm_gap_listing.txt)) was read line by line.
**Finding: this code does not call any function in the traced LED call
graph.** It calls a distinct set of functions (`0x43c054`, `0x430900`,
`0x42f0e0`, `0x43124c`, `0x42fa6c`, `0x415648`, `0x415620`, `0x4156e8`, and
others) none of which match any address identified in
[`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3.

**Interpretation:** this is consistent with an RTOS architecture where the
power-management task updates a piece of **shared state** (a struct field,
global variable, or message-queue post) that a *separate* task — reads
independently, rather than the power-management code directly calling into
LED-setting functions. The live `tasks` debug shell command
([`docs/11_hid_commands.md`](11_hid_commands.md)) lists a task named `vrc` among twelve RTOS
tasks, which is a reasonable candidate for "the task that owns LED policy
decisions," by analogy with `vrc` also being the name used elsewhere in the
config table ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.2, entry index 0) — but this
is **not confirmed**; no `vrc`-task code was specifically identified or
disassembled.

**This reframes the remaining problem**: it is not "find one more function
call," it is "find a shared memory location written by the power-management
code and read by whatever code actually applies LED colors" — a
structurally different and generally harder class of reverse-engineering
task than call-graph tracing, since it requires either data-flow analysis
across the entire compiled unit or runtime observation (e.g., a debugger or
memory-watch capability this project did not have access to).

## Follow-up session: locating the PM struct and its readers (partial progress, connection still not found)

A later session (with live hardware still connected but no ability to
visually observe the controller — see [`docs/13_experiments.md`](13_experiments.md)) picked
this up using the data-flow approach recommended above. Concrete new
findings, none of which close the open question, but all narrowing the
search space for whoever continues this work:

**The PM state struct's exact RAM address was found: `0x2000378c`.** All
four of the power-management functions identified in the previous section
load this same address as their struct base pointer (confirmed via a
Ghidra script reading each function's literal pool operand directly). This
is a concrete, reusable fact — previously only the *offsets within* the
struct (`+0xc` for the main state enum) were known, not its absolute
location.

**A raw search for every other reference to `0x2000378c` in the firmware
image found 14 additional locations** beyond the four already known (a
plain 4-byte little-endian pattern search, not dependent on any
disassembly). This is a stronger technique than searching for a function's
own address, because a data address referenced by an unrelated reader
function will have its own, independent literal pool entry pointing at the
same struct, unaffected by whatever indirect-dispatch mechanism is hiding
the reader function's *own* callers.

Investigating these 14 locations found:

- **New struct field offsets in use**: `+0x28` (a byte, checked as a
  boolean-like condition), `+0x15` and `+0x16` (two separate byte flags,
  each set to `1` from different, unrelated call sites — not the same
  code that writes `+0xc`), and `+0x24` (read and multiplied by 1000,
  suggesting a duration in seconds converted to milliseconds).
- **A lead that looked very promising and turned out to be a false trail**:
  code reading `+0x24` calls two functions, `0x414dbc` and `0x414e38`,
  which are the *exact same two functions* the LED subsystem's
  `FUN_0041d6b4` ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3) calls when applying a
  "glow" pattern. Decompiling both fully (Ghidra) resolved this: they are
  general-purpose software-timer registration/cancellation primitives
  (source file `tick_handler.c`, confirmed via an embedded assert string),
  each with 19–20 unrelated callers spanning the entire firmware. The LED
  subsystem uses them to schedule glow-animation timer ticks; the
  power-management code uses them for something else entirely (most likely
  an unrelated timeout). This is a real, understood dead end — see
  [`docs/14_failed_attempts.md`](14_failed_attempts.md).
- **The same "zero direct callers" symptom recurs** for the new
  `+0x28`-checking and `+0x15`/`+0x16`-writing functions, using the exact
  same three independent search methods that failed for the LED Layer-3
  functions (Ghidra reference manager, raw stored-pointer search, and an
  exhaustive direct-call-encoding search — the last of which required a
  bug fix mid-investigation, see below). **This generalizes the earlier
  finding**: it is not that the LED policy specifically is hidden behind
  some LED-only indirect-dispatch mechanism — multiple, unrelated
  subsystems (LED state application *and* power-management flag setters)
  exhibit the identical symptom. This suggests a firmware-wide, generic
  dispatch architecture (plausibly a table-driven state-machine or event
  framework used throughout this RTOS firmware) is the actual thing
  standing in the way, not something specific to LED policy. Understanding
  *that* generic mechanism, once, would likely unlock this question and
  probably others — see [`docs/18_future_work.md`](18_future_work.md).

**A tooling bug was found and fixed during this session.** The
brute-force direct-call-encoding search ([`scripts/find_bl_callers.py`](../scripts/find_bl_callers.py),
previously used only as an uncommitted inline script) had a bit-shift
error that could, for certain offset magnitudes, alias two different call
targets onto the same encoded instruction bytes — producing an occasional
false-positive "caller." This was caught when a result for the `+0x28`
checker function was manually cross-checked with `capstone` and found to
actually be a call to a different, unrelated address. **The bug was fixed,
and the tool was re-run against the previously-documented "zero callers"
findings for the LED Layer-3 functions (`0x41d6fa`, `0x41d938`,
`0x41da90`) — the result did not change; those functions still have zero
findable direct callers.** The central conclusion of this document is
therefore unaffected. See the bug-history note in
[`scripts/find_bl_callers.py`](../scripts/find_bl_callers.py)'s module docstring for full detail, and
[`docs/14_failed_attempts.md`](14_failed_attempts.md) for why this is preserved rather than quietly
fixed and forgotten.

**Status after this session: still open.** No selective (charging-aware)
patch was produced or could be produced — the connection between
power-management state and LED color remains unlocated, so there is
nothing yet to conditionally branch on. This session's value is in the new
concrete facts above (struct address, field offsets, one ruled-out lead,
one corrected tool) and the reframed hypothesis (a generic dispatch
mechanism, not an LED-specific one) — not in a working patch.

## Connection-state hypothesis (new angle, also inconclusive)

Prompted by the user's observation that blue is a real, existing state for
USB/host-connection and pairing status (correcting an earlier wrong
assumption — see [`docs/14_failed_attempts.md`](14_failed_attempts.md)), and the follow-up request
to explore disabling the LED specifically while connected to SteamVR
(reverting to stock behavior otherwise), a third investigative thread was
opened: is a "connected to host" condition more tractable to locate than
the charging enum?

**What was tried:** the live `battery` debug shell command's `usb:` status
line (`enumerated: yes, power good: yes`) was traced back to its source
strings in the firmware, which — consistent with the recurring pattern
above — had no findable code references via Ghidra's reference manager,
and sat in another large Ghidra-unbounded code region. A separate,
initially promising lead (a "pairing" string match) turned out to be part
of the config key name `pairing_button_press_ms`, not pairing-state LED
logic, and traced to a one-time boot-time mode-announcement function
(prints `"Mode: CONTROLLER"` vs. a lab/test-mode string) — not a live
connection-state tracker.

**What was found:** that mode-announcement function's struct base pointer,
`0x20003878`, is only 20 bytes away from the already-known PM struct base
(`0x2000378c`, §6.5 above). Searching for other references to
`0x20003878` found one very large, complex function (`0x43c1a4`) that
touches struct offsets well beyond `+0x1000` — far larger than a small,
dedicated struct. **This strongly suggests the PM/charging struct and the
mode/pairing struct are not actually separate structures, but different
offsets within one large, shared device-state block** spanning multiple
kilobytes, likely encompassing many subsystems' state (battery, USB,
pairing, and plausibly LED policy) together.

**Status:** this reframes the problem again, but does not solve it.
Properly mapping a structure of this size (identifying which of its many
offsets correspond to which subsystem, and specifically which one the LED
policy reads) is a substantially larger undertaking than anything
attempted so far in this project, and was not completed in this session.
This is recorded as a genuine, promising new lead rather than a dead end
— see [`docs/18_future_work.md`](18_future_work.md) for the specific recommended next step.

## Tooling used, and what it does/doesn't help with

A full headless Ghidra 12.1.2 installation was set up specifically to
support this investigation ([`tools/ghidra_setup.md`](../tools/ghidra_setup.md)), including automated
full-program analysis (function detection, ARM constant-reference
resolution, address-table/switch detection) and scripted decompilation via
custom Java `GhidraScript`s (preserved in `research/decompiler_notes/`).
This was a substantial and successful improvement over the manual
capstone-based disassembly used earlier in the project (it directly
resolved several open questions and caught the Layer-2 function-boundary
mistake described in [`docs/14_failed_attempts.md`](14_failed_attempts.md)) — but it does **not**,
in its default configuration, resolve either the Layer 3 caller mystery or
the RTOS shared-state connection. Both would likely benefit from:

- A dedicated data-flow / value-set analysis pass (Ghidra supports this via
  its P-code analysis APIs, not exercised in this project).
- Manual or semi-automated symbolic execution of the unbounded code
  regions, to determine whether they are truly unreachable or merely
  unreachable *by the specific static techniques already tried*.
- Live memory inspection of the running device (not available without
  additional hardware — e.g., an SWD/JTAG debug probe connected to the
  nRF52840, which was not available or used in this project).

## Current recommendation

See [`docs/18_future_work.md`](18_future_work.md) for the prioritized next steps. In summary,
the most promising next actions:

1. **Live USB traffic capture** during an actual charging-state transition
   on the real device (requires either a hardware USB tap or `usbmon` on
   the host — the project's environment had host-level `usbmon` available
   in principle but this was not exercised). A capture spanning a real
   plug-in/charge-termination event, correlated with the physical LED
   color, would let the researcher work backward from confirmed telemetry
   rather than forward from an incomplete static trace.
2. **Understand the generic dispatch mechanism directly**, rather than
   continuing to chase individual LED- or PM-specific leads. The follow-up
   session above found that *multiple, unrelated* subsystems (LED state
   application, power-management flag setters) share the identical
   "invoked with zero statically-findable direct callers" symptom. This
   strongly suggests one shared, firmware-wide dispatch/event framework is
   responsible, not something specific to either subsystem. Finding and
   understanding *that* mechanism once — most likely by picking one of its
   simplest-looking victims and tracing every reference to *it*, or by
   searching for whatever data structure such a framework would need
   (a table of {condition, handler} pairs, a priority queue, or similar) —
   would likely unlock this question and any other question with the same
   symptom, rather than requiring a fresh investigation per function.
3. **Data-flow analysis in Ghidra** starting from the power-management
   struct's now-known base address (`0x2000378c`) and the field offsets
   identified in the follow-up session above (`+0xc`, `+0xd`, `+0x15`,
   `+0x16`, `+0x24`, `+0x28`) — a raw-address search (as done for
   `0x2000378c` itself) is a cheap first pass; true data-flow/value-set
   analysis through Ghidra's P-code APIs is the more thorough follow-up if
   the raw search doesn't find the reader directly.
