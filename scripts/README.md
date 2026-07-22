# scripts/

All scripts are Python 3, standard library only unless noted. All were
developed and tested on Linux against a wired Valve Index Controller. None
have been tested on Windows or macOS.

**Common prerequisite for every HID-interacting script below:** the
`/dev/hidrawN` device paths hardcoded or passed to these scripts are **not
stable** across reboots, USB reconnects, or firmware flashes. Always run
`dump_hid_descriptors.py` first in any new session to find the current
node numbers before using any other script. See
`../docs/12_debug_interfaces.md`.

---

## `dump_hid_descriptors.py`

**Purpose:** enumerate every `hidraw` device from vendor ID `0x28de`
(Valve) and dump its raw HID report descriptor via the `HIDIOCGRDESC`
ioctl.

**Requirements:** read access to `/dev/hidraw*` (typically works
unprivileged on Linux distributions that ship udev rules granting user
access to Valve devices, e.g. via SteamVR's own installed udev rules).

**Usage:** `python3 dump_hid_descriptors.py`

**Expected output:** for each matching device, its vendor:product ID, USB
`phys` path, report descriptor size, and raw descriptor hex.

**Limitations:** does not parse the descriptor (see
`parse_hid_descriptor.py` for that); will report `OPEN FAILED (Permission
denied)` for any hidraw node it lacks access to rather than failing
entirely.

**Known bug fixed during development:** an early version double-closed the
file descriptor (explicit `os.close()` before a `continue` that was also
inside a `try/finally` that closed it again), causing a spurious `Bad file
descriptor` error. Fixed by removing the redundant explicit close.

---

## `parse_hid_descriptor.py`

**Purpose:** minimal HID report descriptor byte-stream parser, extracting
`(report_id, type, size_bits)` tuples from raw descriptor bytes (as
produced by `dump_hid_descriptors.py`).

**Requirements:** none beyond Python 3 stdlib.

**Usage:** import and call the parser function against raw descriptor
bytes, or invoke against captured output — see
`../research/captures/report_map_parsed.txt` for example output.

**Limitations:** handles only the specific tag subset actually observed in
this project's descriptors (Usage Page/Usage, Logical Min/Max, Report
Size/Count, Report ID, Input/Output/Feature, Collection/End Collection) —
not a general-purpose HID descriptor parser.

---

## `read_feature_reports.py`

**Purpose:** passive `GET_FEATURE` sweep across every known Feature report
ID on every discovered interface, to characterize which reports are
readable.

**Requirements:** read/write access to the target `hidraw` device.

