#!/usr/bin/env python3
"""Patch led_driver_current_r/g/b/w in the app firmware and repackage into
a valid .fw container (zlib stream + 56-byte footer) for lighthouse_watchman_update.

Footer layout (56 bytes), reverse-engineered from the original .fw files:
  [0:4]   magic       constant 0xc0dea1de across all app/fpga firmware
  [4:8]   target      2 = application, 3 = fpga
  [8:12]  comp_size   length of the zlib-compressed stream
  [12:16] crc2        zlib.crc32() of the compressed stream (device-verified;
                        matches the "host/calculated/readback" CRC language
                        in firmware strings)
  [16:20] app_ver     build hash, matches `info` shell command's "App ver"
  [20:40] timestamp   ASCII build date/time, null-terminated
  [40:49] git hash    ASCII short git hash, null-terminated
  [49:52] padding     zero bytes
  [52:56] final_crc   zlib.crc32() of the full 56-byte footer with THIS field
                        itself zeroed out (self-referential checksum).
                        Reverse-engineered by disassembling
                        lighthouse_watchman_update's validator (fcn.00038d00
                        calls fcn.00050230, a standard textbook CRC-32) with
                        radare2 after an initial patch attempt (which kept
                        this field stale from the original file) was rejected
                        client-side with "Error: Invalid firmware file."

Config defaults table (in decompressed app image), reverse-engineered:
  9-byte packed entries starting at file offset 0x2c594:
    [0]    type/flag byte (0x01=bool, 0x07/0x08=int32, etc.)
    [1:5]  pointer to entry's name string (informational only)
    [5:9]  int32 (or float, reinterpreted) value
  Entries 26-29 = led_driver_current_r/g/b/w, currently 8 each.
"""
import os
import struct
import sys
import zlib

# Default assumes a standard Linux Steam install. Override by setting the
# STEAMVR_FW_DIR environment variable, or by editing this path directly.
# On Windows this is typically:
#   C:\Program Files (x86)\Steam\steamapps\common\SteamVR\drivers\indexcontroller\resources\firmware\indexcontroller
# See docs/04_firmware_acquisition.md.
_DEFAULT_FW_DIR = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/SteamVR/drivers/indexcontroller/"
    "resources/firmware/indexcontroller"
)
FW_DIR = os.environ.get("STEAMVR_FW_DIR", _DEFAULT_FW_DIR)
ORIG_FW = os.path.join(FW_DIR, "indexcontroller_app_20230902_v1693638519.fw")
OUT_DIR = "04_firmware/patched"
NEW_VALUE = int(sys.argv[1]) if len(sys.argv) > 1 else 255
OUT_FW = OUT_DIR + f"/indexcontroller_app_LEDTEST_v{NEW_VALUE}.fw"
OUT_DECOMP = OUT_DIR + f"/indexcontroller_app_LEDTEST_v{NEW_VALUE}.decompressed.bin"

TABLE_START = 0x2c594
ENTRY_SIZE = 9
LED_INDICES = {26: 'led_driver_current_r', 27: 'led_driver_current_g',
               28: 'led_driver_current_b', 29: 'led_driver_current_w'}

