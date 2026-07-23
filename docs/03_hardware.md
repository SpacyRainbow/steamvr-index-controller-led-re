# 03 — Hardware

## Scope of this document

This document covers the hardware inventory of the test unit as established
through firmware analysis and the live debug shell ([`docs/12_debug_interfaces.md`](12_debug_interfaces.md)).
No physical teardown, PCB photography, or chip decapping was performed during
this project — all hardware identification below is derived from software
evidence. Photographic documentation is listed as future work
([`18_future_work.md`](18_future_work.md)).

## Test unit identity

| Field | Value | Source |
|---|---|---|
| Serial number | `LHR-XXXXXXXX` | live `info` debug shell command |
| HWID | `0x110e0009` ("Index Controller") | live `info` debug shell command |
| App firmware version | `0x64f2df77`, build timestamp `1693638519` (2023-09-02 00:08:39), git `2c3286c3` | live `info` debug shell command |
| Radio firmware version | `0x5d27b2a9`, build timestamp `1562882729` | live `info` debug shell command |
| FPGA version | `0x21a`, build `538` | live `info` debug shell command |

## Confirmed components

### Main MCU: Nordic nRF52840

**Confidence: 95%.** Identified via public teardown (background research,
[`02_background.md`](02_background.md)) and consistent with all firmware evidence gathered:
ARM Cortex-M4F Thumb-2 instruction encoding throughout the decompiled
firmware (see [`06_firmware_symbols.md`](06_firmware_symbols.md)), a vector-table structure consistent
with a Cortex-M reset/exception model, and RAM addresses in the
`0x20000000`–`0x20040000` range matching the nRF52840's 256 KB SRAM. Not
independently confirmed by reading a chip marking directly (no teardown
performed in this project).

### LED driver: Texas Instruments LP5562

**Confidence: 95%.** This is the single most important hardware finding for
this project's core question, and it is confirmed **directly from firmware
evidence**, not inference from a teardown:

- The decompressed application firmware contains the literal source filename
  strings `led_driver_lp5562.c` and `led_driver_gpio.c`, indicating the
  firmware supports (or historically supported) two different LED driver
  backends — an I2C-addressable LP5562 path and a simpler GPIO path.
- The error string `"LED: lp5562 led error"` is present, referencing the
  chip by name directly.
- The LP5562 is a real, commercially available TI part: a 4-channel
  (RGBW) I2C programmable LED driver with independent per-channel current
  control and PWM duty-cycle control — i.e., a chip capable of far more than
  simple on/off or fixed-color operation. This is the hardware basis for the
  project's core conclusion that software-driven arbitrary color control is
  architecturally possible, not merely a firmware policy restriction.
- The firmware's low-level LED-write function ([`docs/08_lp5562_driver.md`](08_lp5562_driver.md),
  [`docs/06_firmware_symbols.md`](06_firmware_symbols.md)) writes to hardware register offsets `0x10`,
  `0x30`, `0x50` for three of the four channels — spacing and register
  ranges consistent with the LP5562's real PWM/current-control register map
  (exact register-by-register confirmation against the LP5562 datasheet is
  listed as future work).

### FPGA: Lattice iCE40HX8K-CB132

**Confidence: 80% (unconfirmed by firmware string evidence, carried over
from the background teardown research).** Believed to handle optical/IR
sensor timing for Lighthouse base-station tracking. The live `flash_info`
debug shell command ([`docs/11_hid_commands.md`](11_hid_commands.md)) confirms a dedicated
`ice40_image` flash partition (`0x00044000`–`0x00057fff`, 78219 of 81920
bytes used) containing a genuine FPGA bitstream — the presence and size of
this partition is 100% confirmed; the specific FPGA part number is not
independently re-confirmed by this project beyond the original teardown
source.

### SPI NOR flash: Winbond W25Q32JW

**Confidence: 80% (carried over from background teardown research, not
independently re-confirmed).** A 32 Mbit (4 MB) SPI NOR flash chip. The live
`flash_info` output confirms a flash layout with multiple named partitions
totaling well under 4 MB actually used (see [`05_firmware_layout.md`](05_firmware_layout.md) for the
full partition table), consistent with — but not uniquely proving — a chip
of this size.

### Battery fuel gauge: TI bq27421

**Confidence: 100%, directly confirmed live.** The `battery` debug shell
command reports `Fuel gauge: bq27421` and returns live telemetry (state of
charge, voltage, temperature, charger state) consistent with a real fuel
gauge IC on the I2C bus. See [`docs/11_hid_commands.md`](11_hid_commands.md) for the full command
output.

## Unconfirmed / not investigated

- Exact PCB revision or board stepping of the test unit.
- Physical location of the LP5562 and its associated LED package on the
  PCB (single RGBW LED package vs. discrete LEDs).
- Any secondary/simple GPIO-driven LED distinct from the LP5562-driven
  status LED, despite the firmware clearly supporting a `led_driver_gpio.c`
  code path (see [`07_led_architecture.md`](07_led_architecture.md)) — it is not established whether
  this test unit's hardware actually populates a GPIO LED, or whether that
  driver path is dead/vestigial code for this particular board revision.
- Whether other Index Controller hardware revisions (left vs. right
  controller, different manufacturing batches) share identical LED hardware.

## Flash layout (from live `flash_info`)

See [`docs/05_firmware_layout.md`](05_firmware_layout.md) for the complete, annotated partition table
and its significance to firmware patching.
