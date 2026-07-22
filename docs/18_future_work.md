# 18 — Future Work

Prioritized roadmap for continuing this project. Each item includes a
description, difficulty estimate, expected value, likelihood of success,
and recommended approach.

## Priority 1 — Locate the charging-state → LED-color connection

**Description:** find the code (or shared data structure) connecting the
power-management task's charging-state logic to whatever code decides the
LED's color, to enable a selective patch (blank LED during normal use,
preserve charging/charged indication). Full context in
`docs/16_charging_led_research.md`.

**Difficulty:** High. Static call-graph tracing has been exhausted (three
independent methods, all failed to find Layer 3's callers — see
`docs/14_failed_attempts.md`). Remaining approaches require either
data-flow analysis or live hardware observation.

**Expected value:** High — this is the single most user-valuable
improvement over the current "always off" patch, and was the specific
follow-up request that motivated this entire line of investigation.

**Likelihood of success:** Moderate (~50%). The architecture is understood
well enough to know *what kind* of answer to look for (a shared RTOS
variable, most likely); finding the exact location is a matter of applying
the right technique, not an open-ended unknown.

**Recommended approach, in order:**
1. Live USB traffic capture (`usbmon` or a hardware USB tap) during a real
   charging-state transition on the physical device, correlated with
   directly observed/photographed LED color. This sidesteps static analysis
   entirely by providing ground-truth data to work backward from.
2. Ghidra data-flow analysis starting from the power-management task's
   known state-variable write instructions
   (`research/decompiler_notes/pm_gap_listing.txt` has the exact
   addresses), searching for all reads of the same memory location/struct
   field, rather than searching for direct function calls.
3. If hardware access allows it, an SWD/JTAG debug probe on the nRF52840
   for live memory/register inspection — the most direct method, not
   attempted in this project due to lack of the necessary probe hardware.

## Priority 2 — Photographic and video documentation

**Description:** no photographs or video exist of the physical LED
behavior for any state (normal, charging, charged, boot self-test, patched
off) — every observation in this project is the human tester's written
testimony only (`docs/13_experiments.md`).

**Difficulty:** Low — this is a documentation gap, not a research gap.

**Expected value:** High for repository credibility and for resolving the
open "orange/white" color-mapping verification gap noted in
`docs/09_led_policy.md`.

**Likelihood of success:** Very high — purely a matter of doing it.

**Recommended approach:** photograph/video the controller in each known
state (including deliberately triggering charging by connecting/
disconnecting a charge source, if the hardware setup allows observing the
LED while still maintaining a debug-shell connection — note the wired
test setup used in this project could not do both simultaneously, since
the same USB cable provides both power and the debug HID connection; a
setup with independent charging (e.g., a charging dock) and a separate data
connection may be required). Store results in `images/` and `research/screenshots/`,
referenced from `docs/13_experiments.md` and `docs/09_led_policy.md`.

## Priority 3 — Complete the JSON/zlib config protocol reverse engineering

**Description:** confirm the hypothesized JSON+zlib configuration protocol
(`docs/10_protocol_analysis.md` §10.2) by capturing an actual payload, most
likely via a genuine (not same-version) firmware update using
`--restore-json`, combined with a live USB capture.

**Difficulty:** Medium.

**Expected value:** Medium-high — if `led_driver_current_*` (or other
LED-relevant values) are actually stored in the separate `stored_conf`
flash partition (`docs/05_firmware_layout.md` §5.3) and settable via this
protocol independently of a full application firmware reflash, it would be
a significantly lower-risk write path than the current approach.

**Likelihood of success:** Moderate (~60%) — the string evidence for the
protocol's existence is strong; the main uncertainty is whether a
same-version-vs-different-version distinction (per the dead-end note in
`docs/14_failed_attempts.md`) is really the blocker, or something else.

**Recommended approach:** flash an older historical firmware build (hashes
in `hashes/firmware_hashes.txt`), then flash back to the current one with
`--restore-json` active, capturing all filesystem activity and USB traffic
throughout both transitions.

## Priority 4 — Investigate `user_flash` and `user_data` commands

