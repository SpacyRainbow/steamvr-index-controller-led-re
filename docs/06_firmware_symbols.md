# 06 — Firmware Symbols and Recovered Structures

All addresses in this document are **runtime addresses** with the
application firmware based at `0x412000` (see `05_firmware_layout.md` §5.4
for the discrepancy between this and the `flash_info`-reported flash
offset). To convert to a file offset within the decompressed
`indexcontroller_app_20230902_v1693638519.fw` image: `file_offset = runtime_address - 0x412000`.

## 6.1 Vector table and load address (100% confidence)

The first 16 words of the decompressed application image form a standard
Cortex-M vector table:

```
word[0] = 0x20027c00   ; initial stack pointer (valid nRF52840 SRAM address)
word[1] = 0x00412365   ; Reset_Handler (odd address = Thumb bit set)
word[2] = 0x0041236d   ; NMI_Handler
word[3] = 0x004122e5   ; HardFault_Handler
...
```

This vector table, combined with the live `flash_info` command reporting the
`application` region's *size* (204800 bytes allocated, 197940 used — see
`05_firmware_layout.md`), was used to empirically confirm `0x412000` as the
correct disassembly base address: the reset handler and all internal
references only resolve consistently at this base.

## 6.2 The compiled-in config defaults table (100% confidence)

### Discovery method

The live debug shell's `config` command (`docs/11_hid_commands.md`) prints
46 live configuration entries, including an exact, distinctive sequence of
battery-calibration integers:
`charge_voltage_limit_mv=4320, charge_current_ma=896,
charging_low_temp_threshold_c=15, charge_current_low_temp_ma=220, ...`.
Searching the decompressed firmware for these exact values as consecutive
32-bit little-endian integers located a byte-for-byte match, which was then
used to reverse-engineer the surrounding structure.

### Structure layout

Each config entry is a **9-byte packed structure** (no padding — this
firmware appears to be compiled with a packed-struct attribute for this
table), starting at file offset `0x2C594` (runtime `0x43E594`) in the
decompressed `indexcontroller_app_20230902_v1693638519.fw` image:

```c
struct config_entry {
    uint8_t  type;        // offset 0: type/flag tag
    uint32_t name_ptr;     // offset 1: pointer to this entry's own name string
                            //           (NOT a second copy of the value — verified,
                            //            see below)
    int32_t  value;         // offset 5: the actual value, reinterpret as float
                              // for fsr_grip_*/fsr_thumb_* entries
} __attribute__((packed));  // sizeof == 9
```

Observed `type` tag values: `0x01` for boolean entries (`vrc`, `radio`,
`trigger`, `thumbstick`, `haptics`, `fsr` all use this tag with value `1` =
TRUE), `0x07`/`0x08` for plain int32 entries (no confirmed semantic
difference between these two found), `0x0a` for the one observed string
entry (`product_name`).

### Verification

All 30 numeric/boolean entries (indices 0–29 of the live 46-entry `config`
dump) were decoded from this table and compared byte-for-byte against the
live values read from real hardware — **every single one matched exactly**.
The table format breaks down after index 30 (`product_name`, a
variable-length string, which does not fit the fixed 9-byte stride), which
is expected and not a discrepancy — the fixed-size struct assumption was
never claimed to extend to variable-length entries. See
`scripts/decode_config_table.py` for the exact decoder and
`research/firmware_analysis/config_table_decode_output.txt` for the full
verification output.

### The `name_ptr` field's role (verified, not just theorized)

Initial hypothesis was that this field might be a duplicate/second copy of
the value, or a pointer to further metadata. Direct inspection of the bytes
at the address it points to showed ASCII text — specifically, the entry's
own name string (e.g., the `led_driver_current_r` entry's `name_ptr` field
points to a location containing the literal bytes for
`"led_driver_current_r\0"`). This was confirmed for all four LED-current
entries. The field is used to print the human-readable config table (e.g.,
for the `config` debug shell command), not to store or duplicate the value.

### LED-relevant entries

| Index | Name | Type | Live value (as of primary analysis) | File offset (value field) |
|---|---|---|---|---|
| 26 | `led_driver_current_r` | int32 | `8` | `0x2C683` |
| 27 | `led_driver_current_g` | int32 | `8` | `0x2C68C` |
| 28 | `led_driver_current_b` | int32 | `8` | `0x2C695` |
| 29 | `led_driver_current_w` | int32 | `8` | `0x2C69E` |

These are the exact byte locations patched in `docs/15_firmware_patching.md`
Experiment 6. Note (see `docs/16_charging_led_research.md`): these values
scale LED *brightness/current*, not the base color — they are a
multiplicative stage applied after the actual color is already determined,
per the traced code in §6.3 below.

### Full config table decode

The complete 46-entry decoded table (including non-LED entries: battery
calibration, trigger/thumbstick calibration ranges, FSR grip coefficients,
`product_name`, `finger_type`, `sensor_enable`, `debug` flag, etc.) is
preserved in `research/firmware_analysis/config_table_decode_output.txt`.

## 6.3 LED color pipeline functions (100% confidence for structure, live-verified for behavior)

