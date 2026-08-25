# -*- coding: utf-8 -*-
"""Game-wide dialogue polish: kagi quotes + glossary links (all records).

Extends the corridor-scene treatment (tools/corridor_polish.py) to every
stage record with extractor data:
  * dialogue rows  Speaker\n"..."  ->  Speaker\n<kagi>...</kagi>
  * for every linked term in the JP original, wrap the shipped English term
    in link markers (quoted 'Term' / possessive / (Term) / <Term> forms are
    unwrapped first); matches never span a line break
  * quoted glossary terms with NO link in the JP row are de-quoted
  * in-place where the bytes fit, relocate+repoint otherwise (option-3);
    per-record fallback to in-place-only if the slot overflows

Base: iso/srwz_corridor2.bin (rec001 + the 3 ELF patches already applied).
Output: iso/srwz_alldlg.bin
"""
import io
import os, re, sys, json, glob, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import banlz_strict as bs

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
BASE = 0x7566F0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_corridor2.bin")
OUT_ISO = os.path.join(WORK, "iso", "srwz_alldlg.bin")
LO, LC, OQ, CQ = u"\u300a", u"\u300b", u"\u300c", u"\u300d"

# JP glossary term -> EN variants (first match wins; no variant spans \n)
GLOSS = {
 u"\u30a2\u30d7\u30ea\u30ea\u30a6\u30b9": ["Aprilius"],
 u"\u30a2\u30fc\u30b5\u30fc": ["Arthur"],
 u"\u30a2\u30fc\u30e2\u30ea\u30fc\u30ef\u30f3": ["Armory One"],
 u"\u30a4\u30ce\u30bb\u30f3\u30c8": ["Innocents", "Innocent"],
 u"\u30a6\u30a3\u30fc\u30eb": ["<Wheels>", "Wheels", "Wheel"],
 u"\u30a6\u30ba\u30df": ["Uzumi"],
 u"\u30a8\u30a5\u30fc\u30b4": ["AEUG"],
 u"\u30a8\u30af\u30b9\u30c6\u30f3\u30c7\u30c3\u30c9": ["Extended"],
 u"\u30a8\u30af\u30bd\u30c0\u30b9": ["Exodus"],
 u"\u30a8\u30d3\u30c7\u30f3\u30b9\u30fb\u30bc\u30ed\u30ef\u30f3": ["Evidence Zero-One", "Evidence 01"],
 u"\u30aa\u30eb\u30d5\u30a1\u30f3": ["Orfan"],
 u"\u30aa\u30fc\u30d0\u30fc\u30b3\u30fc\u30c8": ["Overcoat"],
 u"\u30aa\u30fc\u30d0\u30fc\u30de\u30f3\u30d0\u30c8\u30eb": ["Overman Battle"],
 u"\u30aa\u30fc\u30d6": ["Orb"],
 u"\u30aa\u30fc\u30d6\u9632\u885b\u6226": ["Orb Defense"],
 u"\u30ab\u30b7\u30e0\u30fb\u30ad\u30f3\u30b0": ["Kashim King"],
 u"\u30ab\u30e9\u30d0": ["Karaba"],
 u"\u30b0\u30ed\u30fc\u30ea\u30fc\u30fb\u30b9\u30bf\u30fc": ["Glory Star"],
 u"\u30b2\u30f3\u30ac\u30ca\u30e0": ["Ghingnham"],
 u"\u30b3\u30f3\u30c8\u30ea\u30ba\u30e0": ["Contolism"],
 u"\u30b3\u30fc\u30c7\u30a3\u30cd\u30a4\u30bf\u30fc": ["Coordinators", "Coordinator"],
 u"\u30b5\u30a4\u30c9\uff13": ["Side 3"],
 u"\u30b5\u30de\u30fc\u30fb\u30aa\u30d6\u30fb\u30e9\u30d6": ["Summer of Love"],
 u"\u30b6\u30d5\u30c8": ["ZAFT"],
 u"\u30b7\u30d9\u30ea\u30a2\u9244\u9053": ["Siberia Railway"],
 u"\u30b8\u30aa\u30f3\u30fb\u30ba\u30e0\u30fb\u30c0\u30a4\u30af\u30f3": ["Zeon Zum Deikun"],
 u"\u30b8\u30e7\u30f3\u30fb\u30d8\u30f3\u30ea": ["John Henry"],
 u"\u30b9\u30ab\u30d6\u30b3\u30fc\u30e9\u30eb": ["Scub Coral"],
 u"\u30c6\u30a3\u30bf\u30fc\u30f3\u30ba": ["Titans"],
 u"\u30c8\u30e9\u30d1\u30fc": ["Trapar"],
 u"\u30ca\u30c1\u30e5\u30e9\u30eb": ["Naturals", "Natural"],
 u"\u30d0\u30eb\u30de\u30fc\u6226\u5f79": ["Balmar War"],
 u"\u30d1\u30c8\u30ea\u30c3\u30af\u30fb\u30b6\u30e9": ["(Patrick Zala)", "Patrick Zala"],
 u"\u30d5\u30a9\u30fc\u30c8\u30bb\u30d0\u30fc\u30f3": ["Fort Severn"],
 u"\u30d6\u30eb\u30fc\u30b3\u30b9\u30e2\u30b9": ["Blue Cosmos"],
 u"\u30d6\u30ed\u30c3\u30af\u30ef\u30fc\u30c9": ["Block Word"],
 u"\u30d7\u30e9\u30f3\u30c8": ["PLANTs", "PLANT"],
 u"\u30d7\u30e9\u30f3\u30c8\u8a55\u8b70\u4f1a\u8b70\u9577": ["PLANT Council Chairman"],
 u"\u30df\u30ea\u30b7\u30e3": ["Militia"],
 u"\u30e2\u30eb\u30b2\u30f3\u30ec\u30fc\u30c6\u793e": ["Morgenroete"],
 u"\u30e6\u30cb\u30a6\u30b9\u6761\u7d04": ["Junius Treaty"],
 u"\u30e9\u30a6\u30fb\u30eb\u30fb\u30af\u30eb\u30fc\u30bc": ["Rau Le Creuset"],
 u"\u30ea\u30d5": ["ref boarders", "ref-board", "ref board", "ref"],
 u"\u30ed\u30b4\u30b9": ["LOGOS"],
 u"\u30f4\u30a9\u30c0\u30e9\u30af": ["Vodarac"],
 u"\u5730\u7403\u9023\u5408": ["Earth Alliance"],
 u"\u5b87\u5b99\u79d1\u5b66\u7814\u7a76\u6240": ["Space Science Lab"],
 u"\u6050\u7adc\u5e1d\u56fd": ["Dinosaur Empire"],
 u"\u76f8\u514b\u754c": ["Conflict Field", "Dimensional Rift", "Overlap", "Rift"],
 u"\u7b2c\uff12\u6b21\u30e4\u30ad\u30f3\u30fb\u30c9\u30a5\u30fc\u30a8\u653b\u9632\u6226":
     ["Second Battle of Jachin Due"],
 u"\u91d1\u7530\u4f0a\u529f": ["Kaneda Ikuo"],
 u"\uff26\uff21\uff29\uff34\uff28": ["FAITH"],
 u"\uff33\uff2f\uff26": ["SOF"],
 u"\uff35\uff2e": ["UN"],
}
ALL_EN_VARIANTS = sorted({v for vs in GLOSS.values() for v in vs
                          if not v.startswith(("(", "<"))},
                         key=len, reverse=True)

