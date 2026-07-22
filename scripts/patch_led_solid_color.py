#!/usr/bin/env python3
"""Patch the low-level LED PWM-write function to force a fixed, single-channel
color, regardless of what the policy layer requests -- a direct generalization
of patch_led_black.py using the identical mechanism and identical risk profile.

*** STATUS: UNTESTED ON REAL HARDWARE as of this script's creation. ***
patch_led_black.py's technique (same patch point, value=0x00) IS proven live
on real hardware (docs/13_experiments.md Experiment 7). This script reuses
that exact mechanism with a nonzero immediate, which is expected on strong
first-principles grounds to work identically, but has NOT itself been
flashed and visually confirmed. Do not treat its output as validated until
someone runs it against real hardware and updates docs/13_experiments.md
and docs/15_firmware_patching.md accordingly.

WHY ONLY ONE CHANNEL: the patched instruction is `movs r4, #imm8`
(Thumb-1, 2 bytes: opcode 0x2400 | imm8), replacing the original
`mov r4, r0` (2 bytes) at file offset 0xbc20 -- see patch_led_black.py for
the full derivation. `movs Rd, #imm8` zero-extends an 8-bit immediate into
the WHOLE 32-bit register: the upper 24 bits are unconditionally zeroed,
not left alone. Given this firmware's packed color layout
(bits31:24=W, 23:16=R, 15:8=G, 7:0=B -- docs/06_firmware_symbols.md sec 6.3),
that means this single 2-byte-for-2-byte swap can only ever produce colors
of the form (W=0, R=0, G=0, B=n) for n in 0..255 -- i.e. shades of pure
BLUE (or black at n=0). It CANNOT produce red, green, or any two-channel
combination (e.g. purple = R+B) without loading a full 32-bit constant,
which does not fit in the original 2-byte instruction slot without
relocating surrounding code (a "code cave" -- see
docs/18_future_work.md for that harder, not-yet-designed follow-on patch).

Usage: python3 patch_led_solid_color.py <blue_intensity 0-255>
  0   = black (identical patch to patch_led_black.py; use that script,
        this one is for a nonzero build)
  255 = maximum-intensity pure blue. NOTE: blue is actually one of the
        controller's normal existing colors (used for USB/host connection
        and pairing status per docs/09_led_policy.md) -- an earlier version
        of this docstring incorrectly claimed it was a color the
        controller never shows. That claim is corrected in
        docs/14_failed_attempts.md; it doesn't affect whether this patch
        works, only the "novel color" framing of why it was chosen.
"""
import os
import struct
import sys
import zlib

_DEFAULT_FW_DIR = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/SteamVR/drivers/indexcontroller/"
    "resources/firmware/indexcontroller"
)
FW_DIR = os.environ.get("STEAMVR_FW_DIR", _DEFAULT_FW_DIR)
ORIG_FW = os.path.join(FW_DIR, "indexcontroller_app_20230902_v1693638519.fw")
OUT_DIR = "04_firmware/patched"

PATCH_OFFSET = 0xbc20
OLD_BYTES = bytes.fromhex("0446")   # mov r4, r0


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    blue = int(sys.argv[1], 0)
    if not (0 <= blue <= 255):
        raise SystemExit("blue_intensity must be 0-255")

    new_instr = 0x2400 | blue  # movs r4, #blue
    new_bytes = struct.pack('<H', new_instr)

    out_fw = os.path.join(OUT_DIR, f"indexcontroller_app_LEDBLUE_{blue}.fw")
    out_decomp = os.path.join(OUT_DIR, f"indexcontroller_app_LEDBLUE_{blue}.decompressed.bin")

    os.makedirs(OUT_DIR, exist_ok=True)

    raw = open(ORIG_FW, 'rb').read()
    d = zlib.decompressobj()
    decompressed = bytearray(d.decompress(raw))
    footer = d.unused_data
    assert len(footer) == 56

    magic, target, orig_comp_size, orig_crc2, app_ver = struct.unpack_from('<IIIII', footer, 0)
    assert magic == 0xc0dea1de and target == 2

    actual = bytes(decompressed[PATCH_OFFSET:PATCH_OFFSET + 2])
    print(f"At file offset 0x{PATCH_OFFSET:x}: found {actual.hex()}, expected {OLD_BYTES.hex()}")
    assert actual == OLD_BYTES, "byte mismatch, refusing to patch!"
    decompressed[PATCH_OFFSET:PATCH_OFFSET + 2] = new_bytes
    print(f"Patched: mov r4,r0 -> movs r4,#{blue} (0x{blue:02x}) "
          f"at file offset 0x{PATCH_OFFSET:x} (runtime 0x{0x412000+PATCH_OFFSET:x})")
    print(f"Resulting forced color: W=0x00 R=0x00 G=0x00 B=0x{blue:02x} "
          f"(packed 0x000000{blue:02x})")

    compressor = zlib.compressobj(level=9)
    new_compressed = compressor.compress(bytes(decompressed)) + compressor.flush()
    new_comp_size = len(new_compressed)
    new_crc2 = zlib.crc32(new_compressed) & 0xffffffff
    print(f"Recompressed: {new_comp_size} bytes (was {orig_comp_size}), crc2=0x{new_crc2:08x}")

    new_footer = bytearray(footer)
    struct.pack_into('<I', new_footer, 8, new_comp_size)
    struct.pack_into('<I', new_footer, 12, new_crc2)
    new_footer[52:56] = b'\x00\x00\x00\x00'
    new_final_crc = zlib.crc32(bytes(new_footer)) & 0xffffffff
    struct.pack_into('<I', new_footer, 52, new_final_crc)
    print(f"Recomputed final_crc: 0x{new_final_crc:08x}")

    new_fw = new_compressed + bytes(new_footer)
    with open(out_fw, 'wb') as f:
        f.write(new_fw)
    with open(out_decomp, 'wb') as f:
        f.write(decompressed)
    print(f"Wrote {out_fw} ({len(new_fw)} bytes)")

    # verify round-trip (this only proves the .fw file is well-formed and
    # would be ACCEPTED by the update tool -- it does NOT prove the LED
    # will actually turn blue on real hardware. See module docstring.)
    verify_raw = open(out_fw, 'rb').read()
    vd = zlib.decompressobj()
    verify_decomp = vd.decompress(verify_raw)
    verify_footer = vd.unused_data
    assert verify_decomp == bytes(decompressed)
    vmagic, vtarget, vcomp_size, vcrc2, vapp_ver = struct.unpack_from('<IIIII', verify_footer, 0)
    assert vmagic == magic and vtarget == target and vapp_ver == app_ver
    assert vcomp_size == new_comp_size and vcrc2 == new_crc2
    vfooter_zeroed = bytearray(verify_footer)
    vfooter_zeroed[52:56] = b'\x00\x00\x00\x00'
    assert (zlib.crc32(bytes(vfooter_zeroed)) & 0xffffffff) == struct.unpack_from('<I', verify_footer, 52)[0]
    assert verify_decomp[PATCH_OFFSET:PATCH_OFFSET+2] == new_bytes
    print("Round-trip verification PASSED (file is well-formed).")
    print("REMINDER: this has not been flashed to real hardware. See module docstring.")


if __name__ == '__main__':
    main()
