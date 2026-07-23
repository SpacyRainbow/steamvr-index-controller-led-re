# tools/

Third-party tools used in this project, and exact, tested setup
instructions for each — written because both tools required
non-obvious, non-root installation procedures on the Linux environment
used for this research, which cost real debugging time
([`../docs/14_failed_attempts.md`](../docs/14_failed_attempts.md) "Environment/tooling dead ends").

| Tool | Version used | Purpose | Setup doc |
|---|---|---|---|
| radare2 | 5.9.8 | x86-64 disassembly of `lighthouse_watchman_update` (Valve's official update tool), and early-stage ARM firmware analysis | [`radare2_setup.md`](radare2_setup.md) |
| Ghidra | 12.1.2 | Full ARM Cortex-M4/Thumb-2 disassembly and decompilation of the controller's application firmware | [`ghidra_setup.md`](ghidra_setup.md) |
| capstone (Python library) | 5.0.9 | Lightweight scriptable Thumb-2 disassembly, used before Ghidra was set up ([`../scripts/disasm_config.py`](../scripts/disasm_config.py)) | installed via `pip install --user capstone`, no special setup needed |

Both radare2 and Ghidra were installed **without root access** by
downloading distribution RPM packages with `dnf download --resolve` (which
does not require root for the download itself) and extracting them with
`rpm2cpio`/`cpio` into a local, non-system directory. This approach is
documented in full in each tool's setup file below, since it is the
non-obvious part — both tools are trivial to use once correctly extracted.