log = {"linked": 0, "link_miss": [], "dequoted": 0, "quoted_rows": 0,
       "reloc": 0, "inplace": 0, "noref": [], "rec_fallback": [],
       "rec_skip": [], "wide": []}


def wrap_term(en, variant):
    """Wrap one occurrence of variant in en with link markers."""
    apos = "'"
    for pat, rep in (
        (apos + variant + apos + apos, LO + variant + LC + apos),
        (apos + variant + apos + "s" + apos, LO + variant + LC + apos + "s"),
        (apos + variant + apos, LO + variant + LC),
        ("(" + variant + ")", LO + variant + LC),
        ("<" + variant + ">", LO + variant + LC),
    ):
        if pat in en:
            return en.replace(pat, rep, 1)
    m = re.search(r"(?<![A-Za-z0-9\u300a])" + re.escape(variant) +
                  r"(?![A-Za-z0-9\u300b])", en)
    if m:
        return en[:m.start()] + LO + variant + LC + en[m.end():]
    return None


def transform(jp, en, recno, idx):
    if en == jp:
        return None                       # untranslated passthrough
    orig = en
    apos = "'"
    jp_terms = re.findall(LO + "([^" + LC + "]+)" + LC, jp)
    for t in jp_terms:
        vs = GLOSS.get(t)
        if not vs:
            log["link_miss"].append((recno, idx, t, "no-gloss"))
            continue
        if any((LO + v) in en for v in vs):
            continue
        done = False
        for v in vs:
            new = wrap_term(en, v)
            if new is not None:
                en = new
                done = True
                log["linked"] += 1
                break
        if not done:
            log["link_miss"].append((recno, idx, t, "no-match"))
    linked_vs = {v for t in jp_terms for v in GLOSS.get(t, [])}
    for v in ALL_EN_VARIANTS:
        if v in linked_vs:
            continue
        for pat, rep in ((apos + v + apos + apos, v + apos),
                         (apos + v + apos + "s" + apos, v + apos + "s"),
                         (apos + v + apos, v)):
            if pat in en:
                en = en.replace(pat, rep)
                log["dequoted"] += 1
    parts = en.split("\n")
    body = "\n".join(parts[1:])
    if len(parts) >= 2 and body.startswith('"') and body.endswith('"'):
        en = parts[0] + "\n" + OQ + body[1:-1] + CQ
        log["quoted_rows"] += 1
    if en == orig:
        return None
    for ln in en.split("\n")[1:]:
        w = sum(0 if c in (LO, LC) else (2 if ord(c) > 0x7F else 1)
                for c in ln)
        if w > 38:
            log["wide"].append((recno, idx, w, ln[:40]))
    return en


