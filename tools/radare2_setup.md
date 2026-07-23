# radare2 setup (no-root install)

Version used: 5.9.8 (Fedora/Nobara `terra`/base repo package).

## Why no-root install was needed

The research environment had no passwordless `sudo` and installation via
the system package manager (`dnf install`) requires root. `dnf download`
(fetching the `.rpm` file itself, without installing it) does **not**
require root, which is the basis of this procedure.

## Procedure

```bash
mkdir -p ~/r2local ~/r2root
cd ~/r2local

# Download radare2 and its full dependency chain (both arches get pulled
# in on a multi-lib system; only the x86_64 ones are needed)
dnf download radare2 --resolve

# Extract every downloaded x86_64 RPM into a local root, without installing
cd ~/r2root
for f in ../r2local/*.x86_64.rpm ../r2local/radare2-common-*.noarch.rpm; do
  rpm2cpio "$f" | cpio -idm --quiet
done

# The extracted binary needs its own lib directory on LD_LIBRARY_PATH,
# since it was never registered with the system linker cache
export LD_LIBRARY_PATH="$HOME/r2root/usr/lib64:$LD_LIBRARY_PATH"
"$HOME/r2root/usr/bin/r2" -v
```

Expected output: `radare2 5.9.8 0 @ linux-x86-64` (or your resolved
version).

## Dependencies pulled in during this project's install

`dnf download --resolve` for `radare2` also pulled: `capstone`,
`libuv`, `lz4-libs`, `libzip`, `xxhash-libs`, `file-libs`,
`radare2-common`. All were extracted the same way. One dependency
(`file-libs` x86_64 specifically) needed a retry due to a slow/failing
mirror on the first attempt — this is a normal transient network issue, not
a setup problem.

## Usage in this project

Two uses:

1. **x86-64 disassembly of `lighthouse_watchman_update`** (Valve's update
   tool) — a normal, un-flagged `r2 -qc "aaa; ..." <binary>` worked cleanly
   and quickly; this is what unblocked the `.fw` footer CRC reverse
   engineering ([`../docs/05_firmware_layout.md`](../docs/05_firmware_layout.md) §5.2).
2. **Early ARM Cortex-M firmware analysis** — attempted with:
   ```bash
   r2 -a arm -b 32 -m 0x412000 -e asm.arch=arm -e anal.arch=arm -e asm.bits=32 -e asm.cpu=cortex <firmware.bin>
   ```
   This worked for basic disassembly but radare2's automatic function/xref
   analysis (`aaa`) struggled significantly on this specific firmware
   (fragmented into many tiny, apparently-noise "functions," and found no
   cross-references for several strings that manual inspection confirmed
   were referenced). This limitation is what ultimately motivated setting
   up Ghidra ([`ghidra_setup.md`](ghidra_setup.md)) for the deeper LED-subsystem tracing work.
   Full account: [`../docs/14_failed_attempts.md`](../docs/14_failed_attempts.md).

## Known limitation encountered

radare2's `aaa` analysis pass on the ARM firmware produced sparse,
low-confidence function boundaries and largely failed to resolve
cross-references that were later confirmed to exist (once Ghidra was
available). This is recorded as an observed limitation for this specific
firmware/toolchain combination, not a general claim about radare2's
capabilities.

## Successful retry with a narrower technique

A later session revisited radare2 on this same firmware, but avoided `aaa`
entirely: explicitly define only the specific functions of interest
(`af @ <addr>`) and use the direct reference-search command (`/r <addr>`)
rather than relying on `aaa` to have already built a complete
cross-reference database across the whole binary. This worked cleanly —
a `pdf` disassembly of the known LED wrapper function matched Ghidra's
output exactly, including the same string reference. Used as a fourth
independent cross-reference check in
[`../research/decompiler_notes/14_r2_and_version_diff.md`](../research/decompiler_notes/14_r2_and_version_diff.md) — see
[`../docs/16_charging_led_research.md`](../docs/16_charging_led_research.md) "Multi-tool sweep session".
