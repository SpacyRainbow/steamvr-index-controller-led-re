# 14 — Failed Attempts and Dead Ends

This document exists specifically to prevent re-investigation of approaches
that were already tried and did not work. Every entry states what was
tried, why it seemed reasonable at the time, why it failed, what was
learned, and whether it is worth retrying (with different circumstances) in
the future.

## Corrected assumptions

Not every entry below is a dead *technique* — some are assumptions this
project stated confidently and got wrong. Preserved for the same reason:
so nobody re-derives the same wrong conclusion, and so it's clear where a
correction came from.

### "Blue is a color the controller never normally shows" — WRONG

**Claimed:** Patch C (`docs/15_firmware_patching.md`,
`scripts/patch_led_solid_color.py`) was originally motivated and
documented as producing "a color the controller's normal policy states
don't produce," listing green/orange/white as the complete known palette.
**Corrected by:** the user, from direct first-hand experience with Index
Controller behavior: blue (solid and blinking) is a real, normal LED
state, used for USB/host connection status and pairing-mode indication.
The user additionally confirmed the full known color palette is green,
red, blue, white, orange — red was not previously documented anywhere in
this project at all.
**Why the project got this wrong:** the "known states" table in
`docs/09_led_policy.md` was built entirely from (a) this project's own
direct visual observation, which only ever saw green (normal use) and the
patched black, and (b) general secondhand knowledge about
charging/charged colors stated at the very start of the investigation.
Connection/pairing states were never in scope for what had been directly
observed or researched, so their existence (and blue's role in them) simply
wasn't in the document to be wrong about — the actual error was
overgeneralizing "the states we've looked into" into "the complete
palette," stated in `scripts/patch_led_solid_color.py`'s docstring as a
motivating claim ("a color this controller's normal policy states are not
known to ever produce") without the hedge that only 2-3 states had ever
actually been investigated.
**Impact:** Patch C's underlying mechanism and expected behavior are
**unaffected** — it still forces a specific solid color via the proven
technique, and is still useful as a demonstration. Only the framing of
*why* it was interesting (a "novel" color) was wrong; it's now understood
as reproducing an existing state (whatever blue's exact role is) via an
unconditional software patch instead, which is arguably still a valid
demonstration (forcing a real state on permanently, regardless of what the
policy would otherwise choose) but not the originally-claimed one.
**Fixed in:** `docs/09_led_policy.md` (full corrected state/color table),
`docs/15_firmware_patching.md`, `scripts/patch_led_solid_color.py`
docstring.
**Lesson:** when a document lists "known states" or "known colors" as if
complete, make the completeness caveat explicit and prominent (e.g. "the
only states we have directly investigated," not just "known states") —
this project generally does this well, but Patch C's motivating claim
compressed a longer, properly-hedged statement in `docs/09_led_policy.md`
into a bare assertion in a different document's docstring, and the hedge
was lost in that compression.

## Research-direction dead ends

### DJm00n/ControllersInfo has no Valve entry

**Tried:** checked this public community-maintained repository cataloguing
VR/game controller USB/HID identifiers, expecting Index Controller report
descriptors or protocol notes.
**Result:** no Valve entries exist in this repository.
**Learned:** this specific resource is not useful for Valve devices;
don't re-check it without reason to believe it has been updated.
**Retry recommended:** only if revisiting years later, in case the
repository has since been extended.

### ValveSoftware IndexHardware repository is CAD-only

**Tried:** checked Valve's own public "IndexHardware" GitHub repository,
expecting mechanical or electrical documentation useful for the LED
hardware question.
**Result:** contains CAD files only — no firmware, no protocol
documentation, nothing electronic-design-relevant beyond mechanical models.
**Learned:** not a useful resource for this project's questions.
**Retry recommended:** no.

## Protocol/HID-layer dead ends

### `config set`/`config get` — the debug shell cannot write config values

**Tried:** numerous argument-syntax variations against the live debug shell
`config` command: `config set <key> <value>` (1, 2, and 3-token forms),
`config get <key>`, `config help`.
**Result:** every variation silently fell through to the same full
read-only table dump, with no error and no value change — behaviorally
distinct from `set_gpio_level`/`get_gpio_level`, which correctly report
`"Argument Input error"` on malformed input, proving the shell's argument
parser in general does distinguish valid from invalid syntax; `config`
specifically just doesn't implement a write path via this command.
**Learned:** config writes, if possible at all, do not go through this
plaintext shell command. This directly motivated the pivot to firmware
flashing as the write mechanism instead (`docs/13_experiments.md`
Experiments 5–7), which succeeded.
**Retry recommended:** no — superseded by the firmware-flash approach,
which works and is documented.

### `--restore-json` did not produce a findable JSON configuration backup file

**Tried:** ran `lighthouse_watchman_update` with the `--restore-json` flag
during both same-version safety-test flashes (Experiment 6a), then searched
`/root`, `/tmp`, and the user's home directory for any newly-created
JSON file.
**Result:** no LWU-related JSON file was found in either case.
**Hypothesis (unconfirmed) for why:** the JSON backup/restore logic may
only trigger when an actual firmware version change is detected; both test
flashes were byte-identical same-version safety tests, which may take a
"no changes needed" fast path that skips the JSON dance while still
performing the underlying flash write (this is consistent with the flash
write itself definitely happening — see Experiment 6a's device
re-enumeration and uptime-reset evidence).
**Learned:** this specific approach does not reveal the JSON config
protocol's wire format.
**Retry recommended:** yes, with a genuine version-differing flash (e.g.,
flash an older historical firmware build, then flash back to the current
one) — this was not attempted due to the added risk of an actual downgrade/
upgrade cycle rather than a no-op test, and was out of scope given time
remaining in the project.

### Passive log-listening for spontaneous "LED color change" log lines

**Tried:** ran a passive HID read loop
(`scripts/listen_debug.py`) on the Debug interface for ~25 seconds while
issuing `watchman suspend`/`watchman resume` and `power get` commands via a
separate process, hoping to trigger and observe the firmware's own
`"LED %u: color = 0x%06X->0x%06X..."` log line for a real state transition.
**Result:** no spontaneous LED-related log output was captured; only the
command echoes from the concurrently-issued shell commands appeared.
**Learned:** these specific commands do not trigger a visible LED-policy
log event, or the log only streams under conditions not met during the
listening window (e.g., only right after a hardware reset, which — see
below — cannot be observed via the Debug interface at all since debug mode
is disabled during early boot).
**Retry recommended:** possibly, if a way is found to trigger a *charging
state transition* specifically (e.g., physically plugging/unplugging a
charge cable) while the debug shell is actively listening — not attempted
because the wired controller's only power/data connection is the same USB
cable used for the debug interface, so unplugging it severs the only
observation channel. A controller with independent battery power and a
separate charge dock might allow this in the future.

## Firmware-flashing dead ends (all safely resolved, preserved for the debugging narrative)

### First `lighthouse_watchman_update` invocation: `--via-bootloader` (default) fails against a running device

**Tried:** ran `lighthouse_watchman_update -mv <file>` without any
`--via-*` flag, against the controller in its normal running (application
firmware) state.
**Result:** `"Error: unable to open device."` (×2), even after obtaining
root via `pkexec`.
**Why this was confusing initially:** since root did not fix it, the
initial hypothesis was a resource conflict (kernel `hidraw` driver holding
the interface, or the extra "Debug" interface confusing enumeration) rather
than a mode mismatch. Both of those hypotheses were tested and ruled out
(no other process held the relevant `hidraw` device per `lsof`; disabling
debug mode to return to 3 interfaces did not fix it either).
**Actual cause, found by reading the tool's own console output carefully:**
the message `"Attempting to update VRC Application via bootloader..."`
appeared just before the error — the tool was defaulting to a mode that
requires the device already be sitting in USB bootloader mode, which a
normally-running controller is not.
**Fix:** pass `--via-application` explicitly.
**Learned:** don't assume a failure's cause matches the first plausible
hypothesis; re-read the tool's own diagnostic output closely before
escalating to more invasive debugging (e.g., before granting root, or before
disassembling the tool).
**Retry recommended:** n/a — solved, documented in
`docs/10_protocol_analysis.md`.

### `sudo -v` fails with no TTY available

**Tried:** asked the human operator to run `sudo -v` themselves (via a
`!`-prefixed shell command in the research assistant's interface) to cache
sudo credentials for later automated use.
**Result:** `"sudo: a terminal is required to read the password; either use
the -S option to read from standard input or configure an askpass
helper"`.
**Learned:** this specific automation environment has no TTY attached to
that command path.
**Working alternative found:** `pkexec` (PolicyKit), which on a desktop
Linux environment with a running polkit authentication agent (confirmed:
KDE Plasma, based on incidental `kdotool`/`plasma-*` process names observed
during unrelated cleanup work) shows a native GUI password dialog
independent of any TTY. This became the standard privilege-escalation
method for the rest of the project.
**Retry recommended:** no — `pkexec` is the documented working solution,
see `docs/17_safety.md`.

## Static-analysis dead ends

### Blind byte-pattern search for a color-constants table

**Tried:** having found the config-defaults table via exact-value byte
search (a technique that worked very well — see
`docs/06_firmware_symbols.md` §6.2), the same technique was tried for
finding a hypothetical state→color table, searching for specific plausible
packed-color values (various greens, oranges, whites) as raw 4-byte
little-endian patterns across the entire firmware image.
**Result:** almost all candidates had zero hits. One candidate
(`0x00FF8000`, a plausible orange) had exactly one hit, which on inspection
turned out to be a coincidental overlap with unrelated IEEE-754
floating-point constants (`0x7F800000` = +infinity, `0x3F800000` = 1.0f)
stored nearby for an unrelated numeric purpose.
**A broader heuristic search** (any 4-byte value with at least one "high"
byte, excluding values that look like valid code pointers) was also tried
and produced over 40,000 hits — overwhelmingly matching ordinary ARM Thumb-2
instruction encodings that coincidentally contain high bytes (very common,
since many Thumb-2 32-bit instruction encodings begin with `0xF0`–`0xFF`).
This heuristic was abandoned as unworkable.
**Learned:** this firmware's color values, if they exist as a literal
table at all, are either encoded differently than assumed (e.g., built
via multiple discrete instruction immediates rather than stored as a
contiguous packed constant), or genuinely are not stored as literal data
constants findable this way.
**Retry recommended:** no, unless a specific, independently-derived
candidate value becomes available (e.g., from a genuine live capture of a
color-change log line, per the retry note above).

### Raw-pointer search for the color-wrapper function's address (hunting a vtable)

**Tried:** searched the entire firmware image for the runtime address of
the `0x41d7ac` color-request wrapper function (and, separately, several
related "state handler" function addresses found later), both with and
without the Thumb bit set, as a raw 4-byte little-endian value — the same
technique that successfully located name-string pointers in the config
table (`docs/06_firmware_symbols.md` §6.2).
**Result:** zero hits, for every candidate address tried, across multiple
rounds of this search as new candidate addresses were identified.
**Learned:** whatever mechanism invokes these functions (they are
definitely called — three direct callers of the wrapper were eventually
found via Ghidra's reference manager, see `docs/06_firmware_symbols.md`),
it does not involve a plain stored absolute pointer anywhere in the static
image. Possible explanations (none confirmed): PC-relative-only addressing
throughout this specific compilation unit, or a calling mechanism this
project did not identify at all (see `docs/16_charging_led_research.md`).
**Retry recommended:** possibly, with a proper Ghidra function-pointer/
vtable-detection pass rather than a manual literal search — not attempted
within this project's time budget.

### Misattributed indirect-call ("vtable") pattern

**Tried (early in the project, before Ghidra was available):** manual
capstone-based disassembly of the region around file offset `0xb7a8`
identified an indirect call pattern (`ldr r2,[r0,#8]; blx r2`) and this was
assumed, at the time, to belong to the color-request wrapper function,
motivating a substantial search for a "state dispatch vtable" driving it.
**Result:** after installing Ghidra and getting a clean decompilation, this
pattern was found to actually belong to a **different, unrelated function**
(`0x41d804`, believed to be a per-LED-*hardware-type* dispatcher, not a
per-*state* dispatcher) located at a nearby but distinct address — the
manual disassembly had mis-identified which function's body the pattern
belonged to, an off-by-a-few-tens-of-bytes function-boundary error.
**Learned:** manual ARM Thumb-2 disassembly without proper tooling is prone
to exactly this class of error — a byte sequence found via linear scanning
can easily be attributed to the wrong logical function if function
boundaries are not independently verified. This is preserved as a concrete
cautionary example, not just an abstract warning.
**Retry recommended:** n/a — corrected once Ghidra was available; any
future manual disassembly work should independently verify function
boundaries (e.g., via a `push {..., lr}` prologue immediately preceding the
region of interest, cross-checked against a proper tool) before drawing
conclusions from a pattern found by linear scanning.

### "Ownership tag" constants turned out to be self-referential

**Tried:** two functions found deep in the LED call graph
(`docs/07_led_architecture.md` Layer 3) each compare a value against a
distinctive constant (`0x43E9B0`, `0x43E9CC`) while iterating a table,
suggesting — by analogy with common "does this table entry belong to me"
patterns — that these might be shared identifiers other subsystems also
reference, which could have been searched for to find related code.
**Result:** both constants, when inspected as addresses, pointed directly
back into the *same two functions* that use them (specifically, to
addresses very close to each function's own entry point) — i.e., each
function uses its own address as a unique "this is my own request" cookie,
a self-referential ownership-check idiom, not a cross-subsystem shared tag.
**Learned:** this specific lead does not generalize to finding other
related code; searching for cross-references to these constants was
therefore a dead end (zero results, consistent with the self-referential
explanation).
**Retry recommended:** no.

### No cross-references found for power-management state-transition log strings, even with Ghidra

**Tried:** located firmware log strings clearly belonging to the
power-management task's charging-state machine (`" PM -> charging\n"`,
`" PM: charging -> on\n"`, etc.) and asked Ghidra's reference manager for
every code location that references them, expecting this to directly
reveal the state-transition function.
**Result:** zero cross-references found by Ghidra for either string
address, despite Ghidra's auto-analysis (including its "ARM Constant
Reference Analyzer" and "Create Address Tables" passes, both specifically
designed to catch this kind of reference) having completed successfully
elsewhere in the same firmware image with good results.
**Follow-up:** the actual containing code region *was* found (by checking
`getFunctionContaining` on the string address and finding it fell in
another large unbounded code gap, then manually reading through that gap
linearly) — the string reference itself works fine in the actual firmware
(confirmed indirectly, since the code clearly does reference and print
these strings, based on the surrounding `adr`/`bl` call pattern read
manually), Ghidra's reference-tracking specifically failed to record it as
a formal Reference object for reasons not determined.
**Learned:** this firmware, or this specific compiler/toolchain's output,
triggers a class of reference-resolution gap in Ghidra's default analysis
that recurred multiple times across this project (also seen for the
config-table name-string pointers early on, before that was solved via a
different, exact-address raw-byte search rather than relying on Ghidra
xrefs). Do not trust "zero cross-references" as proof that a string or
function is unreferenced in this firmware — always double check with a
manual linear listing of the surrounding bytes.
**Retry recommended:** yes, as a tooling investigation in its own right —
understanding *why* Ghidra's reference analysis misses these specific
cases could unblock several currently-open questions at once (see
`docs/18_future_work.md`).

### The `0x414dbc`/`0x414e38` "glow trigger" lead was actually a generic timer facility

**Tried:** during the follow-up power-management data-flow session
(`docs/16_charging_led_research.md`), found that code reading a
power-management struct field (`+0x24`, scaled by 1000) calls two
functions, `0x414dbc` and `0x414e38` — the exact same two functions the
LED subsystem's `FUN_0041d6b4` calls for its "glow" pattern trigger
(`docs/06_firmware_symbols.md` §6.3). This looked like a strong, direct
LED connection.
**Result:** decompiling both functions fully with Ghidra showed they are
general-purpose software-timer registration (`0x414dbc`, takes a context
ID, a delay, a flag byte, and a callback argument, storing into a 20-slot
table) and cancellation (`0x414e38`, matches and clears a slot by context
ID). An embedded assert string confirms the source file is `tick_handler.c`
— a generic RTOS scheduling primitive. Checking their caller lists found
19–20 callers each, spanning addresses all over the firmware, consistent
with a widely-shared utility rather than an LED-specific one.
**Learned:** the LED subsystem uses this generic timer facility to
schedule its own glow-animation ticks; the power-management code
independently uses the same facility for an unrelated purpose (most likely
a timeout, given the `*1000` scaling from what is presumably a
seconds-denominated struct field). Sharing a generic utility function is
not evidence of a direct relationship between two callers — this is a
concrete example of that general caution.
**Retry recommended:** no — this specific lead is closed. The two
functions remain useful as a landmark for finding *other* code that
schedules timed events, but not as an LED-connection lead.

### Brute-force `BL`-encoding search had a real bug (found, fixed, prior results re-verified)

**Tried:** while continuing the search for callers of newly-identified
power-management functions (the `docs/16_charging_led_research.md`
follow-up session), the exhaustive direct-call-encoding search technique
(previously used successfully to find the LED wrapper's real callers, and
trusted as "alignment-independent" and therefore highly reliable) reported
a caller for a `+0x28`-checking function.
**Result:** manually cross-checking that specific instruction with
`capstone` showed it actually encodes a call to a *different* address —
the search had produced a false positive. Tracing the bug to its source
found a bit-shift error in the immediate-field encoding
(`imm10 = (imm >> 13) & 0x3FF` where the correct shift, per the ARM
architecture reference, is `>> 11`), which can alias two different call
targets onto identical encoded bytes for certain offset magnitudes.
**Follow-up:** the bug was fixed and committed as
`scripts/find_bl_callers.py` (previously this technique existed only as an
uncommitted inline script during live sessions, not a saved, reusable
tool). The corrected version was re-run against every previously-documented
"zero callers" finding that depended on this technique — most importantly
the LED Layer-3 functions (`0x41d6fa`, `0x41d938`, `0x41da90`,
`docs/16_charging_led_research.md`) — and **the results did not change**;
those functions still show zero direct callers under the corrected
encoder. The central conclusions of `docs/16_charging_led_research.md`
are therefore unaffected by this bug.
**Learned:** even a technique designed to be more rigorous than disassembly
(exact byte-pattern matching, no alignment assumptions) can still have an
implementation bug — the fix here was to independently cross-verify with a
second, unrelated tool (`capstone`) the moment a result looked surprising,
rather than trusting a single method's output at face value, especially
for a *positive* (nonzero) result. Zero-result findings from this
technique are comparatively safer to trust (a bug that mis-encodes bytes
can produce a spurious match, but is very unlikely to spuriously produce
zero matches when a real one exists, since that would require the bug to
consistently avoid encoding the one correct answer while still matching
nothing else by chance).
**Retry recommended:** no further action needed — bug fixed, tool
committed with the bug history documented in its own module docstring, and
the dependent conclusions re-verified. Anyone using
`scripts/find_bl_callers.py` going forward should still manually
cross-check any nonzero result, per the caution now embedded in the
script's own docstring.

## Environment/tooling dead ends (preserved because they cost real time)

### Ghidra headless launcher rejects a technically-correct Java version

**Tried:** extracted a `java-21-openjdk-headless` RPM locally (no root) and
pointed Ghidra's `JAVA_HOME` at it, matching Ghidra 12.1.2's documented
minimum Java version (21).
**Result:** Ghidra's launcher rejected it as an "unsupported java version,"
even though `java -version` reported exactly `21.0.11`, a version
satisfying the documented minimum.
**Actual cause:** the `-headless` RPM subpackage does not include `javac`;
Ghidra's launch mode requires a full JDK (`javac` present), not just a JRE.
**Fix:** additionally downloaded and extracted the `-devel` RPM subpackage,
which provides `javac` and the rest of the JDK toolchain.
**Learned:** "unsupported java version" from this launcher can mean
"wrong/incomplete JDK layout," not literally "wrong version number" — check
for `javac`'s presence before assuming the version itself is the problem.
**Retry recommended:** n/a — solved, documented in `tools/ghidra_setup.md`.

### Runaway `inotifywait` recursive self-watch filled the sandbox's temp filesystem

**Tried:** started `inotifywait -m -r /tmp ...` (recursive watch of `/tmp`)
to look for temp files created by the update tool, writing its own log
output to a file *inside* the directory tree it was watching.
**Result:** the watcher's own output-file growth triggered new watched
events about itself, creating a runaway feedback loop; one log file reached
29 GB before this was noticed, filling the sandbox's 31 GB tmpfs completely
and breaking the automation tooling's own output capture until manually
diagnosed and fixed (killed the process, deleted the runaway files).
**Learned:** never point a recursive file-system watcher at a directory
tree that also contains its own output file. Use bounded before/after
`find -newer` snapshot diffs instead of live recursive watches for this
class of task.
**Retry recommended:** n/a — this is a pure operational/tooling caution, not
a research finding; documented here so it is not repeated.