def replace_ptr(buf, oldp, newp):
    ob, nb, cnt, i = struct.pack("<I", oldp), struct.pack("<I", newp), 0, 0
    while True:
        j = buf.find(ob, i)
        if j < 0:
            break
        if j % 4 == 0:
            buf[j:j + 4] = nb
            cnt += 1
            i = j + 4
        else:
            i = j + 1
    return cnt


def build_record(rec0, rows, changes, allow_reloc):
    rec = bytearray(rec0)
    for idx, enc in changes:
        r = rows[idx]
        off, nb = r["offset"], r["nbytes"]
        if len(enc) <= nb:
            rec[off:off + nb] = enc + b"\x00" * (nb - len(enc))
            log["inplace"] += 1
        elif allow_reloc:
            new_off = len(rec)
            tmp = bytearray(rec)
            tmp += enc + b"\x00"
            cnt = replace_ptr(tmp, BASE + off, BASE + new_off)
            if cnt < 1:
                log["noref"].append(idx)
                continue
            for x in range(off, off + nb):
                tmp[x] = 0
            rec = tmp
            log["reloc"] += 1
    return rec


def main():
    with open(BASE_ISO, "rb") as f:
        f.seek(STAGE_LBA * SECTOR)
        stage = bytearray(f.read(STAGE_SIZE))
    recs = banlz.decompress_all(bytes(stage))
    starts = [r[0] for r in recs] + [len(stage)]

    jsons = {}
    for fp in glob.glob(os.path.join(WORK, "analysis", "rec*_script.json")):
        n = int(re.search(r"rec(\d+)_", fp).group(1))
        jsons[n] = fp

    changed_records = 0
    for n in sorted(jsons):
        if n == 1 or n >= len(recs) or recs[n][1] is None:
            continue                      # rec001 already done (corridor)
        rows = json.load(open(jsons[n], encoding="utf-8"))
        rec0 = recs[n][1]
        changes = []
        for idx, r in enumerate(rows):
            jp = r.get("text") or ""
            raw = rec0[r["offset"]:r["offset"] + r["nbytes"]].split(b"\x00")[0]
            try:
                en = raw.decode("cp932")
            except Exception:
                continue
            new = transform(jp, en, n, idx)
            if new is None:
                continue
            try:
                enc = new.encode("cp932")
            except Exception:
                continue
            changes.append((idx, enc))
        if not changes:
            continue
        slot = starts[n + 1] - starts[n]
        total, flags, at = banlz.parse_header(bytes(stage), starts[n])
        stat_bak = (log["inplace"], log["reloc"])
        rec = build_record(rec0, rows, changes, True)
        blob = banlz.compress_record(bytes(rec), flags)
        if len(blob) > slot:
            blob = banlz.compress_record_optimal(bytes(rec), flags)
            if len(blob) > slot:
                log["rec_fallback"].append(n)
                log["inplace"], log["reloc"] = stat_bak
                rec = build_record(rec0, rows, changes, False)
                blob = banlz.compress_record_optimal(bytes(rec), flags)
                if len(blob) > slot:
                    log["rec_skip"].append(n)
                    continue
        assert banlz.decompress_record(blob)[0] == bytes(rec)
        stage[starts[n]:starts[n] + slot] = blob + b"\x00" * (slot - len(blob))
        changed_records += 1

    chk = banlz.decompress_all(bytes(stage))
    assert all(x[1] is not None for x in chk)
    nprob = 0
    for n in range(len(chk)):
        t2, fl2, at2 = banlz.parse_header(bytes(stage), starts[n])
        nprob += len(bs.verify(bytes(stage), at2, t2)[1])
    print("records changed:", changed_records)
    print("rows: %d in-place, %d relocated, %d quoted, %d links added, "
          "%d de-quotes" % (log["inplace"], log["reloc"], log["quoted_rows"],
                            log["linked"], log["dequoted"]))
    print("link misses:", len(log["link_miss"]),
          " wide lines:", len(log["wide"]),
          " fallback recs:", log["rec_fallback"],
          " skipped recs:", log["rec_skip"], " noref:", log["noref"])
    print("strict problems total:", nprob)
    assert nprob == 0

    shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR)
        f.write(stage)
    json.dump({k: v for k, v in log.items() if isinstance(v, list)},
              io.open(os.path.join(WORK, "analysis", "alldlg_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("wrote", OUT_ISO)


if __name__ == "__main__":
    main()
