# 15 — Firmware Patching: Mechanics and Procedure

This document is the practical reference for building and flashing a
patched firmware image. For the underlying container-format research, see
[`docs/05_firmware_layout.md`](05_firmware_layout.md). For the experimental record of each patch
actually built and tested, see [`docs/13_experiments.md`](13_experiments.md). For the specific
open problem of a *selective* (non-blanket) patch, see
[`docs/16_charging_led_research.md`](16_charging_led_research.md).

## 15.1 General patch-building procedure

1. Obtain the target `.fw` file from a legitimate SteamVR installation
   ([`docs/04_firmware_acquisition.md`](04_firmware_acquisition.md)) and verify its hash against
   [`hashes/firmware_hashes.txt`](../hashes/firmware_hashes.txt).
2. Decompress it ([`docs/04_firmware_acquisition.md`](04_firmware_acquisition.md) §"Extracting"), keeping
   the trailing 56-byte footer (`d.unused_data`) separately.
3. Apply the desired byte-level modification(s) to the decompressed image.
   **Every modification must be documented**: exact file offset, exact
   original bytes, exact new bytes, and the reasoning for why this offset
   was chosen. See §15.3 for the two patches actually built in this
   project as worked examples.
4. Recompress the modified image with zlib (`level=9` was used
   throughout this project; the exact compression level is not required to
   match the original — only `comp_size` and `crc2` need to be recomputed
   to match whatever the new compressed output actually is).
5. Rebuild the 56-byte footer:
   - `magic` (offset `0x00`): unchanged, always `0xC0DEA1DE`.
   - `target` (offset `0x04`): unchanged (`2` for application firmware).
   - `comp_size` (offset `0x08`): set to the length of the newly
     recompressed stream.
   - `crc2` (offset `0x0C`): set to `zlib.crc32(new_compressed_stream)`.
   - `app_ver` (offset `0x10`), `timestamp` (offset `0x14`), `git_hash`
     (offset `0x28`), `padding` (offset `0x31`): left unchanged, copied
     verbatim from the original footer. (This is a deliberate choice, not
     an oversight — see §15.4 "On leaving version metadata unchanged.")
   - `final_crc` (offset `0x34`): **must be recomputed** — set the field to
     four zero bytes, compute `zlib.crc32()` over the entire 56-byte
     footer with that field zeroed, and write the result into the field.
     See [`docs/05_firmware_layout.md`](05_firmware_layout.md) §5.2 for why this is necessary (a
     stale `final_crc` is what caused the very first patch attempt to be
     rejected — [`docs/13_experiments.md`](13_experiments.md) Experiment 5).
6. Concatenate `new_compressed_stream + new_footer` and write to a new
   `.fw` file.
7. **Verify before flashing**: decompress the newly-built file again from
   scratch and confirm (a) it decompresses cleanly, (b) the footer fields
   are internally self-consistent (recompute `final_crc` from the built
   footer and confirm it matches), and (c) the intended byte modification
   is actually present at the expected offset in the round-tripped content.
   Both patch scripts in this project ([`scripts/patch_led_firmware.py`](../scripts/patch_led_firmware.py),
   [`scripts/patch_led_black.py`](../scripts/patch_led_black.py)) perform this verification automatically
   and abort loudly if it fails — do not skip this step in any derivative
   work.
8. Flash via Valve's official tool:
   ```bash
   pkexec /path/to/lighthouse_watchman_update -mv <patched.fw> --via-application
   ```
   (`--via-application` is mandatory — see [`docs/10_protocol_analysis.md`](10_protocol_analysis.md)
   and [`docs/14_failed_attempts.md`](14_failed_attempts.md) for why the default mode fails against
   a normally-running controller.)
9. After flashing, wait for USB re-enumeration, re-enable the debug
   interface ([`docs/12_debug_interfaces.md`](12_debug_interfaces.md)), and confirm the device is
   healthy via the `info` debug shell command before concluding the flash
   succeeded.

## 15.2 Prerequisites

- A wired Valve Index Controller connected via USB.
- SteamVR installed (provides both the firmware files and the official
  `lighthouse_watchman_update` tool).
- Root access on the host machine, via `sudo` or `pkexec` (see
  [`docs/17_safety.md`](17_safety.md) for guidance on obtaining this safely in an
  automation context without a TTY).
- Python 3 with the standard library only (no third-party dependencies
  needed for patch-building itself).

## 15.3 Worked examples (patches actually built and flashed in this project)

### Patch A — LED driver current values ([`scripts/patch_led_firmware.py`](../scripts/patch_led_firmware.py))

