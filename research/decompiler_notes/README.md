# research/decompiler_notes/

Analysis scripts and their raw output, preserved as primary evidence for
the claims made in [`../../docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md), [`../../docs/07_led_architecture.md`](../../docs/07_led_architecture.md),
and [`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md). Originally, and still mostly,
Ghidra headless scripts (Java `GhidraScript` subclasses, scripts 01-11
below) — see [`../../tools/ghidra_setup.md`](../../tools/ghidra_setup.md) for how to set up the environment
needed to run those. A later "multi-tool sweep" session (scripts 12-14)
added angr, Unicorn Engine, and radare2 to the mix, run because Ghidra's
reference manager has a confirmed history of missing real cross-references
in this exact firmware — these live in this directory rather than
`scripts/` because, like everything else here, they're one-off
investigation notes hardcoded to specific firmware addresses, not general
reusable tooling.

These are a representative subset of the scripts actually written during
the investigation (numbered here in the order that best tells the
investigation's story, not necessarily the exact original chronological
order — the original session produced more incremental variants than are
preserved here; these were selected as the ones that each established a
genuinely new fact).

## Scripts

- **[`01_LedTrace_initial_decompile.java`](01_LedTrace_initial_decompile.java)** — first successful decompilation
  attempt against the low-level PWM writer (`0x41dbf0`), the "off-path"
  function (`0x41e7d8`), and the channel-scaling function (`0x419250`).
  This is what confirmed Ghidra's decompiler output was directly usable
  for this firmware (in contrast to the difficulties encountered with
  radare2's auto-analysis on the same target — see
  [`../../tools/radare2_setup.md`](../../tools/radare2_setup.md)), and is what first surfaced the *second*
  direct caller of the "off-path" function that a manual/brute-force
  search had not previously found.

- **[`02_LedTrace_wrapper_callers.java`](02_LedTrace_wrapper_callers.java)** — corrected the color-request
  wrapper function's entry-point address (from the mistakenly-assumed
  `0x41d7a8` to the actual `0x41d7ac`, see
  [`../../docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md)) and enumerated its three real
  callers. Output (cleaned) preserved as [`wrapper_decompile.c`](wrapper_decompile.c) in this
  directory.

- **[`03_LedTrace_gap_region_listing.java`](03_LedTrace_gap_region_listing.java)** — linearly disassembles a
  specific byte range regardless of Ghidra's function-boundary detection,
  used to read through the large unbounded code region containing the
  three Layer-3 caller functions when `getFunctionContaining` and the
  reference manager both came up empty for them. Output:
  [`layer3_gap_region_listing.txt`](layer3_gap_region_listing.txt).

- **[`04_LedTrace_pm_string_xrefs.java`](04_LedTrace_pm_string_xrefs.java)** — attempted (unsuccessfully) to
  find cross-references to the power-management task's charging-state log
  strings via Ghidra's reference manager. The zero-result outcome of this
  script is itself an important, documented negative finding — see
  [`../../docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md).

- **[`05_LedTrace_pm_gap_listing.java`](05_LedTrace_pm_gap_listing.java)** — the same linear-listing technique
  as script 03, applied to the code region actually containing the
  power-management state-transition logic (found via `getFunctionContaining`
  once the reference-manager approach failed). Output: [`pm_gap_listing.txt`](pm_gap_listing.txt),
  the primary evidence behind [`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md)'s
  conclusion that this code does not directly call into the traced LED
  call graph.

- **[`06_pm_struct_base_address.java`](06_pm_struct_base_address.java)** — reads each of the four known
  power-management functions' literal-pool operand directly, confirming
  they all load the same RAM address (`0x2000378c`) as their struct base
  pointer. This is what turned "the PM code touches *some* struct" into a
  concrete, searchable fact — see
  [`../../docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md) §6.5.

