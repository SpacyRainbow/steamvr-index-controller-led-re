# 13 — Experiments

Every experiment performed against real hardware or real firmware artifacts
in this project, in chronological order. Each follows the same format:
Goal, Background, Reasoning, Method, Expected result, Actual result,
Evidence, Conclusion, Confidence, Repeatability, Recommendation.

Purely analytical/static work (disassembly, string searches with no live
hardware interaction) is documented in `docs/06_firmware_symbols.md` and
`docs/07_led_architecture.md` rather than as "experiments" here, since those
were not directly experimental in the sense of testing against real
hardware. The line is not perfectly sharp; some entries below have both a
static and a live component.

---

## Experiment 1 — Full HID interface/report enumeration

**Goal:** Map every HID interface, report ID, and report type (Input/
Output/Feature) the controller exposes, as a foundation for finding any
undocumented command surface.

**Background:** Prior art (`docs/02_background.md`) established that
Valve's Watchman-family devices expose vendor commands over standard HID
Output/Feature reports. No existing public documentation covers the Index
Controller's exact report layout.

**Reasoning:** If an undocumented LED-control command exists, it is most
likely reachable via an HID report not covered by any existing tooling or
documentation — systematic enumeration is the most direct way to find
candidate reports.

**Method:** `scripts/dump_hid_descriptors.py` reads the raw HID report
descriptor via `HIDIOCGRDESC` ioctl for every `hidraw` device matching
vendor ID `0x28de`, for the wired controller and connected Watchman
dongles. `scripts/parse_hid_descriptor.py` parses the raw descriptor bytes
into a table of (report ID, type, size).

**Expected result:** A list of report IDs per interface, establishing which
are plausible candidates for further probing.

**Actual result:** Three HID interfaces mapped completely on the wired
controller, each with multiple numbered Feature/Output reports of varying
sizes. Full raw output in `research/captures/report_descriptors_raw.txt`
and `research/captures/report_map_parsed.txt`.

**Evidence:** Raw descriptor bytes and parsed tables, both preserved.

**Conclusion:** Provided the candidate report list used in Experiment 2.

**Confidence:** 100% (raw device queries, fully reproducible).

**Repeatability:** Fully repeatable on any connected wired Index Controller;
hidraw node numbers will differ per session.

**Recommendation:** Re-run at the start of any future session — do not
assume node numbers or even the exact report layout are unchanged, since a
firmware update (this project performed several) could in principle alter
descriptors, though none was observed to.

---

## Experiment 2 — Feature report GET/SET sweep → Debug interface discovery

**Goal:** Determine which Feature reports are readable, writable, or both,
and specifically hunt for any single-byte report that might be a
boolean/mode toggle.

**Background:** Experiment 1 produced a full report list; several
single-byte Feature reports stood out as plausible toggle candidates.

**Reasoning:** A toggle-sized Feature report that doesn't correspond to any
documented function is a reasonable place to look for hidden functionality,
by analogy with how many embedded devices gate debug/manufacturing features
behind an otherwise-unused control bit.

**Method:** `scripts/read_feature_reports.py` performed a `GET_FEATURE`
sweep of every known report ID. `scripts/test_feature_toggle_candidates.py`
then performed `SET_FEATURE(report_id, 0x01)` on each single-byte candidate
(`0x06`, `0x0c`, `0x0d`, `0x12`, `0x16`), followed by a delay and an attempt
to revert to `0x00`.

**Expected result:** Most candidates would have no observable effect; at
best, one might toggle a minor, cosmetic behavior.

**Actual result:** `SET_FEATURE(0x12, 0x01)` caused the device to reset and
re-enumerate with a fourth HID interface named "Debug" in its USB string
descriptors. The subsequent revert-to-`0x00` call failed with `ENODEV`
because the device had already reset and the file descriptor was stale —
this is expected behavior given the reset, not a bug.

**Evidence:** `research/captures/feature_toggle_candidates_log.txt`, plus
the newly-appeared fourth hidraw node confirmed via a follow-up descriptor
dump.

**Conclusion:** A previously undocumented "Debug" USB HID interface exists
and is trivially unlockable with a single unauthenticated `SET_FEATURE`
call. See `docs/12_debug_interfaces.md` for full details.

**Confidence:** 100%, reproduced live multiple times across the project
(the interface reliably reappears after being deliberately disabled or
after resetting).

**Repeatability:** Fully repeatable; requires re-doing after every firmware
flash or power cycle, since the debug-mode state does not persist.

**Recommendation:** This is now a routine step (`docs/12_debug_interfaces.md`
gives the exact reusable code) for any continuation of this work.

---

## Experiment 3 — Reverse engineering the debug shell wire framing

