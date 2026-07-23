# Project Timeline

Compact chronological milestone table. Each row links to the document with
full Objective/Reasoning/Method/Evidence/Outcome detail — this table is a
navigation aid, not a duplicate of that detail.

| Date | Milestone | Outcome | Full detail |
|---|---|---|---|
| 2026-07-22 | Background/prior-art research | Established LighthouseRedox HID precedent, hardware hypothesis (nRF52840/iCE40/Winbond) | [`docs/02_background.md`](../../docs/02_background.md) |
| 2026-07-22 | Firmware acquisition attempt | Trivial success — no protection to bypass | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 4 |
| 2026-07-22 | LED driver chip identification | Confirmed TI LP5562 via firmware strings | [`docs/08_lp5562_driver.md`](../../docs/08_lp5562_driver.md) |
| 2026-07-22 | Full HID interface/report enumeration | Complete map of 3 interfaces' reports | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 1 |
| 2026-07-22 | Feature-report toggle sweep | **Discovered undocumented "Debug" HID interface** | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 2 |
| 2026-07-22 | Debug shell wire-framing reverse engineering | Corrected framing bug, working shell client | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 3 |
| 2026-07-22 | Config command write-path testing | Confirmed dead end — shell is read-only for config | [`docs/14_failed_attempts.md`](../../docs/14_failed_attempts.md) |
| 2026-07-23 | Config defaults table structure recovery | Fully mapped 9-byte packed struct, verified against 30 live values | [`docs/06_firmware_symbols.md`](../../docs/06_firmware_symbols.md) §6.2 |
| 2026-07-23 | `.fw` footer format reverse engineering | Full field layout incl. self-referential CRC | [`docs/05_firmware_layout.md`](../../docs/05_firmware_layout.md) §5.2 |
| 2026-07-23 | First live flash (same-version safety test) | Success — pipeline proven safe | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 6a |
| 2026-07-23 | First patch attempt | Rejected safely (stale footer CRC) — root cause found via tool disassembly | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 5 |
| 2026-07-23 | LED-current value patches (255, then 0) | Real but inconclusive/incomplete effects | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 6b–6c |
| 2026-07-23 | **Layer-1 code patch: forced LED black** | **Confirmed complete blackout on real hardware — primary project result** | [`docs/13_experiments.md`](../../docs/13_experiments.md) Exp. 7 |
| 2026-07-23 | Selective (charging-aware) patch investigation begins | Traced 3 layers of LED call graph, hit genuine dead end at Layer 3→4 | [`docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md) |
| 2026-07-23 | Ghidra toolchain installed (no root) | Resolved several prior open questions, including a function-boundary correction | [`tools/ghidra_setup.md`](../../tools/ghidra_setup.md) |
| 2026-07-23 | Power-management task lead | Confirmed charging-state code does NOT directly call LED subsystem — reframed remaining problem as RTOS shared-state, not call-graph | [`docs/16_charging_led_research.md`](../../docs/16_charging_led_research.md) |
| 2026-07-23 | This repository created | Full documentation archive per project philosophy | [`README.md`](../../README.md) |

See `daily_logs/2026-07-22.md` and `daily_logs/2026-07-23.md` for
narrative chronological detail, and
[`investigation_evolution.md`](investigation_evolution.md) for how understanding specifically changed at
each major pivot.
