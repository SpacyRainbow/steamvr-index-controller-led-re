# Finding: hidden "Debug" HID interface unlocked via Feature report 0x12

**Date:** 2026-07-22
**Device:** Wired Index Controller, serial `LHR-XXXXXXXX`, bus 001 (originally device 012, now device 013 after reset)

## Sequence of events

1. Baseline: wired connection enumerates with **3** HID interfaces: `IMU` (input0), `Optical` (input1), `Controller` (input2). Report descriptors captured in `report_descriptors_raw.txt` / `report_map_parsed.txt`.
2. Ran `scripts/test_feature_toggle_candidates.py`, which does `SET_FEATURE` with value `0x01` then `0x00` on five untested 1-byte Feature report IDs (`0x06, 0x0c, 0x0d, 0x12, 0x16`) on the IMU interface (hidraw at the time: hidraw19).
3. `SET_FEATURE(0x06, 0x01)` → OK, revert to `0x00` → OK.
4. `SET_FEATURE(0x0c, 0x01)` → OK, revert → OK.
5. `SET_FEATURE(0x0d, 0x01)` → OK, revert → OK.
6. `SET_FEATURE(0x12, 0x01)` → OK. **~2.5s later**, the revert call (`SET_FEATURE(0x12, 0x00)`) failed with `errno=19 ENODEV ("No such device")`.
7. `SET_FEATURE(0x16, 0x01)` also failed with `ENODEV` — consistent with the device having already reset by this point (not a separate finding).
8. Checked `lsusb`: device re-enumerated as **Bus 001 Device 013** (was 012), same serial `LHR-XXXXXXXX` — confirms this is a controller-initiated USB reset/re-enumeration, not a disconnect or crash. Device is healthy.
9. **New USB configuration has 4 interfaces, not 3.** The new 4th interface (bInterfaceNumber 3, input3) has `iInterface` string **"Debug"**.

## Working hypothesis

`Feature report 0x12 = 0x01` on the IMU interface plausibly means **"enable debug mode"**, causing the firmware to re-enumerate USB with an additional diagnostic HID interface exposed. This has not been previously documented anywhere found in Phase 1 research. Not yet confirmed which single write in the batch caused it (0x12 is the leading candidate given exact timing, but 0x06/0x0c/0x0d cannot be fully ruled out as contributing — all three round-tripped without error, but a delayed effect is possible; a repeat test toggling only 0x12 in isolation should be run to confirm).

## Debug interface report map

```
0600ff0901a101150026ff007508953f8576090181027508953f857609019102953f85750901b102c0
```

Parsed:
- Report ID `0x76`, **Input**, 63 bytes
- Report ID `0x76`, **Output**, 63 bytes
- Report ID `0x75`, **Feature**, 63 bytes

## Probing so far (read-only)

- Passive listen on Input `0x76` for 3s: silent, no autonomous output.
- `GET_FEATURE(0x75)`: `EPIPE` (write-only, consistent with the pattern seen on every other Feature report on this device — only true state-reporting IDs like the dongle's version report respond to GET).

## Status / next steps

**Not yet attempted:** writing to Output report `0x76` or `SET_FEATURE(0x75, ...)`. This is flagged as higher-risk than the LED toggle candidates — an interface explicitly named "Debug" on an nRF52840 could plausibly expose memory/flash-level primitives, not just cosmetic controls. Recommend: confirm with the user before writing to this channel, and if proceeding, start with the most conservative possible payloads (e.g. single zero byte, or short recognizable ASCII like `?`/`help` in case it's a text-based debug console) while watching for any sign of DFU/bootloader entry (which would show as yet another USB re-enumeration with a different VID/PID or descriptor).

## Confirmed side effects of the batch test

- Controller LED was not observed by a human during this test (nobody was watching). **Unknown whether 0x06, 0x0c, 0x0d, or 0x12 changed the LED at any point** — worth re-running each in isolation with the user watching, now that we know 0x12 has a side effect unrelated to LED (or which might BE the LED-adjacent "identify/debug indicator" — unconfirmed).
- No permanent harm: device recovered on its own, re-enumerated cleanly, serial/identity unchanged.
