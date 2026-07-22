# 02 — Background and Prior Art

## Starting knowledge

Before this investigation began, the following was publicly known and used
as a starting point:

- The Valve Index Controller ("Knuckles") is part of Valve's Lighthouse /
  Watchman family of tracked VR devices, which share a common wireless
  protocol lineage going back to the original HTC Vive wand controller.
- Valve's `hid-steam.c` Linux kernel driver (upstream, publicly available)
  documents a haptic-pulse command (`ID_TRIGGER_HAPTIC_PULSE = 0x8F`) sent
  as an Output report on Valve HID devices, establishing that these devices
  accept vendor-defined command bytes over standard USB HID Output/Feature
  reports.
- The community project **`nairol/LighthouseRedox`** (public GitHub
  repository) had previously reverse-engineered the wireless HID protocol
  used by the original Vive wand ("Watchman"), including: use of HID Report
  ID 255 as a multiplexed command channel, command `0x8F` for haptic pulses,
  and command `0x9F` for power-off (with a magic byte sequence `'o','f','f','!'`).
  This established precedent for how Valve's firmware exposes vendor
  commands over HID, and directly informed the initial hypothesis that a
  similar undocumented channel might exist for LED control on the newer
  Index Controller.
- OpenVR's public API exposes exactly one LED-adjacent property:
  `Prop_Identifiable_Bool` (property ID 1043), used for "blink to identify."
  No other LED-related property exists in the public OpenVR/SteamVR headers.

## What was NOT known at the start

- Whether the Index Controller's LED is a simple on/off or fixed-color
  indicator, or a fully addressable RGB(W) element.
- Whether the controller's firmware is encrypted, signed, or otherwise
  protected against extraction or modification.
- Whether any undocumented HID interfaces or debug facilities exist on the
  Index Controller specifically (as opposed to the older Vive wand, which
  LighthouseRedox covered).
- The exact microcontroller, LED driver chip, or flash layout used by the
  Index Controller.

## Related public tooling consulted

- **`DJm00n/ControllersInfo`** (public GitHub repository cataloguing VR
  controller USB/HID identifiers) — checked early in the investigation.
  Found to have **no entry for Valve devices**, a dead end noted and
  discarded quickly. See `14_failed_attempts.md`.
- **`ValveSoftware` public IndexHardware repository** — found to contain CAD
  files only, no firmware or protocol information. Another quickly-discarded
  dead end.
- Valve's own **`hid-steam.c`** kernel driver source — useful for the
  haptic-pulse command precedent above, but does not cover LED behavior at
  all.

## Hardware identification (initial pass, via public teardown)

A publicly available iFixit teardown of the Index Controller was used as the
initial source for hardware identification, later independently confirmed
via firmware string analysis (see `03_hardware.md` for the confirmed,
firmware-verified hardware inventory):

- MCU: Nordic nRF52840 (Cortex-M4F, Bluetooth Low Energy SoC family)
- FPGA: Lattice iCE40HX8K-CB132, believed to handle optical/IR sensor timing
  for the Lighthouse tracking system
- SPI NOR flash: Winbond W25Q32JW

## nRF52840 flash-protection bypass research (background, not used)

Because the nRF52840 supports a hardware flash-read-protection mechanism
(APPROTECT), the investigation initially researched voltage-glitching
techniques to bypass it as a *backup* firmware-extraction path, in case the
firmware turned out to be protected. Two specific public references were
identified:

- Research by **LimitedResults** on nRF52 APPROTECT bypass via voltage
  glitching.
- A public ESP32-based automated glitching tool by **Aaron Christophel**.

This path was **never exercised**, because firmware extraction turned out to
require no special technique at all — see `04_firmware_acquisition.md`. It
is recorded here only because it shaped early risk assessment (the
investigation was prepared for the possibility of protected firmware, which
did not materialize) and because it remains a viable fallback for anyone
extending this work to a firmware build that does turn out to be protected.

## How prior art shaped the investigation's direction

The single most consequential piece of prior art was the LighthouseRedox
HID protocol precedent. It established the expectation that Valve's
firmware likely exposes vendor commands over standard HID Output/Feature
reports rather than some entirely custom transport, which directly motivated
the systematic HID report enumeration described in `12_debug_interfaces.md`
— a process that led to discovering the undocumented Debug interface, the
single most important structural discovery of this project.
