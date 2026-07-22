# 04 — Firmware Acquisition

## Summary

Valve ships the Index Controller's firmware images as plain files inside a
normal SteamVR installation. No extraction tool, dump utility, chip
programmer, or hardware access is required — the files are present on disk
the moment SteamVR is installed. This was the first concrete finding of the
investigation and immediately eliminated an entire planned phase of the
original research methodology (hardware-based extraction via APPROTECT
bypass, see `02_background.md`).

**This repository does not include these files.** Valve's firmware remains
Valve's property; see the Legal Notice in the top-level `README.md`. Obtain
them from your own legitimate SteamVR installation using the steps below,
and verify you have the exact files this documentation refers to using the
SHA-256 hashes in `hashes/firmware_hashes.txt`.

## How to obtain the firmware

1. Install Steam and SteamVR (App ID `250820`) through the normal Steam
   client. No VR headset needs to be connected.
2. Locate your SteamVR installation directory. On Linux with a default Steam
   install, this is typically:
   ```
   ~/.local/share/Steam/steamapps/common/SteamVR/
   ```
   On Windows, typically:
   ```
   C:\Program Files (x86)\Steam\steamapps\common\SteamVR\
   ```
3. The Index Controller firmware images are at:
   ```
   drivers/indexcontroller/resources/firmware/indexcontroller/
   ```
4. Verify your files match this documentation:
   ```bash
   cd <SteamVR>/drivers/indexcontroller/resources/firmware/indexcontroller/
   sha256sum *.fw
   ```
   Compare the output against `hashes/firmware_hashes.txt`. If your SteamVR
   version ships different firmware builds, the hashes will differ — that is
   expected and does not indicate a problem, but means the specific
   file-offset findings in `05_firmware_layout.md` and `06_firmware_symbols.md`
   (which were derived from one specific build) may need to be re-derived
   for your build. The overall container format (`05_firmware_layout.md`)
   and analysis methodology are expected to generalize across builds; the
   `.fw` container format was independently verified against five different
   firmware files during this project (see below).

## Firmware files found (this project's SteamVR installation)

Seven `.fw` files were present, spanning multiple historical builds. All
seven were used to independently verify the container-format reverse
engineering in `05_firmware_layout.md` (i.e., that work is not
overfit to a single file). See `hashes/firmware_hashes.txt` for the complete,
exact list with SHA-256 sums:

- Four **application firmware** builds (`indexcontroller_app_*.fw`),
  spanning 2019-06-21 through 2023-10-13 (the last being an "ev" —
  presumably "early validation" or similar — variant).
- One **FPGA bitstream** (`indexcontroller_fpga_2_26.fw`).
- Two **radio firmware** builds (`indexcontroller_radio_*.fw`) — notably,
  these two are **not** zlib-compressed (see below), unlike every other file.

The primary analysis target throughout this project was
`indexcontroller_app_20230902_v1693638519.fw` (2023-09-02, git `2c3286c3`),
chosen as the most recent application build and the one matching the test
unit's actually-running firmware (confirmed via the live `info` debug shell
command — see `docs/03_hardware.md`).

## Container format at a glance

Every application and FPGA firmware file examined is a raw zlib-compressed
stream immediately followed by a 56-byte plaintext footer — no header
before the compressed data. Full format details, including the fully
reverse-engineered footer field layout and CRC algorithm, are in
`05_firmware_layout.md`.

The two radio firmware files are **not** zlib-wrapped — attempting to
`zlib.decompress()` them fails with "incorrect header check." They begin
directly with what appears to be a raw ARM vector table (first word
`0x00203240`, a plausible nRF52-range initial stack pointer). These were not
analyzed further in this project; see `18_future_work.md`.

## Extracting the compressed application/FPGA firmware

Minimal reproducible extraction (Python 3, standard library only):

```python
import zlib

with open("indexcontroller_app_20230902_v1693638519.fw", "rb") as f:
    raw = f.read()

d = zlib.decompressobj()
decompressed = d.decompress(raw)
footer = d.unused_data  # exactly 56 bytes for every file tested

with open("decompressed.bin", "wb") as f:
    f.write(decompressed)
```

This is genuinely the entire extraction procedure. There is no encryption,
no obfuscation beyond ordinary zlib compression, and no signature
verification blocking a local read of the content (there *is* a signature-
like CRC-32 checksum in the footer, but it protects data integrity for the
device's own flashing process, not confidentiality — see
`05_firmware_layout.md`). This was independently confirmed for all five
zlib-wrapped files in this project's SteamVR installation; `d.unused_data`
was exactly 56 bytes in every case, with a consistent, fully decoded field
layout (`05_firmware_layout.md`).

## Reproducibility checklist

- [ ] SteamVR installed from Steam (any recent version; firmware build
      availability may vary by SteamVR version).
- [ ] Located the `drivers/indexcontroller/resources/firmware/indexcontroller/`
      directory.
- [ ] Verified file hashes against `hashes/firmware_hashes.txt`, or noted
      that your files differ and treated file-offset-specific findings as
      needing re-derivation.
- [ ] Successfully decompressed at least one `.fw` file using the snippet
      above and confirmed `len(d.unused_data) == 56`.

If any step fails, see `docs/14_failed_attempts.md` for known issues, or
`docs/17_safety.md` for general troubleshooting guidance before proceeding
further.
