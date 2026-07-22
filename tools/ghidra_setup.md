# Ghidra setup (no-root install)

Version used: 12.1.2 (Fedora/Nobara `terra` repo package), run in headless
mode.

## Why no-root install was needed

Same constraint as radare2 (`radare2_setup.md`): no passwordless `sudo` in
this environment. The same `dnf download` (no root required) + `rpm2cpio`
extraction approach was used.

## Procedure

### 1. Download and extract Ghidra

```bash
mkdir -p ~/ghidra_local ~/ghidra_root
cd ~/ghidra_local
dnf download ghidra --resolve
cd ~/ghidra_root
rpm2cpio ../ghidra_local/ghidra-*.x86_64.rpm | cpio -idm --quiet
```

This produces a ~314 MB extracted tree; `~/ghidra_root/usr/lib64/ghidra/`
is the Ghidra installation root, and
`~/ghidra_root/usr/lib64/ghidra/support/analyzeHeadless` is the headless
entry point used throughout this project (no GUI was used).

### 2. Obtain a compatible full JDK — the non-obvious part

Ghidra 12.1.2 requires **Java 21 minimum**
(`Ghidra/application.properties`: `application.java.min=21`). This
environment's system Java was version 25, which the launcher rejected
outright:

```
WARNING: JAVA_HOME environment specifies unsupported java version: ...
ERROR: Unable to prompt user for JDK path, no TTY detected.
```

Downloading and extracting `java-21-openjdk` (the same no-root
`dnf download` + `rpm2cpio` technique) still failed with the identical
error message — the *actual* cause was not the version number at all, but
that the specific RPM subpackage extracted (`java-21-openjdk-headless`)
does **not** include `javac`, and Ghidra's launcher requires a full JDK
(with `javac`), not just a JRE, even to run in headless analysis mode. The
error message did not make this distinction obvious.

**Fix:** additionally download and extract `java-21-openjdk-devel`, which
provides `javac` and the rest of the toolchain:

```bash
cd ~/java21_local
dnf download java-21-openjdk java-21-openjdk-headless java-21-openjdk-devel --resolve
cd ~/java21_root
for f in ../java21_local/*.rpm; do
  rpm2cpio "$f" | cpio -idm --quiet
done
# Confirm javac is now present:
ls ~/java21_root/usr/lib/jvm/java-21-openjdk/bin/javac
```

### 3. Point Ghidra at the extracted JDK

Either via environment variable for a single invocation:

```bash
export JAVA_HOME=~/java21_root/usr/lib/jvm/java-21-openjdk
```

or persistently, by editing `support/launch.properties` inside the Ghidra
tree:

```
JAVA_HOME_OVERRIDE=/home/<you>/java21_root/usr/lib/jvm/java-21-openjdk
```

Verify with a bare invocation:

```bash
~/ghidra_root/usr/lib64/ghidra/support/analyzeHeadless
```
Expected: the tool prints its own version banner and a usage/help message
(no arguments given), not a Java version error.

## Running an analysis

Import and fully auto-analyze a decompressed firmware image as a raw
binary, ARM Cortex-M4, little-endian, based at the empirically-determined
load address (`../docs/05_firmware_layout.md` §5.4):

```bash
GHIDRA=~/ghidra_root/usr/lib64/ghidra
analyzeHeadless=$GHIDRA/support/analyzeHeadless

"$analyzeHeadless" ~/ghidra_proj myproject \
    -import <decompressed_firmware.bin> \
    -processor "ARM:LE:32:Cortex" \
    -loader BinaryLoader \
    -loader-baseAddr 0x412000 \
    -overwrite
```

This completed in ~21 seconds on the machine used for this project and
included Ghidra's constant-reference, address-table, and function-start
analyzers — no manual configuration of the analysis pipeline was needed
beyond specifying the processor/base address at import time.

## Running custom scripts against an already-analyzed project

```bash
"$analyzeHeadless" ~/ghidra_proj myproject \
    -process "<program name inside the project>" \
    -noanalysis \
    -scriptPath /path/to/your/scripts/dir \
    -postScript YourScript.java \
    > output.txt 2>&1
```

Custom scripts used in this project are Java `GhidraScript` subclasses
(not Jython) — this was a deliberate choice for headless-mode reliability,
not a hard requirement of Ghidra itself. Representative examples are
preserved in `../research/decompiler_notes/` with comments explaining what
each was investigating, since they double as a record of the investigation
process, not just tooling.

## Known API gotchas encountered

- `ghidra.program.util.DefinedDataIterator.definedStrings(Program)` does
  not exist in this Ghidra version's API (a script using it failed with
  `cannot find symbol`) — use
  `currentProgram.getListing().getDefinedData(true)` and filter with
  `Data.hasStringValue()` instead.
- `getFunctionAt(address)` returns `null` if the address is not an exact,
  recognized function *entry point* — even if the address is unambiguously
  inside a function's body. Use `getFunctionContaining(address)` when you
  are not certain the address is an exact entry point (this distinction
  caused real confusion early in the Layer-3 tracing work — see
  `../docs/14_failed_attempts.md`).
- Large regions of this specific firmware were **not** included in any
  function Ghidra's auto-analysis recognized, despite containing valid,
  disassemblable Thumb-2 code (confirmed by manually walking through them
  instruction-by-instruction). `getReferencesTo()` on addresses inside
  these regions can return zero results even when a real code reference
  exists — see `../docs/14_failed_attempts.md` for the specific
  recurring cases and `../docs/18_future_work.md` Priority 6 for the
  suggestion to investigate this Ghidra-specific limitation further.

## Cleanup / project location note

The Ghidra project directory used in this project's development
environment was created under a session-scoped temporary directory that
does **not** persist across reboots. Anyone continuing this work should
re-run the import step at the start of a new session rather than expecting
the previous session's Ghidra project to still exist.
