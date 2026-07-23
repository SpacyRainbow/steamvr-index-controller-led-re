#!/usr/bin/env python3
"""Tests for the 9-byte packed config-entry struct format documented in
docs/06_firmware_symbols.md section 6.2, using an entirely synthetic
buffer built to match the documented layout -- no real firmware bytes.

This exercises the *decoding logic* independently of
scripts/decode_config_table.py (which is hardcoded to a specific real
firmware file's byte offsets and isn't directly unit-testable without
that file); the point of this test is to pin down the struct format
itself as a regression check, since that format was reverse engineered
from a single real device and has not been independently verified
against a second one (see docs/17_safety.md "Version compatibility
warnings").

Run with: python3 -m unittest tests.test_config_table_format -v
"""
import struct
import unittest


def decode_entry(buf, offset):
    """Decode one 9-byte packed config entry, per docs/06_firmware_symbols.md
    section 6.2:
        offset 0: type/flag byte
        offset 1: uint32 name_ptr (pointer to the entry's own name string)
        offset 5: int32 value (reinterpret as float for some entries)
    """
    type_byte = buf[offset]
    name_ptr = struct.unpack_from('<I', buf, offset + 1)[0]
    value_i32 = struct.unpack_from('<i', buf, offset + 5)[0]
    value_f32 = struct.unpack_from('<f', buf, offset + 5)[0]
    return type_byte, name_ptr, value_i32, value_f32


def build_synthetic_entry(type_byte, name_ptr, value):
    """Build one synthetic 9-byte entry. `value` may be an int or a float;
    floats are packed as IEEE-754 single precision, matching how this
    project found fsr_grip_*/fsr_thumb_* entries encoded in the real
    firmware."""
    buf = bytearray(9)
    buf[0] = type_byte
    struct.pack_into('<I', buf, 1, name_ptr)
    if isinstance(value, float):
        struct.pack_into('<f', buf, 5, value)
    else:
        struct.pack_into('<i', buf, 5, value)
    return bytes(buf)


class TestConfigEntryFormat(unittest.TestCase):
    def test_entry_is_9_bytes(self):
        entry = build_synthetic_entry(0x07, 0x0041e964, 8)
        self.assertEqual(len(entry), 9)

    def test_int32_entry_round_trip(self):
        # mirrors the real led_driver_current_r entry: type 0x07, value 8
        entry = build_synthetic_entry(0x07, 0x0041e964, 8)
        type_byte, name_ptr, value_i32, _ = decode_entry(entry, 0)
        self.assertEqual(type_byte, 0x07)
        self.assertEqual(name_ptr, 0x0041e964)
        self.assertEqual(value_i32, 8)

    def test_boolean_entry_round_trip(self):
        # mirrors the real 'vrc'/'debug' style entries: type 0x01, value 1
        entry = build_synthetic_entry(0x01, 0x00441690, 1)
        type_byte, _, value_i32, _ = decode_entry(entry, 0)
        self.assertEqual(type_byte, 0x01)
        self.assertEqual(value_i32, 1)

    def test_negative_int32_entry_round_trip(self):
        entry = build_synthetic_entry(0x07, 0x00420760, -12345)
        _, _, value_i32, _ = decode_entry(entry, 0)
        self.assertEqual(value_i32, -12345)

    def test_float_entry_round_trip(self):
        # mirrors the real fsr_grip_A entry: -0.255
        entry = build_synthetic_entry(0x07, 0x00420800, -0.255)
        _, _, _, value_f32 = decode_entry(entry, 0)
        self.assertAlmostEqual(value_f32, -0.255, places=5)

    def test_consecutive_entries_at_correct_stride(self):
        """The real config table's four LED-current entries are packed
        back-to-back with no padding (docs/06_firmware_symbols.md section
        6.2) -- confirm decoding at stride-9 offsets recovers each one
        independently, uncorrupted by its neighbors."""
        entries = [
            build_synthetic_entry(0x07, 0x1000, 8),   # r
            build_synthetic_entry(0x07, 0x1010, 16),  # g
            build_synthetic_entry(0x07, 0x1020, 32),  # b
            build_synthetic_entry(0x07, 0x1030, 64),  # w
        ]
        buf = b''.join(entries)
        self.assertEqual(len(buf), 36)

        expected_values = [8, 16, 32, 64]
        for i, expected in enumerate(expected_values):
            with self.subTest(index=i):
                _, _, value_i32, _ = decode_entry(buf, i * 9)
                self.assertEqual(value_i32, expected)

    def test_name_ptr_is_not_confused_with_value(self):
        """Regression guard for the specific hypothesis this project
        initially entertained and disproved (docs/06_firmware_symbols.md
        section 6.2, "The name_ptr field's role"): name_ptr and value are
        genuinely independent fields, not a duplicated value."""
        entry = build_synthetic_entry(0x07, 0xAAAAAAAA, 8)
        _, name_ptr, value_i32, _ = decode_entry(entry, 0)
        self.assertNotEqual(name_ptr, value_i32)
        self.assertEqual(name_ptr, 0xAAAAAAAA)
        self.assertEqual(value_i32, 8)


if __name__ == '__main__':
    unittest.main()
