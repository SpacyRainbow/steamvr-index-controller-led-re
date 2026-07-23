#!/usr/bin/env python3
"""angr-based second opinion on the PM struct (0x2000378c) question, run
because Ghidra's own reference manager has a confirmed history of missing
real cross-references in this exact firmware (docs/14_failed_attempts.md).

Two independent checks, both using angr's own CFG recovery and VEX-based
disassembly rather than Ghidra's p-code analyzer:

1. Callgraph reachability from the LED Layer-3 functions -- do any
   PM-struct-touching functions reach them, at any depth?
2. A systematic raw literal-pool scan for the struct base address across
   its full plausible offset range (+0x0..+0x2f), not just +0x0. This is
   what found 5 reference sites the earlier Ghidra-era raw-byte search
   (07_pm_reference_investigation.java) missed -- that search only ever
   checked for the base pointer itself, at a fixed list of addresses, not
   a systematic scan of the offset range. One of those 5 new sites led
   directly to sub_422f21, the first located reader of the state enum
   (see 13_unicorn_state_handler_sweep.py and docs/16_charging_led_research.md
   "Multi-tool sweep session").

Requires: pip install --user angr
"""
import struct
import angr
import logging

logging.getLogger('angr').setLevel(logging.ERROR)
logging.getLogger('cle').setLevel(logging.ERROR)
logging.getLogger('pyvex').setLevel(logging.ERROR)

FW = 'indexcontroller_app_20230902_v1693638519.fw.decompressed.bin'  # see docs/04_firmware_acquisition.md
BASE = 0x412000  # see docs/06_firmware_symbols.md section 6.1
PM_STRUCT = 0x2000378c

LAYER3 = [0x41d6fa, 0x41d938, 0x41da90]
WRAPPER = 0x41d7ac
INIT_FN = 0x43c1a4
# original (Ghidra-era) known reference sites, for comparison
ORIGINAL_SITES = [0x417f00, 0x4193d0, 0x419c68, 0x419d3c, 0x419d6c, 0x419de4,
                   0x41c334, 0x41d0b8, 0x41e37c, 0x41ebd8, 0x420938, 0x420994,
                   0x4258fc, 0x42984c]


def raw_literal_pool_scan(fw_path):
    with open(fw_path, 'rb') as f:
        data = f.read()
    hits = []
    for off_range_check in range(0, 0x30):
        target = PM_STRUCT + off_range_check
        for i in range(0, len(data) - 3):
            if struct.unpack_from('<I', data, i)[0] == target:
                hits.append((BASE + i, off_range_check))
    return hits


def main(fw_path):
    p = angr.Project(
        fw_path,
        main_opts={'backend': 'blob', 'arch': 'ARMCortexM', 'base_addr': BASE,
                   'entry_point': BASE | 0x365},
        auto_load_libs=False,
    )

    hits = raw_literal_pool_scan(fw_path)
    new_sites = [h for h in hits if (h[0] & ~1) not in ORIGINAL_SITES]
    print(f"Raw literal-pool scan (0x2000378c + 0x0..0x2f): {len(hits)} total hits, "
          f"{len(new_sites)} not in the original Ghidra-era site list:")
    for addr, off in new_sites:
        print(f"  0x{addr:x}  (struct+0x{off:x})")

    starts = set((a | 1) for a in LAYER3 + [WRAPPER, INIT_FN] + [h[0] for h in hits])
    cfg = p.analyses.CFGFast(force_complete_scan=True, function_starts=list(starts), normalize=True)
    print(f"\nCFG recovered {len(cfg.functions)} functions")

    print("\nCallgraph reachability check: do any PM-struct-touching functions "
          "reach the LED Layer-3 functions, at any depth?")
    import networkx as nx

    def containing(addr):
        for faddr, f in cfg.functions.items():
            if f.size and faddr <= addr < faddr + f.size:
                return f
        return None

    touch_funcs = {containing(h[0]).addr for h in hits if containing(h[0])}
    cg = cfg.functions.callgraph
    reachable = set()
    for tf in touch_funcs:
        if tf in cg:
            reachable |= nx.descendants(cg, tf)
    layer3_set = set((a | 1) for a in LAYER3) | set(LAYER3)
    hit = reachable & layer3_set
    print(f"  PM-struct-touching functions found: {[hex(x) for x in touch_funcs]}")
    print(f"  Any reach Layer-3 LED functions? {bool(hit)} -> {[hex(x) for x in hit]}")


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else FW)
