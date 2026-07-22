#!/usr/bin/env python3
"""Minimal HID report descriptor parser, enough to enumerate report IDs/types/sizes
for Valve's vendor-defined (usage page 0xff00) descriptors."""
import sys

TAGS = {
    0x04: 'Usage Page', 0x08: 'Usage', 0x14: 'Logical Minimum', 0x24: 'Logical Maximum',
    0x74: 'Report Size', 0x94: 'Report Count', 0x84: 'Report ID',
    0x80: 'Input', 0x90: 'Output', 0xb0: 'Feature',
    0xa0: 'Collection', 0xc0: 'End Collection',
}


def parse(data):
    i = 0
    report_size = 0
    report_count = 0
    report_id = None
    results = []  # (report_id, kind, size_bits)
    while i < len(data):
        b = data[i]
        tag = b & 0xfc
        size = b & 0x03
        size = {0: 0, 1: 1, 2: 2, 3: 4}[size]
        i += 1
        val = 0
        if size:
            val = int.from_bytes(data[i:i+size], 'little')
            i += size
        name = TAGS.get(tag, f'0x{tag:02x}')
        if tag == 0x74:
            report_size = val
        elif tag == 0x94:
            report_count = val
        elif tag == 0x84:
            report_id = val
        elif tag in (0x80, 0x90, 0xb0):
            kind = {0x80: 'Input', 0x90: 'Output', 0xb0: 'Feature'}[tag]
            results.append((report_id, kind, report_size * report_count))
    return results


def main():
    path = sys.argv[1]
    with open(path) as f:
        text = f.read()
    blocks = []
    cur_name = None
    cur_hex = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('==='):
            cur_name = line
        elif line.startswith('hex:'):
            cur_hex = line.split('hex:')[1].strip()
            blocks.append((cur_name, cur_hex))
    for name, hexstr in blocks:
        data = bytes.fromhex(hexstr)
        results = parse(data)
        print(name)
        for rid, kind, bits in results:
            rid_s = f"0x{rid:02x} ({rid:>3d})" if rid is not None else "0x00 (none)"
            print(f"  report_id={rid_s}  type={kind:<8s} size={bits:>4d} bits = {bits//8} bytes")
        print()


if __name__ == '__main__':
    main()
