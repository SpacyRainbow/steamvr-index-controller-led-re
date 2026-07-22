# 05 — Firmware Layout

## 5.1 The `.fw` container format

**Confidence: 100%.** Verified against all five zlib-wrapped firmware files
present in this project's SteamVR installation (four application builds, one
FPGA bitstream), and further verified by successfully building syntactically
valid, footer-correct patched firmware files that Valve's own official
update tool accepted and flashed to real hardware (`docs/15_firmware_patching.md`,
`docs/13_experiments.md` Experiments 6–7).

Structure: `[zlib-compressed stream][56-byte footer]`, with no header before
the compressed data.

### Footer field layout (56 bytes total)

| Offset | Size | Field | Value / meaning |
|---|---|---|---|
| `0x00` | 4 | `magic` | Constant `0xC0DEA1DE` (little-endian) in every file examined — confirmed **not** a computed checksum, since it is byte-identical across five files with completely different content. |
| `0x04` | 4 | `target` | Device/region selector. `2` = application firmware, `3` = FPGA bitstream, observed values in this project. |
| `0x08` | 4 | `comp_size` | Length in bytes of the zlib-compressed stream that precedes the footer. Verified to exactly equal the actual stream length in every file. |
| `0x0C` | 4 | `crc2` | `CRC-32(compressed_stream)`, standard IEEE 802.3 polynomial (identical algorithm to Python's `zlib.crc32`). Verified exact match against the compressed byte stream for all five files. |
| `0x10` | 4 | `app_ver` | Build identifier hash. Matches the "App ver" hex value reported by the live `info` debug shell command exactly (`docs/11_hid_commands.md`). |
| `0x14` | 20 | `timestamp` | ASCII build date/time string, null-terminated, e.g. `"2023-09-02 00:08:39\0"`. |
| `0x28` | 9 | `git_hash` | ASCII short git commit hash, null-terminated, e.g. `"2c3286c3\0"`. Matches the `info` command's reported git hash exactly. |
| `0x31` | 3 | `padding` | Observed as zero bytes in every file examined. |
| `0x34` | 4 | `final_crc` | **Self-referential CRC-32**: `CRC-32(footer[0:56])` computed with *this field itself* replaced by four zero bytes during the calculation. See §5.2. |

### 5.2 The self-referential final CRC

This is the one field whose meaning was not obvious from static analysis
alone and required disassembling Valve's own update tool
(`lighthouse_watchman_update`) to determine (full account of that process in
`14_failed_attempts.md` and `13_experiments.md`, Experiment 5).

**How it was found:** an early patch attempt left this field byte-identical
to the original firmware's value while `comp_size` and `crc2` were correctly
recomputed for new (patched) content. The official update tool rejected the
file locally, before any device communication, with `"Error: Invalid
firmware file."` — a safe failure with zero device risk, but one that made
clear this field is actually validated.

**Method:** the update tool binary was disassembled with radare2 (see
`tools/radare2_setup.md`). The string `"Error: Invalid firmware file."` was
located, its cross-reference traced to the calling function
(`fcn.0003e750`), which calls a footer-parsing function (`fcn.00038d00`),
which in turn calls a small CRC routine (`fcn.00050230`) **twice**:

1. Once over the entire file **excluding** the footer (i.e., the compressed
   stream) — result compared against the `crc2` field (§5.1, offset `0x0C`).
2. Once over the 56-byte footer **with the `final_crc` field's own four
   bytes zeroed out** — result compared against the original (unmodified)
   value that was in the `final_crc` field before zeroing.

The CRC routine itself (`fcn.00050230`) is a textbook table-driven CRC-32
with the classic bitwise-NOT pre/post conditioning — algorithmically
identical to Python's `zlib.crc32`.

**Verification:** this exact formula —
`final_crc == zlib.crc32(footer_with_final_crc_field_zeroed)` — was checked
against all five known-good firmware files and matched in every case before
it was ever used to build a patched file. Example verification (Python):

```python
import struct, zlib

footer = ...  # the trailing 56 bytes of a genuine .fw file
z = bytearray(footer)
z[52:56] = b'\x00\x00\x00\x00'
computed = zlib.crc32(bytes(z)) & 0xffffffff
stored = struct.unpack_from('<I', footer, 52)[0]
assert computed == stored
```

This was the key that unblocked live firmware patching — see
`docs/15_firmware_patching.md` for the full patch-building procedure that
depends on this formula.

## 5.3 Flash partition layout (live, from `flash_info`)

**Confidence: 100%, read directly from real hardware** via the live debug
shell (`docs/12_debug_interfaces.md`, `docs/11_hid_commands.md`). Note the
address discrepancy discussed in §5.4 below.

```
[   bootloader ]: 0x00000000 - 0x00011fff ( 53048 of  73728 bytes used) CRC: 0x7f421c1b v1
[  ice40_image ]: 0x00044000 - 0x00057fff ( 78219 of  81920 bytes used) CRC: 0x0ea4139c v1
[  application ]: 0x00012000 - 0x00043fff (197940 of 204800 bytes used) CRC: 0x40006924 v1
[   data_store ]: 0x0007a000 - 0x0007bfff (  8184 of   8192 bytes used) CRC: 0x29474b95 v1
[  stored_conf ]: 0x0007c000 - 0x0007dfff (  1702 of   8192 bytes used) CRC: 0x00000000 v1
[  descriptors ]: 0x0007e000 - 0x0007ffff (   360 of   8192 bytes used) CRC: 0x00000000 v1
[  hardware_id ]: 0xc0ffeeee - 0xc0fff0ed (     0 of    512 bytes used) CRC: 0x00000000 v1
[   scratchpad ]: 0x00058000 - 0x00079fff (     0 of 139264 bytes used) CRC: 0x00000000 v1
[     reserved ]: 0x0007a000 - 0x00079fff (     0 of      0 bytes used) CRC: 0x00000000 v1
```

Note: the `hardware_id` region's address range (`0xc0ffeeee`–`0xc0fff0ed`)
is a deliberately human-readable placeholder-style value ("coffeeee"), not a
real flash address in the normal sense — its exact significance was not
investigated further (`18_future_work.md`).

**`stored_conf`** (`0x0007c000`–`0x0007dfff`) is architecturally important:
it is a *separate* flash region from the application firmware image, and its
existence is why `docs/06_firmware_symbols.md` explicitly distinguishes
between the application's **compiled-in config defaults table** (inside the
`application` partition, described there) and any *possible* runtime
override storage in `stored_conf`. This project did **not** conclusively
determine whether `stored_conf` overrides the LED current values reverse
engineered in `06_firmware_symbols.md`, or whether it is used for other
purposes only — see `16_charging_led_research.md` for why this distinction
matters and remains open.

