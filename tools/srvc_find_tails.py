# -*- coding: utf-8 -*-
"""Find head-truncated battle-voice tails in the SRVC copy the game uses."""
import struct
import sys

PATH = b"\x5cBTL\x5cSRVC.BIN;1"

iso = open(r"E:\Projects\SRW Z\_work\iso\srwz_fix3.bin", "rb")
head = iso.read(8 * 1024 * 1024)
p = head.find(PATH)
print("ftable at", hex(p))
lba, secs = struct.unpack_from("<II", head, p + 0x28)
print("game uses LBA", lba, "sectors", secs)
iso.seek(lba * 2048)
d = iso.read(secs * 2048)
iso.close()
open(r"E:\Projects\SRW Z\_work\analysis\_srvc_cur.bin", "wb").write(d)

for tail in (b"you now!", b"ce!"):
    i = 0
    hits = []
    while True:
        j = d.find(tail, i)
        if j < 0:
            break
        hits.append(j)
        i = j + 1
    print(tail, len(hits))
    for h in hits[:12]:
        seg = d[max(0, h - 70):h + 16]
        parts = seg.split(b"\x00")
        for pt in parts:
            if tail in pt:
                sys.stdout.buffer.write(
                    ("  @%#x: %r\n" % (h, pt.decode("cp932", "replace")))
                    .encode("utf-8"))
                break