- **[`07_pm_reference_investigation.java`](07_pm_reference_investigation.java)** — given a list of raw
  reference addresses found by a plain byte search for `0x2000378c`
  ([`docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md) follow-up session), uses Ghidra's
  reference manager to identify the actual referencing instruction and
  dump surrounding context for each. Found several new struct-field
  offsets and one promising-but-ultimately-unrelated lead (the
  `0x414dbc`/`0x414e38` timer functions).

- **[`08_tick_handler_decompile.java`](08_tick_handler_decompile.java)** — full decompilation of
  `0x414dbc`/`0x414e38`, which resolved the timer-function lead above as a
  dead end (confirmed via an embedded `tick_handler.c` assert string and
  each function's 19–20 unrelated callers). See
  [`../../docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md).

- **[`09_usb_pairing_string_xrefs.java`](09_usb_pairing_string_xrefs.java)** — investigated the USB-status
  ("enumerated"/"power good") and a "pairing" string match, as part of the
  connection-state hypothesis ([`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md)).
  Found the USB-status strings have the same recurring
  zero-cross-references symptom; found the "pairing" match was a
  boot-time mode-announcement function, not live pairing-state logic.

- **[`10_mode_announce_fn_decompile.java`](10_mode_announce_fn_decompile.java)** — full decompilation of that
  mode-announcement function, revealing its struct base address
  (`0x20003878`) sits only 20 bytes from the already-known PM struct base
  (`0x2000378c`).

- **[`11_shared_struct_investigation.java`](11_shared_struct_investigation.java)** — follows references to
  `0x20003878`, finding a single large initialization function
  (`0x43c1a4`) touching struct offsets beyond `+0x1000` — the evidence
  behind the "one large shared device-state block" hypothesis in
  [`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md).

- **[`12_angr_literal_pool_sweep.py`](12_angr_literal_pool_sweep.py)** — angr-based second opinion: a
  systematic literal-pool scan across the PM struct's full plausible
  offset range (`+0x0`..`+0x2f`, not just `+0x0` as script 07 checked),
  which found 5 reference sites the earlier search missed, and an
  independent callgraph-reachability check confirming (again) zero path
  from any PM-struct-touching function to the LED Layer-3 functions. One
  of the 5 new sites led directly to `sub_422f21` — see script 13.

- **[`13_unicorn_state_handler_sweep.py`](13_unicorn_state_handler_sweep.py)** — empirically verifies
  `sub_422f21` (found via script 12), the first located reader of the PM
  state enum, by actually executing it in Unicorn Engine (with its own
  `bl` calls NOP-patched out) across a swept range of initial state
  values. Confirms the disassembly reading exactly: states `{0,1,2,5}`
  transition the enum to `3`; states `{3,4,6,7}` are a no-op. See
  [`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md) "Multi-tool sweep session" for
  the annotated disassembly this validates.

- **[`14_r2_and_version_diff.md`](14_r2_and_version_diff.md)** — radare2 was tried on this exact
  firmware early in the project and largely abandoned (`aaa` produced poor
  results, [`../../tools/radare2_setup.md`](../../tools/radare2_setup.md)); this session revisited it with a
  narrower technique (explicit per-function `af` + direct `/r` reference
  search instead of blanket `aaa`) and got a clean, usable independent
  cross-reference check (also zero results, corroborating Ghidra, the
  project's `BL`-search, and angr). Also includes a DIY version-diff Python
  snippet confirming `sub_422f21` and the PM struct's exact layout are
  present, byte-identical, in a second separate firmware build.

## Output files

- **[`wrapper_decompile.c`](wrapper_decompile.c)** — cleaned, annotated decompilation of the
  Layer-2 color-request wrapper function, with reading notes.
- **[`layer3_gap_region_listing.txt`](layer3_gap_region_listing.txt)** — raw linear instruction listing of
  the ~620-byte unbounded code region containing the three Layer-3 LED
  entry-point functions and several related helpers (a "glow not
  supported" stub, an ownership-tag-based table-iteration function, a
  struct-clearing utility). Referenced throughout
  [`../../docs/07_led_architecture.md`](../../docs/07_led_architecture.md) and [`../../docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md).
- **[`pm_gap_listing.txt`](pm_gap_listing.txt)** — raw linear instruction listing of the
  power-management task's charging-state-transition code, including the
  `bl` call targets that were checked against (and found not to match) the
  LED call graph. Referenced in [`../../docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md).

## A note on Ghidra's auto-generated names

All `FUN_*`, `DAT_*`, and `param_*`/`uVar*`/`iVar*` names visible in this
directory's output are Ghidra's own automatic naming, not manually assigned
labels. Human-assigned names and roles (e.g. "low-level PWM writer" for
`FUN_0041dbf0`) are documented separately in
[`../../docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md), which should be read alongside these
raw outputs for interpretation.