## 5.4 The `0x412000` base-address discrepancy (unresolved detail)

The application firmware, when disassembled, must be based at runtime
address `0x00412000` for all internal cross-references, string offsets, and
the vector table's own reset-handler pointer to resolve consistently (this
was empirically verified — see `06_firmware_symbols.md`). However,
`flash_info` reports the `application` partition's raw flash offset as
`0x00012000`, exactly `0x400000` (4 MiB) lower.

This project did not fully resolve the reason for this fixed `0x400000`
offset. Plausible explanations, none confirmed:

- A memory-mapping/aliasing region on the nRF52840 or an associated
  co-processor that maps flash at two different base addresses depending on
  context (e.g., a raw flash-offset view used by the bootloader/updater
  vs. an execution-time-mapped view used by the running application).
- A deliberate linker script offset for reasons not otherwise evidenced.

**Practical impact:** none for the work in this project — the `0x412000`
base was empirically derived and consistently verified (vector table,
`flash_info` region *sizes* excluding the offset, and successful
disassembly/decompilation all lined up), so all analysis in this repository
uses it directly. Anyone continuing this work should be aware the
`flash_info`-reported offset and the correct disassembly base differ by
exactly `0x400000`, and should not be confused by this when cross-referencing
the two.

## 5.5 Firmware sizes summary

| File | Compressed size | Decompressed size | SHA-256 |
|---|---|---|---|
| `indexcontroller_app_20190621_v1561139887.fw` | 137,982 | 197,940 (see hashes file — differs slightly per build) | see `hashes/firmware_hashes.txt` |
| `indexcontroller_app_20190712_v1562916277.fw` | 138,107 | — | see `hashes/firmware_hashes.txt` |
| `indexcontroller_app_20230902_v1693638519.fw` | 138,645 | 197,940 | see `hashes/firmware_hashes.txt` |
| `indexcontroller_app_ev_20231013_v1697193759.fw` | 139,185 | — | see `hashes/firmware_hashes.txt` |
| `indexcontroller_fpga_2_26.fw` | 78,219 | — | see `hashes/firmware_hashes.txt` |
| `indexcontroller_radio_20190612_v1560372213.fw` | 34,756 (not compressed) | n/a | see `hashes/firmware_hashes.txt` |
| `indexcontroller_radio_20190711_v1562882729.fw` | 34,844 (not compressed) | n/a | see `hashes/firmware_hashes.txt` |

Exact decompressed sizes and hashes for every file are in
`hashes/firmware_hashes.txt`.
