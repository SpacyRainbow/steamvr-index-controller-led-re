# 10 — Protocol Analysis

This document covers the two distinct protocols identified for
communicating with the controller beyond normal HID input/output reports:
the plaintext debug shell (summarized here, fully documented in
`docs/11_hid_commands.md` and `docs/12_debug_interfaces.md`), and the binary
firmware/config update protocol used by Valve's official
`lighthouse_watchman_update` tool, which is the primary subject of this
document.

## 10.1 Overview: two independent protocols exist

It is important to distinguish these clearly, because early in the project
they were conflated:

1. **The debug shell protocol** — ASCII text commands and responses over a
   dedicated HID interface (report ID `0x76`). Human-oriented, read-mostly
   (writes to config values via this channel were attempted and did not
   work — see `docs/14_failed_attempts.md`). Fully documented in
   `docs/11_hid_commands.md` and `docs/12_debug_interfaces.md`.
2. **The firmware/config update protocol** — a binary protocol used to
   transfer entire firmware images (and, per the official tool's
   command-line flags, potentially standalone JSON configuration data) to
   the device, driving an actual flash erase/write/verify cycle. This is
   the subject of the remainder of this document.

## 10.2 Evidence for a JSON+zlib config protocol distinct from firmware flashing

Firmware string analysis found log messages strongly suggesting the
existence of a JSON-based configuration protocol, separate from full
firmware images:

```
"LWU: JSON"
"Config: load JSON"
"Config: JSON err"
"JSON: save %d bytes"
"JSON: unzip err"
"JSON: %d of %d bytes used"
"JSON overflow: %u bytes > %u free"
"JSON: Out of sequence request"
```

("LWU" is believed to stand for "Lighthouse Watchman Update," matching the
name of Valve's own tool discussed below.) These strings, combined with the
existence of a dedicated `stored_conf` flash partition separate from the
application firmware image (`docs/05_firmware_layout.md` §5.3), support the
hypothesis that device-specific calibration/configuration data (distinct
from the compiled-in defaults table documented in
`docs/06_firmware_symbols.md`) is transferred to and from the device as a
JSON payload, compressed with zlib, chunked over HID `SET_FEATURE`/
`GET_FEATURE` transfers.

**This hypothesis was never independently confirmed by capturing an actual
JSON payload.** Two attempts were made:

- Passively listening on the debug HID interface for spontaneous log output
  during a config-related event — no output was captured (the debug
  interface does not appear to stream this class of log line, or the
  triggering event never occurred during the listening window). See
  `docs/14_failed_attempts.md`.
- Running the official update tool with its `--restore-json` flag (which
  should, per its own `--help` text, back up and restore a JSON
  configuration file around a firmware update) — no backup file was found
  on disk after two full successful firmware updates. The most likely
  explanation (unconfirmed): the JSON backup/restore logic may only
  activate on an actual version change, and both test updates were
  same-version (byte-identical) safety tests. See
  `docs/13_experiments.md` Experiment 5.

**Status: hypothesis, ~70% confidence.** The string evidence for the
protocol's *existence* is strong; its exact wire format and how to trigger
it independently of a full firmware flash were not determined.

## 10.3 The firmware flashing protocol (confirmed, used successfully)

Unlike the JSON config protocol, the firmware-image flashing protocol was
**fully exercised successfully**, four times, using Valve's own official
tool rather than a protocol implementation built from scratch. This section
documents what running that tool revealed, not a from-scratch reverse
engineering of the wire protocol.

### The tool

`lighthouse_watchman_update`, a native Linux x86-64 binary shipped as part
of SteamVR at `tools/lighthouse/bin/linux64/lighthouse_watchman_update`.
Confirmed to run standalone, without SteamVR itself running.

Relevant command-line flags discovered via `--help` and used successfully:

```
-m<dev>                  Update main firmware (default)
--via-application         (Watchman v3 devices only) Sends the update
                           via the device's application interface
--via-bootloader          (default if --via-application is not given)
                           Sends the update via the device's bootloader —
                           requires the device already be in bootloader
                           mode, which a running application-firmware
                           device is NOT. Using this flag against a
                           normally-running controller fails cleanly with
                           "Error: unable to open device." — this consumed
                           significant debugging time before being
                           understood; see docs/14_failed_attempts.md.
-s <serial num>            Target a specific device by serial (optional
                           if only one matching device is connected)
--restore-json             Backup/restore JSON config around the update
                           (see 10.2 above — did not produce an observable
                           backup file in this project's testing)
```

### Observed protocol behavior (from tool console output, successful run)

```
Searching for devices with any HWID
Found 1 matching device
Serial: LHR-80E7752A, PID: 2300, HWID: 110e0009 (index controller pv right)
Updating device: 1 of 1
Attempting to update WATCHMAN v3 (target: 2) via application
Computed checksum (offset 0): 00000000
Starting update...
Sending data...
[... progress dots, one per chunk sent ...]
Done
Sending reset command
Successfully updated firmware.
Waiting for firmware to apply update...
Done
```

This confirms: the update is chunked (progress dots), a checksum is
computed and communicated before the transfer begins, and an explicit reset
command is sent after the data transfer completes, causing the device to
re-enumerate on USB (confirmed via `lsusb` device-number increments,
`docs/13_experiments.md`).

### Underlying transport (from string evidence in the tool binary, not fully disassembled)

Strings found in the tool binary (`strings -a`) indicate it communicates
over `hidraw` using `ioctl (SFEATURE)` — i.e., standard Linux HID
`SET_FEATURE` control transfers, the same general transport class used by
the debug shell — with a maximum single-message payload noted as 61 bytes
(`"Simple HID message payload %zd is larger than max size of 61"`),
suggesting a similar `[report_id][length][data]`-style framing to what was
independently reverse-engineered for the debug shell
(`docs/12_debug_interfaces.md`), though this was not directly confirmed by
USB traffic capture — no USB-level packet capture (e.g., via `usbmon` or
Wireshark) was performed in this project. This is listed as a priority item
in `docs/18_future_work.md`, since a live capture would definitively answer
the open JSON-protocol questions in §10.2.

## 10.4 What was proven vs. inferred — summary

| Claim | Status | Confidence |
|---|---|---|
| A firmware image can be pushed to the device via `lighthouse_watchman_update --via-application` and successfully applied | **Proven**, reproduced 4 times live | 100% |
| The `.fw` container format (`docs/05_firmware_layout.md`) is what the device/tool actually validates | **Proven** — a footer-format error was reproduced, understood, and fixed, after which patched files were accepted and flashed successfully | 100% |
| A separate JSON+zlib config protocol exists | Inferred from strings; plausible | ~70% |
| The exact wire framing of the JSON config protocol | Not determined | n/a |
| The underlying HID transport uses `SET_FEATURE` with `[report_id][length][data]`-style framing, similar to the debug shell | Inferred from tool strings, not captured | ~60% |
