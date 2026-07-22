# research/firmware_analysis/

Derived analysis output from the decompressed firmware image (not the
firmware itself — see `../../firmware/README.md` and
`../../hashes/firmware_hashes.txt`).

| File | Contents | Referenced by |
|---|---|---|
| `strings_led_all.txt` | Every LED-related string extracted from the decompressed application firmware (~70 strings) | `docs/06_firmware_symbols.md` §6.4, `docs/08_lp5562_driver.md`, `docs/09_led_policy.md` |
| `config_table_decode_output.txt` | Full 46-entry decode of the compiled-in config defaults table, with live-value cross-check | `docs/06_firmware_symbols.md` §6.2, produced by `../../scripts/decode_config_table.py` |

For Ghidra-specific decompiler output (function decompilations, gap-region
listings), see `../decompiler_notes/` instead.
