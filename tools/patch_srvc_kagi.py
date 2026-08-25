# -*- coding: utf-8 -*-
"""Battle voice captions: ASCII "quotes" -> kagi brackets 「」.

Matches the dialogue-box style (STAGE text has used 「」 since v2.00).
The JP caption data used 「(0x8175) 」(0x8176) natively, so the renderer
is proven safe with them. Cost: +1 byte per bracket; the space padding
absorbs it in most fields, overflow fields are skipped and counted.

Rules per pure-English field (same classifier as patch_srvc_polish):
  * field with >= 2 ASCII '"': first -> 「, last -> 」
  * field with exactly 1 '"': leading '"' -> 「, trailing '"' -> 」
    (page-split halves keep their single bracket)
Usage: patch_srvc_kagi.py <iso>   (idempotent)
"""
import sys

SRVC_LBA, SECTOR = 1826000, 2048
SRVC_SECTORS = 1624
OPEN, CLOSE = b"\x81\x75", b"\x81\x76"
FW = (b"\x81\x44", b"\x81\x63", b"\x81\x43", OPEN, CLOSE)


def convert(txt):
    body = txt.rstrip(b" ")
    pad = len(txt) - len(body)
    i = 0
    ascii_seen = False
    while i < len(body):
        if body[i:i + 2] in FW:
            i += 2
            continue
        b = body[i]
        if 0x20 <= b < 0x7F:
            if b != 0x20:
                ascii_seen = True
            i += 1
            continue
        return None
    if not ascii_seen or b'"' not in body:
        return None
    qpos = [k for k in range(len(body)) if body[k:k+1] == b'"']
    # never split a fullwidth pair: quotes are ASCII so positions are safe
    new = bytearray(body)
    if len(qpos) >= 2:
        first, last = qpos[0], qpos[-1]
        new = new[:first] + OPEN + new[first+1:last] + CLOSE + new[last+1:]
    else:
        q = qpos[0]
        if q == 0:
            new = OPEN + new[1:]
        elif q == len(body) - 1:
            new = new[:q] + CLOSE
        else:
            return None                    # lone mid-line quote: leave it
    new = bytes(new)
    if len(new) > len(body) + pad:
        return "OVER"
    return new + b" " * (len(body) + pad - len(new))


def main():
    iso_path = sys.argv[1]
    with open(iso_path, "r+b") as iso:
        iso.seek(SRVC_LBA * SECTOR)
        d = bytearray(iso.read(SRVC_SECTORS * SECTOR))
        n = n_over = 0
        i = 0
        while i < len(d):
            if d[i] == 0:
                i += 1
                continue
            end = d.find(b"\x00", i)
            if end < 0:
                break
            new = convert(bytes(d[i:end]))
            if new == "OVER":
                n_over += 1
            elif new is not None:
                assert len(new) == end - i
                d[i:end] = new
                n += 1
            i = end + 1
        iso.seek(SRVC_LBA * SECTOR)
        iso.write(bytes(d))
    print("kagi-converted %d caption fields, %d skipped (no room)" % (n, n_over))


if __name__ == "__main__":
    main()
