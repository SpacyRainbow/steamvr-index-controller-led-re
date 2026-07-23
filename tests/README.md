# tests/

Automated tests for this repository's reusable analysis logic. All tests
use entirely synthetic data — none require, embed, or redistribute any
real Valve firmware, per this project's Legal Notice (top-level [`README.md`](../README.md)).

## Why these exist

Most of this project's work is one-off, hands-on reverse engineering
against real hardware — not the kind of thing that's normally
unit-testable. But a few pieces of *logic* extracted from that work are
pure, self-contained, and directly testable: the `.fw` footer's
self-referential CRC formula, the config-table struct layout, and the
Thumb-2 `BL` instruction encoder. These are exactly the pieces most likely
to silently break if refactored later, and — in the case of the `BL`
encoder — a real bug in exactly this class of logic already caused a
false research lead during live investigation (see
[`../docs/14_failed_attempts.md`](../docs/14_failed_attempts.md) "Brute-force `BL`-encoding search had a
real bug"). These tests exist to catch that class of mistake automatically
next time, rather than relying on a researcher noticing a surprising
result and manually cross-checking it.

## Running the tests

No dependencies beyond the Python 3 standard library:

```bash
cd steamvr-index-controller-led-re
python3 -m unittest discover -s tests -v
```

or, if you have `pytest` installed:

```bash
python3 -m pytest tests/ -v
```

## What's covered

| File | Covers | Why it matters |
|---|---|---|
| [`test_bl_encoder.py`](test_bl_encoder.py) | [`scripts/find_bl_callers.py`](../scripts/find_bl_callers.py)'s Thumb-2 `BL` encoder | Includes a direct regression test for the exact bug found during research ([`../docs/14_failed_attempts.md`](../docs/14_failed_attempts.md)), plus a round-trip encode/decode check across many synthetic offsets |
| [`test_footer_format.py`](test_footer_format.py) | The `.fw` container's self-referential `final_crc` field ([`../docs/05_firmware_layout.md`](../docs/05_firmware_layout.md) §5.2) | This is the exact field whose staleness caused a real, live "Invalid firmware file" rejection during patch development ([`../docs/13_experiments.md`](../docs/13_experiments.md) Experiment 5) — these tests pin down the correct behavior so a future patch script can't reintroduce that bug silently |
| [`test_config_table_format.py`](test_config_table_format.py) | The 9-byte packed config-entry struct ([`../docs/06_firmware_symbols.md`](../docs/06_firmware_symbols.md) §6.2) | Regression-pins the struct layout this project reverse engineered from a single real device, and specifically guards against re-confusing the `name_ptr` field with a value (an early, disproven hypothesis during the original research) |

## What's NOT covered, and why

The actual patch-building scripts ([`scripts/patch_led_black.py`](../scripts/patch_led_black.py),
[`scripts/patch_led_firmware.py`](../scripts/patch_led_firmware.py), [`scripts/patch_led_solid_color.py`](../scripts/patch_led_solid_color.py)) are
**not** directly unit-tested here, because they are hardcoded against a
specific real firmware file's exact byte offsets and content, which this
repository cannot include (see [`../firmware/README.md`](../firmware/README.md)). Their correctness
is instead verified by:

1. The built-in round-trip check every one of those scripts performs on
   its own output before declaring success (decompress the file it just
   built, confirm the footer is self-consistent, confirm the intended byte
   change is present) — see [`../docs/15_firmware_patching.md`](../docs/15_firmware_patching.md) §15.1 step 7.
2. Live hardware verification, documented per-patch in
   [`../docs/13_experiments.md`](../docs/13_experiments.md).

If you obtain the real firmware yourself ([`../docs/04_firmware_acquisition.md`](../docs/04_firmware_acquisition.md))
and want to exercise these scripts end-to-end, that is real, valuable
testing this repository's automated suite cannot do for you without
redistributing Valve's firmware — do it locally, and consider updating
[`../docs/13_experiments.md`](../docs/13_experiments.md) or [`../docs/17_safety.md`](../docs/17_safety.md) "Version
compatibility warnings" with what you find, especially against any
firmware build other than the one this project's own hashes reference.