def main():
    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    raw = open(ORIG_FW, 'rb').read()
    d = zlib.decompressobj()
    decompressed = bytearray(d.decompress(raw))
    footer = d.unused_data
    assert len(footer) == 56, f"unexpected footer length {len(footer)}"
    print(f"Original: {len(raw)} bytes total, {len(decompressed)} decompressed, footer {len(footer)} bytes")

    magic, target, orig_comp_size, orig_crc2, app_ver = struct.unpack_from('<IIIII', footer, 0)
    print(f"magic=0x{magic:08x} target={target} orig_comp_size={orig_comp_size} orig_crc2=0x{orig_crc2:08x} app_ver=0x{app_ver:08x}")
    assert magic == 0xc0dea1de
    assert target == 2

    # --- patch the config defaults table ---
    print("\nPatching LED driver current values:")
    for idx, name in LED_INDICES.items():
        off = TABLE_START + idx * ENTRY_SIZE
        flag = decompressed[off]
        addr = struct.unpack_from('<I', decompressed, off + 1)[0]
        old_val = struct.unpack_from('<i', decompressed, off + 5)[0]
        struct.pack_into('<i', decompressed, off + 5, NEW_VALUE)
        new_val = struct.unpack_from('<i', decompressed, off + 5)[0]
        print(f"  [{idx}] {name}: file_off=0x{off:x} flag=0x{flag:02x} addr=0x{addr:08x} value {old_val} -> {new_val}")

    # --- recompress ---
    compressor = zlib.compressobj(level=9)
    new_compressed = compressor.compress(bytes(decompressed)) + compressor.flush()
    new_comp_size = len(new_compressed)
    new_crc2 = zlib.crc32(new_compressed) & 0xffffffff
    print(f"\nRecompressed: {new_comp_size} bytes (was {orig_comp_size}), crc2=0x{new_crc2:08x} (was 0x{orig_crc2:08x})")

    # --- rebuild footer: same magic/target/app_ver, new comp_size/crc2,
    #     keep timestamp/git/padding/final_crc bytes verbatim from original ---
    new_footer = bytearray(footer)
    struct.pack_into('<I', new_footer, 8, new_comp_size)
    struct.pack_into('<I', new_footer, 12, new_crc2)
    # magic[0:4], target[4:8], app_ver[16:20], and [20:52] all left unchanged.
    # final_crc[52:56] MUST be recomputed: it's crc32(footer[0:56]) with
    # bytes[52:56] themselves zeroed during the calculation.
    new_footer[52:56] = b'\x00\x00\x00\x00'
    new_final_crc = zlib.crc32(bytes(new_footer)) & 0xffffffff
    struct.pack_into('<I', new_footer, 52, new_final_crc)
    print(f"Recomputed final_crc (footer self-checksum): 0x{new_final_crc:08x}")

    new_fw = new_compressed + bytes(new_footer)
    with open(OUT_FW, 'wb') as f:
        f.write(new_fw)
    with open(OUT_DECOMP, 'wb') as f:
        f.write(decompressed)
    print(f"\nWrote {OUT_FW} ({len(new_fw)} bytes)")

    # --- verify round-trip ---
    verify_raw = open(OUT_FW, 'rb').read()
    vd = zlib.decompressobj()
    verify_decomp = vd.decompress(verify_raw)
    verify_footer = vd.unused_data
    assert verify_decomp == bytes(decompressed), "round-trip decompress mismatch!"
    assert len(verify_footer) == 56
    vmagic, vtarget, vcomp_size, vcrc2, vapp_ver = struct.unpack_from('<IIIII', verify_footer, 0)
    assert vmagic == magic and vtarget == target and vapp_ver == app_ver
    assert vcomp_size == new_comp_size and vcrc2 == new_crc2
    vfooter_zeroed = bytearray(verify_footer)
    vfooter_zeroed[52:56] = b'\x00\x00\x00\x00'
    vfinal_crc_check = zlib.crc32(bytes(vfooter_zeroed)) & 0xffffffff
    vfinal_crc_stored = struct.unpack_from('<I', verify_footer, 52)[0]
    assert vfinal_crc_check == vfinal_crc_stored, "final_crc self-check failed!"
    print(f"final_crc self-check PASSED: 0x{vfinal_crc_stored:08x}")
    for idx, name in LED_INDICES.items():
        off = TABLE_START + idx * ENTRY_SIZE
        val = struct.unpack_from('<i', verify_decomp, off + 5)[0]
        assert val == NEW_VALUE, f"{name} readback {val} != {NEW_VALUE}"
    print("Round-trip verification PASSED: decompresses cleanly, footer fields consistent, LED values confirmed patched.")

if __name__ == '__main__':
    main()
