#!/usr/bin/env python3
"""Test SET_FEATURE on the small (1-byte) Feature report candidates identified on
the wired Index Controller's 'IMU' interface (hidraw19): 0x06, 0x0c, 0x0d, 0x12, 0x16.

These are the LED-control candidates: single-byte Feature slots, GET_FEATURE on them
returned EPIPE (write-only), which matches what you'd expect from a simple on/off or
mode-select command. This script sets each to 0x01, pauses for visual observation,
then sets back to 0x00, pausing again. It logs the raw ioctl success/failure for
each write — it CANNOT see the LED itself, that requires the human operator watching
the controller in real time.
"""
import fcntl
import os
import time

PATH = '/dev/hidraw19'
CANDIDATES = [0x06, 0x0c, 0x0d, 0x12, 0x16]
PAUSE = 2.5


def HIDIOCSFEATURE(length):
    dir_ = 3  # _IOC_READ | _IOC_WRITE
    type_ = ord('H')
    nr = 0x06
    return (dir_ << 30) | (type_ << 8) | nr | (length << 16)


def set_feature(fd, report_id, value_byte):
    buf = bytearray([report_id, value_byte])
    ioc = HIDIOCSFEATURE(len(buf))
    fcntl.ioctl(fd, ioc, buf)


def main():
    fd = os.open(PATH, os.O_RDWR)
    try:
        for rid in CANDIDATES:
            print(f"=== report 0x{rid:02x}: SET to 0x01 ===")
            try:
                set_feature(fd, rid, 0x01)
                print("  ioctl OK. WATCH THE CONTROLLER LED NOW.")
            except OSError as e:
                print(f"  ioctl FAILED errno={e.errno} ({e.strerror})")
                continue
            time.sleep(PAUSE)
            print(f"=== report 0x{rid:02x}: SET back to 0x00 ===")
            try:
                set_feature(fd, rid, 0x00)
                print("  ioctl OK (reverted).")
            except OSError as e:
                print(f"  ioctl FAILED errno={e.errno} ({e.strerror})")
            time.sleep(1.0)
            print()
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
