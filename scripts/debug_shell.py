#!/usr/bin/env python3
"""Reusable debug-shell client for the Index Controller's firmware CLI, reachable
over the 'Debug' HID interface (report id 0x76, framing: [report_id][len][ascii]).
"""
import os
import select
import sys
import time

PATH = '/dev/hidraw4'
REPORT_ID = 0x76
PAYLOAD_LEN = 63


def send_line(fd, text):
    line = (text + '\n').encode('ascii')
    assert len(line) <= PAYLOAD_LEN - 1
    buf = bytearray(1 + PAYLOAD_LEN)
    buf[0] = REPORT_ID
    buf[1] = len(line)
    buf[2:2 + len(line)] = line
    os.write(fd, bytes(buf))


def read_response(fd, idle_timeout=1.0, overall_timeout=5.0):
    out = bytearray()
    end = time.time() + overall_timeout
    last_data = time.time()
    while time.time() < end:
        remaining_idle = idle_timeout - (time.time() - last_data)
        if remaining_idle <= 0:
            break
        r, _, _ = select.select([fd], [], [], remaining_idle)
        if not r:
            break
        data = os.read(fd, 128)
        last_data = time.time()
        if len(data) >= 2 and data[0] == REPORT_ID:
            length = data[1]
            out += data[2:2 + length]
    return bytes(out)


def run(cmd):
    fd = os.open(PATH, os.O_RDWR | os.O_NONBLOCK)
    try:
        send_line(fd, cmd)
        resp = read_response(fd)
        return resp.decode('ascii', errors='replace')
    finally:
        os.close(fd)


if __name__ == '__main__':
    cmd = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'help'
    print(f">>> {cmd}")
    print(run(cmd))