**Goal:** Determine the correct byte framing for sending/receiving text
commands over the newly-discovered Debug interface.

**Background:** Experiment 2 confirmed the interface exists and its report
descriptor (Report ID `0x76`, 63-byte Input/Output) but not how to actually
communicate with it.

**Reasoning:** A reasonable first guess was that the ASCII command text
could simply be written starting immediately after the report-ID byte.

**Method:** `scripts/probe_debug_shell.py` sent `"help\n"` with the text
starting at `buf[1]` and inspected the raw response bytes.

**Expected result:** Either a working response to `help`, or no response at
all (if the interface requires some different unlock/protocol entirely).

**Actual result:** The device responded with `"Unknown Command elp"` — the
text was received but truncated by one leading character, and the
response's own second byte numerically matched the exact length of `"elp"`.

**Evidence:** `research/captures/debug_shell_help_attempt1.txt` (buggy
framing) and `debug_shell_help_attempt2.txt` (corrected framing, full
command list returned).

**Conclusion:** The correct framing places a length byte at `buf[1]`, with
ASCII text starting at `buf[2]` — not immediately after the report-ID byte
as first guessed. `scripts/debug_shell.py` implements the corrected,
reusable version.

**Confidence:** 100%, confirmed by successfully retrieving the full,
sensible command list on the corrected attempt, and by every subsequent
successful command interaction throughout the rest of the project.

**Repeatability:** Fully repeatable; this is now baseline tooling.

**Recommendation:** None — solved.

---

## Experiment 4 — Firmware extraction and container-format identification

**Goal:** Extract usable firmware content from the `.fw` files shipped with
SteamVR.

**Background:** Original project methodology anticipated this could require
significant effort (hardware-based extraction via APPROTECT bypass,
`docs/02_background.md`), if firmware turned out to be encrypted or
protected.

**Reasoning:** Check the simplest possible hypothesis first — that the
files are usable as-is or with trivial decompression — before investing in
hardware-level extraction techniques.

**Method:** Inline Python `zlib.decompress()` against each `.fw` file, per
`docs/04_firmware_acquisition.md`.

**Expected result:** Uncertain; genuinely did not know whether this would
work.

**Actual result:** Every firmware file except the two radio builds
decompressed cleanly as a standard zlib stream with a trailing 56-byte
footer of `d.unused_data`, with **zero effort and no protection to
bypass**.

**Evidence:** Decompressed binaries preserved (locally, not redistributed —
see `hashes/firmware_hashes.txt` for verification hashes);
`research/firmware_analysis/` contains derived analysis artifacts.

**Conclusion:** No encryption or extraction-blocking protection exists on
this firmware family, beyond the self-referential integrity CRC discovered
later (`docs/05_firmware_layout.md`), which protects against corruption
during flashing, not confidentiality. This eliminated the entire
hardware-extraction contingency plan from the project's remaining scope.

**Confidence:** 100%.

**Repeatability:** Fully repeatable, see `docs/04_firmware_acquisition.md`.

**Recommendation:** None — solved definitively.

---

## Experiment 5 — First firmware patch attempt: rejected by the update tool

**Goal:** Build a modified firmware image (LED current values changed) and
flash it to real hardware for the first time.

**Background:** By this point, the config defaults table
(`docs/06_firmware_symbols.md` §6.2) and the `.fw` container's `magic`,
`target`, `comp_size`, and `crc2` fields were understood
(`docs/05_firmware_layout.md`), but the final 4-byte footer field's meaning
was not yet known — it was initially left byte-identical to the original
file's value.

**Reasoning:** Recompute the fields known to be content-dependent
(`comp_size`, `crc2`), leave the rest, and see what happens — a controlled
first test with an easy failure signature to interpret.

**Method:** `scripts/patch_led_firmware.py` (an early version) patched the
four `led_driver_current_*` values, recompressed, rebuilt the footer with
only `comp_size`/`crc2` updated, and attempted to flash via
`lighthouse_watchman_update -mv <file> --via-application` under `pkexec`.

**Expected result:** Either success, or a clear rejection.

**Actual result:** The tool printed `"Error: Invalid firmware file."` and
exited **before any device communication was attempted** (confirmed: no
"Attempting to update..." message appeared, and the USB device number did
not increment).

**Evidence:** Console output captured in session logs
(`research/daily_logs/`); the tool's own binary was subsequently
disassembled to explain this result (`docs/05_firmware_layout.md` §5.2).

**Conclusion:** The rejection was a **safe, local, pre-flight validation
failure** — no risk to the device — caused by the un-recomputed final
4-byte footer field, which was subsequently identified as a self-referential
CRC-32 and fixed. This is documented in full in
`docs/05_firmware_layout.md` §5.2 rather than repeated here.