**What it changes:** the four `led_driver_current_{r,g,b,w}` values in the
compiled-in config defaults table ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.2), at
file offsets `0x2C683`, `0x2C68C`, `0x2C695`, `0x2C69E` (4-byte int32 each),
from their default value `8` to a caller-supplied value.

**Usage:** `python3 scripts/patch_led_firmware.py <value>` (e.g. `255` or
`0`).

**Result observed:** value changes are correctly applied and confirmed via
live `config` readout, but do not by themselves reach a full LED blackout
— see [`docs/13_experiments.md`](13_experiments.md) Experiment 6 and
[`docs/08_lp5562_driver.md`](08_lp5562_driver.md) for why.

### Patch B — force LED color to black ([`scripts/patch_led_black.py`](../scripts/patch_led_black.py))

**What it changes:** a single 2-byte Thumb instruction at file offset
`0xBC20` (runtime address `0x41DC20`), inside the low-level LP5562
PWM-write function. Original bytes `04 46` (`mov r4, r0`) are replaced with
`00 24` (`movs r4, #0`) — both valid 2-byte Thumb encodings, so no
surrounding code needs to shift.

**Why this specific instruction:** it is the point where the fully-computed
packed color value (already scaled by the per-channel calibration values
from Patch A) is copied into the register subsequently split into
per-channel bytes and written to hardware. Forcing this register to zero
makes every subsequent channel write zero, regardless of what color was
actually requested by any caller. See [`docs/07_led_architecture.md`](07_led_architecture.md) Layer 1
for the full architectural context and [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3
for the disassembly this conclusion is based on.

**Usage:** `python3 scripts/patch_led_black.py` (no arguments — this patch
is a fixed byte substitution, not parameterized).

**Result observed:** confirmed complete LED blackout on real hardware —
see [`docs/13_experiments.md`](13_experiments.md) Experiment 7. This is the project's primary
positive result.

### Patch C — force LED to a fixed, unusual color ([`scripts/patch_led_solid_color.py`](../scripts/patch_led_solid_color.py)) — UNTESTED

**Status: built and verified as a well-formed `.fw` file; NOT yet flashed
to real hardware.** This patch was designed and produced during a session
with no physical access to the test controller. It reuses Patch B's exact
mechanism and risk profile, and is expected on strong first-principles
grounds to work, but "expected to work" is explicitly not the same
confidence level as Patch B's "confirmed on real hardware" — do not treat
this section as a proven result until someone flashes it and updates this
document with the observed outcome (and, ideally, photographic evidence —
[`docs/18_future_work.md`](18_future_work.md) Priority 2).

**Motivation:** a natural follow-up question to the proven black patch is
whether the same technique can produce a specific *visible* color, as an
even more legible demonstration than "off" for an observer unfamiliar with
the project. **Correction:** this patch was originally motivated as
producing "a color the controller never normally shows" — this was wrong.
The user subsequently confirmed blue is an existing, normal state (used
for USB/host connection and pairing indication, [`docs/09_led_policy.md`](09_led_policy.md)).
The patch and its underlying mechanism are unaffected by this correction —
it's still a real, working (pending live verification) demonstration of
forcing a specific solid color via software — but it does not demonstrate
a color outside the controller's existing palette. See
[`docs/14_failed_attempts.md`](14_failed_attempts.md) for this correction preserved in full.

**What it changes:** the same 2-byte instruction at file offset `0xBC20`
as Patch B, but replaced with `movs r4, #<value>` (Thumb-1 encoding
`0x2400 | value`) instead of `movs r4, #0`.

**Why this only reaches blue, not arbitrary colors:** `movs Rd, #imm8` is a
zero-extending load — it sets the *entire* 32-bit register from an 8-bit
immediate, not just the low byte. Given this firmware's packed color
layout ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3: bits 31:24 = W, 23:16 = R,
15:8 = G, 7:0 = B), any value loaded this way necessarily has W=R=G=0,
with only the low (Blue) byte set. The reachable color space through this
single-instruction patch is therefore exactly: black, and 255 shades of
pure blue. This is a real, understood **limitation of the technique**, not
an unexplained gap — see "Why a code-cave is needed for two-channel colors"
below for what a true purple patch would require.

**Usage:** `python3 scripts/patch_led_solid_color.py <0-255>` (e.g. `255`
for maximum-intensity blue).

**Expected outcome (unverified):** every LED color request, from every
policy state, forced to pure blue at the specified intensity.

**When this gets tested:** update this subsection with the actual observed
outcome, add a corresponding entry to [`docs/13_experiments.md`](13_experiments.md), and remove
the "UNTESTED" status markers throughout this section and in
[`hashes/firmware_hashes.txt`](../hashes/firmware_hashes.txt).

