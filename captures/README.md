# captures/ (top-level)

Reserved for raw USB traffic captures (e.g. `usbmon` or Wireshark/USBPcap
output). None were taken during this project — this is a flagged gap; see
[`docs/18_future_work.md`](../docs/18_future_work.md) Priority 1 and Priority 3, both of which identify
a live USB capture as the most promising next step for the project's two
biggest open questions (the charging-LED policy connection, and confirming
the JSON+zlib config protocol's wire format).

This directory is distinct from `research/captures/`, which holds
processed/derived HID descriptor dumps and debug-shell text transcripts
(not raw USB bus traffic) — see [`research/captures/README.md`](../research/captures/README.md).

When a capture is added here, reference it from the relevant document
([`docs/10_protocol_analysis.md`](../docs/10_protocol_analysis.md) for protocol-level captures,
[`docs/16_charging_led_research.md`](../docs/16_charging_led_research.md) for a charging-transition-correlated
capture) and note the exact capture tool/version/command used for
reproducibility.
