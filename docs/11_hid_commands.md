# 11 — Debug Shell Commands

All commands below are issued over the undocumented USB HID "Debug"
interface (`docs/12_debug_interfaces.md`). All were tested live against the
project's test controller (serial `LHR-XXXXXXXX`). Full raw transcripts are
preserved in `research/captures/`.

For each command: where it was discovered, what was tested, the exact
output observed, and confidence in the interpretation given.

## Full command list (discovered via `help`)

```
help, info, set_gpio_level, get_gpio_level, set_gpio_dir, spi, watchman,
imu, usb, wdt, reset, shutdown, tasks, flash_info, user_flash, queue,
route, battery, config, user_data, lep, schedule, fpga, power, haptics,
radio, controller, trackpad, fingers
```

Discovered by sending `help\n` after correctly reverse-engineering the wire
framing (see `docs/12_debug_interfaces.md` for the framing bug and fix).
**Confidence: 100%**, reproduced live, response captured in full.

## `info`

**Purpose:** device identity and firmware version report.
**Tested:** yes, multiple times across the project (used as a standard
"is the device alive and which firmware is running" health check after
every firmware flash).

```
S/N: LHR-XXXXXXXX
HWID: 0x110e0009 (Index Controller)
App ver: 0x64f2df77 1693638519 / 2023-09-02 00:08:39 git: 2c3286c3
Radio ver: 0x5d27b2a9 1562882729
FPGA ver: 0x21a 538
```

**Confidence: 100%.**

## `config`

**Purpose:** dumps all 46 live compiled-in configuration values.
**Tested:** yes, extensively — this command's output was the anchor used to
reverse engineer the config defaults table structure
(`docs/06_firmware_symbols.md` §6.2).

Sample (full 46-entry dump preserved in
`research/captures/debug_shell_config_syntax.txt`):

```
Config: 1508 of 3072 bytes
  0: vrc                             (0x7e589aed) = TRUE
  ...
 26: led_driver_current_r            (0x7765723d) = 8 (0x00000008)
 27: led_driver_current_g            (0xd9e4b742) = 8 (0x00000008)
 28: led_driver_current_b            (0x233149da) = 8 (0x00000008)
 29: led_driver_current_w            (0xfdd37f1b) = 8 (0x00000008)
  ...
 45: debug                           (0x0addd94c) = 1 (0x00000001)
```

**Write behavior: read-only via this shell (confirmed dead end).** `config
set <key> <value>`, `config get <key>`, and several other argument
combinations were tried; all silently produced the same full read-only dump
with no error and no value change, unlike commands with genuine argument
validation (see `set_gpio_level` below, which correctly reports an error on
bad input). See `docs/14_failed_attempts.md` for the full list of syntaxes
tried. **Confidence the shell cannot write config: 90%** — it is possible an
undiscovered syntax exists, but the behavior (silent no-op rather than an
error) is consistent with there being no write path through this specific
command at all.

## `flash_info`

**Purpose:** reports the six-region code/RAM layout and the full named
flash partition table.
**Tested:** yes. Output reproduced verbatim in `docs/05_firmware_layout.md`
§5.3. This command was the source of the `0x412000` vs. flash-offset
`0x012000` discrepancy discussed there.

