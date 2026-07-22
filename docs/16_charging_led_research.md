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
(`docs/15_firmware_patching.md` Patch B, `docs/13_experiments.md`
Experiment 7), which is too blunt for this purpose since it disables the
LED unconditionally, including while charging.

## Why this is a fundamentally harder problem than the "always off" patch

The "always off" patch works because it targets a genuine choke point: one
low-level function through which every color request passes
(`docs/07_led_architecture.md` Layer 1). A selective patch cannot target
that same choke point with a simple unconditional change — it needs the
patch to distinguish *which* state is requesting the color, which requires
locating the code that makes that distinction in the first place. That code
was not found. This section documents the trace, layer by layer, and
exactly where it stops.

## What was successfully traced (high confidence)

See `docs/07_led_architecture.md` and `docs/06_firmware_symbols.md` §6.3
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
  `docs/14_failed_attempts.md`) was identified. Two of these
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
   `docs/14_failed_attempts.md` for the related, separately-documented
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
  analyzed in this project at all — see `docs/06_firmware_symbols.md` §6.5
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
`research/decompiler_notes/pm_gap_listing.txt`) was read line by line.
**Finding: this code does not call any function in the traced LED call
graph.** It calls a distinct set of functions (`0x43c054`, `0x430900`,
`0x42f0e0`, `0x43124c`, `0x42fa6c`, `0x415648`, `0x415620`, `0x4156e8`, and
others) none of which match any address identified in
`docs/06_firmware_symbols.md` §6.3.

**Interpretation:** this is consistent with an RTOS architecture where the
power-management task updates a piece of **shared state** (a struct field,
global variable, or message-queue post) that a *separate* task — reads
independently, rather than the power-management code directly calling into
LED-setting functions. The live `tasks` debug shell command
(`docs/11_hid_commands.md`) lists a task named `vrc` among twelve RTOS
tasks, which is a reasonable candidate for "the task that owns LED policy
decisions," by analogy with `vrc` also being the name used elsewhere in the
config table (`docs/06_firmware_symbols.md` §6.2, entry index 0) — but this
is **not confirmed**; no `vrc`-task code was specifically identified or
disassembled.

**This reframes the remaining problem**: it is not "find one more function
call," it is "find a shared memory location written by the power-management
code and read by whatever code actually applies LED colors" — a
structurally different and generally harder class of reverse-engineering
task than call-graph tracing, since it requires either data-flow analysis
across the entire compiled unit or runtime observation (e.g., a debugger or
memory-watch capability this project did not have access to).

## Tooling used, and what it does/doesn't help with

A full headless Ghidra 12.1.2 installation was set up specifically to
support this investigation (`tools/ghidra_setup.md`), including automated
full-program analysis (function detection, ARM constant-reference
resolution, address-table/switch detection) and scripted decompilation via
custom Java `GhidraScript`s (preserved in `research/decompiler_notes/`).
This was a substantial and successful improvement over the manual
capstone-based disassembly used earlier in the project (it directly
resolved several open questions and caught the Layer-2 function-boundary
mistake described in `docs/14_failed_attempts.md`) — but it does **not**,
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

See `docs/18_future_work.md` for the prioritized next steps. In summary,
the two most promising next actions, neither attempted in this project:

1. **Live USB traffic capture** during an actual charging-state transition
   on the real device (requires either a hardware USB tap or `usbmon` on
   the host — the project's environment had host-level `usbmon` available
   in principle but this was not exercised). A capture spanning a real
   plug-in/charge-termination event, correlated with the physical LED
   color, would let the researcher work backward from confirmed telemetry
   rather than forward from an incomplete static trace.
2. **Data-flow analysis in Ghidra** starting from the power-management
   task's known state-variable write locations (the `str r0,[r4,#0xc]`-style
   writes visible in the manually-read gap listing,
   `research/decompiler_notes/pm_gap_listing.txt`) to find every code
   location that subsequently *reads* the same struct field — this is a
   different, more targeted question than "who calls this function," and
   Ghidra's decompiler-backed data-flow tools are well suited to it, though
   this project ran out of time before attempting it.
