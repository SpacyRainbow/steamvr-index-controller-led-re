# patches/

This directory contains binary patch files (`.xdelta3` format, apply with
the `xdelta3` tool) and their full documentation. It does **not** contain
complete firmware images — see the top-level `README.md` legal notice and
`docs/04_firmware_acquisition.md`.

Each `.xdelta3` file is a diff against the **decompressed** application
firmware image (`indexcontroller_app_20230902_v1693638519.fw.decompressed.bin`,
hash in `../hashes/firmware_hashes.txt`) — i.e., it must be applied
*before* the recompression/footer-rebuild step, not against the raw `.fw`
file directly (recompressing the same logical content can legitimately
produce different compressed bytes depending on the zlib implementation and
settings used, so a diff against the compressed form would be needlessly
fragile; a diff against the decompressed form is exact and minimal).

For the full reproducible procedure (decompress → apply patch → recompress
→ rebuild footer → flash), see `../docs/15_firmware_patching.md`. The
`.py` scripts in `../scripts/` perform the same byte-level modification
directly (they do not use these `.xdelta3` files internally — the two are
independent, equivalent representations of the same patch, provided so a
reader can use whichever fits their workflow).

## How to apply a patch file

```bash
# 1. Obtain and decompress the source firmware (see docs/04_firmware_acquisition.md)
# 2. Apply the patch:
xdelta3 -d -s indexcontroller_app_20230902_v1693638519.fw.decompressed.bin \
    patch_B_led_black.decompressed.xdelta3 \
    output.decompressed.bin
# 3. Verify the result's hash against hashes/firmware_hashes.txt
sha256sum output.decompressed.bin
# 4. Recompress and rebuild the .fw footer -- see docs/15_firmware_patching.md
#    §15.1 steps 4-7, or simply use scripts/patch_led_black.py / 
#    scripts/patch_led_firmware.py directly, which do all of this in one step.
```

---

## Patch A — LED driver current values

**File:** `patch_A_led_current_255.decompressed.xdelta3`,
`patch_A_led_current_0.decompressed.xdelta3`
**Generator script:** `../scripts/patch_led_firmware.py <value>`

**Goal:** test whether the firmware's per-channel LED brightness
calibration values respond to software changes, as a first, low-risk probe
of software LED control.

**Reasoning:** the debug shell's `config` command
(`../docs/11_hid_commands.md`) exposes four `led_driver_current_{r,g,b,w}`
values, default `8`, identified via the config-table structure recovery
in `../docs/06_firmware_symbols.md` §6.2. These are the most directly
identifiable, named LED-related values in the firmware, making them a
natural first target.

**Binary location:** decompressed image, file offsets `0x2C683`,
`0x2C68C`, `0x2C695`, `0x2C69E` (4-byte int32 each), within the config
defaults table starting at `0x2C594`.

**Patch description:** replace the 4-byte little-endian value `08 00 00 00`
at each of the four offsets with the caller-supplied value (e.g. `ff 00 00
00` for 255, `00 00 00 00` for 0).

**Expected outcome:** a visible brightness change proportional to the new
value.

**Observed outcome:** value=255 produced no clearly perceptible brightness
increase to the human tester (inconclusive result — see
`../docs/13_experiments.md` Experiment 6b). value=0 produced a dramatic,
clearly visible dimming, but not a complete blackout (Experiment 6c).

**Side effects:** none observed beyond the intended brightness change; all
other config values, device identity, and general functionality were
confirmed unaffected via the live `info`/`config` debug shell commands
after each flash.

**Rollback procedure:** flash the original, unmodified firmware (see
`../docs/15_firmware_patching.md` §15.5).

**Compatibility:** validated only against
`indexcontroller_app_20230902_v1693638519.fw` (hash in
`../hashes/firmware_hashes.txt`). The config table's exact offsets are
expected to shift on any firmware build compiled differently — see
`../docs/17_safety.md`.

**Safety notes:** low risk — a pure data-value change with no code
modification. This was the first live patch attempted after two
same-version safety-test flashes had already confirmed the flashing
pipeline itself was safe.

---

## Patch B — force LED color to black (primary proven result)

**File:** `patch_B_led_black.decompressed.xdelta3`
**Generator script:** `../scripts/patch_led_black.py`

**Goal:** achieve a complete, unambiguous LED blackout via software, as
the strongest possible positive demonstration of this project's core
research question.