**Confidence:** 100% for the observed rejection behavior; the *explanation*
(self-referential CRC) was independently verified against 5 known-good
firmware files before being trusted.

**Repeatability:** The failure is reproducible with any incorrectly-computed
`final_crc` field; the fix is documented and reproducible.

**Recommendation:** Always use `scripts/patch_led_firmware.py`'s
current version (which correctly recomputes `final_crc`), not an
early/incomplete patch script.

---

## Experiment 6 — Live firmware flashing: safety tests and the LED-current patches

**Goal (6a):** Confirm the flashing pipeline is safe by pushing a
byte-identical, same-version firmware image.
**Goal (6b):** Test whether patching `led_driver_current_{r,g,b,w}` produces
a visible LED change.

**Background:** With the footer-CRC issue (Experiment 5) understood and
fixed, and root access obtained via `pkexec` (a KDE PolicyKit GUI prompt,
used because this test machine had no passwordless `sudo` and no TTY
available for `sudo -v` to prompt interactively), the pipeline was ready
for a real test.

**Reasoning:** Test the delivery mechanism itself, isolated from any actual
content change, before trusting it with a behavioral patch. This is a
standard "prove the pipe works before sending something down it" step.

### 6a — Same-version safety test

**Method:** Flashed the *exact*, unmodified
`indexcontroller_app_20230902_v1693638519.fw` (byte-identical, MD5-verified
against the SteamVR-installed copy) via
`pkexec lighthouse_watchman_update -mv <file> --via-application`.

**Expected result:** A true no-op reflash: erase, write, verify, reset,
with the device coming back up identical.

**Actual result:** Completed successfully twice. Each time: tool reported
`"Successfully updated firmware."` / exit code 0; the USB device number
incremented (confirming a genuine reset/re-enumeration, not a skipped
no-op); and the debug shell's `info` command afterward reported an
identical app version/git hash with an uptime reset to 1–2 minutes
(confirming a real reboot into freshly-written code).

**Evidence:** Console transcripts and `lsusb`/`info` output captured in
session logs.

**Conclusion:** The flashing pipeline is safe and repeatable for this
device/firmware/tool combination.

**Confidence:** 100%, reproduced twice independently.

### 6b — LED current patch, value = 255

**Method:** `scripts/patch_led_firmware.py 255` set all four
`led_driver_current_*` values to `255` (from default `8`), flashed via the
same pipeline.

**Expected result:** A visibly brighter LED.

**Actual result:** Flash succeeded and the new value was confirmed live via
the debug shell's `config` command (`led_driver_current_r/g/b/w = 255`).
The human tester reported: **"im not actually sure if its brighter. its
still green and on."**

**Evidence:** Live `config` readout confirming the patched value took
effect; human tester's direct testimony (recorded verbatim above, not
paraphrased) as the only available "brightness" measurement — no
photographic or instrumented light measurement was performed.

**Conclusion:** The patch reached the device and took effect at the
firmware-value level, but produced no clearly perceptible brightness change
to the human eye. See `docs/08_lp5562_driver.md` "Brightness floor and
ceiling phenomena" for discussion of possible explanations, none confirmed.

**Confidence:** 100% that the value was written and read back correctly;
0% (i.e., no meaningful confidence either way) on any brightness effect,
since it was not measured, only subjectively and inconclusively judged.

### 6c — LED current patch, value = 0

**Method:** Same procedure, `scripts/patch_led_firmware.py 0`.

**Expected result:** LED fully off, or close to it.

**Actual result:** Human tester reported: **"it is not off, but it is
dimmed by alot. also during the powerup, it did cycle trhough a few
colors."**

**Evidence:** Live `config` readout confirming value=0 took effect; human
tester's direct testimony.

**Conclusion:** `led_driver_current_*` is a real, working, per-channel
brightness-scaling control confirmed to affect real hardware — a
significant, positive result — but does **not** by itself reach a complete
blackout, and does not appear to affect the boot self-test's color-cycling
behavior (which remained visible even with these values at 0). See
`docs/09_led_policy.md` and `docs/08_lp5562_driver.md` for the
interpretation of this result.

**Confidence:** 100% for the observed dimming and the persistence of the
boot color-cycle; the *explanation* for why full black wasn't reached is a
~70%-confidence hypothesis (calibration-scale-vs-base-color distinction),
not confirmed at the hardware register level.

**Repeatability (6a–6c):** Fully repeatable given the tooling in
`scripts/`, `docs/13_experiments.md` procedures, and root access via
`pkexec` or `sudo`.

**Recommendation:** For a true blackout, use the Layer-1 code patch
(Experiment 7) instead of the config-value patch.

---

