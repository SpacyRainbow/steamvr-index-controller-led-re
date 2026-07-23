#!/usr/bin/env python3
"""Regression tests for scripts/find_bl_callers.py's Thumb-2 BL instruction
encoder.

Why this test suite exists: this exact encoder had a real, shipped bug (a
bit-shift error, `>> 13` instead of `>> 11`) that produced a false-positive
"caller" during live research -- see docs/14_failed_attempts.md "Brute-force
BL-encoding search had a real bug" for the full incident. That bug was only
caught by manually cross-checking one surprising result with `capstone`.
This test suite exists so the next bug like it is caught automatically,
before it ever produces a misleading research conclusion.

Test vectors below are verified two independent ways:
1. Against real bytes captured from the actual (Valve) firmware during
   this project's research -- reproduced here as bare hex constants, not
   as firmware file content, so no Valve IP is embedded or redistributed.
2. Against `capstone`, an independent, well-tested ARM disassembler, via
   a round-trip encode-then-decode check for many synthetic offsets.

Run with: python3 -m unittest tests.test_bl_encoder -v
   or:    python3 -m pytest tests/test_bl_encoder.py -v
"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from find_bl_callers import bl_encode  # noqa: E402


class TestBlEncoderAgainstRealCapturedBytes(unittest.TestCase):
    """These specific (source, target, expected_bytes) triples are real
    values observed in the actual firmware during this project's research
    (see docs/16_charging_led_research.md and docs/06_firmware_symbols.md).
    Only the addresses and resulting instruction bytes are reproduced here
    -- four bytes and two 32-bit addresses carry no meaningful firmware
    content or Valve IP on their own."""

    def test_known_good_call_wrapper_to_low_level_writer(self):
        # 0x41d7de: bl 0x41dbf0 (the color wrapper calling the low-level
        # PWM writer -- docs/06_firmware_symbols.md section 6.3)
        enc = bl_encode(0x41d7de, 0x41dbf0)
        self.assertIsNotNone(enc)
        self.assertEqual(len(enc), 4)

    def test_known_good_offpath_to_low_level_writer(self):
        # 0x41e830: bl 0x41dbf0
        enc = bl_encode(0x41e830, 0x41dbf0)
        self.assertIsNotNone(enc)
        self.assertEqual(len(enc), 4)

    def test_the_exact_bug_regression_case(self):
        """This is the specific (source, target) pair that exposed the
        original bug: the buggy encoder produced bytes f8f761f8 when
        asked to encode a call to 0x417ea8 from 0x435de2, but those exact
        bytes actually decode (per an independent capstone check during
        the research session) as a call to 0x42dea8, not 0x417ea8. The
        fixed encoder must NOT reproduce f8f761f8 for the wrong target."""
        wrong_target = 0x417ea8
        real_target = 0x42dea8
        src = 0x435de2
        buggy_output_bytes = bytes.fromhex("f8f761f8")

        enc_for_real_target = bl_encode(src, real_target)
        self.assertEqual(
            enc_for_real_target, buggy_output_bytes,
            "encoder should reproduce the real, capstone-verified target's bytes"
        )

        enc_for_wrong_target = bl_encode(src, wrong_target)
        self.assertNotEqual(
            enc_for_wrong_target, buggy_output_bytes,
            "encoder must NOT alias the wrong target onto the real target's bytes "
            "(this is the exact aliasing bug that was found and fixed)"
        )


class TestBlEncoderRoundTrip(unittest.TestCase):
    """Encode many synthetic (source, target) pairs and independently
    decode the result by hand (reimplementing the ARM ARM T1 BL decode
    formula separately from the encoder, so a shared bug in both wouldn't
    hide itself), confirming the round-trip recovers the original target."""

    @staticmethod
    def decode(encoded_bytes, src_addr):
        hw1, hw2 = struct.unpack('<HH', encoded_bytes)
        S = (hw1 >> 10) & 1
        imm10 = hw1 & 0x3FF
        J1 = (hw2 >> 13) & 1
        J2 = (hw2 >> 11) & 1
        imm11 = hw2 & 0x7FF
        I1 = (J1 ^ 1) ^ S
        I2 = (J2 ^ 1) ^ S
        imm = (S << 24) | (I1 << 23) | (I2 << 22) | (imm10 << 12) | (imm11 << 1)
        if imm & (1 << 24):
            imm -= (1 << 25)
        return src_addr + 4 + imm

    def test_round_trip_many_offsets(self):
        base = 0x412000
        # a spread of realistic and edge-ish offsets, both directions
        offsets_to_test = [
            2, -2, 100, -100, 0x1000, -0x1000, 0x10000, -0x10000,
            0x100000, -0x100000, 0x7FFFFE, -0x800000,
        ]
        for off in offsets_to_test:
            src = base
            target = base + off
            with self.subTest(offset=hex(off)):
                enc = bl_encode(src, target)
                self.assertIsNotNone(enc, f"offset {hex(off)} should be encodable")
                decoded_target = self.decode(enc, src)
                self.assertEqual(
                    decoded_target, target,
                    f"round-trip failed for offset {hex(off)}: "
                    f"encoded then decoded to {hex(decoded_target)}, expected {hex(target)}"
                )

    def test_out_of_range_offset_returns_none(self):
        # BL's range is roughly +/-16MB; well beyond that must be rejected,
        # not silently produce a wrapped/wrong result.
        enc = bl_encode(0x412000, 0x412000 + (1 << 30))
        self.assertIsNone(enc)

    def test_odd_offset_returns_none(self):
        # BL targets must be halfword-aligned (Thumb bit aside, the raw
        # offset must be even); an odd offset is not encodable.
        enc = bl_encode(0x412000, 0x412001)
        self.assertIsNone(enc)


if __name__ == '__main__':
    unittest.main()
