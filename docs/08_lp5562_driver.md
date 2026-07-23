# 08 — The LP5562 and Its Firmware Driver

## The chip

The Texas Instruments LP5562 is a commercially available I2C-addressable
LED driver IC providing four independent current-sink output channels
(commonly wired to a single RGBW LED package or four discrete LEDs), each
with its own programmable current-limit register and PWM duty-cycle engine,
plus a small internal "program engine" capable of running simple animation
sequences (fades, blinks) autonomously without CPU intervention. This is a
publicly documented, off-the-shelf part — the driver IC itself is not
Valve-specific or secret in any way; only its *use* within this firmware
was reverse engineered.

**Why this chip's existence matters to this project's core question:** a
device wired to a simple GPIO-driven fixed-color/fixed-brightness LED could
only ever support on/off control, or at best a few hardware-fixed colors. A
device wired to an LP5562 is, by the chip's own design, capable of
arbitrary 24-bit-ish color and independent brightness control per channel —
the hardware ceiling for "how programmable can this LED possibly be" is
very high. This directly supports the project's core conclusion (see
[`docs/01_project_overview.md`](01_project_overview.md)): the limiting factor on LED control, if any,
is firmware policy, not hardware capability.

## Evidence this project relied on

1. String evidence in the decompressed firmware: `led_driver_lp5562.c`
   (source filename), `"LED: lp5562 led error"` (a runtime error message
   naming the chip directly). See [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.4.
2. The low-level color-write function (`0x41dbf0`,
   [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3, [`docs/07_led_architecture.md`](07_led_architecture.md) Layer 1)
   writes to hardware register offsets `0x10`, `0x30`, `0x50` — three
   distinct, evenly-adjacent-looking register addresses for what are
   believed to be the R/G/B channel PWM/current registers respectively
   (exact per-register confirmation against the public LP5562 datasheet
   register map was **not** performed in this project — see
   [`18_future_work.md`](18_future_work.md)).
3. A fourth channel (W, "white") is handled via a separate code branch in
   the same function, consistent with the LP5562 being a genuine 4-channel
   part rather than a 3-channel RGB-only driver.
4. The live debug shell's `config` command exposes exactly four
   `led_driver_current_{r,g,b,w}` values (§ [`docs/06_firmware_symbols.md`](06_firmware_symbols.md)
   §6.2), matching the LP5562's 4-channel architecture precisely.

## What was proven about the driver's behavior (live, on real hardware)

- Setting all four `led_driver_current_*` values to `255` (from a default of
  `8`) via a firmware patch did **not** produce an obviously perceptible
  brightness increase to the human tester. This is recorded as an open,
  unexplained observation — see "Brightness floor and ceiling phenomena"
  below.
- Setting all four values to `0` produced a dramatic, clearly visible
  dimming, but **not** a complete blackout — some residual glow remained.
- Directly patching the code that computes the final color value (Layer 1
  in [`docs/07_led_architecture.md`](07_led_architecture.md)) to force the color to literal zero
  **did** produce a complete, unambiguous blackout, confirmed by the human
  tester ("the LED is off!!").

This progression (current=0 dims but doesn't fully black out; a code-level
color=0 patch does) is itself evidence about the driver's internal
architecture: `led_driver_current_*` is a **scaling/calibration** value
applied multiplicatively to an already-determined base color (see the
scaler function `0x419250` in [`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.3), not the
sole determinant of output brightness. Depending on rounding/minimum
duty-cycle behavior in the driver or the LP5562's own internal current-sink
floor, a near-zero scale factor may not reach true zero output — but forcing
the *base color itself* to zero bypasses that scaling stage entirely and
reaches genuine hardware-level black. This explanation is a **hypothesis at
~70% confidence**, not confirmed by register-level tracing into the LP5562
I2C transactions themselves.

## Brightness floor and ceiling phenomena (open questions)

Two specific observations remain unexplained and are flagged for future
work ([`docs/18_future_work.md`](18_future_work.md)):

1. **Why did current=255 not look obviously brighter than the default
   (current=8)?** Possible explanations, none confirmed: the human-perceived
   brightness scale may already be near-saturated at low current values
   (nonlinear perception, gamma-correction-like behavior somewhere in the
   pipeline); the "current" registers might be clamped or interpreted
   differently than assumed (e.g., truncated to a smaller effective range
   before reaching the LP5562); or the specific color/state active during
   that test did not visually change even though the underlying values did.
2. **Why did current=0 not reach full black?** See the calibration-scaling
   hypothesis above.

Neither of these was resolved with hardware-level (oscilloscope/logic
analyzer on the I2C bus, or LP5562 register readback) verification. This
project relied entirely on firmware patching plus human visual observation,
not electrical instrumentation.

## What was NOT investigated

- The LP5562's internal "program engine" (for autonomous fade/blink
  sequences without CPU involvement) — whether this firmware uses it at
  all, and if so, how, was not determined. The `"glow not supported\n"`
  string ([`docs/06_firmware_symbols.md`](06_firmware_symbols.md) §6.4) suggests some animation
  capability exists in the driver architecture but may be disabled for this
  hardware/firmware configuration.
- Exact I2C bus address, transaction framing, or timing.
- Direct register-level readback (this project only observed effects via
  firmware-side state, never confirmed the LP5562's actual register
  contents independently).
- Whether the physical LED package is a single RGBW element or four
  discrete LEDs (this affects nothing about the software findings, but
  would be a natural companion fact for physical/photographic
  documentation, per [`18_future_work.md`](18_future_work.md)).
