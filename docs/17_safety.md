# 17 — Safety

Read this before performing any firmware modification described in this
repository against real hardware.

## Risk summary

**All firmware-flashing work in this project was performed against a
physical controller the human operator explicitly described as already
damaged and considered expendable for testing purposes** ("it is live
hardware. but the physical hardware is damaged... if it breaks, its not a
loss"). This materially affected the risk tolerance applied during testing
— several steps (e.g., proceeding with a full flash cycle immediately after
an earlier attempt was interrupted mid-transfer) were taken with a
willingness to accept device loss that would not be appropriate on hardware
you are not prepared to lose. Do not assume the risk profile described here
transfers to your own, undamaged hardware.

That said, across four full successful flash cycles (two same-version
safety tests, two behavioral patches) and one interrupted/timed-out attempt,
**the controller was never damaged or left in an unbootable state.** This
is a positive safety signal, not a guarantee.

## What was observed to be safe

- **A `.fw` file that fails local validation** (bad footer CRC, wrong
  target field, etc.) is rejected by `lighthouse_watchman_update` **before
  any device communication occurs**. This was directly confirmed
  ([`docs/13_experiments.md`](13_experiments.md) Experiment 5, [`docs/14_failed_attempts.md`](14_failed_attempts.md)) —
  no USB device number change, no "Attempting to update..." message. This
  class of failure carries no observed device risk.
- **An interrupted flash attempt** (in one case, a command was killed by an
  8-second timeout right after the tool printed
  `"Attempting to update VRC Application via bootloader..."`) did not
  damage the device — the tool had not yet begun the actual bootloader
  reset/transfer sequence at that point, confirmed by the USB device
  number remaining unchanged afterward and the debug shell reporting an
  unmodified firmware version.
- **A full, successful flash cycle** (erase, write, verify, reset) was
  performed four times with no failure and no observed corruption.

## What was NOT tested, and should be treated as unknown risk

- Interrupting a flash **during** the actual data-transfer phase (after
  "Starting update... Sending data..." begins) — this project never
  deliberately or accidentally interrupted a transfer once it had started,
  so the device's resilience to a mid-transfer interruption (power loss,
  USB disconnect, killed process) is **untested and unknown**.
- Flashing a firmware image with an intentionally *invalid* internal
  structure that nonetheless passes the footer/CRC checks (e.g., corrupted
  ARM code that would crash immediately on boot). Every patch built in this
  project was a minimal, deliberately conservative modification (either a
  config value change or a single 2-byte instruction substitution) — larger
  or more invasive modifications have not been tested and carry
  unknown additional risk.
- Flashing across different firmware *versions* — every patch in this
  project was derived from and reflashed as the *same* version
  (`indexcontroller_app_20230902_v1693638519.fw`). Whether the device's
  bootloader/update logic behaves identically when the version number
  itself changes (a real upgrade or downgrade, as opposed to same-version
  patching) was not tested.
- Any other Index Controller unit, hardware revision, or firmware build.
  All conclusions in this repository, including the "observed to be safe"
  points above, are specific to the single test unit and firmware version
  in [`hashes/firmware_hashes.txt`](../hashes/firmware_hashes.txt).

## Recovery / rollback

If you have a bootable, functioning connection to the controller (i.e., it
still enumerates on USB and the debug shell or the update tool can see it),
recovery is straightforward: flash the original, unmodified `.fw` file
obtained from your own SteamVR installation, following the same procedure
as any other flash ([`docs/15_firmware_patching.md`](15_firmware_patching.md) §15.1). This is exactly
what was done in this project's own "same-version safety test" experiments.

If the device does **not** enumerate normally after a failed/interrupted
flash: this project did not encounter this situation and has no
first-hand recovery procedure to offer. The live `flash_info` debug shell
output ([`docs/05_firmware_layout.md`](05_firmware_layout.md) §5.3) shows a dedicated `bootloader`
flash region separate from the `application` region, which is architecturally
promising for recoverability (a corrupted application image should, in
principle, leave the bootloader itself intact and able to accept a new
application image) — but this is an inference from the partition layout,
**not a tested or confirmed recovery path**. See [`docs/18_future_work.md`](18_future_work.md)
for this as a flagged research gap.

## Root/privilege requirements and how to obtain them safely

Flashing requires root access on the host machine (the official update
tool needs to claim the raw USB device, which `hidraw`-only access —
sufficient for the debug shell — does not permit). This project's test
environment had **no passwordless `sudo`** and no TTY available for `sudo
-v` to prompt interactively in the automation context used
([`docs/14_failed_attempts.md`](14_failed_attempts.md)). The working solution was `pkexec`
(PolicyKit), which shows a native GUI authentication dialog on a desktop
Linux session, independent of any TTY:

```bash
pkexec /path/to/lighthouse_watchman_update -mv <file.fw> --via-application
```

If your environment has working passwordless `sudo` or an interactive TTY,
plain `sudo` is equally valid — `pkexec` was specifically a workaround for
this project's automation constraints, not a requirement of the underlying
task.

## Version compatibility warnings

- The exact byte offsets used in [`scripts/patch_led_black.py`](../scripts/patch_led_black.py) (the
  code patch) are **specific to the compiled output of
  `indexcontroller_app_20230902_v1693638519.fw`**. Applying this script's
  patch logic to a different firmware build without first re-verifying the
  target bytes (the script does verify the expected original bytes before
  patching and will refuse to proceed if they don't match — but this only
  prevents a *silent* wrong-offset patch, it does not find the *correct*
  offset for a different build automatically) will either fail safely (byte
  mismatch, script aborts) or, in the worst case if the coincidental bytes
  happen to match, patch the wrong instruction.
- [`scripts/patch_led_firmware.py`](../scripts/patch_led_firmware.py) (the config-value patch) locates its
  target via the config table structure format
  ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.2), which is somewhat more likely to
  generalize across nearby firmware builds sharing the same compiler/config
  system version, but this was **not tested** against any build other than
  the primary target.
- Both scripts should be treated as validated **only** for
  `indexcontroller_app_20230902_v1693638519.fw` (hash in
  [`hashes/firmware_hashes.txt`](../hashes/firmware_hashes.txt)) until independently re-verified against
  any other build.

## Unsupported hardware

This project tested exactly one physical unit (a wired Index Controller,
serial `LHR-XXXXXXXX`). Wireless-only (dongle-paired) controllers were
never flashed or patched — all `lighthouse_watchman_update` invocations in
this project used `--via-application` (a wired-application-interface mode);
the tool also supports `--via-dongle` for wireless updates, which was never
exercised and carries entirely unverified risk characteristics.

## If something goes wrong

1. Do not panic-flash repeatedly — if a flash fails, understand *why*
   before retrying (see [`docs/14_failed_attempts.md`](14_failed_attempts.md) and
   [`docs/13_experiments.md`](13_experiments.md) for the failure modes already characterized).
2. Check [`docs/11_hid_commands.md`](11_hid_commands.md) (`info`, `flash_info`, `battery`) for
   any signs the device is still alive and responsive before assuming the
   worst.
3. If the device still enumerates on USB in any form, a fresh flash of
   known-good original firmware is the first recovery step to try.
4. Preserve whatever diagnostic information you can (console output,
   `lsusb` state, any debug shell responses) before taking further action —
   this is valuable regardless of outcome, per this project's stated
   philosophy of preserving evidence, including of failures
   ([`docs/14_failed_attempts.md`](14_failed_attempts.md)).
