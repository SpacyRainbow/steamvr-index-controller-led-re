#!/usr/bin/env python3
"""Disassemble the decompressed app firmware (Thumb-2, Cortex-M) and locate
cross-references (LDR literal-pool loads, MOVW/MOVT pairs) to known anchor
string addresses, to find the config read/write command dispatch code."""
import sys
import capstone

FW = "04_firmware/decompressed/indexcontroller_app_20230902_v1693638519.fw.decompressed.bin"
BASE = 0x412000

def load():
    return open(FW, 'rb').read()

def disasm_range(data, start_off, length):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = False
    code = data[start_off:start_off+length]
    addr = BASE + start_off
    insns = list(md.disasm(code, addr))
    return insns

def find_xrefs(data, target_addrs, start_off=0, end_off=None):
    """Find MOVW/MOVT pairs (and literal pool LDRs) that build one of target_addrs."""
    if end_off is None:
        end_off = len(data)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = False
    code = data[start_off:end_off]
    addr = BASE + start_off
    results = []
    pending_movw = {}  # reg -> (low16, insn_addr)
    for insn in md.disasm(code, addr):
        mnem = insn.mnemonic
        ops = insn.op_str
        if mnem == 'movw':
            try:
                reg, imm = ops.split(',')
                reg = reg.strip()
                imm = int(imm.strip().replace('#','').replace('0x',''), 16) if '0x' in imm else int(imm.strip().replace('#',''))
                pending_movw[reg] = (imm, insn.address)
            except Exception:
                pass
        elif mnem == 'movt':
            try:
                reg, imm = ops.split(',')
                reg = reg.strip()
                imm = imm.strip().replace('#','')
                imm = int(imm, 16) if '0x' in imm else int(imm)
                if reg in pending_movw:
                    low16, movw_addr = pending_movw[reg]
                    full = (imm << 16) | low16
                    if full in target_addrs:
                        results.append((movw_addr, insn.address, reg, full))
            except Exception:
                pass
        elif mnem == 'ldr' and '[pc' in ops.lower():
            # literal pool load; compute target
            pass
    return results

if __name__ == '__main__':
    data = load()
    if sys.argv[1] == 'range':
        off = int(sys.argv[2], 16)
        length = int(sys.argv[3], 16)
        for insn in disasm_range(data, off, length):
            print(f"0x{insn.address:x}:\t{insn.mnemonic}\t{insn.op_str}")
    elif sys.argv[1] == 'xref':
        targets = [int(x, 16) for x in sys.argv[2:]]
        hits = find_xrefs(data, set(targets))
        for movw_a, movt_a, reg, full in hits:
            print(f"movw/movt at 0x{movw_a:x}/0x{movt_a:x} reg={reg} -> 0x{full:x}")
