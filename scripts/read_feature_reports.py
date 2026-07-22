#!/usr/bin/env python3
"""Read-only recon: query GET_FEATURE for every known Feature report ID on the
wired Valve Index Controller (and Watchman dongles). This is passive — it asks the
device to report its current state, it cannot write/change anything.
"""
import fcntl
import struct
import os
import sys

# Map of hidraw path -> list of (report_id, byte_len) for Feature reports,
# taken from parse_hid_descriptor.py output.
TARGETS = {
    '/dev/hidraw19': [  # Index Controller wired, interface 0 "IMU"
        (0x01, 2), (0x03, 46), (0x04, 4), (0x07, 4), (0x05, 52), (0x08, 8),
        (0x09, 63), (0x06, 1), (0x0c, 1), (0x0d, 1), (0x13, 63), (0x15, 62),
        (0x10, 2), (0x11, 63), (0x12, 1), (0x16, 1), (0x20, 64), (0x21, 63),
        (0x22, 63), (0x24, 61),
    ],
    '/dev/hidraw20': [],  # Optical interface: no Feature reports in descriptor
    '/dev/hidraw21': [(0x00, 40)],  # Controller interface: no report ID (uses 0)
    '/dev/hidraw14': [  # Watchman Dongle A
        (0x01, 2), (0x02, 33), (0xff, 63), (0x03, 46), (0x05, 52), (0x0b, 3),
        (0x0a, 3), (0x10, 2), (0x11, 63),
    ],
    '/dev/hidraw16': [  # Watchman Dongle B
        (0x01, 2), (0x02, 33), (0xff, 63), (0x03, 46), (0x05, 52), (0x0b, 3),
        (0x0a, 3), (0x10, 2), (0x11, 63),
    ],
}


def HIDIOCGFEATURE(length):
    dir_ = 3  # _IOC_READ | _IOC_WRITE
    type_ = ord('H')
    nr = 0x07
    return (dir_ << 30) | (type_ << 8) | nr | (length << 16)


def get_feature(fd, report_id, byte_len):
    buflen = byte_len + 1
    buf = bytearray(buflen)
    buf[0] = report_id
    ioc = HIDIOCGFEATURE(buflen)
    fcntl.ioctl(fd, ioc, buf)
    return bytes(buf)


def main():
    for path, reports in TARGETS.items():
        if not reports:
            continue
        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        except OSError as e:
            print(f"{path}: OPEN FAILED ({e})")
            continue
        print(f"=== {path} ===")
        for report_id, byte_len in reports:
            try:
                data = get_feature(fd, report_id, byte_len)
                print(f"  GET_FEATURE id=0x{report_id:02x} len={byte_len}: {data.hex()}")
            except OSError as e:
                print(f"  GET_FEATURE id=0x{report_id:02x} len={byte_len}: FAILED errno={e.errno} ({e.strerror})")
        os.close(fd)
        print()


if __name__ == '__main__':
    main()
