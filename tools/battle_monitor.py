# -*- coding: utf-8 -*-
"""Monitor set_text_pos draw positions during a battle scene (10 min)."""
import sys
import time
sys.path.insert(0, r'E:\Projects\SRW Z\_work\tools')

STUB = [0x3C010078, 0x3421BCF8, 0x8C2A0000, 0x2D4B0040, 0x11600008, 0,
        0x000A58C0, 0x01615821, 0xAD7F0008, 0xA564000C, 0xA565000E,
        0x254A0001, 0xAC2A0000, 0x3C010047, 0xA424E340, 0xA425E342,
        0x03E00008, 0]

p = None
seen = set()
out = open(r'E:\Projects\SRW Z\_work\analysis\_battle_pos.log', 'w')
t0 = time.time()
while time.time() - t0 < 600:
    try:
        if p is None:
            from pine_read import Pine
            p = Pine()
            if p.read32_batch([0x139e20])[0] != 0x081E2F00:
                for i, w in enumerate(STUB):
                    p.write32(0x78BC00 + i * 4, w)
                p.write32(0x78BCF8, 0)
                p.write32(0x139e20, 0x081E2F00)
                p.write32(0x139e24, 0)
                out.write('# logger installed t=%.1f\n' % (time.time() - t0))
                out.flush()
        p.write32(0x78BCF8, 0)
        time.sleep(0.4)
        cnt = p.read32_batch([0x78BCF8])[0]
        n = min(cnt, 64)
        if n:
            addrs = []
            for i in range(n):
                addrs += [0x78BD00 + i * 8, 0x78BD00 + i * 8 + 4]
            words = p.read32_batch(addrs)
            for i in range(n):
                ra = words[i * 2]
                w1 = words[i * 2 + 1]
                x = w1 & 0xffff
                y = (w1 >> 16) & 0xffff
                if x >= 0x8000:
                    x -= 0x10000
                if y >= 0x8000:
                    y -= 0x10000
                k = (ra, x, y)
                if k not in seen:
                    seen.add(k)
                    out.write('ra=%#x x=%d y=%d t=%.1f\n'
                              % (ra, x, y, time.time() - t0))
                    out.flush()
    except Exception:
        p = None
        time.sleep(2)
out.write('# done, %d unique\n' % len(seen))
out.close()
print('monitor done,', len(seen), 'unique')