## Experiment 7 — Layer-1 code patch: forcing the LED fully off (primary positive result)

**Goal:** Achieve a genuine, complete LED blackout via software, as the
strongest possible demonstration of the project's core research question.

**Background:** Experiment 6c showed that the config-value approach
(`led_driver_current_*`) does not reach true black. Static analysis
(`docs/06_firmware_symbols.md` §6.3, `docs/07_led_architecture.md`) located
the low-level function (`0x41dbf0`) that all LED color requests funnel
through, and specifically the instruction (`mov r4, r0` at runtime address
`0x41dc20`) that copies the final computed color into the register used for
all three hardware channel writes.

**Reasoning:** If every color request passes through this exact point (as
established by static call-graph analysis showing the function has only two
direct callers, both eventually reachable from any LED state), then
replacing that one instruction with an unconditional "set to zero"
instruction should force every color, from every state, to black —
independent of any brightness-scaling floor effects seen in Experiment 6c.

**Method:** `scripts/patch_led_black.py` replaced the 2-byte Thumb
instruction `mov r4, r0` (bytes `04 46`) with `movs r4, #0` (bytes `00 24`)
at file offset `0xbc20` in the decompressed image — a same-size,
same-alignment substitution requiring no code relocation. The image was
recompressed, footer rebuilt with correctly recomputed `comp_size`, `crc2`,
and `final_crc` (per `docs/05_firmware_layout.md` §5.2), and flashed via
the same pipeline as Experiment 6.

**Expected result:** LED fully off, in all states.

**Actual result:** Human tester reported: **"the LED is off!!"**

**Evidence:** The exact byte replacement was verified against the source
file before patching (`scripts/patch_led_black.py` asserts the expected
original bytes are present before writing, refusing to patch otherwise);
the flash succeeded (`Successfully updated firmware.`, device
re-enumeration confirmed); the debug shell's `info` command confirmed the
device rebooted successfully into the patched firmware
(fresh uptime, correct version/git-hash reporting — the version/git-hash
fields are unaffected by this patch since they are copied verbatim into the
new footer, not derived from the patched content); and the human tester's
direct, enthusiastic, unambiguous confirmation.

**Conclusion:** This is the project's central positive result. A firmware
patch, built and delivered entirely through software (no debugger, no
hardware modification, no chip-level access), demonstrably and visibly
changed the Index Controller's real-world LED behavior. This directly and
conclusively answers the project's core research question in the
affirmative.

**Confidence:** 100%. This is the highest-confidence result in the entire
project — a controlled software change, a specific predicted effect, and a
direct human-observed confirmation of exactly that effect, with no
ambiguity in interpretation (unlike the inconclusive brightness judgments
in Experiment 6b).

**Repeatability:** Fully repeatable using `scripts/patch_led_black.py`
against the same firmware version (`indexcontroller_app_20230902_v1693638519.fw`,
hash in `hashes/firmware_hashes.txt`). Patching a *different* firmware
build would require re-locating the exact instruction offset, since it is
specific to this build's compiled code layout (`docs/17_safety.md`
discusses version compatibility).

**Recommendation:** This patch is the safe, proven "reference" patch for
anyone wanting to reproduce a positive result quickly. For a more useful
*selective* patch, see `docs/16_charging_led_research.md` for the current
(incomplete) state of that follow-up work.

---

## Experiment 8 — Attempted trace of the state-to-color policy decision

**Goal:** Locate the code that decides which color to request for which
device state (charging/charged/ready), to enable a selective patch that
preserves charging indication while blanking the LED during normal use.

**Background/Reasoning/Method/Result:** This experiment is large enough,
and ended in a genuinely open (not simply failed) state, that it has its
own dedicated document: `docs/16_charging_led_research.md`. It is listed
here for completeness of the chronological experiment record, with a
summary only.

**Summary of outcome:** Successfully traced three full layers of the LED
call graph with high confidence (`docs/07_led_architecture.md`), including
correcting an earlier mistaken function-boundary identification. Located
the power-management task's charging-state-transition code via its log
strings, and established that it does **not** call into the traced LED call
graph directly — implying an RTOS shared-state connection rather than a
direct call, which was not further resolved within this project's time
budget.

**Confidence:** High confidence (~90%) in everything traced; the central
open question (the actual connecting mechanism) remains unresolved, which
is itself a confident, evidence-backed conclusion (not a guess) — see
`docs/16_charging_led_research.md` for the full account, including several
specific dead ends (self-referential "ownership tag" constants, absent
cross-references even under a full Ghidra analysis) that are individually
useful negative results for anyone continuing this work.

**Recommendation:** See the prioritized next steps in
`docs/16_charging_led_research.md` and `docs/18_future_work.md`.