**Reasoning:** Patch A demonstrated that the brightness-calibration values
are real and effective but do not reach true black, consistent with them
being a multiplicative scaling stage applied to an already-nonzero base
color rather than the sole determinant of output (`../docs/08_lp5562_driver.md`).
Static analysis (`../docs/06_firmware_symbols.md` §6.3,
`../docs/07_led_architecture.md` Layer 1) identified the exact instruction
where the final, fully-computed color value is captured before being split
into per-channel hardware register writes — patching *that* value directly
bypasses the scaling-floor issue entirely.

**Binary location:** decompressed image, file offset `0xBC20` (runtime
address `0x41DC20`), inside the low-level LP5562 PWM-write function
(`0x41DBF0`).

**Patch description:** replace the 2-byte Thumb instruction `04 46`
(`mov r4, r0`) with `00 24` (`movs r4, #0`). Both are valid 2-byte Thumb
encodings; no surrounding code shifts, and no other bytes in the image are
modified by this patch.

**Expected outcome:** every LED color request, from every device state,
forced to black (0,0,0,0) at the point of hardware write.

**Observed outcome:** confirmed complete LED blackout on real hardware,
directly reported by the human tester ("the LED is off!!"). See
`../docs/13_experiments.md` Experiment 7 for the full evidence chain.

**Side effects:** this patch is **unconditional** — it disables the LED in
every state, including charging/charged indication, which most users would
likely want to retain. This is the project's known, documented limitation;
see `../docs/16_charging_led_research.md` for the (currently unresolved)
work to make this selective.

**Rollback procedure:** flash the original, unmodified firmware (see
`../docs/15_firmware_patching.md` §15.5). No special unpatch procedure is
needed — this single-instruction change has no persistent side effects
outside the flashed firmware image itself.

**Compatibility:** validated only against
`indexcontroller_app_20230902_v1693638519.fw` (hash in
`../hashes/firmware_hashes.txt`). The exact file offset is specific to this
build's compiled code layout — see `../docs/17_safety.md`.

**Safety notes:** the patch script verifies the expected original bytes
are present at the target offset before writing, and aborts loudly (does
not silently proceed) if they are not — this prevents accidentally
patching the wrong instruction if applied against an unexpected firmware
build. Do not bypass or remove this check in any derivative work.

---

## Patch C — force LED to a fixed blue color — **UNTESTED, not yet flashed to real hardware**

**File:** `patch_C_led_blue_255.decompressed.xdelta3`
**Generator script:** `../scripts/patch_led_solid_color.py`

**Status:** this patch was designed and file-verified during a session
with no physical access to the test controller. Everything below is a
documented *plan and expectation*, not an observed result. See
`../docs/18_future_work.md` Priority 1 for the recommendation to flash and
verify it as the first task in the next session with hardware access, and
`../docs/13_experiments.md`, which intentionally does **not** yet contain
an entry for this patch — one should be added once it's actually tested.

**Goal:** produce a specific, visually striking color (not just
"off") using the exact same low-risk mechanism as the proven Patch B, as a
second, independent demonstration of software LED control — and
specifically a color the controller's known normal states (green/orange/
white, `../docs/09_led_policy.md`) don't produce.

**Reasoning:** Patch B's patch point captures the fully-computed color
value in register `r4` before it's split into per-channel writes.
Patch B replaces that capture with `movs r4, #0` (always zero). The same
instruction family, `movs r4, #<any 8-bit value>`, is still only a 2-byte
Thumb instruction — no larger than the original — so it drops into the
exact same slot with the exact same "no code needs to move" property that
made Patch B safe.

**Binary location:** identical to Patch B — decompressed image, file
offset `0xBC20` (runtime address `0x41DC20`).

**Patch description:** replace `04 46` (`mov r4, r0`) with `<lo> 24` where
`<lo>` is the desired blue intensity byte (e.g. `ff 24` for maximum
intensity, encoding `movs r4, #0xff`).

**Expected outcome (not yet observed):** every LED color request forced to
pure blue (packed color `0x000000ff` at max intensity) — W, R, and G all
forced to zero, since the instruction zero-extends into the whole
register. This is a hard *limitation* of this specific technique, not a
design choice — see `../docs/15_firmware_patching.md` §15.3 for why a
different, harder patch (a code cave) would be needed to reach a
two-channel color like purple.

**Side effects:** same as Patch B — unconditional across all device
states, including charging/charged indication.

**Rollback procedure:** identical to Patch B — flash the original,
unmodified firmware.

**Compatibility:** same firmware-build specificity as Patch B.

**Safety notes:** same built-in byte-verification safety check as Patch B.
Additionally: because this patch is unverified on real hardware, treat the
very first flash of it with the same caution as any first-time firmware
modification (`../docs/17_safety.md`) — don't assume it's as
"pre-validated" as Patch B just because it reuses the same mechanism.
