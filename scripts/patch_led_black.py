#!/usr/bin/env python3
"""Patch the low-level LED PWM-write function to force color = black (0,0,0)
regardless of what the policy layer requests, then repackage into a valid .fw.

Found by disassembling the function at runtime addr 0x41dbf0 (file offset
0xbbf0), reached via led.c's generic "set LED color" path (anchored off the
log string "LED %u: color = 0x%06X->0x%06X..."). That function:
  - calls fcn.419250 to compute a packed 32-bit WRGB color value -> r0
  - 0x41dc20: `mov r4, r0`   <- r4 keeps the packed color for the rest of
                                 the function
  - then extracts W/R/G/B bytes from r4 via lsrs/ubfx/uxtb and writes each
    to the LP5562 driver via fcn.4232c4 with register offsets 0x10/0x30/0x50
    (R/G/B channel PWM duty registers)

Patch: change `mov r4, r0` (bytes 04 46) to `movs r4, #0` (bytes 00 24) at
file offset 0xbc20. Both are 2-byte Thumb instructions, so no realignment
needed. This forces every channel's extracted byte to 0 for every LED color
request, independent of policy state, current-register calibration, or boot
self-test sequences.
"""
import os
import struct
import zlib

# Default assumes a standard Linux Steam install. Override by setting the
# STEAMVR_FW_DIR environment variable, or by editing this path directly.
# See docs/04_firmware_acquisition.md.
_DEFAULT_FW_DIR = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/SteamVR/drivers/indexcontroller/"
    "resources/firmware/indexcontroller"
)
FW_DIR = os.environ.get("STEAMVR_FW_DIR", _DEFAULT_FW_DIR)
ORIG_FW = os.path.join(FW_DIR, "indexcontroller_app_20230902_v1693638519.fw")
OUT_DIR = "04_firmware/patched"
OUT_FW = OUT_DIR + "/indexcontroller_app_LEDBLACK.fw"
OUT_DECOMP = OUT_DIR + "/indexcontroller_app_LEDBLACK.decompressed.bin"

PATCH_OFFSET = 0xbc20
OLD_BYTES = bytes.fromhex("0446")   # mov r4, r0
NEW_BYTES = bytes.fromhex("0024")   # movs r4, #0

def main():
    import os
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
    decompressed[PATCH_OFFSET:PATCH_OFFSET + 2] = NEW_BYTES
    print(f"Patched: mov r4,r0 -> movs r4,#0 at file offset 0x{PATCH_OFFSET:x} (runtime 0x{0x412000+PATCH_OFFSET:x})")

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
    with open(OUT_FW, 'wb') as f:
        f.write(new_fw)
    with open(OUT_DECOMP, 'wb') as f:
        f.write(decompressed)
    print(f"Wrote {OUT_FW} ({len(new_fw)} bytes)")

    # verify round-trip
    verify_raw = open(OUT_FW, 'rb').read()
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
    assert verify_decomp[PATCH_OFFSET:PATCH_OFFSET+2] == NEW_BYTES
    print("Round-trip verification PASSED.")

if __name__ == '__main__':
    main()
