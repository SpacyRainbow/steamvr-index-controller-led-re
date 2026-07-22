#!/usr/bin/env python3
"""Dump raw HID report descriptors from all connected Valve devices via hidraw ioctl.

No root required as long as the hidraw device node grants rw to the current user
(confirmed via getfacl on this box for the wired Index Controller nodes).
"""
import fcntl
import struct
import glob
import os
import sys

# from <linux/hidraw.h>
HIDIOCGRDESCSIZE = 0x80044801
HIDIOCGRDESC = 0x90044802
HIDIOCGRAWINFO = 0x80084803
HIDIOCGRAWNAME = 0x80ff4804
HIDIOCGRAWPHYS = 0x80ff4805

HIDRAW_DESC_SIZE = 4096


def get_raw_info(fd):
    buf = bytearray(8)
    fcntl.ioctl(fd, HIDIOCGRAWINFO, buf)
    bustype, vendor, product = struct.unpack('<iHH', buf)
    return bustype, vendor, product


def get_name(fd):
    buf = bytearray(256)
    try:
        fcntl.ioctl(fd, HIDIOCGRAWNAME, buf)
        return buf.split(b'\x00')[0].decode(errors='replace')
    except OSError:
        return '?'


def get_phys(fd):
    buf = bytearray(256)
    try:
        fcntl.ioctl(fd, HIDIOCGRAWPHYS, buf)
        return buf.split(b'\x00')[0].decode(errors='replace')
    except OSError:
        return '?'


def get_report_descriptor(fd):
    size_buf = struct.pack('<i', 0)
    size_buf = bytearray(size_buf)
    fcntl.ioctl(fd, HIDIOCGRDESCSIZE, size_buf)
    (size,) = struct.unpack('<i', size_buf)

    class hidraw_report_descriptor(object):
        pass

    buf = bytearray(4 + HIDRAW_DESC_SIZE)
    struct.pack_into('<i', buf, 0, size)
    fcntl.ioctl(fd, HIDIOCGRDESC, buf)
    data = bytes(buf[4:4 + size])
    return size, data


def main():
    paths = sorted(glob.glob('/dev/hidraw*'))
    for path in paths:
        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        except OSError as e:
            print(f"{path}: OPEN FAILED ({e})")
            continue
        try:
            bustype, vendor, product = get_raw_info(fd)
            if vendor != 0x28de:
                continue
            name = get_name(fd)
            phys = get_phys(fd)
            size, desc = get_report_descriptor(fd)
            print(f"=== {path} ===")
            print(f"  vendor:product = {vendor:04x}:{product:04x}  name='{name}'  phys='{phys}'")
            print(f"  report descriptor size = {size}")
            print(f"  hex: {desc.hex()}")
            print()
        except OSError as e:
            print(f"{path}: ioctl failed ({e})")
        finally:
            os.close(fd)


if __name__ == '__main__':
    main()