### Why a code-cave is needed for two-channel colors (e.g. true purple) — design notes, not yet implemented

Purple requires both the Red and Blue channels nonzero simultaneously
(e.g. `R=0x80, G=0x00, B=0x80`), which cannot be produced by a single
`movs Rd, #imm8` instruction (see Patch C above). Loading an arbitrary
32-bit constant into a register in Thumb code normally takes a
`MOVW`/`MOVT` pair — two 32-bit-encoded Thumb-2 instructions, 4 bytes
each, 8 bytes total — which does not fit in the 2-byte slot Patches B and
C occupy without overwriting (and thereby breaking) the instructions
immediately following it, which are still needed (the very next
instruction, `lsrs r0, r0, #0x18`, feeds the W-channel branch decision —
see [`research/decompiler_notes/wrapper_decompile.c`](../research/decompiler_notes/wrapper_decompile.c) and
[`docs/07_led_architecture.md`](07_led_architecture.md) Layer 1).

The standard technique for this situation is a **code cave**: replace the
original short instruction with a branch to unused space elsewhere in the
same firmware image, execute the longer replacement logic there (build the
full 32-bit color constant, do whatever the original instruction did with
it), then branch back to resume normal execution exactly where it would
have continued. This is a well-established reverse-engineering patching
technique in general, but applying it here requires design work not yet
done in this project:

1. **Finding safe unused space** within the *decompressed application
   image itself* (not the separate `scratchpad` flash partition, which is
   a different region of flash not necessarily reachable by a short-range
   branch from this code, and not part of the image this project's
   scripts actually modify — see [`docs/05_firmware_layout.md`](05_firmware_layout.md) §5.3). The
   application partition has some slack between the image's actual used
   size (197,940 bytes) and its allocated size (204,800 bytes,
   [`docs/05_firmware_layout.md`](05_firmware_layout.md) §5.3) — whether that slack is (a) part of
   the same decompressed byte range this project's scripts operate on, and
   (b) actually safe to write arbitrary code into, was not determined.
2. **Branch encoding.** A 2-byte Thumb unconditional branch (`B`) has a
   range of roughly ±2 KB; reaching a code cave outside that range needs a
   4-byte `B.W`, which itself doesn't fit in the original 2-byte slot
   either — meaning even the "jump out" step likely needs a small amount
   of instruction relocation/insertion beyond just the color-loading logic
   itself, compounding the design work.
3. **Testing.** None of the above has been attempted, even as a
   file-level (unflashed) build. This is flagged as concrete future work
   in [`docs/18_future_work.md`](18_future_work.md), not attempted here because it requires
   materially more careful design than Patches B/C to avoid a genuinely
   higher risk of a broken patch (as opposed to Patches B/C, which reuse
   an already-proven-safe patch point and instruction size).

**Bottom line:** blue (Patch C) is a low-risk, same-technique extension of
the proven black patch, ready to test. Purple (or any other two-channel
color) is a meaningfully bigger undertaking that has not been designed to
completion, let alone tested — do not attempt it without first reading and
extending this design discussion.

## 15.4 On leaving version metadata unchanged

Both patches described above leave the `.fw` footer's `app_ver`,
`timestamp`, and `git_hash` fields byte-identical to the original,
unpatched firmware, even though the actual code/data content has changed.
This is a deliberate simplification for this project's research purposes,
not a best practice for any production use of this technique:

- It kept the `info` debug shell command's version report unchanged across
  patches, which was useful for this project's own health-check workflow
  (confirming a successful reboot without needing to distinguish "which
  patch is currently flashed" via that specific field).
- It means the device's self-reported version number does **not**
  accurately reflect that the firmware has been modified. Anyone building
  on this work for a purpose where accurate version reporting matters
  (e.g., avoiding confusion about which firmware variant is actually
  running) should assign a distinct, clearly-marked version/build string
  instead.

## 15.5 Rollback procedure

To restore the original, unmodified firmware: repeat the flashing procedure
(§15.1 step 8 onward) using the original, unmodified `.fw` file obtained
directly from the SteamVR installation (not a patched derivative). This was
performed successfully in this project ([`docs/13_experiments.md`](13_experiments.md)
Experiment 6a, run twice as same-version safety tests, which are
functionally identical to a rollback-to-stock operation). No special
"undo" tooling is required — flashing the original file is the rollback.

See [`docs/17_safety.md`](17_safety.md) for what to do if a flash is interrupted or fails
partway through.
