#!/usr/bin/env python3
"""Tests for the .fw container footer format documented in
docs/05_firmware_layout.md -- specifically the self-referential final_crc
field, which is the piece of this project's own patch-building logic most
likely to silently break if ever refactored (patch_led_black.py and
patch_led_firmware.py both depend on getting this exact right, and a
mistake here produces a file that Valve's own update tool rejects before
ever touching real hardware -- see docs/13_experiments.md Experiment 5 for
what that looked like the first time this project got it wrong).

These tests build entirely synthetic footer bytes -- no real Valve
firmware content is used or required.

Run with: python3 -m unittest tests.test_footer_format -v
"""
import struct
import sys
import unittest
import zlib

MAGIC = 0xC0DEA1DE


def build_synthetic_footer(target=2, comp_size=12345, app_ver=0xDEADBEEF,
                            timestamp=b"2020-01-01 00:00:00\x00",
                            git_hash=b"abcdef01\x00"):
    """Build a syntactically valid 56-byte footer with placeholder content,
    matching the documented layout in docs/05_firmware_layout.md section 5.1,
    with a correctly-computed crc2 and final_crc for the given fields."""
    assert len(timestamp) == 20
    assert len(git_hash) == 9
    footer = bytearray(56)
    struct.pack_into('<I', footer, 0, MAGIC)
    struct.pack_into('<I', footer, 4, target)
    struct.pack_into('<I', footer, 8, comp_size)
    # crc2 [12:16] is normally CRC-32 of the compressed stream; for these
    # synthetic tests we just need *a* plausible value, since these tests
    # focus on the final_crc self-check, not crc2's relationship to real
    # compressed data (that relationship is exercised end-to-end by the
    # patch scripts themselves against real firmware, not here).
    struct.pack_into('<I', footer, 12, 0x12345678)
    struct.pack_into('<I', footer, 16, app_ver)
    footer[20:40] = timestamp
    footer[40:49] = git_hash
    footer[49:52] = b'\x00\x00\x00'
    # final_crc [52:56]: the documented self-referential formula
    footer[52:56] = b'\x00\x00\x00\x00'
    final_crc = zlib.crc32(bytes(footer)) & 0xffffffff
    struct.pack_into('<I', footer, 52, final_crc)
    return bytes(footer)


def verify_final_crc(footer):
    """Re-implementation of the verification logic used by
    scripts/patch_led_black.py and patch_led_firmware.py, kept
    intentionally separate from those scripts so a shared bug wouldn't
    hide itself from this test."""
    assert len(footer) == 56
    zeroed = bytearray(footer)
    zeroed[52:56] = b'\x00\x00\x00\x00'
    computed = zlib.crc32(bytes(zeroed)) & 0xffffffff
    stored = struct.unpack_from('<I', footer, 52)[0]
    return computed == stored


class TestFooterMagicAndLayout(unittest.TestCase):
    def test_footer_is_56_bytes(self):
        footer = build_synthetic_footer()
        self.assertEqual(len(footer), 56)

    def test_magic_field(self):
        footer = build_synthetic_footer()
        magic = struct.unpack_from('<I', footer, 0)[0]
        self.assertEqual(magic, MAGIC)

    def test_field_offsets_round_trip(self):
        footer = build_synthetic_footer(target=3, comp_size=99999, app_ver=0x1234)
        target, comp_size = struct.unpack_from('<II', footer, 4)
        app_ver = struct.unpack_from('<I', footer, 16)[0]
        self.assertEqual(target, 3)
        self.assertEqual(comp_size, 99999)
        self.assertEqual(app_ver, 0x1234)


class TestSelfReferentialFinalCrc(unittest.TestCase):
    """This is the field that caused a real, live rejection during the
    project's research (docs/13_experiments.md Experiment 5) when it was
    left stale after a patch changed comp_size/crc2 but not this field."""

    def test_synthetic_footer_passes_its_own_check(self):
        footer = build_synthetic_footer()
        self.assertTrue(verify_final_crc(footer))

    def test_stale_final_crc_is_detected(self):
        """Directly reproduces the historical bug: build a footer, then
        change comp_size (simulating a patch that recompressed content)
        WITHOUT recomputing final_crc, and confirm the verification
        correctly flags it as invalid -- this is exactly the safety net
        docs/15_firmware_patching.md says every patch script must have."""
        footer = bytearray(build_synthetic_footer(comp_size=1000))
        # simulate a patch that changed comp_size but "forgot" to redo
        # the final_crc step
        struct.pack_into('<I', footer, 8, 2000)
        self.assertFalse(
            verify_final_crc(bytes(footer)),
            "a stale final_crc after changing footer content must be detected as invalid"
        )

    def test_correctly_rebuilt_final_crc_passes(self):
        """The correct procedure (docs/15_firmware_patching.md section 15.1
        step 5): after changing any footer field, zero final_crc, recompute
        over the whole footer, write it back. Confirm that procedure
        produces a footer that passes."""
        footer = bytearray(build_synthetic_footer(comp_size=1000))
        struct.pack_into('<I', footer, 8, 2000)  # simulate the same content change
        footer[52:56] = b'\x00\x00\x00\x00'
        new_crc = zlib.crc32(bytes(footer)) & 0xffffffff
        struct.pack_into('<I', footer, 52, new_crc)
        self.assertTrue(verify_final_crc(bytes(footer)))

    def test_single_bit_flip_anywhere_in_footer_is_detected(self):
        """A basic integrity sanity check: flipping any single bit in the
        footer (other than by re-running the real rebuild procedure)
        should change final_crc's expected value and be caught."""
        footer = bytearray(build_synthetic_footer())
        # flip one bit in the timestamp field, elsewhere in the footer
        footer[25] ^= 0x01
        self.assertFalse(verify_final_crc(bytes(footer)))


if __name__ == '__main__':
    unittest.main()
