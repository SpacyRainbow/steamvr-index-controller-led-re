# 01 — Project Overview

## Objective

Determine, with a high degree of confidence, whether the status LED on a
Valve Index Controller can be controlled by software beyond the behavior
SteamVR/OpenVR expose to applications. If software control is possible,
demonstrate it concretely (a working method, ideally verified visually on
real hardware). If it is not possible, determine exactly why and document the
limiting factor.

This was framed from the outset as a reverse-engineering project, not a
documentation-search exercise: the goal was to keep investigating — firmware
extraction, live protocol probing, binary patching — until a definitive,
evidence-backed answer was reached, rather than stopping at "SteamVR doesn't
expose an API for this."

## Why this question matters

OpenVR exposes exactly one LED-adjacent capability to applications:
`Prop_Identifiable_Bool` (OpenVR property 1043), a boolean that triggers a
"blink to identify" behavior. There is no documented way for a SteamVR
application, or any other software, to set an arbitrary color, change
brightness, or disable the LED. Whether that gap is a deliberate API
limitation over a much more capable piece of hardware, or a reflection of a
genuinely fixed-function LED, was previously unknown and not something either
Valve's documentation or public community knowledge resolved.

## Research philosophy

The investigation followed a small number of explicit rules, established at
the start and adhered to throughout:

- Do not assume the answer is "no." Do not assume the answer is "yes."
  Follow the evidence.
- Whenever one avenue is exhausted, begin another rather than stopping.
- If firmware extraction appears possible, prioritize it over further web
  research — direct evidence from the actual firmware outweighs
  documentation or forum speculation.
- If firmware extraction turns out to be impossible, determine exactly why
  and document the limiting factor (this did not end up being necessary —
  extraction was trivial; see `04_firmware_acquisition.md`).
- Preserve dead ends. A technique that failed is still evidence, and
  prevents future re-investigation of the same false lead.

## Methodology, as actually followed

The investigation moved through phases, though not always in a strictly
linear order — several phases were revisited as new evidence surfaced. In
the order they were substantively pursued:

1. **Prior-art and documentation research** — establishing what is publicly
   known about the Index Controller's hardware, the Lighthouse/Watchman
   protocol family, and prior community reverse-engineering work. See
   `02_background.md`.
2. **Firmware acquisition** — locating and extracting the firmware images
   SteamVR ships for the controller. See `04_firmware_acquisition.md`.
3. **Static firmware analysis** — identifying the LED driver hardware and
   its firmware-side driver code via string analysis, before any
   disassembly tooling was available. See `08_lp5562_driver.md`.
4. **Live USB HID protocol investigation** — mapping every HID report on
   every interface the controller exposes, which led to discovering an
   undocumented debug interface. See `12_debug_interfaces.md`,
   `11_hid_commands.md`.
5. **Firmware container format reverse engineering** — driven by a failed
   patch attempt against Valve's own update tool, which forced a full
   disassembly of that tool's validation logic. See `05_firmware_layout.md`.
6. **Live firmware patching and flashing** — building and successfully
   flashing modified firmware to real hardware, first as a same-version
   safety test, then as an actual behavioral patch. See
   `13_experiments.md`, `15_firmware_patching.md`.
7. **Deep ARM/Thumb-2 disassembly of the LED subsystem**, first by hand and
   with lightweight tools, later with a properly installed Ghidra headless
   toolchain, to trace the exact code path from "LED color request" down to
   the hardware register writes. See `06_firmware_symbols.md`,
   `07_led_architecture.md`.
8. **RTOS task-boundary tracing**, the current open frontier — attempting to
   connect the power-management task's charging-state logic to the LED
   policy's color decision. See `16_charging_led_research.md`.

## What "done" looks like for this project

The core research question (can software control the LED at all) is
answered with high confidence and does not require further work to close.
The project's remaining open work is a *refinement*, not a re-litigation of
that answer: producing a firmware patch that changes LED behavior
selectively (e.g., preserving charging-status indication while disabling the
LED during normal use) rather than only as a blunt "always on" / "always
off" toggle.

See `18_future_work.md` for the prioritized list of what remains.