Full narrative and call-graph description in `docs/07_led_architecture.md`.
This section is the symbol table reference.

| Address | Name (assigned) | Role | Callers found |
|---|---|---|---|
| `0x41DBF0` | low-level LP5562 PWM writer | Extracts W/R/G/B bytes from a packed 32-bit color and writes each to LP5562 registers (`0x10`/`0x30`/`0x50` for R/G/B; W handled via a separate branch) via `0x4232C4` | Exactly 2 direct callers: `0x41D7DE` (inside the color wrapper below) and `0x41E830` (inside the "off-path" function below) — exhaustively verified via a brute-force scan of every possible `BL` instruction encoding across the entire firmware image, not just a disassembly-dependent search |
| `0x419250` | per-channel calibration scaler | `out_channel = (in_channel * calibration_byte) / 100` for each of W/R/G/B, using a per-LED calibration struct pointer | 5 callers found (both LP5562 and GPIO driver paths use it) |
| `0x4232C4` | single-channel register writer | Writes one channel's PWM/current value to the LP5562 over I2C (not further disassembled at the I2C-transaction level) | called from `0x41DBF0` |
| `0x41D7AC` | color-request wrapper (note: entry point is `0x41D7AC`, *not* `0x41D7A8` — an early manual-disassembly mistake mis-identified the entry by 4 bytes; `0x41D7A8` is actually a preceding data word, a RAM pointer, not code) | Checks a per-LED "was off" flag; if set, first calls the off-path function, then always calls the low-level writer with the caller-supplied color | 3 direct callers (all in an unbounded code region Ghidra's auto-analysis did not include in any function — see `docs/07_led_architecture.md` §"Unbounded code regions") |
| `0x41E7D8` | "off-path" function | Performs several hardware-capability checks, then calls the low-level writer with a literal packed color of `0` | 2 direct callers |
| `0x41D764` | GPIO-driver color writer | Parallel, simpler code path for the `led_driver_gpio.c` driver — not the primary I2C/LP5562 path | 3 direct callers |
| `0x41D6B4` | per-LED state-struct applier | Copies a 4-word {color, ?, glow_pattern_id, ?} struct into per-LED persistent storage, then calls the GPIO writer and either an RTOS notification function (no glow) or a "start glow pattern" function | 2 direct callers |
| `0x41D804` | per-LED-type dispatcher | Reads a byte at struct-offset `+3`; if it equals `2`, calls one function-pointer field, otherwise a different one — genuine hardware-type dispatch (LP5562 vs. GPIO, believed), **not** a state (ready/charging) dispatch | 1 direct caller (`0x430732`, not further traced) |

### A note on the two "vtable" false leads

Early in the investigation, an indirect `blx` call pattern
(`ldr r2,[r0,#8]; blx r2`) was found and initially misattributed to the
`0x41D7AC` wrapper function, leading to a substantial and ultimately
unproductive search for a "state dispatch vtable." This pattern actually
belongs to the unrelated `0x41D804` per-LED-type dispatcher (§ above), which
was only correctly identified after installing Ghidra and getting a clean
decompilation. This is preserved here, and expanded on in
`docs/14_failed_attempts.md`, as a concrete example of how manual
disassembly without proper tooling can misattribute code to the wrong
function boundary — a mistake worth watching for in any continuation of
this work.

## 6.4 Notable strings (LED subsystem)

Full list preserved in `research/firmware_analysis/strings_led_all.txt`.
Highlights:

- `"LED %u: color = 0x%06X->0x%06X, status: %u, blink_on = %s\n"` — proves
  the firmware internally supports transitioning any LED between two
  arbitrary 24-bit RGB colors with a blink flag, addressed by numeric ID.
  This is the single strongest piece of string evidence for the project's
  core conclusion.
- `"Invalid LED ID %u\n"` — confirms multiple LED IDs are a valid concept in
  this firmware, though this project only ever observed behavior consistent
  with a single physical status LED.
- `"glow not supported\n"` — printed unconditionally by one of the
  LED-setting entry points (§6.3, `0x41D908`region), suggesting a "glow"
  (breathing/pulsing) feature exists in the driver architecture but is
  disabled or unimplemented for this LED/hardware configuration.
- `"led_driver_lp5562.c"`, `"led_driver_gpio.c"`, `"led_policy_knuckles.c"`,
  `"led.c"` — compiler-embedded source filenames, used throughout this
  project as anchors for locating related code (the debug/log macro
  convention in this firmware embeds the source filename as a string
  immediately preceded by a 4-byte RAM pointer, believed to be a
  module-specific log-gating variable).

## 6.5 What is NOT yet mapped

- The RTOS task functions themselves (only referenced by name via the
  debug shell's `tasks` command output — `shell, IDLE, sync on beam,
  watchman, vrc, sync on beam bg, wdt, Tmr Svc, battery, imu, fpga, power`
  — not located as addresses in the disassembly).
- The power-management (`PM`) and battery-management (`BM`) state-machine
  functions beyond the narrow slice examined in
  `docs/16_charging_led_research.md`.
- Any function in the `0x430000`+ address range beyond the handful of
  addresses referenced as call targets from the LED subsystem.
