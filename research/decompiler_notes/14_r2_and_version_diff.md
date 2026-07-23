# radare2 second-opinion analysis, and a version-diff sanity check

Not a Ghidra script (this directory's other numbered files are) -- these
are the exact commands/approach used for the two remaining legs of the
"multi-tool sweep" session (see [`docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md)
"Multi-tool sweep session"), preserved here rather than in `scripts/`
since, like the rest of this directory, they're one-off investigation
notes tied to specific firmware addresses, not reusable general tooling.

## radare2 setup

No-root local extraction, same procedure as [`tools/radare2_setup.md`](../../tools/radare2_setup.md).
radare2 was tried on this exact firmware early in the project and largely
abandoned (`aaa`, its blanket whole-binary auto-analysis, produced sparse
function boundaries and missed real cross-references later confirmed via
Ghidra -- [`tools/radare2_setup.md`](../../tools/radare2_setup.md) "Known limitation encountered"). This
session revisited it with a narrower technique instead: explicitly define
only the functions of interest (`af @ <addr>`) and use radare2's direct
reference-search command (`/r <addr>`) rather than relying on `aaa` having
already built a complete cross-reference database.

## Commands used

```bash
export LD_LIBRARY_PATH="$HOME/r2root/usr/lib64:$LD_LIBRARY_PATH"
FW=indexcontroller_app_20230902_v1693638519.fw.decompressed.bin

# sanity check: analyze a known function, confirm r2's disassembly agrees
# with Ghidra's (it does -- same instructions, same string reference)
r2 -q -m 0x412000 -e asm.arch=arm -e asm.bits=16 -e anal.arch=arm "$FW" <<'EOF'
af @ 0x41d7ac
pdf @ 0x41d7ac
EOF

# the actual second-opinion check: cross-reference search (r2's own
# analyzer, independent of Ghidra's and angr's) against the LED Layer-3
# functions and the PM struct base address
r2 -q -m 0x412000 -e asm.arch=arm -e asm.bits=16 -e anal.arch=arm "$FW" <<'EOF'
af @ 0x41d6fa
af @ 0x41d938
af @ 0x41da90
af @ 0x41d7ac
/r 0x41d6fa
/r 0x41d938
/r 0x41da90
/r 0x2000378c
EOF
```

## Result

`/r` (radare2's cross-reference search) found **zero** references to any
of the three LED Layer-3 function addresses, and zero references to the
PM struct base address -- independently corroborating the same negative
result Ghidra's reference manager, the project's own exhaustive `BL`-search,
and angr's CFG recovery had each already found separately. Four
independent techniques now agree.

One small side-finding, not chased further this session: a sanity check
using a known-real reference (`0x41e7d8`, the LED "off-path" function)
found not just its expected caller inside `fcn.0041d7ac` (the wrapper),
but a *second* caller at `0x41da32`, flagged `(nofunc)` -- i.e. inside a
region r2's analyzer also hasn't bounded into a function, the same
"unbounded gap region" symptom documented throughout this project for
Ghidra. `0x41da32` sits between the second and third Layer-3 functions
(`0x41d938` and `0x41da90`) -- worth a closer look in a future session,
see [`docs/18_future_work.md`](../../docs/18_future_work.md).

## Version-diff sanity check (DIY, no Diaphora/BinDiff)

Simple Python byte-search, run against every firmware build already held
locally by this project (see [`hashes/firmware_hashes.txt`](../../hashes/firmware_hashes.txt) -- Diaphora and
BinDiff were considered but not installed, judged not worth the setup risk
for a single targeted comparison):

```python
import struct

STATE_CHECK_SIG = bytes.fromhex('6818b101')  # ldr r0,[r4,#0xc]; cbz r0,...

for path in [...]:  # each locally-held *.decompressed.bin
    data = open(path, 'rb').read()
    struct_lit_hits = sum(
        1 for i in range(len(data) - 3)
        if struct.unpack_from('<I', data, i)[0] == 0x2000378c
    )
    sig_hits = []
    idx = 0
    while (idx := data.find(STATE_CHECK_SIG, idx)) != -1:
        sig_hits.append(idx)
        idx += 1
    print(path, struct_lit_hits, sig_hits)
```

**Result:** the `ev` variant build (2023-10-13, a completely separate
build from the 2023-09-02 primary analysis target) contains the *exact
same* struct base address, at the *exact same* 18 file offsets, and
`sub_422f21`'s opcode signature at the *identical* file offset -- a real
cross-build confirmation this isn't specific to one file. Both 2019-era
builds lack the literal `0x2000378c` (expected -- different-era RAM
layout) but do each contain the `ldr r0,[r4,#0xc]; cbz` opcode signature
once, at their own offsets -- suggesting a structurally similar state
handler has existed across at least ~4 years of firmware releases. Not
traced further (would require redoing the base-address analysis
per-build) -- see [`docs/18_future_work.md`](../../docs/18_future_work.md).
