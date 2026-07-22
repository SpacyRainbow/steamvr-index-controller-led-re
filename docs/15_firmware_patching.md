# 15 — Firmware Patching: Mechanics and Procedure

This document is the practical reference for building and flashing a
patched firmware image. For the underlying container-format research, see
`docs/05_firmware_layout.md`. For the experimental record of each patch
actually built and tested, see `docs/13_experiments.md`. For the specific
open problem of a *selective* (non-blanket) patch, see
`docs/16_charging_led_research.md`.

## 15.1 General patch-building procedure

1. Obtain the target `.fw` file from a legitimate SteamVR installation
   (`docs/04_firmware_acquisition.md`) and verify its hash against
   `hashes/firmware_hashes.txt`.
2. Decompress it (`docs/04_firmware_acquisition.md` §"Extracting"), keeping
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
     See `docs/05_firmware_layout.md` §5.2 for why this is necessary (a
     stale `final_crc` is what caused the very first patch attempt to be
     rejected — `docs/13_experiments.md` Experiment 5).
6. Concatenate `new_compressed_stream + new_footer` and write to a new
   `.fw` file.
7. **Verify before flashing**: decompress the newly-built file again from
   scratch and confirm (a) it decompresses cleanly, (b) the footer fields
   are internally self-consistent (recompute `final_crc` from the built
   footer and confirm it matches), and (c) the intended byte modification
   is actually present at the expected offset in the round-tripped content.
   Both patch scripts in this project (`scripts/patch_led_firmware.py`,
   `scripts/patch_led_black.py`) perform this verification automatically
   and abort loudly if it fails — do not skip this step in any derivative
   work.
8. Flash via Valve's official tool:
   ```bash
   pkexec /path/to/lighthouse_watchman_update -mv <patched.fw> --via-application
   ```
   (`--via-application` is mandatory — see `docs/10_protocol_analysis.md`
   and `docs/14_failed_attempts.md` for why the default mode fails against
   a normally-running controller.)
9. After flashing, wait for USB re-enumeration, re-enable the debug
   interface (`docs/12_debug_interfaces.md`), and confirm the device is
   healthy via the `info` debug shell command before concluding the flash
   succeeded.

## 15.2 Prerequisites

- A wired Valve Index Controller connected via USB.
- SteamVR installed (provides both the firmware files and the official
  `lighthouse_watchman_update` tool).
- Root access on the host machine, via `sudo` or `pkexec` (see
  `docs/17_safety.md` for guidance on obtaining this safely in an
  automation context without a TTY).
- Python 3 with the standard library only (no third-party dependencies
  needed for patch-building itself).

## 15.3 Worked examples (patches actually built and flashed in this project)

### Patch A — LED driver current values (`scripts/patch_led_firmware.py`)

**What it changes:** the four `led_driver_current_{r,g,b,w}` values in the
compiled-in config defaults table (`docs/06_firmware_symbols.md` §6.2), at
file offsets `0x2C683`, `0x2C68C`, `0x2C695`, `0x2C69E` (4-byte int32 each),
from their default value `8` to a caller-supplied value.

**Usage:** `python3 scripts/patch_led_firmware.py <value>` (e.g. `255` or
`0`).

**Result observed:** value changes are correctly applied and confirmed via
live `config` readout, but do not by themselves reach a full LED blackout
— see `docs/13_experiments.md` Experiment 6 and
`docs/08_lp5562_driver.md` for why.

### Patch B — force LED color to black (`scripts/patch_led_black.py`)

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
actually requested by any caller. See `docs/07_led_architecture.md` Layer 1
for the full architectural context and `docs/06_firmware_symbols.md` §6.3
for the disassembly this conclusion is based on.

**Usage:** `python3 scripts/patch_led_black.py` (no arguments — this patch
is a fixed byte substitution, not parameterized).

**Result observed:** confirmed complete LED blackout on real hardware —
see `docs/13_experiments.md` Experiment 7. This is the project's primary
positive result.

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
performed successfully in this project (`docs/13_experiments.md`
Experiment 6a, run twice as same-version safety tests, which are
functionally identical to a rollback-to-stock operation). No special
"undo" tooling is required — flashing the original file is the rollback.

See `docs/17_safety.md` for what to do if a flash is interrupted or fails
partway through.
