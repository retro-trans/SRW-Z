# -*- coding: utf-8 -*-
"""Find apply_stage rows whose [offset, offset+budget) region overwrites LIVE
(non-zero, post-terminator) bytes in the original decompressed record. Such a
row's zero-fill/English write clobbers adjacent event/deployment script data.
Also reports rows actually translated (in recNNN_en.py) vs latent."""
import glob, json, os, importlib.util

WORK = r"E:\Projects\SRW Z\_work"

def load_T(n):
    py = os.path.join(WORK, "tools", "rec%03d_en.py" % n)
    if not os.path.exists(py):
        return {}
    spec = importlib.util.spec_from_file_location("r%d" % n, py)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return dict(m.T)

flagged = []
for js in sorted(glob.glob(os.path.join(WORK, "analysis", "rec*_script.json"))):
    base = os.path.basename(js)
    n = int(base[3:6])
    dec = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
    if not os.path.exists(dec):
        continue
    orig = open(dec, "rb").read()
    rows = json.load(open(js, encoding="utf-8"))
    T = load_T(n)
    for idx, r in enumerate(rows):
        off = r["offset"]; bud = r.get("budget", r["nbytes"])
        region = orig[off:off+bud]
        # first NUL terminator of the text field
        z = region.find(b"\x00")
        if z < 0:
            # no terminator inside budget: text fills whole budget (tight field) - ok-ish
            continue
        tail = region[z:]  # should be all zero padding
        nz = len(tail) - tail.count(b"\x00")
        if nz > 0:
            # bytes after the terminator are NOT all zero -> budget spans live data
            applied = idx in T
            # locate first non-zero in tail for context
            firstnz = next(k for k in range(len(tail)) if tail[k] != 0)
            flagged.append((n, idx, off, bud, z, nz, applied,
                            bytes(region[z+firstnz:z+firstnz+16])))

flagged.sort(key=lambda x: (-x[6], -x[5]))  # applied first, then most live bytes
print("rows whose budget region overwrites post-terminator LIVE bytes: %d" % len(flagged))
print("  (applied=True means the English translation actually writes over it NOW)\n")
print("%-7s %-4s %-8s %-6s %-5s %-6s %-8s %s" %
      ("rec","row","offset","budget","txt","liveB","applied","first-live-bytes"))
for n, idx, off, bud, z, nz, applied, ctx in flagged[:60]:
    print("rec%03d  %-4d 0x%05X %-6d %-5d %-6d %-8s %r" %
          (n, idx, off, bud, z, nz, applied, ctx))
napp = sum(1 for f in flagged if f[6])
print("\nTOTAL flagged: %d | actually-applied (live corruption NOW): %d" % (len(flagged), napp))
