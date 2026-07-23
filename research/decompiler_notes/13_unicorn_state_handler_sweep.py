#!/usr/bin/env python3
"""Empirically verify sub_422f21 (the PM state-enum reader/writer found via
12_angr_literal_pool_sweep.py) by actually executing it in Unicorn Engine,
rather than trusting a by-eye disassembly reading. Every `bl` inside the
function's own body is statically NOP-patched out first, so only its own
branching logic runs -- this validates the *branching semantics* without
needing to emulate everything it calls.

Sweeps the initial value of the PM struct's state enum (0x2000378c+0xc)
from 0 to 7 and records, for each, whether the function writes +0xc <- 3
and which exit path it reaches. Confirmed: {0,1,2,5} -> writes 3, reaches
the tail-call to 0x4156e8; {3,4,6,7} -> early exit, no write. This matches
the disassembly exactly (see docs/16_charging_led_research.md "Multi-tool
sweep session" for the annotated listing).

Requires: pip install --user unicorn capstone
"""
import struct as pystruct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UcError
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_PC
import capstone

FW = 'indexcontroller_app_20230902_v1693638519.fw.decompressed.bin'
BASE = 0x412000
FUNC = 0x422f21 & ~1  # angr tags Thumb function addresses with the low bit set;
                       # strip it before doing file-offset arithmetic, or you'll
                       # read one byte into the middle of the real instruction
                       # stream and get garbage disassembly (a real bug hit
                       # while writing this script -- see the file-offset note
                       # in docs/16_charging_led_research.md if this recurs).
STRUCT = 0x2000378c
FUNC_WINDOW = 0x90


def patch_out_calls(fw_data: bytearray):
    cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    code = bytes(fw_data[FUNC - BASE: FUNC - BASE + FUNC_WINDOW])
    bl_sites = [(insn.address, insn.size) for insn in cs.disasm(code, FUNC) if insn.mnemonic == 'bl']
    for addr, size in bl_sites:
        off = addr - BASE
        fw_data[off:off + size] = b'\x00\xbf' * (size // 2)  # Thumb NOP (0xBF00) x N
    return bl_sites


def run_one(fw_data: bytes, state_val: int):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    map_base = BASE & ~0xfff
    map_size = ((len(fw_data) + (BASE - map_base) + 0xfff) // 0x1000) * 0x1000
    mu.mem_map(map_base, map_size)
    mu.mem_write(BASE, fw_data)

    stack_base, stack_size = 0x20000000, 0x4000
    mu.mem_map(stack_base, stack_size)
    mu.reg_write(UC_ARM_REG_SP, stack_base + stack_size - 0x100)
    # PM struct's page falls inside the stack mapping above by coincidence
    # of address ranges chosen here; map it separately only if it doesn't.
    struct_page = STRUCT & ~0xfff
    if not (stack_base <= struct_page < stack_base + stack_size):
        mu.mem_map(struct_page, 0x1000)
    mu.mem_write(STRUCT + 0xc, pystruct.pack('<I', state_val))

    trace = []
    mu.hook_add(UC_HOOK_CODE, lambda uc, addr, size, ud: trace.append(addr))

    def on_write(uc, access, address, size, value, ud):
        if STRUCT <= address < STRUCT + 0x40:
            trace.append(('WRITE', address - STRUCT, value))
    mu.hook_add(UC_HOOK_MEM_WRITE, on_write)

    try:
        mu.emu_start(FUNC | 1, FUNC + FUNC_WINDOW, count=200)
    except UcError as e:
        trace.append(('ERROR', str(e)))

    wrote_c = [t[2] for t in trace if isinstance(t, tuple) and t[0] == 'WRITE' and t[1] == 0xc]
    pcs = [t for t in trace if isinstance(t, int)]
    return wrote_c, pcs[-3:] if pcs else []


def main(fw_path):
    with open(fw_path, 'rb') as f:
        fw_data = bytearray(f.read())
    bl_sites = patch_out_calls(fw_data)
    print(f"Patched {len(bl_sites)} BL call sites with NOPs (execution stays inside "
          f"sub_422f21's own body): {[hex(a) for a, _ in bl_sites]}\n")
    fw_bytes = bytes(fw_data)

    for state_val in range(8):
        wrote, tail = run_one(fw_bytes, state_val)
        print(f"initial struct+0xc = {state_val}: wrote +0xc <- {wrote}  "
              f"final PC trail: {[hex(a) for a in tail]}")


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else FW)
