# -*- coding: utf-8 -*-
"""Shrink record N's dialogue just enough to fit its STAGE compression slot,
using safe meaning-preserving contractions/filler removal. Rewrites recNNN_en.py.
Usage: tighten_slot.py <N> [<N> ...]"""
import sys, os, json, importlib.util as u, contextlib, io
import apply_stage as A
import banlz

SUBS = [("  ", " "), ("...", ".."), (" I will ", " I'll "), (" you will ", " you'll "),
        (" cannot ", " can't "), ("cannot", "can't"), (" it is ", " it's "),
        (" that is ", " that's "), (" I am ", " I'm "), (" you are ", " you're "),
        (" we are ", " we're "), (" they are ", " they're "), (" do not ", " don't "),
        (" is not ", " isn't "), (" will not ", " won't "), (" I have ", " I've "),
        (" you have ", " you've "), (" would ", " 'd "), (" really ", " "), (" just ", " "),
        (" very ", " "), (" even ", " "), (" only ", " "), (" of course", ""),
        (" right now", " now"), (" as well", ""), (" going to ", " gonna "),
        (" want to ", " wanna "), (" them", " 'em"), (" because ", " since ")]


def bl(s): return len(s.encode('cp932', 'replace'))


def blob_size(n, T):
    dec = os.path.join(A.WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
    js = os.path.join(A.WORK, "analysis", "rec%03d_script.json" % n)
    orig = bytearray(open(dec, "rb").read())
    rows = json.load(open(js, encoding="utf-8"))
    exp = bytearray(orig)
    for idx, en in sorted(T.items()):
        r = rows[idx]; off = r["offset"]
        lead = 0
        while lead < 4 and off+lead < len(orig) and orig[off+lead] < 0x20 and orig[off+lead] != 0x0A:
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        isd = ("\n" in en and len(first) <= 15 and not first.endswith((".", "!", "?")))
        body = bytes(orig[off:off+lead]) + A.pencode(en, "ascii" if isd else "menu")
        bud = r.get("budget", r["nbytes"])
        if len(body) > bud:
            continue
        exp[off:off+bud] = body + b"\x00" * (bud - len(body))
    A.heal_cues(exp, rows)
    return len(banlz.compress_record(bytes(exp))), exp, rows


def slot_of(n):
    stage = bytearray(open(os.path.join(A.WORK, "extracted", "DATA_STAGE.BIN"), "rb").read())
    recs = banlz.decompress_all(stage)
    s1 = recs[n][0]; s2 = recs[n+1][0] if n+1 < len(recs) else len(stage)
    return s2 - s1


def main():
    for a in sys.argv[1:]:
        n = int(a)
        p = "rec%03d_en.py" % n
        s = u.spec_from_file_location("m%d" % n, p); m = u.module_from_spec(s); s.loader.exec_module(m)
        T = dict(m.T); slot = slot_of(n)
        with contextlib.redirect_stdout(io.StringIO()):
            size, _, _ = blob_size(n, T)
        order = sorted(T, key=lambda i: -bl(T[i]))
        oi = 0
        while size > slot and oi < len(order):
            i = order[oi]; oi += 1
            cur = T[i]
            for aa, bb in SUBS:
                if aa in cur:
                    cur = cur.replace(aa, bb)
            cur = cur.replace("  ", " ")
            if cur != T[i]:
                T[i] = cur
                with contextlib.redirect_stdout(io.StringIO()):
                    size, _, _ = blob_size(n, T)
        lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue."""' % n, "", "T = {"]
        for k in sorted(T): lines.append("    %d: %r," % (k, T[k]))
        lines.append("}")
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("rec%03d: slot %d, final blob %d, %s" % (n, slot, size, "FITS" if size <= slot else "STILL OVER by %d" % (size-slot)))


if __name__ == "__main__":
    main()
