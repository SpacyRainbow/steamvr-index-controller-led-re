#!/usr/bin/env python3
"""Sanity check: send a haptic-pulse-style command on the wired Index Controller's
Output report (id=0x01, 63-byte payload on hidraw19 'IMU' interface) using the
command-ID byte documented for the Steam Controller / LighthouseRedox family (0x8F).

This is a SAFE, REVERSIBLE, tactile test (should just cause a brief buzz if the
controller correctly parses it as a haptic command) — used only to confirm whether
Output report 0x01 is in fact a generic command channel analogous to report 255
on the wireless dongle path. Does not require visual LED confirmation.
"""
import os
import sys
import time

PATH = '/dev/hidraw19'
REPORT_ID = 0x01
PAYLOAD_LEN = 63  # from descriptor: Output report 0x01 = 504 bits = 63 bytes


def send(fd, cmd_byte, params=b''):
    buf = bytearray(1 + PAYLOAD_LEN)
    buf[0] = REPORT_ID
    buf[1] = cmd_byte
    buf[2:2 + len(params)] = params
    n = os.write(fd, bytes(buf))
    print(f"  wrote {n} bytes: {bytes(buf).hex()}")
    return n


def main():
    fd = os.open(PATH, os.O_RDWR)
    try:
        print("Test 1: 0x8F (haptic pulse cmd id from hid-steam.c / LighthouseRedox)")
        print("  trying with a plausible duration/amplitude payload after cmd byte")
        # Guess: motor_index(1) + duration_us_lo(1) + duration_us_hi(1) style, several variants
        variants = [
            bytes([0x00, 0x00, 0x00]),          # all zero params
            bytes([0x00, 0xff, 0x00]),          # short duration guess
            bytes([0x01, 0xff, 0xff]),          # different motor index
        ]
        for v in variants:
            send(fd, 0x8f, v)
            time.sleep(0.6)
        print("If you felt/heard NOTHING, that's a valid (negative) result — log it.")
        print("If you felt a buzz, tell me which variant index (1-3) coincided with it.")
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
