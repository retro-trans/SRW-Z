# -*- coding: utf-8 -*-
"""Extract every encyclopedia (図鑑) text field to analysis/zkn_jp.json.

Unlike the stage/ELF strings, these fields are NOT fixed slots: each chunk
carries its own u32 length, so the English may be longer or shorter as long as
the length, the record's DSIZ/DATA totals and the archive offsets are rewritten
(see zkn_build.py).  So no per-field byte budget is recorded here.

Output: {"RT": {"0": {"PRDC": "...", "RBTN": "...", ...}, ...}, "PT": ..., "KW": ...}
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zkn

WORK = r"E:\Projects\SRW Z\_work"
FILES = {"RT": "DATA_MTVZKNRT.BIN",   # 321 robots
         "PT": "DATA_MTVZKNPT.BIN",   # 411 characters
         "KW": "DATA_MTVZKNKW.BIN"}   # 52 glossary terms

# Text-bearing chunks per file kind. VOIC/LOOK are binary (voice-sample and
# portrait ids), DSIZ/DATA are sizes, LorR is a flag - none are text.
TEXT = {
    "ROBO": ["PRDC", "RBTN", "PLTN", "HEIT", "WEIT", "DSCR", "DSC2", "KANA"],
    "CHAR": ["CHFN", "CHNN", "PRDC", "ACTR", "DSCR", "DSC2"],
    "KYWD": ["WORD", "SRCE", "DSCR", "DSC2"],
}


def main():
    out = {}
    stats = {}
    for key, fn in FILES.items():
        path = os.path.join(WORK, "extracted", fn)
        ent = {}
        nchars = 0
        for ri, rec in zkn.records(path):
            magic, kind, ver, chunks = zkn.parse(zkn.payload_of(rec))
            want = TEXT[kind]
            d = {}
            for tag, off, data in chunks:
                if tag not in want or not isinstance(data, bytes):
                    continue
                t = data.decode("cp932").rstrip("\x00")
                d[tag] = t
                nchars += len(t)
            ent[str(ri)] = d
        out[key] = ent
        stats[key] = (len(ent), nchars)
    p = os.path.join(WORK, "analysis", "zkn_jp.json")
    io.open(p, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    for k, (n, c) in stats.items():
        print("%s: %3d entries, %6d JP chars" % (k, n, c))
    print("total %d entries, %d chars -> %s"
          % (sum(s[0] for s in stats.values()),
             sum(s[1] for s in stats.values()), p))


if __name__ == "__main__":
    main()