**Description:** these two debug-shell commands (`docs/11_hid_commands.md`)
were discovered but never fully exercised. If LED-relevant configuration is
stored in the `stored_conf`/`data_store` flash partitions rather than the
application firmware's compiled-in defaults table, these commands (or the
`-j`/`--target=user` flags on the official update tool, also not fully
exercised) may be a much smaller, lower-risk write path than a full
application reflash.

**Difficulty:** Low-medium.

**Expected value:** Medium — mainly valuable as a safer alternative
delivery mechanism, not as new research insight.

**Likelihood of success:** Moderate — genuinely unknown without trying.

**Recommended approach:** start with `user_data header` and
`user_data all` (read-only, safe) to understand the current data layout
before attempting any write.

## Priority 5 — Understand the `0x412000` / `0x012000` base-address discrepancy

**Description:** documented as an open question in
`docs/05_firmware_layout.md` §5.4 — why the disassembly-correct base
address differs by exactly `0x400000` from the flash offset `flash_info`
reports.

**Difficulty:** Low-medium — likely resolvable by reading bootloader code
or nRF52840 documentation on memory-mapping/aliasing behavior.

**Expected value:** Low direct value (doesn't block any current work,
since the correct base was empirically established and works), but would
close a genuine unresolved oddity and might reveal something about the
boot/update process worth knowing.

**Likelihood of success:** High, if pursued — this is a "look it up"
problem, not an open-ended research problem.

## Priority 6 — Extend the Ghidra reference-resolution investigation

**Description:** understand why Ghidra's cross-reference analysis
repeatedly failed to find references that manual inspection confirmed exist
(`docs/14_failed_attempts.md`, multiple entries) — this recurring pattern
suggests a specific, identifiable analysis gap (compiler idiom, addressing
mode, or Ghidra configuration issue) rather than coincidence.

**Difficulty:** Medium — requires Ghidra internals familiarity.

**Expected value:** High if solved — would likely unblock Priority 1 and
several other open questions at once, since the recurring failure mode is
exactly what's blocking the Layer 3 caller search.

**Likelihood of success:** Moderate — this class of tooling gap is
sometimes a known, documented Ghidra limitation (worth checking Ghidra's
own issue tracker/documentation for ARM Cortex-M-specific reference
analysis caveats) and sometimes something project-specific.

## Priority 7 — Firmware-version compatibility testing

**Description:** all live patching work in this project targeted exactly
one firmware build. Confirm whether the patch offsets, config table
structure, and `.fw` container format understanding generalize to the other
four application firmware builds present in this project's SteamVR
installation (`hashes/firmware_hashes.txt`).

**Difficulty:** Low — mostly repeating already-documented analysis
procedures against different input files.

**Expected value:** Medium — improves confidence and reusability of the
tooling in this repository.

**Likelihood of success:** High for the container-format work (already
independently verified across all 5 zlib-wrapped files, see
`docs/05_firmware_layout.md`); lower/unknown for the exact code-patch
offsets, which are expected to shift between builds with different compiled
code layouts.

## Priority 8 — Radio firmware analysis

**Description:** the two `indexcontroller_radio_*.fw` files are not
zlib-compressed and were not analyzed at all in this project
(`docs/04_firmware_acquisition.md`). Unknown whether they are relevant to
the LED question at all (unlikely, but not confirmed) or of independent
research interest.

**Difficulty:** Unknown — not investigated.

**Expected value:** Low for this project's specific LED-focused question;
possibly higher for other research questions about the controller.

**Likelihood of success:** Unknown.

## Priority 9 — Security-focused follow-up on the Debug interface

**Description:** the undocumented Debug interface
(`docs/12_debug_interfaces.md`) requires no authentication and exposes
significant device internals. This project did not investigate the broader
security implications (e.g., whether malicious host software could abuse
this without special privileges, whether SteamVR itself ever triggers it,
disclosure considerations).

**Difficulty:** Low to start (mostly a different analytical lens on
already-gathered facts), potentially high if it leads to deeper protocol
work.

**Expected value:** Depends entirely on project goals — out of scope for
this project's LED-focused research question, but a natural, well-scoped
follow-up project.

**Likelihood of success:** N/A — depends on what "success" means for a
security-focused effort; flagged here as a scope note rather than a
technical prediction.
