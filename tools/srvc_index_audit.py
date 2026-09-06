# -*- coding: utf-8 -*-
"""Gate + fix for SRVC.BIN cell-index corruption (v0.9.56, Maaie "No Crew").

Every SRVC block is [header][cell index: 8-byte (u16 clip, u16 sec, u16 off, 0)]
[string pool]. The game finds the pool at a HEADER-derived constant (base+K),
and reads each caption at pool+off.

srvc.parse mis-parses most blocks: it finds 1 cell and tiles the real index as
NUL-separated pseudo-strings. Two consequences that shipped:

  1. STRAY CAPTIONS IN THE INDEX. srvc_apply assigns captions by string slot,
     so an English caption can be written into a pseudo-slot INSIDE the index.
     The index grows, the pool moves, the header constant does not: every
     caption of that block is read N bytes early. Block 234 (+19 B) is why
     Maaie's caption came back empty and her plate drew "No Crew"; block 151
     (+48 B) was the same.
  2. UNREPOINTED CELLS. `--free` repoints cells through a detector that is
     blind on some blocks; those kept JAPANESE offsets over a shorter ENGLISH
     pool, so the game read past the pool end -> blank captions (25 blocks,
     1,489 cells).

Invariant checked here, per block, against the JAPANESE disc: the bytes before
the pool must equal the JP block except <=2-byte offset fields, and every cell
offset must land on a string start. Fix: delete stray bytes (re-added as zero
padding at the block end, so block size and SEG never change) and remap bad
cells by string ORDER (srvc.build preserves order and count).

Usage:
    srvc_index_audit.py <iso> --against iso/srwz.bin          # gate: exit 1 on any problem
    srvc_index_audit.py <iso> --against iso/srwz.bin --fix    # dry run of the fix
    srvc_index_audit.py <iso> --against iso/srwz.bin --fix --write   # in place, same size
Run the gate before every chdman, together with verify_pointers.py.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srvc
from srvclib import getfile

SECTOR = 2048


def locate(iso_path, name):
    """(lba, size) of /BTL/<name> from the directory record."""
    head = open(iso_path, "rb").read(4 * 1024 * 1024)
    rec = head.find(name.encode() + b";1", 0x80000) - 33
    return (struct.unpack_from("<I", head, rec + 2)[0],
            struct.unpack_from("<I", head, rec + 10)[0])


def strings_from(raw, P, n=8):
    out, p = [], P
    for _ in range(n):
        e = raw.find(b"\x00", p)
        if e < 0:
            break
        out.append(raw[p:e])
        p = e + 1
    return out


def texty_jp(s):
    if len(s) < 2:
        return False
    try:
        t = s.decode("cp932")
    except UnicodeDecodeError:
        return False
    return all(ord(c) >= 0x20 for c in t)


def jp_pool(raw):
    """pool start of a JAPANESE block: first NUL-preceded SJIS line followed by text."""
    for i in range(16, len(raw) - 2):
        if raw[i - 1] == 0 and raw[i] >= 0x81:
            ss = strings_from(raw, i, 8)
            if (ss and len(ss[0]) >= 4 and texty_jp(ss[0])
                    and sum(texty_jp(s) for s in ss) >= max(1, int(len(ss) * 0.75))):
                return i
    return None


def is_caption(seg):
    if len(seg) < 4:
        return False
    if seg[0] == 0x22:
        return (sum(0x20 <= c < 0x7F for c in seg) >= len(seg) - 4
                and sum(chr(c).isalpha() for c in seg) >= 2)
    if seg[:2] == b"\x81\x75":
        return texty_jp(seg)
    return False


def diff_runs(x, a, n):
    runs, i = [], 0
    while i < n:
        if x[i] != a[i]:
            j = i
            while j < n and x[j] != a[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def cells(raw, P):
    out = []
    for k in range(1, (P - 16) // 8 + 1):
        q = P - 8 * k
        clip, sec, off, z = struct.unpack_from("<HHHH", raw, q)
        if z != 0 or clip == 0:
            break
        out.append((q, off))
    return out


def bad(raw, P, off):
    return P + off >= len(raw) or (off > 0 and raw[P + off - 1] != 0) or raw[P + off] == 0


def pool_strings(raw, P):
    out, p = [], P
    while p < len(raw):
        e = raw.find(b"\x00", p)
        if e < 0 or (e == p and not any(raw[p:])):
            break
        out.append((p - P, raw[p:e]))
        p = e + 1
    return out


def fix_block(a, b):
    """Returns (bytes, report). Never changes len(b)."""
    rep = {"strays": [], "remapped": 0, "bad": 0, "note": ""}
    P = jp_pool(a)
    if P is None:
        rep["note"] = "" if a == b else "no pool, differs from JP"
        return b, rep
    X = bytearray(b)
    # 1. strays in the index
    for _ in range(64):
        runs = [r for r in diff_runs(X, a, min(P, len(X))) if r[1] - r[0] > 2]
        if not runs:
            break
        d = runs[0][0]
        s0 = X.rfind(b"\x00", 0, d) + 1
        e0 = X.find(b"\x00", d)
        if e0 > 0 and is_caption(bytes(X[s0:e0])) and bytes(X[s0:e0]) != a[s0:e0]:
            rep["strays"].append((s0, bytes(X[s0:e0])))
            del X[s0:e0]
            continue
        rep["note"] = "unresolved diff at 0x%X" % d
        break
    X += b"\x00" * (len(b) - len(X))
    # 2. cell offsets (only where our cell reading fits the JP block)
    jc = cells(a, P)
    if jc and not any(bad(a, P, o) for _, o in jc):
        badc = [(q, o) for q, o in cells(X, P) if bad(X, P, o)]
        if badc:
            jp_s = pool_strings(a, P)
            ou_s = pool_strings(X, P)
            # order mapping is trusted only over the leading run of captions
            m = 0
            for k in range(min(len(jp_s), len(ou_s))):
                if not (jp_s[k][1].startswith(b"\x81\x75")
                        and (ou_s[k][1].startswith(b'"') or ou_s[k][1].startswith(b"\x81\x75"))):
                    break
                m += 1
            jidx = {o: k for k, (o, _) in enumerate(jp_s[:m])}
            for q, o in badc:
                jo = struct.unpack_from("<H", a, q + 4)[0]
                if jo in jidx:
                    struct.pack_into("<H", X, q + 4, ou_s[jidx[jo]][0])
                    rep["remapped"] += 1
            rep["bad"] = sum(1 for q, o in cells(X, P) if bad(X, P, o))
    return bytes(X), rep


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(args) < 1 or "--against" not in sys.argv:
        raise SystemExit(__doc__)
    iso = args[0]
    ref = sys.argv[sys.argv.index("--against") + 1]
    fix = "--fix" in sys.argv
    write = "--write" in sys.argv
    jd = getfile(ref, "/BTL/SRVC.BIN")
    js = srvc.read_seg(getfile(ref, "/BTL/SRVC.SEG"))
    lba, size = locate(iso, "SRVC.BIN")
    with open(iso, "rb") as f:
        f.seek(lba * SECTOR)
        od = f.read(size)
    os_ = srvc.read_seg(getfile(iso, "/BTL/SRVC.SEG"))
    out = bytearray()
    problems = 0
    for bi in range(len(js) - 1):
        a = jd[js[bi]:js[bi + 1]]
        b = od[os_[bi]:os_[bi + 1]]
        if a[:2] != b"\x00\x4F" or len(a) < 16 or a == b:
            out += b
            continue
        X, rep = fix_block(a, b)
        out += X if fix else b
        if rep["strays"] or rep["remapped"] or rep["bad"] or rep["note"]:
            problems += 1
            print("block %d: %d stray(s), %d cell(s) remapped, %d still bad %s"
                  % (bi, len(rep["strays"]), rep["remapped"], rep["bad"], rep["note"]))
            for p, t in rep["strays"]:
                print("     stray at raw+0x%X: %r" % (p, t))
    assert len(out) == len(od)
    if problems == 0:
        print("SRVC index: OK (%d blocks match %s before the pool, all cell offsets resolve)"
              % (len(js) - 1, ref))
        return 0
    print("SRVC index: %d block(s) with problems" % problems)
    if fix and write:
        with open(iso, "r+b") as f:
            f.seek(lba * SECTOR)
            f.write(bytes(out))
            f.flush()
            f.seek(lba * SECTOR)
            ok = f.read(size) == bytes(out)
        print("written in place at LBA %d (%d B, same size); read-back %s" % (lba, size, ok))
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
