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

### Live empirical test: connecting to real SteamVR does not visibly change the LED

The SteamVR-launch attempt documented as blocked in
[`docs/14_failed_attempts.md`](14_failed_attempts.md) ("Launching SteamVR to empirically observe
connection-state behavior") was retried in a later session with the human
tester physically present to click through the one-time privilege dialog.
This time SteamVR reached the controller: `vrserver`'s log
(`~/.local/share/Steam/logs/vrserver.txt`) shows `lighthouse: Attempting
HID Open VrController: LHR-XXXXXXXX` followed by `lighthouse: Lighthouse
VrController HID opened` — a real, confirmed connection event, not a
stalled attempt.

**Result:** the human tester visually confirmed the LED remained **solid
green — no visible change** at the moment of connection, or in the
following minutes with SteamVR still connected. The debug shell's `power
get` (`PM: level 0`) and `battery`/`usb:` telemetry also showed no change
from the documented baseline values in [`docs/11_hid_commands.md`](11_hid_commands.md), for
whatever that's worth given those specific fields were never confirmed to
be sensitive to this event in the first place.

**Why this matters:** it directly narrows the premise behind the
"disable LED while connected to SteamVR" feature request that motivated
this whole research thread. The controller's LED apparently does **not**
carry a distinct "connected to SteamVR" visual state at all — green here
represents the same "normal operation" state whether or not SteamVR
happens to be attached. That's consistent with (but doesn't prove) the
idea that connection-status LED behavior (blue, per the corrected
palette) is specific to *pairing/enumeration* moments rather than an
ongoing "is SteamVR currently using this controller" indicator — i.e., a
selective patch keyed on "connected to SteamVR" may not correspond to any
existing firmware-side condition at all, and might need to be
**introduced** (e.g., patching in a genuinely new check against some
already-located connection-status field) rather than **located** as an
existing behavior to selectively suppress.

**Not yet tried:** a longer observation window (this was checked shortly
after connection, not across a full VR session with headset/room-setup
interaction, which this test machine cannot currently do without a
headset), and comparing against the *disconnection* half of the same
event (unplugging while SteamVR still expects the controller). Both
remain open if a future session wants to chase this specific angle
further; see [`docs/18_future_work.md`](18_future_work.md).

## Multi-tool sweep session: a reader of `+0xc` found, and a concrete dispatch-mechanism hypothesis

Prompted by a deliberate step back to ask "what other tools would a mature
RE project already have tried" (independent of any specific new lead), this
session ran the same open question — what connects the PM struct's state
enum to a consumer like the LED policy — through several tools never
previously used in this project: **angr** (CFG recovery + literal-pool/
call-graph analysis), **Unicorn Engine** (direct emulation of one function,
to empirically verify a static reading rather than trust it by eye), and
**radare2** revisited on this firmware with a narrower technique than its
earlier, largely-abandoned attempt ([`tools/radare2_setup.md`](../tools/radare2_setup.md)), plus a
lightweight DIY version-diff across this project's own locally-held
firmware builds. IDA Free and Binary Ninja were deliberately not attempted
— both require creating a vendor account through a login-gated download,
which isn't appropriate to do on the user's behalf without them present;
they remain valid untried options for a future session.

### A reader of `+0xc` — the field previously documented as having none

A wider literal-pool scan (raw 4-byte little-endian search for the struct
base address across the *entire* offset range `+0x0`..`+0x2f`, not just
`+0x0` as the original Ghidra-era search checked) found 5 reference sites
the earlier investigation had missed: four more `+0x0` (base-pointer)
references at `0x422fa8`, `0x423078`, `0x423160`, `0x423218`, and one
reference to `+0x2c` specifically at `0x4376d4`. This is itself a small
methodological finding worth naming: the original raw-byte search
([`research/decompiler_notes/07_pm_reference_investigation.java`](../research/decompiler_notes/07_pm_reference_investigation.java)) was
narrower than it looked — it searched for the base pointer only, at a
fixed list of addresses, not a systematic scan of the full plausible
offset range. A systematic scan found more.

The site at `0x423218` sits immediately after a `strb r0, [r4, #0xc]` —
a **write to the state enum** — inside a function angr's CFG recovery
resolves to `sub_422f21` (entry `0x422f21`). Full disassembly of that
function shows:

```
push {r4, lr}
ldr  r4, [pc, #imm]        ; r4 = &PM_struct (0x2000378c)
ldr  r0, [r4, #0xc]        ; r0 = state enum
cbz  r0, do_first_call
cmp  r0, #1
beq  do_first_call
cmp  r0, #2
bne  skip_first_call
do_first_call:
  movs r0, #1
  bl   0x43c055             ; builds a small tagged stack buffer, calls 0x41f56d
skip_first_call:
ldr  r0, [r4, #0xc]        ; re-read state enum
cbz  r0, do_transition
cmp  r0, #1
beq  do_transition
cmp  r0, #2
beq  do_transition
cmp  r0, #5
bne  early_exit             ; state not in {0,1,2,5}: nothing happens
do_transition:
  <build/log strings via 0x42ce91/0x42ce7b>
  movs r0, #3
  str  r0, [r4, #0xc]       ; STATE TRANSITION: write 3
  bl   0x43c249
  bl   0x43c079
  bl   0x43ac89              ; branches further calls on r0 (return value)
  ... (conditional call sequences)
  bl   0x43ad05
  bl   0x415649
  bl   0x415621
  pop.w {r4, lr}
  b.w  0x4156e9               ; tail-call: builds ANOTHER tagged buffer
                               ; (opcode 0x53), calls 0x4153e5
early_exit:
  pop {r4, pc}
```

This is the first time this project has located code that both *reads*
and *acts on* the PM state enum with real branching semantics — states
`{0, 1, 2, 5}` reach the transition path (which sets the enum to `3` and
is therefore an idempotent "already transitioned" guard against re-firing:
once the state is `3`, a later call to this same function takes the
early-exit path), while `{3, 4, 6, ...}` do nothing.

**Empirically verified, not just read by eye:** a Unicorn Engine harness
([`research/decompiler_notes/13_unicorn_state_handler_sweep.py`](../research/decompiler_notes/13_unicorn_state_handler_sweep.py)) loaded
the real firmware bytes, statically NOP-patched out every `bl` inside this
function's body (so only its own branching logic executes, without
needing to emulate everything it calls), and swept the initial value of
`+0xc` from 0 to 7. Result matched the disassembly reading exactly for
every value: `{0, 1, 2, 5}` → struct`+0xc` written to `3`, execution
reaches the `0x4156e8` tail; `{3, 4, 6, 7}` → early exit, no write. This
is the first empirical (executed, not just statically reasoned about)
confirmation obtained in this project without real hardware.

### A concrete hypothesis for *why* no direct caller has ever been found: message/event dispatch, not function calls

The two functions `sub_422f21` calls into when it takes a "real" branch
(`0x43c055`/`0x43c079` on the first check, and the `0x4156e8` tail on the
second) share a distinctive pattern: each builds a small buffer on the
stack, writes a specific one- or two-byte "opcode" into it (`0x40`, `0x2`,
`0x53` observed so far), sets a small length, and calls a small number of
shared functions (`0x41f56d`, `0x4153e5`) to do something with it. This is
the classic shape of a **typed message or event post** — "opcode + payload,
handed to a generic dispatcher" — not a direct function call to a specific
handler.

**This would explain, architecturally, why every static call-graph
technique tried in this project — Ghidra's reference manager, the
project's own exhaustive `BL`-encoding search, a raw stored-pointer search,
angr's CFG recovery, and (this session) radare2's independent analyzer —
has found zero direct callers for the LED Layer-3 functions.** If LED
updates are driven by a dispatched message read by a separate
handler/task, rather than a direct call, there is no direct call for any
of these techniques to find — the absence isn't a tooling gap, it's
consistent with the actual mechanism being something else entirely. Four
independent tools now agree on the negative result (see "Methods attempted
to find Layer 3's callers, and why each failed" above), which upgrades
this from "one tool's blind spot" to "this
firmware genuinely does not connect these functions via a direct call,
under any technique tried."

**This is a hypothesis, not a confirmed finding.** It has not been proven
that the LED subsystem is on the *receiving* end of this specific dispatch
mechanism — only that the PM state-transition code demonstrably uses
*some* form of tagged message dispatch for at least some of its own
side effects. Finding and decoding what `0x41f56d`/`0x4153e5` actually do
with the opcode (a jump table? a linked list of registered handlers? a
fixed RTOS message queue post?) is the concrete next step — see
[`docs/18_future_work.md`](18_future_work.md), which has been updated to reflect this as the new
top-priority approach for this research thread, ahead of the "map the
whole shared struct" recommendation from the previous session.

### radare2, revisited with a narrower technique

`radare2` was tried on this exact firmware early in the project and
largely abandoned for it — `aaa` (radare2's blanket whole-binary
auto-analysis) produced sparse, low-confidence function boundaries and
missed cross-references later confirmed to exist once Ghidra was set up
([`tools/radare2_setup.md`](../tools/radare2_setup.md), "Known limitation encountered"). This
session revisited it with a narrower technique instead of retrying `aaa`
wholesale: explicitly defining only the functions of interest (`af @
<addr>`) and using radare2's direct reference-search command (`/r
<addr>`, which scans for actual call/reference encodings to a specific
target rather than relying on `aaa`'s general auto-analysis to have
already built a complete xref database). This targeted approach worked
cleanly this time — a `pdf` sanity check against the known LED wrapper
function matched Ghidra's disassembly exactly, including the same string
reference (`led_driver_lp5562.c`).

With that confidence, `/r` was run against the three LED Layer-3 function
addresses and the PM struct base address, and found **zero references**
to any of them — corroborating, via a completely different codebase and
analysis approach than either Ghidra or angr, the same negative result.
Four independent techniques (Ghidra, this project's own `BL`-search, angr,
radare2) now agree. `/r` did surface one small, unchased lead: a call to
the LED "off-path function" (`0x41e7d8`) from `0x41da32`, inside the same
Ghidra-unbounded gap region that contains the Layer-3 functions themselves
— not investigated further this session (see [`docs/18_future_work.md`](18_future_work.md)).

### Version-diff sanity check across this project's own local firmware builds

Rather than install Diaphora or BinDiff (heavier tools, not worth the setup
risk for a single targeted check), a small Python script compared the raw
bytes of `sub_422f21`'s opcode signature (`ldr r0, [r4, #0xc]; cbz r0,
...`) and the PM struct's literal-pool footprint across every firmware
build already held locally by this project
([`hashes/firmware_hashes.txt`](../hashes/firmware_hashes.txt)):

- The **`ev` variant (2023-10-13)** — a completely separate build from the
  primary 2023-09-02 analysis target — contains the *exact same* struct
  base address (`0x2000378c`), the *exact same* 18 literal-pool reference
  offsets, and `sub_422f21`'s opcode signature at the *identical* file
  offset. This is a genuine cross-build confirmation that the finding
  isn't an artifact specific to one single firmware file.
- Both **2019-era builds** (`20190621`, `20190712`) do **not** contain the
  literal `0x2000378c` (expected — a much older build almost certainly has
  a different RAM layout), but **do** contain the same `ldr r0, [r4,
  #0xc]; cbz` opcode signature once each, at their own (different)
  offsets — suggesting this state-handling function, or something
  structurally identical to it, has existed in this firmware's codebase
  for at least the ~4 years spanning these builds. Not traced further
  (would require redoing the base-address/struct-offset analysis
  per-build) — noted as a future-work item, not chased this session.

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
the most promising next actions, updated after the multi-tool sweep
session above:

1. **Decode the message/event dispatch mechanism** — now the top
   recommendation, superseding the more general "understand the generic
   dispatch mechanism" framing from the earlier session. This session
   narrowed it from a vague hypothesis to concrete targets: `0x41f56d` and
   `0x4153e5`, called with small tagged stack buffers (opcodes observed so
   far: `0x40`, `0x2`, `0x53`) by `sub_422f21`'s state-transition path.
   Tracing what these two functions do with their opcode argument (a jump
   table indexed by opcode? a linked list of registered handlers? a
   fixed-size RTOS message queue post?) is now the single most direct
   remaining path — if the LED subsystem is also invoked through this same
   mechanism (unconfirmed), finding the dispatch table would likely reveal
   it directly, the same way `sub_422f21`'s own struct-literal reference
   revealed the state handler.
2. **Live USB traffic capture** during an actual charging-state transition
   on the real device (requires either a hardware USB tap or `usbmon` on
   the host — the project's environment had host-level `usbmon` available
   in principle but this was not exercised). A capture spanning a real
   plug-in/charge-termination event, correlated with the physical LED
   color, would let the researcher work backward from confirmed telemetry
   rather than forward from an incomplete static trace.
3. **Hardware SWD debugging**, if hardware modification becomes an option
   in a future session: the nRF52840 exposes SWD, and OpenOCD/a debug
   probe would allow a hardware watchpoint directly on
   `0x2000378c`+`0xc`, which would show — with certainty, live, on real
   hardware — every piece of code that touches it, sidestepping static
   analysis (and its shared blind spot around indirect/dispatched calls)
   entirely. Not pursued this session (hardware modification explicitly
   off the table for now), but this remains the most direct way to close
   this question if it ever becomes available.
4. **Data-flow analysis in Ghidra** starting from the power-management
   struct's now-known base address (`0x2000378c`) and the field offsets
   identified in the follow-up session above (`+0xc`, `+0xd`, `+0x15`,
   `+0x16`, `+0x24`, `+0x28`) — a raw-address search (as done for
   `0x2000378c` itself) is a cheap first pass; true data-flow/value-set
   analysis through Ghidra's P-code APIs is the more thorough follow-up if
   the raw search doesn't find the reader directly.
5. **A second-opinion decompiler** (IDA Free or Binary Ninja) on
   `0x41f56d`/`0x4153e5` specifically — not attempted this session since
   both require a login-gated vendor download not appropriate to do
   autonomously, but worth trying if a human is available to install one:
   a different decompiler's own struct/switch-table inference sometimes
   resolves exactly the kind of indirect dispatch this project keeps
   running into.
