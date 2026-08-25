# -*- coding: utf-8 -*-
"""Monitor blit-entry logger: dedupe (ra, x) pairs, record string ptr (12 min)."""
import sys
import time
sys.path.insert(0, r'E:\Projects\SRW Z\_work\tools')
from pine_read import Pine

p = None
seen = {}
out = open(r'E:\Projects\SRW Z\_work\analysis\_blit_callers.log', 'w')
t0 = time.time()
while time.time() - t0 < 720:
    try:
        if p is None:
            p = Pine()
        p.write32(0x78C5F8, 0)
        time.sleep(0.35)
        cnt = p.read32_batch([0x78C5F8])[0]
        n = min(cnt, 24)
        if n:
            addrs = []
            for i in range(n):
                addrs += [0x78C600 + i * 16, 0x78C600 + i * 16 + 4,
                          0x78C600 + i * 16 + 8]
            words = p.read32_batch(addrs)
            for i in range(n):
                ra = words[i * 3]
                a0 = words[i * 3 + 1]
                w2 = words[i * 3 + 2]
                x = w2 & 0xffff
                if x >= 0x8000:
                    x -= 0x10000
                k = (ra, x)
                if k not in seen:
                    seen[k] = a0
                    out.write('ra=%#x x=%d str=%#x t=%.1f\n'
                              % (ra, x, a0, time.time() - t0))
                    out.flush()
    except Exception:
        p = None
        time.sleep(2)
out.write('# done\n')
out.close()
print('done', len(seen))
