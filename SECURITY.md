# Security

## Scope of this document

This project's primary subject is LED behavior, not security research —
but the investigation surfaced one finding with real security relevance,
and this document exists to handle it responsibly rather than bury it in
a technical appendix.

## The finding

An undocumented USB HID interface ("Debug", [`docs/12_debug_interfaces.md`](docs/12_debug_interfaces.md))
on the Valve Index Controller can be enabled with a single, unauthenticated
`SET_FEATURE` HID control transfer — no PIN, no cryptographic challenge, no
prior pairing step. Once enabled, it exposes a live text command shell with
access to device internals: calibration constants, battery/charging
telemetry, hardware diagnostics, and (per firmware string evidence,
[`docs/10_protocol_analysis.md`](docs/10_protocol_analysis.md)) very likely a path to writing
configuration data, not just reading it.

Separately, this project also demonstrated that arbitrary modified
firmware can be built and flashed to the device by any host with USB
access and root/administrator privileges, using Valve's own official
update tool ([`docs/13_experiments.md`](docs/13_experiments.md), [`docs/15_firmware_patching.md`](docs/15_firmware_patching.md)).

## Why this is disclosed here, and how

This project did not report these findings to Valve as a formal security
vulnerability, for reasons explained below — this is a judgment call,
documented so a reader can evaluate the reasoning rather than just the
conclusion:

- **Physical/USB access is already required.** Both findings require the
  attacker to already have a working USB connection to the controller
  (either physically wired, or already paired over the wireless
  Watchman/dongle protocol). Neither finding demonstrates a way to reach
  the device remotely, over a network, or without the access level a
  legitimate owner or a physically-present attacker already has.
- **Firmware flashing already requires host-side privilege.** The
  demonstrated flashing path requires root/administrator access on the
  *host* machine ([`docs/17_safety.md`](docs/17_safety.md)), which is a privilege boundary
  Valve's tooling assumes, not one this project bypassed.
- **The debug interface's practical impact is primarily
  confidentiality/tamper of the controller's own calibration data**, not a
  path demonstrated in this project to escalate privilege on the host, hide
  malware, or affect anything beyond the single connected controller.

**This is a judgment call, not a definitive security assessment** — this
project did not attempt a rigorous threat-modeling exercise (e.g.,
whether a compromised or malicious application with ordinary user-level
USB access, but without root, could reach the debug interface and abuse
it in ways not explored here; whether the debug interface's write
capabilities, if any, could corrupt calibration data in a way that
degrades the device without full firmware reflashing; or whether this
generalizes to other Valve/Watchman-family devices beyond the Index
Controller). Anyone who believes this warrants formal disclosure to Valve
is encouraged to do so — this project's own conclusion not to is not
authoritative, and is stated explicitly so it can be second-guessed.

## What this repository does and doesn't help someone do

This repository documents how to:
- Enable the undocumented debug interface and use its read-only
  telemetry/diagnostic commands.
- Build and flash modified firmware, including a working example that
  disables a safety-irrelevant cosmetic feature (the status LED).

It does **not** document, and this project did not investigate:
- Any way to reach these capabilities without the same USB/host access a
  legitimate owner already has.
- Any firmware modification that disables safety-relevant functionality
  (e.g., tracking accuracy, battery safety cutoffs) — every patch built in
  this project targets the LED subsystem specifically and was chosen for
  that reason.
- Any technique for hiding a modification from the device's own reporting
  (patches in this project leave the firmware version string unchanged for
  the project's own convenience, which is explicitly flagged as a
  reproducibility choice with a caveat in [`docs/15_firmware_patching.md`](docs/15_firmware_patching.md)
  §15.4 — not a stealth feature, and not recommended practice for anyone
  building on this work for a purpose where that distinction matters).

## Responsible use

If you use this repository's findings or tooling: only against hardware
you own or have explicit authorization to test, and see
[`docs/17_safety.md`](docs/17_safety.md) before flashing anything to real hardware. This
project's own hands-on hardware work was performed exclusively against
the researcher's own controller, with the researcher's explicit
acknowledgment of and consent to the associated risk ([`docs/17_safety.md`](docs/17_safety.md)
"Risk summary").

## Reporting a concern about this repository

If you believe something in this repository should be handled
differently (redacted, disclosed to Valve first, or anything else), open
an issue on the repository, or see [`CONTRIBUTING.md`](CONTRIBUTING.md) for other contact
paths.
