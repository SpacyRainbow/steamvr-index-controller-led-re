#!/usr/bin/env python3
"""Decode the compiled-in config defaults table found in the app firmware.
Each entry is 9 bytes: [flag:1][address:4 LE][value:4 LE int32].
Table start located empirically at file offset 0x2c594 (== BASE+0x2c594 runtime),
anchored via the exact byte sequence for charge_voltage_limit_mv=4320 etc.
"""
import struct

FW = "04_firmware/decompressed/indexcontroller_app_20230902_v1693638519.fw.decompressed.bin"
BASE = 0x412000
TABLE_START = 0x2c594
ENTRY_SIZE = 9
N = 46

# names + live values from the 2026-07-23 debug shell `config` dump, for cross-check
LIVE = [
    ("vrc", "TRUE"), ("radio", "TRUE"), ("charge_voltage_limit_mv", 4320),
    ("charge_current_ma", 896), ("charging_low_temp_threshold_c", 15),
    ("charge_current_low_temp_ma", 220), ("charging_high_temp_threshold_c", 38),
    ("charge_current_high_temp_ma", 220), ("bq27421_design_capacity", 1100),
    ("bq27421_design_energy", 4180), ("bq27421_terminate_voltage", 3300),
    ("bq27421_taper_rate", 71), ("trigger", "TRUE"), ("trigger_field_min", 400),
    ("trigger_field_max", 700), ("thumbstick", "TRUE"), ("thumbstick_center_x", 2050),
    ("thumbstick_min_x", 1350), ("thumbstick_max_x", 2750), ("thumbstick_center_y", 2050),
    ("thumbstick_min_y", 1350), ("thumbstick_max_y", 2750), ("thumbstick_deadzone_raw", 350),
    ("haptics", "TRUE"), ("fsr", "TRUE"), ("power_on_button_press_ms", 400),
    ("led_driver_current_r", 8), ("led_driver_current_g", 8), ("led_driver_current_b", 8),
    ("led_driver_current_w", 8), ("product_name", "Index Controller"), ("finger_type", 11),
    ("sensor_enable", 66846654), ("sensor_env_on_pin_a", 147456), ("trackpad", 8),
    ("thumbstick_flip_x", 1), ("thumbstick_flip_y", 1), ("fsr_grip_A", -0.255),
    ("fsr_grip_B", 0.92), ("fsr_grip_C", 0.2772), ("fsr_grip_D", 1.253725),
    ("fsr_thumb_A", -0.245), ("fsr_thumb_B", 0.91), ("fsr_thumb_C", 0.269199),
    ("fsr_thumb_D", 1.132344), ("debug", 1),
]

def main():
    data = open(FW, 'rb').read()
    print(f"{'idx':>3} {'name':<32} {'flag':>4} {'addr':>10} {'file_off':>10} {'value_i32':>12} {'value_f32':>14} {'live':>20} match")
    for i in range(N):
        off = TABLE_START + i * ENTRY_SIZE
        flag = data[off]
        addr = struct.unpack_from('<I', data, off + 1)[0]
        raw4 = data[off + 5:off + 9]
        vi = struct.unpack('<i', raw4)[0]
        vf = struct.unpack('<f', raw4)[0]
        name, live = LIVE[i] if i < len(LIVE) else ("?", "?")
        match = ""
        if isinstance(live, (int, float)) and not isinstance(live, bool):
            if abs(vi - live) < 1e-6 if isinstance(live, float) else vi == live:
                match = "OK(int)"
            elif abs(vf - live) < 1e-3:
                match = "OK(float)"
        print(f"{i:>3} {name:<32} 0x{flag:02x} 0x{addr:08x} 0x{off:08x} {vi:>12} {vf:>14.6f} {str(live):>20} {match}")

if __name__ == '__main__':
    main()
