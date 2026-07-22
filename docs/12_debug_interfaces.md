# 12 — The Undocumented USB HID Debug Interface

This is, alongside the successful firmware-patching work, one of the two
most significant findings of this project. It required no special hardware,
no vulnerability exploitation, and no signed/authenticated unlock sequence —
just a single standard USB HID `SET_FEATURE` control transfer.

## Discovery process

The controller, connected via USB, normally exposes exactly three HID
interfaces (confirmed via `dump_hid_descriptors.py`,
`scripts/dump_hid_descriptors.py`), corresponding to `input0` (an "IMU"-like
interface with the most report IDs), `input1`, and `input2`.

Systematic enumeration of every Feature report on every interface (a
methodical GET_FEATURE sweep, `scripts/read_feature_reports.py`) found that
most Feature reports on the wired controller returned `EPIPE` (write-only
slots), except a small number of single-byte Feature reports that looked
like plausible boolean/enum toggles by their declared size. These were
tested one at a time with `SET_FEATURE`
(`scripts/test_feature_toggle_candidates.py`): report `0x06`, `0x0c`,
`0x0d`, `0x12`, `0x16`.

**Setting report `0x12` to value `0x01` caused the device to reset and
re-enumerate on USB with a fourth HID interface** (`input3`), whose
`iInterface` USB string descriptor is literally the ASCII text **"Debug"**.

## Confirming it is the same physical device

The device's USB serial descriptor (`LHR-XXXXXXXX`) was confirmed identical
before and after the reset, while the Linux USB device number changed (e.g.
012 → 013) — the expected behavior for a genuine re-enumeration of the same
physical device, not a different device appearing.

## The Debug interface's report descriptor

```
0600ff0901a101150026ff007508953f8576090181027508953f857609019102953f85750901b102c0
```

Decoded (`scripts/parse_hid_descriptor.py`): Report ID `0x76`, 63-byte Input;
Report ID `0x76`, 63-byte Output; Report ID `0x75`, 63-byte Feature.

## Enabling it, reproducibly

```python
import os, fcntl

# Find the correct hidraw node for "input0" of the Valve Index Controller
# first — this changes across reboots/reconnects, always re-verify.
PATH = '/dev/hidrawN'
HIDIOCSFEATURE = lambda length: (3 << 30) | (ord('H') << 8) | 0x06 | (length << 16)

fd = os.open(PATH, os.O_RDWR)
try:
    fcntl.ioctl(fd, HIDIOCSFEATURE(2), bytes([0x12, 0x01]))
finally:
    os.close(fd)
```

After running this, wait ~2 seconds and re-enumerate hidraw nodes
(`scripts/dump_hid_descriptors.py`) — a fourth "Valve Index Controller"
hidraw node will appear (`input3`), matching the report descriptor above.

**Important operational note:** debug mode does **not** persist across a
firmware reflash or a full power cycle — it must be re-enabled after every
such event. This was observed consistently across the project (confirmed
after both firmware-patch flashes and both same-version safety-test
flashes).

## Disabling it

The same call with value `0x00` instead of `0x01` reverts the device to
three interfaces. Confirmed working (used deliberately at one point to test
whether the extra interface was interfering with the official update tool —
see `docs/14_failed_attempts.md`; it was not the cause of that particular
issue, but disabling was confirmed to work cleanly regardless).

## The command shell wire protocol

Once the Debug interface is open, it hosts a live ASCII text command shell.
The wire framing was **not** documented anywhere and had to be reverse
engineered empirically (see `docs/14_failed_attempts.md` for the framing
bug encountered along the way):

**Request/response framing:** `[report_id = 0x76][length_byte][ascii_text]`,
sent as a 64-byte HID report (1 report-ID byte + 63-byte payload capacity,
though the payload's *first* byte within that 63 is the ASCII length, not
data).

- To send a command: write a report with `buf[0] = 0x76`,
  `buf[1] = len(command_text_including_trailing_newline)`,
  `buf[2:2+len] = command_text.encode('ascii')`.
- Responses arrive as one or more 64-byte HID Input reports with the same
  `[0x76][length][ascii]` framing; multi-report responses must be
  reassembled by concatenating the `[2:2+length]` slice of each report in
  arrival order.

**Discovery bug (preserved for the record):** the first attempt sent the
command text starting immediately at `buf[1]` (omitting the length byte
entirely). The device responded with `"Unknown Command elp"` (missing the
leading `h` of `help`) — the response's own length byte matched exactly the
byte count of `"elp"`, which was the clue that the *first* byte of the
payload needed to be a length field, not text. See
`scripts/probe_debug_shell.py` (the buggy version, kept for the record) and
`scripts/debug_shell.py` (the corrected, reusable client).

## Reusable client

`scripts/debug_shell.py` implements this protocol as a simple `run(cmd)`
function. See `docs/11_hid_commands.md` for the full catalogue of commands
discovered through it, and `tools/` for setup notes.

**Known fragility:** the script hardcodes a `/dev/hidrawN` path that
reflects whatever node number was assigned during a specific session — this
number is **not stable** across reboots, reconnects, or firmware flashes
(all of which cause re-enumeration). Always re-run
`scripts/dump_hid_descriptors.py` first and update the path before using
`debug_shell.py` in a new session.

## Security implications (brief note, not a focus of this project)

This interface requires no authentication, PIN, or cryptographic unlock —
a single unauthenticated HID Feature-report write from any USB host with
access to the device is sufficient to enable a full read (and, per the
firmware string evidence discussed in `docs/10_protocol_analysis.md`,
likely write) interface to internal device state, including calibration
data. This project did not investigate the security implications in
depth (e.g., whether this could be triggered by malicious software with no
special privileges, or whether SteamVR itself ever enables it) — this is
flagged as a possible area for separate, security-focused follow-up work in
`docs/18_future_work.md`, distinct from this project's LED-focused scope.
