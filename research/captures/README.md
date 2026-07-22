# research/captures/

Raw, unedited capture output referenced throughout `docs/`. These are the
primary evidence artifacts for the HID/debug-shell findings — treat them as
you would lab notebook raw data: not polished, but authoritative.

| File | Contents | Referenced by |
|---|---|---|
| `report_descriptors_raw.txt` | Raw HID report descriptor hex for every Valve device found on the test machine | `docs/12_debug_interfaces.md`, `docs/13_experiments.md` Exp. 1 |
| `report_map_parsed.txt` | Parsed (report ID, type, size) tables derived from the above | `docs/13_experiments.md` Exp. 1 |
| `feature_reports_dump.txt` | `GET_FEATURE` sweep results across all interfaces | `docs/13_experiments.md` Exp. 1–2 |
| `FINDING_debug_interface.md` | Original discovery writeup for the Debug interface, preserved as first-written | `docs/12_debug_interfaces.md` |
| `feature_toggle_candidates_log.txt` | Log of the `SET_FEATURE` toggle sweep that discovered the Debug interface | `docs/13_experiments.md` Exp. 2 |
| `debug_shell_help_attempt1.txt` | The buggy first debug-shell framing attempt (truncated response) | `docs/13_experiments.md` Exp. 3, `docs/14_failed_attempts.md` |
| `debug_shell_help_attempt2.txt` | The corrected attempt, full command list returned | `docs/13_experiments.md` Exp. 3 |
| `debug_shell_usage_queries.txt` | Usage-text queries for individual shell commands | `docs/11_hid_commands.md` |
| `debug_shell_command_survey.txt` | Survey of remaining shell commands' default behavior | `docs/11_hid_commands.md` |
| `debug_shell_config_syntax.txt` | Full 46-entry live `config` dump plus write-syntax attempts | `docs/06_firmware_symbols.md` §6.2, `docs/14_failed_attempts.md` |
| `config_set_attempt1.txt` | One specific `config set` write attempt and its (no-op) result | `docs/14_failed_attempts.md` |
| `session2_user_flash_probe.txt` | Probing of the `user_flash`/`user_data`/`flash_info` commands | `docs/11_hid_commands.md` |
| `haptic_sanity_check_log.txt` | Early sanity check confirming the wired connection is a full HID link | `docs/02_background.md`, `scripts/test_haptic_sanity_check.py` |

All captures are from the single test unit described in `docs/03_hardware.md`
(serial `LHR-XXXXXXXX`).