**Confidence: 100%** for the values reported; the *interpretation* of some
fields (e.g. the `hardware_id` region's placeholder-looking address) is
lower confidence.

## `battery`

**Purpose:** live battery/charging telemetry.
**Tested:** yes, used specifically to attempt correlating charging state
with LED color (`docs/16_charging_led_research.md`).

Sample output:

```
vbus: state: host
usb: enumerated: yes, power good: yes, input cur limit: 500 mA
battery: detected: yes, in termination: yes, state of charge: 100 %,
         voltage: 4242 mV, average current: 0 mA, capacity remaining: 674 mAh
fuel gauge: external temp: 30.9 C, internal temp: 30.9 C, flags: 0x0208,
            control status: 0x039a, cycle_count: 0x0
charger: connected: yes, state: charge term
Fuel gauge: bq27421
DM Code: 97 (0x0061)
```

**Confidence: 100%** for the telemetry values shown; this directly confirms
a live `bq27421` fuel gauge (`docs/03_hardware.md`) and a `charge term`
charging state at the time of capture.

## `set_gpio_level` / `get_gpio_level` / `set_gpio_dir`

**Purpose:** direct read/write of named GPIO pins (e.g. `PA21`).
**Tested:** usage text only (`<addr> (eg PA21)`, `<level> (high/low or h/l)`)
— not used to actually toggle a pin during this project, since the FPGA
"led" GPIO pin name found in firmware strings (a GPIO pin-name table entry,
`docs/06_firmware_symbols.md`) was not conclusively mapped to a specific
`PAxx`/`PBxx` address. **Confidence: 100%** these commands exist and have
correct-syntax validation (confirmed by triggering a proper `"Argument
Input error"` on bad input, which is notably *different* behavior from
`config`'s silent no-op — this contrast is what established that `config`'s
write behavior specifically is a dead end rather than a general shell
limitation).

## `battery`, `power`, `haptics`, `controller`, `trackpad`, `fingers`, `watchman`, `imu`, `lep`, `schedule`, `tasks`, `route`, `queue`

All tested with no arguments to observe default/usage behavior. Summary:

| Command | Observed behavior | Confidence |
|---|---|---|
| `power` | `power get` returns `PM: level 0`; `power set <level>` implied by usage text, not exercised | 100% for `get`, untested for `set` |
| `haptics` | Returned empty response with no arguments | 100% (behavior observed; purpose beyond that not explored) |
| `controller` | Live VRC state dump: buttons, trigger, fsr, trackpad, thumbstick, fingers values | 100% |
| `trackpad`, `fingers` | Not separately explored beyond appearing in `controller`'s combined output | n/a |
| `watchman` | `watchman suspend` / `watchman resume` both work, produce `Watchman: suspend` / `Watchman: resume (Controller)` responses; used in an attempt to trigger a state-change log (unsuccessful) — see `docs/14_failed_attempts.md` | 100% (commands work) |
| `imu` | Reports `running 250 Hz 2000 dps 8 G` | 100% |
| `lep` | Lighthouse Edge Processor stats — output captured but not analyzed in depth | 100% (command exists), low confidence on interpretation |
| `schedule` | Usage: `disable`/`enable`/`test`/`apply <seconds> <32b sensor mask, base16>` — not exercised beyond usage text | n/a |
| `tasks` | Returns the 12-entry RTOS task list: `shell, IDLE, sync on beam, watchman, vrc, sync on beam bg, wdt, Tmr Svc, battery, imu, fpga, power` | 100% — this list is the basis for believing an `vrc` task (not directly confirmed) handles LED policy, discussed in `docs/16_charging_led_research.md` |
| `route` | Returns `MSG route: USB` | 100%, purpose (whether this affects async log streaming) not conclusively determined |
| `queue` | Returned empty with no arguments | 100% (behavior observed), purpose not explored further |

## `reset`, `shutdown`, `wdt`, `usb`

Used operationally throughout the project (`reset` in particular, to
trigger a reboot after firmware flashes) but not independently
"documented" beyond their obvious function. `shutdown` and `wdt` were never
exercised (deliberately, to avoid unnecessary device state changes not
needed for the research question).

## `user_flash`, `user_data`

**Purpose (inferred):** `user_flash` returned an empty response to a bare
invocation and to `user_flash help` — its purpose was not determined.
`user_data` returned proper usage text:
```
user_data header       header information
user_data entry <name> information on the named entry
user_data all          information the header and all entries
```
These commands were investigated as a possible alternative, lower-risk path
to writing config values (as opposed to a full firmware reflash) but were
not pursued to conclusion within this project's time budget. **This is
flagged as a priority item in `docs/18_future_work.md`** — if
`led_driver_current_*` (or the actual LED policy state) turns out to live in
the separate `stored_conf`/`data_store` flash partitions rather than the
compiled-in application defaults table, `user_data`/`user_flash` may be the
correct, much lower-risk write path instead of a full application reflash.

## `spi`, `radio`, `fpga`

Present in the command list; not exercised in this project beyond
confirming they exist via `help`. Purpose inferred from name only (SPI
flash access, radio subsystem control, FPGA control respectively).
