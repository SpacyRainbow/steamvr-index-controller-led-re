#!/usr/bin/env python3
"""Find every direct Thumb-2 `BL` call to a given target address, by
computing the exact instruction encoding for a call from every possible
2-byte-aligned source address and searching for those bytes directly --
bypassing disassembly (and therefore any code/data misalignment issues)
entirely. This was the method used to establish, with high confidence,
that several firmware functions in this project have zero direct callers
(docs/16_charging_led_research.md, docs/14_failed_attempts.md).

*** Bug history (read before trusting old results from this technique) ***
An earlier, uncommitted version of this encoder had a bit-shift error
(`imm10 = (imm >> 13) & 0x3FF` instead of the correct `>> 11`), which could
alias two different targets onto the same encoded bytes for certain offset
magnitudes -- producing an occasional FALSE POSITIVE "caller" that a manual
disassembly check (capstone, or Ghidra) would then correctly show was
actually calling something else. This was caught during a later session
while investigating the power-management struct's field usage, when a
"caller" found this way turned out, on manual verification, to call a
different address than the one searched for.

The central, previously-documented "zero callers" findings for the LED
Layer-3 functions (0x41d6fa, 0x41d938, 0x41da90) were re-run with the
corrected encoder in this script and the result did NOT change -- still
zero callers found. That conclusion stands. But treat any NONZERO result
from this tool (old or new) with a manual disassembly cross-check
(e.g. capstone, as shown in the __main__ block below) before trusting it,
since a single coincidental collision can't be ruled out in general.

Usage: python3 find_bl_callers.py <target_hex_addr> [<target_hex_addr> ...]
"""
import struct
import sys

FW = "04_firmware/decompressed/indexcontroller_app_20230902_v1693638519.fw.decompressed.bin"
BASE = 0x412000


def bl_encode(src_addr, target_addr):
    """Encode a Thumb-2 BL instruction from src_addr to target_addr, per
    the ARM ARM T1 encoding: imm32 = SignExtend(S:I1:I2:imm10:imm11:'0'),
    I1 = NOT(J1 XOR S), I2 = NOT(J2 XOR S). Returns None if out of range."""
    offset = target_addr - (src_addr + 4)
    if offset % 2 != 0:
        return None
    imm = offset // 2  # 24-bit signed value (imm32 with trailing 0 bit removed)
    if not (-(1 << 24) <= offset < (1 << 24)):
        return None
    S = (imm >> 23) & 1
    I1 = (imm >> 22) & 1
    I2 = (imm >> 21) & 1
    imm10 = (imm >> 11) & 0x3FF   # NOTE: >>11, not >>13 -- see bug history above
    imm11 = imm & 0x7FF
    J1 = (I1 ^ S) ^ 1
    J2 = (I2 ^ S) ^ 1
    hw1 = (0b11110 << 11) | (S << 10) | imm10
    hw2 = (0b11 << 14) | (J1 << 13) | (1 << 12) | (J2 << 11) | imm11
    return struct.pack('<HH', hw1, hw2)


def find_callers(data, target):
    found = []
    for file_off in range(0, len(data) - 4, 2):
        src_addr = BASE + file_off
        enc = bl_encode(src_addr, target)
        if enc is None:
            continue
        if data[file_off:file_off + 4] == enc:
            found.append(BASE + file_off)
    return found


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    data = open(FW, 'rb').read()
    for arg in sys.argv[1:]:
        target = int(arg, 16)
        callers = find_callers(data, target)
        print(f"callers of 0x{target:x}: {[hex(c) for c in callers]}")
        if callers:
            print("  ^ verify each of these manually (capstone/Ghidra) before trusting -- see bug history in the module docstring.")
