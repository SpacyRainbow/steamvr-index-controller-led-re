# Glossary

Terms, acronyms, and project-specific shorthand used throughout this
repository, for a reader encountering them for the first time. Where a
term is a firmware-internal name (not a standard industry term), that's
noted explicitly.

## Standard technical terms

**ARM Thumb-2 / Thumb** — the compact 16/32-bit instruction encoding used
by ARM Cortex-M processors (including this project's target, the
nRF52840). Most instructions are 2 bytes; some (including `BL`, the "branch
with link" call instruction) are 4-byte "wide" encodings. See
[`docs/06_firmware_symbols.md`](docs/06_firmware_symbols.md).

**CRC-32** — a 32-bit cyclic redundancy check, a checksum algorithm used
throughout the firmware update protocol this project reverse engineered
([`docs/05_firmware_layout.md`](docs/05_firmware_layout.md)). This project confirmed the specific
variant used is the standard IEEE 802.3 polynomial, identical to Python's
`zlib.crc32`.

**Cortex-M4(F)** — the ARM processor core family used by the nRF52840 (the
"F" suffix denotes the floating-point unit variant, relevant since this
firmware's dense VFP/floating-point instruction usage made some static
analysis harder — [`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)).

**Decompiler vs. disassembler** — a disassembler converts machine code
bytes into assembly-language text (still very low-level); a decompiler
(what Ghidra provides, [`tools/ghidra_setup.md`](tools/ghidra_setup.md)) further reconstructs
C-like pseudocode with inferred variables and control flow, which is
generally much faster for a human to read.

**Feature report / GET_FEATURE / SET_FEATURE** — a category of USB HID
report used for device configuration rather than continuous input/output
data; `SET_FEATURE(report_id=0x12, value=0x01)` is the exact call that
unlocks the undocumented Debug interface ([`docs/12_debug_interfaces.md`](docs/12_debug_interfaces.md)).

**HID** — Human Interface Device, the USB device class this controller
(and its debug interface) communicates over.

**RTOS** — Real-Time Operating System — the firmware's underlying task
scheduler, evidenced by the live `tasks` debug shell command listing 12
concurrently-running tasks ([`docs/11_hid_commands.md`](docs/11_hid_commands.md)). This project's
central open question ([`docs/16_charging_led_research.md`](docs/16_charging_led_research.md)) hinges on RTOS
architecture: whether two pieces of code communicate via a direct function
call or via shared state read by separate tasks.

**Thumb bit** — in ARM/Thumb interworking, function pointer values have
their least-significant bit set to 1 to indicate "call this address in
Thumb mode" — this is why vector table entries and function pointers in
this project's disassembly are consistently odd addresses
([`docs/06_firmware_symbols.md`](docs/06_firmware_symbols.md) §6.1).

**VFP** — Vector Floating Point, the ARM floating-point instruction
extension; used heavily in parts of this firmware, which made some manual
disassembly harder ([`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)).

**zlib** — the general-purpose compression library/format used to
compress this firmware's `.fw` container ([`docs/05_firmware_layout.md`](docs/05_firmware_layout.md)).
Confirmed to be unmodified/standard zlib, not a custom variant.

## Firmware/project-internal terms and abbreviations

**BM** — "Battery Management," a code-region label inferred from firmware
log strings (e.g. bq27421 fuel-gauge–related messages,
[`docs/16_charging_led_research.md`](docs/16_charging_led_research.md)). Distinct from PM (below), though the
two are closely related and not fully disentangled by this project.

**LWU** — "Lighthouse Watchman Update," inferred from firmware log strings
(`"LWU: JSON"`, etc., [`docs/10_protocol_analysis.md`](docs/10_protocol_analysis.md)) and matching the
name of Valve's own update tool, `lighthouse_watchman_update`. Refers to
the firmware-side code handling incoming update/config data.

**PM** — "Power Management," a code-region label inferred from firmware
log strings (`" PM -> charging\n"`, etc.). The central subject of the
open research in [`docs/16_charging_led_research.md`](docs/16_charging_led_research.md).

**Layer 1 / Layer 2 / Layer 3 / Layer 4** — this project's own naming for
the LED subsystem's call-graph depth, from the hardware register write
(Layer 1) up to the still-unlocated policy decision (Layer 4) — see
[`docs/07_led_architecture.md`](docs/07_led_architecture.md). Not a firmware-internal term; invented for
this documentation.

**Patch A / Patch B / Patch C** — this project's own naming for the three
firmware patches built during the investigation (LED current values,
forced black, forced blue respectively) — see [`docs/15_firmware_patching.md`](docs/15_firmware_patching.md).
Not firmware-internal; invented for this documentation.

**"vrc"** — appears both as a debug shell live-state command
([`docs/11_hid_commands.md`](docs/11_hid_commands.md)) and as a config table boolean entry
([`docs/06_firmware_symbols.md`](docs/06_firmware_symbols.md) §6.2), almost certainly short for something
like "VR Controller." Used informally throughout this project as the
suspected name of the RTOS task that owns controller-facing logic
(unconfirmed — [`docs/16_charging_led_research.md`](docs/16_charging_led_research.md)).

**Watchman** — Valve's family name for its wireless VR tracking device
protocol, spanning the original HTC Vive wand controller through the
Index Controller ([`docs/02_background.md`](docs/02_background.md)). Also the name of both a
debug shell command (`watchman suspend`/`resume`, [`docs/11_hid_commands.md`](docs/11_hid_commands.md))
and the underlying wireless protocol family this device belongs to.

## Tools referenced

**capstone** — an open-source, multi-architecture disassembly library
(Python bindings used here), see [`tools/README.md`](tools/README.md).

**Ghidra** — the NSA's open-source software reverse engineering suite,
providing disassembly, decompilation, and scriptable analysis; the
primary tool for this project's deepest analysis work
([`tools/ghidra_setup.md`](tools/ghidra_setup.md)).

**radare2** — an open-source reverse engineering framework, used
primarily for x86-64 analysis of Valve's own update tool in this project
([`tools/radare2_setup.md`](tools/radare2_setup.md)).

**xdelta3** — a binary diff/patch tool, used in this repository to
distribute firmware patches as diffs rather than full images
([`patches/README.md`](patches/README.md)), consistent with this project's no-firmware-
redistribution policy.
