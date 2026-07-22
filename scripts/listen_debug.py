#!/usr/bin/env python3
"""Passively read the Debug HID interface for a while, printing any
unsolicited log lines the firmware emits (e.g. LED color-change logs),
without sending any command first."""
import os
import select
import sys
import time

PATH = '/dev/hidraw4'
REPORT_ID = 0x76

def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    fd = os.open(PATH, os.O_RDWR | os.O_NONBLOCK)
    buf = bytearray()
    end = time.time() + duration
    print(f"listening for {duration}s...", file=sys.stderr)
    try:
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], max(0, end - time.time()))
            if not r:
                continue
            data = os.read(fd, 128)
            if len(data) >= 2 and data[0] == REPORT_ID:
                length = data[1]
                content = data[2:2 + length]
                buf += content
                text = buf.decode('ascii', errors='replace')
                if '\n' in text or '\r' in text:
                    print(text, end='')
                    buf.clear()
                else:
                    # print partial anyway so we don't miss anything on timeout
                    pass
        if buf:
            print(buf.decode('ascii', errors='replace'))
    finally:
        os.close(fd)

if __name__ == '__main__':
    main()
