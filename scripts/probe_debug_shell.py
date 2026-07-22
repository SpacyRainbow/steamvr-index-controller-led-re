#!/usr/bin/env python3
"""Send a benign ASCII command to the firmware's debug shell (confirmed via firmware
strings: 'Commands are called in the form: "cmd <param1> <param2> ..."', hosted on
udi_hid_debug.c / the 'Debug' HID interface, report id 0x76 in/out, 63-byte payload).

Starts with 'help' — read-only, purely informational, cannot alter device state.
"""
import os
import select
import sys
import time

PATH = '/dev/hidraw11'  # Debug interface (input3)
REPORT_ID = 0x76
PAYLOAD_LEN = 63


def send_line(fd, text):
    line = (text + '\n').encode('ascii')
    buf = bytearray(1 + PAYLOAD_LEN)
    buf[0] = REPORT_ID
    buf[1] = len(line)
    buf[2:2 + len(line)] = line
    n = os.write(fd, bytes(buf))
    print(f"  sent {n} bytes: {bytes(buf).hex()}")
    print(f"  as text: {line!r}")


def drain(fd, timeout=2.0):
    end = time.time() + timeout
    got_any = False
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], max(0, end - time.time()))
        if not r:
            break
        data = os.read(fd, 128)
        got_any = True
        print(f"  RECV {len(data)} bytes: {data.hex()}")
        try:
            length = data[1]
            content = data[2:2 + length]
            print(f"    len={length} content: {content.decode('ascii', errors='replace')!r}")
        except Exception:
            pass
    if not got_any:
        print("  (no response)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    fd = os.open(PATH, os.O_RDWR | os.O_NONBLOCK)
    try:
        print(f"=== sending '{cmd}' ===")
        send_line(fd, cmd)
        drain(fd)
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
