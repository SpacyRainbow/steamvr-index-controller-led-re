/* Ghidra decompilation of the color-request wrapper function.
 * Runtime address: 0x41d7ac (decompressed file offset 0xd7ac - 0x412000...
 * i.e. file offset 0x97ac in indexcontroller_app_20230902_v1693638519.fw.decompressed.bin)
 *
 * Produced by: research/decompiler_notes/02_LedTrace_wrapper_callers.java
 * (LedTrace3.java in the original session, renumbered here for clarity)
 *
 * This is Layer 2 in docs/07_led_architecture.md. Decompiled cleanly on
 * the first attempt once the correct function entry point was identified
 * (see docs/14_failed_attempts.md for the earlier mis-identification of
 * this function's boundary at 0x41d7a8 instead of the correct 0x41d7ac).
 *
 * Ghidra auto-generated names (param_1, param_2, DAT_*, FUN_*) are left
 * unmodified below, exactly as produced -- this is the raw evidence, not
 * a cleaned-up rewrite. See docs/06_firmware_symbols.md for the
 * human-assigned names/roles cross-referenced against these addresses.
 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_0041d7ac(int param_1,undefined4 param_2)

{
  int iVar1;

  if ((int)(uint)*_DAT_0041d7e8 < param_1) {
                    /* WARNING: Subroutine does not return */
    FUN_00429064(s_led_driver_lp5562_c_0041d7eb + 1,0x8a);
  }
  iVar1 = DAT_0041d800 + param_1 * 10;
  if (*(char *)(iVar1 + 1) != '\0') {
    *(undefined1 *)(iVar1 + 1) = 0;
    FUN_0041e7d8(param_1);
  }
  FUN_0041dbf0(param_1,param_2);
  return 0;
}

/* Reading notes:
 *
 * - param_1 = led_id, param_2 = requested packed WRGB color (opaque to
 *   this function -- it never inspects the color value itself, only
 *   forwards it).
 * - First block: bounds-check led_id against a maximum (loaded from
 *   DAT_0041d7e8), calling the assert/error handler FUN_00429064 with a
 *   "led_driver_lp5562.c" filename string and line number (0x8a) if out
 *   of range. This matches the "Invalid LED ID %u" string found
 *   elsewhere in the firmware (docs/06_firmware_symbols.md sec 6.4).
 * - Second block: looks up a per-LED 10-byte struct (stride confirmed:
 *   `param_1 * 10`) at a fixed base (DAT_0041d800), checks a flag byte at
 *   offset +1. If set, clears it and calls FUN_0041e7d8(led_id) -- the
 *   "off-path" function (docs/07_led_architecture.md), presumably to
 *   force a clean transition from a previous "off" state before applying
 *   a new color.
 * - Final line: unconditionally calls FUN_0041dbf0(led_id, color) -- the
 *   low-level PWM writer (docs/06_firmware_symbols.md sec 6.3) -- with
 *   whatever color the caller originally requested. This is the function
 *   that patches/patch_B_led_black.decompressed.xdelta3 ultimately forces
 *   to always receive/apply color=0, by patching inside FUN_0041dbf0
 *   itself rather than here.
 *
 * This function's three direct callers (found via Ghidra's reference
 * manager once this entry point was correctly identified) are documented
 * in docs/16_charging_led_research.md -- none of them were successfully
 * traced further upward to find the actual state-to-color policy
 * decision.
 */
