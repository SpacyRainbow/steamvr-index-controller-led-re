# Valve Index Controller — LED Software Control Reverse Engineering

**A research journal, technical reference, and reproducible engineering record
investigating whether the Valve Index Controller's status LED can be
controlled by software beyond documented SteamVR/OpenVR behavior.**

This is not a release announcement. It is the working archive of an active
reverse-engineering investigation, written so that another engineer — with no
access to the original research session — can understand exactly what was
found, how it was found, what failed, and what remains open.

---

## Project status

**Active / paused between sessions.** See [`docs/18_future_work.md`](docs/18_future_work.md) for the
current task queue and `research/daily_logs/` for the most recent session log.

## Core question and answer

> Can the Valve Index Controller's status LED be controlled by software
> beyond what SteamVR/OpenVR expose?

**Answer: Yes — confidence 97%.** This has been directly demonstrated on real
hardware: a modified firmware image, built and flashed entirely through
software (no debugger, no chip-off, no soldering), changed the controller's
real-world visible LED behavior (verified by a human observer watching the
physical device). See [`docs/13_experiments.md`](docs/13_experiments.md) (Experiments 6 and 7) for the
full evidence trail.

The remaining 3% is not about *whether* software control is possible — that
is proven — it is about how *finely* that control can be exercised. A
blanket "LED always off" patch is proven and repeatable. A *selective* patch
(e.g. "off only while not charging, but preserve the charging/charged
indicator colors") is understood at the architecture level but not yet fully
traced to the exact code that decides those colors. See
[`docs/16_charging_led_research.md`](docs/16_charging_led_research.md).

## Major discoveries (with confidence levels)

| # | Finding | Confidence | Reference |
|---|---|---|---|
| 1 | Firmware is unencrypted, zlib-compressed with a self-describing footer | 100% (reproduced on 5 files) | [`docs/04_firmware_acquisition.md`](docs/04_firmware_acquisition.md), [`docs/05_firmware_layout.md`](docs/05_firmware_layout.md) |
| 2 | LED hardware is a TI LP5562 I2C RGBW driver, not a simple GPIO LED | 95% | [`docs/08_lp5562_driver.md`](docs/08_lp5562_driver.md) |
| 3 | An undocumented USB HID "Debug" interface exists and is trivially unlockable | 100% (reproduced live) | [`docs/12_debug_interfaces.md`](docs/12_debug_interfaces.md) |
| 4 | The live debug shell can read (not write) firmware config values | 100% (reproduced live) | [`docs/11_hid_commands.md`](docs/11_hid_commands.md) |
| 5 | Valve's own firmware update tool can be driven from Linux to push arbitrary modified firmware to the real device | 100% (reproduced live, 4 successful flashes) | [`docs/10_protocol_analysis.md`](docs/10_protocol_analysis.md), [`docs/13_experiments.md`](docs/13_experiments.md) |
| 6 | The `.fw` container's trailing CRC field is a self-referential CRC-32, fully reverse engineered | 100% (verified against all known-good firmware files) | [`docs/05_firmware_layout.md`](docs/05_firmware_layout.md) |
| 7 | The compiled-in config defaults table structure (9-byte packed entries) is fully mapped | 100% (verified against 30 live values) | [`docs/06_firmware_symbols.md`](docs/06_firmware_symbols.md) |
| 8 | The low-level LED PWM-write function was located, patched, and the patch visually confirmed to turn the LED off on real hardware | 100% (reproduced live) | [`docs/15_firmware_patching.md`](docs/15_firmware_patching.md), [`docs/13_experiments.md`](docs/13_experiments.md) Experiment 7 |
| 9 | The state-to-color policy decision (which color for "charging" vs "ready") is **not yet located** — it lives beyond an RTOS task boundary (shared state, not a direct call) | Hypothesis, ~70% | [`docs/16_charging_led_research.md`](docs/16_charging_led_research.md) |

## What didn't work

This project treats a documented dead end as a real deliverable, not a
footnote — reproducing a failed approach costs real time, and the whole
point of this archive is to save the next person that time. Every failed
technique below is written up in full (what was tried, why it seemed
reasonable, why it failed, what it ruled out) in
**[`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)**. Headline entries:

- The debug shell's `config` command cannot write values through any
  syntax tried — real time was spent confirming this negative result
  before pivoting to firmware flashing instead, which worked.
- Three independent, individually-reliable methods (Ghidra's reference
  manager, an exhaustive brute-force call-site search, a raw stored-pointer
  search) all failed to find who calls the LED policy's per-state entry
  points — see [`docs/16_charging_led_research.md`](docs/16_charging_led_research.md) for why this consistent
  failure is itself meaningful evidence, not just "didn't look hard
  enough."
- An early manual (pre-Ghidra) disassembly pass misattributed an indirect
  call pattern to the wrong function, sending part of the investigation
  down a wrong path for a while — preserved as a concrete cautionary
  example of how manual ARM disassembly without independently-verified
  function boundaries can go wrong.
- `--restore-json` (Valve's own update tool flag) never produced a
  findable configuration backup file in this project's testing, despite
  two full successful firmware updates.
- **Current, unresolved:** as of the most recent session, firmware
  flashing itself is broken — the update tool locally rejects every file
  built by this project's patch pipeline, including a fresh rebuild of the
  *already-proven* black patch, while the unmodified original firmware
  still flashes fine. Zero device risk (every rejection happens before any
  device communication), but it blocks further live patching until
  resolved. See [`docs/13_experiments.md`](docs/13_experiments.md) Experiment 9.

None of this is hidden in a "known issues" appendix — [`docs/14_failed_attempts.md`](docs/14_failed_attempts.md)
is linked from the repository layout below like every other document, and
individual dead ends are cross-referenced from whichever `docs/` page they
relate to, so you hit them in context, not just in one long list.

## Hardware and software scope

- **Controller tested:** wired Valve Index Controller, serial `LHR-XXXXXXXX`,
  HWID `0x110e0009`.
- **Firmware analyzed:** `indexcontroller_app_20230902_v1693638519.fw`
  (2023-09-02, git `2c3286c3`) as the primary target, cross-checked against
  four other historical firmware builds. See [`hashes/firmware_hashes.txt`](hashes/firmware_hashes.txt) for
  exact versions and SHA-256 sums.
- **SteamVR version used:** build ID `23791826` (Steam depot manifest
  timestamp 2026-06-17).
- **Host OS:** Linux (Fedora/Nobara-based), no Windows testing performed.
- **Not tested:** wireless-only (dongle) controllers, other controller
  hardware revisions, any Index Controller other than the single unit
  described above.

## Repository layout

```
README.md                      you are here
LICENSE                        MIT license for original work (see scope note inside)
SECURITY.md                     the one security-relevant finding, and why it wasn't formally disclosed
CONTRIBUTING.md                 how to contribute: verify claims, continue open research, report dead ends
GLOSSARY.md                     terms, acronyms, and project-specific shorthand used throughout
requirements.txt                Python dependencies for scripts/

docs/                           the primary technical reference, read in order
  01_project_overview.md          what this project is and why it exists
  02_background.md                prior art, related projects, starting knowledge
  03_hardware.md                  MCU/FPGA/flash/LED driver hardware inventory
  04_firmware_acquisition.md      how to obtain and extract firmware, reproducibly
  05_firmware_layout.md           .fw container format, footer, CRC algorithm
  06_firmware_symbols.md          recovered structures: config table, functions
  07_led_architecture.md          the LED subsystem call graph, driver -> policy -> HW
  08_lp5562_driver.md             the LP5562 chip and its firmware driver
  09_led_policy.md                what is and isn't known about state-to-color logic
  10_protocol_analysis.md         the JSON/zlib config protocol and LWU update protocol
  11_hid_commands.md              every debug-shell command discovered, with evidence
  12_debug_interfaces.md          the undocumented USB HID Debug interface
  13_experiments.md               every experiment performed, in full scientific format
  14_failed_attempts.md           dead ends, preserved deliberately
  15_firmware_patching.md         patch mechanics: .fw format, footer CRC, byte patches
  16_charging_led_research.md     the open problem: selective color patching
  17_safety.md                    brick risk, recovery, rollback, what NOT to do
  18_future_work.md               prioritized roadmap for continuing this work

research/                       raw research material, organized but unedited
  daily_logs/                     chronological session logs
  notes/                          scratch notes and working hypotheses
  screenshots/                    (none captured yet — see 18_future_work.md)
  captures/                       raw USB HID descriptor dumps, debug shell transcripts
  firmware_analysis/              raw disassembly/decompiler output referenced by docs/
  decompiler_notes/               Ghidra script source and setup notes

scripts/                        all analysis/automation scripts, documented
tools/                          notes on third-party tools used (radare2, Ghidra, etc.)
patches/                        firmware patch generators and their documentation
captures/                       (reserved for future USB traffic captures)
images/                         (reserved for hardware photographs — none taken yet)
firmware/                       NOT firmware binaries — instructions for obtaining them
hashes/                         SHA-256 manifests for every firmware artifact referenced
tests/                          automated tests for reusable logic (synthetic data only)
```

## Quick start

**To reproduce the read-only findings** (HID descriptor mapping, debug shell
access, config readout) you need: a wired Valve Index Controller, Linux,
Python 3, and SteamVR installed (for the firmware files and the official
update tool). Start with [`docs/04_firmware_acquisition.md`](docs/04_firmware_acquisition.md) and
[`docs/12_debug_interfaces.md`](docs/12_debug_interfaces.md).

**To reproduce the firmware patching work** you additionally need root access
(via `sudo` or `pkexec`) and are advised to read [`docs/17_safety.md`](docs/17_safety.md) in full
before writing anything to real hardware.

**To continue the open research** (selective charging-color patch), install
Ghidra per [`tools/ghidra_setup.md`](tools/ghidra_setup.md) and start from
[`docs/16_charging_led_research.md`](docs/16_charging_led_research.md), which documents exactly how far the trace
got and where it stopped.

**To run the automated tests** (synthetic-data-only checks of a few
reusable, self-contained pieces of logic — the `.fw` footer CRC formula,
the config-table struct layout, and the Thumb-2 `BL` instruction encoder),
install the dependencies in [`requirements.txt`](requirements.txt) and run:

```bash
python3 -m unittest discover -s tests -v
```

See [`tests/README.md`](tests/README.md) for what's covered and why.

## Current capabilities (proven, reproducible)

- Extract and decompress any Index Controller firmware image shipped with
  SteamVR.
- Read the controller's live configuration (calibration constants, LED
  driver current values, battery/charging telemetry) via an undocumented USB
  HID debug shell, with no special hardware.
- Build a modified firmware image with an arbitrary patch, repackage it into
  a valid signed/checksummed `.fw` container, and flash it to a real
  controller using Valve's own official tool run under Linux.
- Force the LED fully off via a two-byte code patch, proven on real hardware.

## Known limitations

- **Firmware flashing is currently broken** (as of the most recent
  session) — see "What didn't work" above and
  [`docs/13_experiments.md`](docs/13_experiments.md) Experiment 9. This affects the currently
  buildable Patch C and any re-flash of the already-proven Patch B alike.
- The blanket "LED off" patch disables **all** LED indication, including the
  charging/charged status colors that most users would want to keep. See
  [`docs/16_charging_led_research.md`](docs/16_charging_led_research.md).
- The exact mechanism connecting the power-management RTOS task's charging
  state to the LED policy's color choice has not been located.
- Only one controller unit and one firmware build have been extensively
  tested live. Behavior on other hardware revisions or firmware versions is
  unverified (see [`docs/17_safety.md`](docs/17_safety.md) for version-compatibility notes).
- No photographs or video of the physical LED behavior have been captured
  yet; findings rely on the human tester's direct visual observation,
  recorded as commentary in [`docs/13_experiments.md`](docs/13_experiments.md).
- This repository does not (and per its legal notice, must not) include any
  Valve firmware binary. Anyone reproducing this work needs their own
  legitimate SteamVR installation.

## Warnings

Read [`docs/17_safety.md`](docs/17_safety.md) before attempting any of this on your own hardware.
In summary:

- Flashing modified firmware to a real controller carries a real, if small,
  risk of leaving the device in a bad state. All patching in this project so
  far was performed on hardware the tester explicitly described as already
  damaged / expendable for testing.
- Do not attempt firmware flashing on a controller you are not prepared to
  lose.
- Every reflash cycle resets the debug-mode HID interface off; this is
  expected and does not indicate failure.

## Legal notice

Valve Index Controller firmware, the SteamVR software suite, and the
`lighthouse_watchman_update` tool are the property of Valve Corporation. This
project does not redistribute any of them. Firmware is referenced by
SHA-256 hash only (`hashes/`), and all firmware modifications are documented
as patch instructions/scripts to be applied to a firmware image the reader
obtains themselves from their own legitimate SteamVR installation. Excerpts
of strings, structure layouts, and disassembly shown in this documentation
are included for interoperability and security research purposes and remain
Valve's property. See `LICENSE` for the license scope covering only this
project's original contributions.

## Credits

Investigation and documentation: project contributors (session-based
research, 2026-07-22 through 2026-07-23 and ongoing).

Built on prior public reverse-engineering work on Valve's Lighthouse/Watchman
protocol family, most notably the `nairol/LighthouseRedox` project, which
established HID report ID conventions for the original Vive wand controller
that informed early hypotheses in this project (see [`docs/02_background.md`](docs/02_background.md)).

## Future goals

See [`docs/18_future_work.md`](docs/18_future_work.md) for the full prioritized roadmap. Headline
items:

1. Locate the shared-state connection between the power-management RTOS task
   and the LED policy's color decision, to enable a selective
   (charging-color-preserving) patch.
2. Capture photographic/video evidence of LED behavior for each experiment.
3. Extend the firmware symbol map beyond the LED subsystem.
4. Test firmware compatibility across all historical firmware builds, not
   just the single primary target.