**Usage:** `python3 read_feature_reports.py` (edit the target device
list/paths at the top of the file for your current session's node numbers).

**Expected output:** for each report ID, either the returned feature data
or an `EPIPE`/`errno` if the report is write-only or otherwise unreadable.

**Limitations:** purely observational; does not attempt any writes. See
`test_feature_toggle_candidates.py` for the write-testing counterpart.

---

## `test_feature_toggle_candidates.py`

**Purpose:** `SET_FEATURE` testing of specific single-byte report IDs
identified as toggle candidates. **This is the script that discovered the
undocumented Debug interface** (`../docs/12_debug_interfaces.md`,
`../docs/13_experiments.md` Experiment 2) — running it with report `0x12`
set to `0x01` triggers the device to reset and expose a 4th "Debug" HID
interface.

**Requirements:** read/write access to the target `hidraw` device.

**Usage:** `python3 test_feature_toggle_candidates.py`

**Expected output:** for each candidate report, confirmation of the
`SET_FEATURE` call succeeding, followed by an attempt to revert. Note: the
revert attempt for report `0x12` is *expected* to fail with `ENODEV` — the
device has already reset by that point, which is the interesting result,
not an error to be fixed.

**Limitations/safety note:** this script deliberately triggers a device
reset. Not destructive (confirmed safe, reproduced many times across this
project), but be aware it will interrupt any other active HID session with
the device.

---

## `probe_debug_shell.py`

**Purpose:** preserved specifically as the *buggy* first version of the
debug-shell communication attempt, documenting the wire-framing discovery
process (`../docs/12_debug_interfaces.md`, `../docs/13_experiments.md`
Experiment 3). Sends command text starting at the wrong buffer offset,
producing a truncated response.

**Use this for historical/educational reference only — use
`debug_shell.py` for actual work.**

---

## `debug_shell.py`

**Purpose:** the corrected, reusable client for the Debug interface's text
command shell. Exposes a `run(cmd)` function returning the decoded ASCII
response.

**Requirements:** the Debug interface must already be enabled
(`../docs/12_debug_interfaces.md` — a one-time `SET_FEATURE` call per
session/boot) and its current `hidraw` node identified.

**Usage:**
```python
from debug_shell import run
print(run("info"))
print(run("config"))
```
or from the command line: `python3 debug_shell.py info`

**Expected output:** the decoded text response from the firmware, exactly
as it would appear if you had a native terminal connection to the shell.

**Limitations:** hardcodes `PATH = '/dev/hidraw4'` (or whatever value was
current in the last edit) at the top of the file — **you must update this
to match your current session's Debug-interface node** before use. This is
a deliberate simplicity choice for a single-session research tool, not an
oversight; a more robust version would auto-discover the correct node.

**Full command catalogue discovered through this script:**
`../docs/11_hid_commands.md`.

---

## `listen_debug.py`

**Purpose:** passively read the Debug interface for a specified duration,
printing any unsolicited (not command-triggered) output — used in an
attempt to catch spontaneous firmware log lines (e.g., LED color-change
events). See `../docs/14_failed_attempts.md` for the outcome (no
spontaneous output was captured in the scenarios tried).

**Requirements:** same as `debug_shell.py`.

**Usage:** `python3 listen_debug.py <duration_seconds>`

**Limitations:** this is a genuinely useful tool for a *retry* of the
log-listening approach (`../docs/18_future_work.md` Priority 1) but did not
itself produce a positive result in this project.

---

## `decode_config_table.py`

**Purpose:** decode the compiled-in config defaults table
(`../docs/06_firmware_symbols.md` §6.2) from a decompressed firmware image,
printing every entry's type, name-pointer, and value, with a built-in
cross-check against the live values captured from the debug shell's
`config` command.

**Requirements:** a decompressed firmware image (see
`../docs/04_firmware_acquisition.md`).

**Usage:** edit the `FW` path constant at the top of the file to point at
your decompressed image, then `python3 decode_config_table.py`.

**Expected output:** a table with columns for index, name, flag byte,
name-pointer address, file offset, decoded int32/float value, and the
corresponding live value with a match/no-match indicator. Full example
output preserved in
`../research/firmware_analysis/config_table_decode_output.txt`.

**Limitations:** the table-start offset (`TABLE_START = 0x2c594`) and
struct layout are specific to the primary analysis target firmware
(`indexcontroller_app_20230902_v1693638519.fw`) — not verified against
other builds.

---

## `disasm_config.py`

**Purpose:** lightweight Thumb-2 disassembly helper built on the
`capstone` library, used for early manual disassembly work before Ghidra
was set up (`../tools/ghidra_setup.md`). Provides a `range` subcommand
(linear disassembly of a byte range) and an `xref` subcommand (a manual
MOVW/MOVT-pair-based cross-reference search — largely superseded by
Ghidra's proper reference analysis once available, but preserved since it
was used to produce several documented findings before that point).

**Requirements:** `pip install capstone`.

**Usage:** `python3 disasm_config.py range <hex_offset> <hex_length>` or
`python3 disasm_config.py xref <hex_addr1> [hex_addr2...]`

**Limitations:** performs purely linear disassembly with no function-
boundary awareness — it will happily "disassemble" data bytes as if they
were code when run across a region containing embedded data (this
limitation is discussed at length in `../docs/14_failed_attempts.md` and is
part of why Ghidra was later adopted for deeper work). Useful for quick,
targeted checks of a known-good code region; not reliable for broad
exploratory scanning.

---

## `patch_led_firmware.py`

**Purpose:** Patch A — set all four `led_driver_current_{r,g,b,w}` config
values to a caller-specified integer and rebuild a valid `.fw` file. Full
documentation: `../docs/15_firmware_patching.md` §15.3 "Patch A",
`../patches/README.md`.

**Requirements:** the original, unmodified `.fw` source file (path
hardcoded near the top of the script — update `ORIG_FW` to your local
SteamVR installation path), Python 3 stdlib only.

**Usage:** `python3 patch_led_firmware.py <value>` (e.g. `255` or `0`).
Writes output to `04_firmware/patched/` (path relative to the script's
original working directory — adjust `OUT_DIR` if reusing elsewhere).

**Expected output:** console log of each patched field's old/new value,
the recompressed size, recomputed CRCs, and a PASS/FAIL round-trip
verification before the file is trusted for flashing.

**Limitations:** does not by itself achieve a full LED blackout — see
`../docs/08_lp5562_driver.md` and `../docs/13_experiments.md` Experiment 6
for why, and `patch_led_black.py` for the patch that does.

---

## `patch_led_black.py`

**Purpose:** Patch B — the project's primary proven positive-result patch.
Replaces a single 2-byte instruction to force every LED color request to
black, unconditionally. Full documentation:
`../docs/15_firmware_patching.md` §15.3 "Patch B",
`../docs/13_experiments.md` Experiment 7, `../patches/README.md`.

**Requirements:** same as `patch_led_firmware.py`.

**Usage:** `python3 patch_led_black.py` (no arguments).

**Expected output:** confirmation of the exact byte replacement, the
recompressed size, recomputed CRCs, and a PASS/FAIL round-trip
verification. The script **refuses to patch** and aborts loudly if the
expected original bytes are not found at the target offset — this is a
deliberate safety check, not a bug, and should never be bypassed.

**Limitations:** the target offset is specific to the exact firmware build
documented in `hashes/firmware_hashes.txt` — see
`../docs/17_safety.md` "Version compatibility warnings."

---

## `patch_led_solid_color.py`

**Purpose:** Patch C — generalizes `patch_led_black.py`'s technique to any
single-byte value, producing shades of pure blue instead of only black.
**UNTESTED on real hardware** — built and file-verified only, during a
session with no physical access to the controller. Full documentation:
`../docs/15_firmware_patching.md` §15.3 "Patch C",
`../docs/18_future_work.md` Priority 1 (flashing/verifying this is the
recommended first task for the next session with hardware access),
`../patches/README.md`.

**Requirements:** same as `patch_led_black.py`.

**Usage:** `python3 patch_led_solid_color.py <0-255>` (e.g. `255` for
maximum-intensity blue; `0` is equivalent to `patch_led_black.py`, but use
that script directly for the black case since it's the proven one).

**Expected output:** same structure as `patch_led_black.py` — byte
replacement confirmation, recompressed size, recomputed CRCs, and a
PASS/FAIL round-trip verification, plus an explicit printed reminder that
the output has not been flashed to real hardware.

**Limitations:** same firmware-build specificity as `patch_led_black.py`.
Additionally, and more fundamentally: this technique can only reach colors
of the form (W=0, R=0, G=0, B=n) — pure blue shades — because the
underlying Thumb instruction (`movs Rd, #imm8`) zero-extends into the
whole register, not just one byte. It **cannot** produce red, green, or
any two-channel combination like purple. See
`../docs/15_firmware_patching.md` §15.3 "Why a code-cave is needed for
two-channel colors" for why, and what a purple-capable patch would
actually require.

---

## `test_haptic_sanity_check.py`

**Purpose:** early-project sanity check confirming the wired controller
accepts Output report `0x01` (the documented haptic-pulse command, per
`hid-steam.c`/LighthouseRedox precedent — see `../docs/02_background.md`),
establishing that the wired connection is a genuine full-featured HID link
before investing further effort in HID-based investigation.

**Requirements:** read/write access to the controller's primary HID
interface.

**Usage:** `python3 test_haptic_sanity_check.py`

**Expected output:** confirmation that three haptic command variants were
successfully written (64 bytes each, including report-ID prefix).

**Limitations:** whether the controller actually produced a physical
haptic buzz was never independently confirmed by the human tester in this
project (an oversight, not a negative result) — this script only confirms
the *write* succeeded, not the physical effect.
