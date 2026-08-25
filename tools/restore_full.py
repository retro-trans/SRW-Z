# -*- coding: utf-8 -*-
"""FULL-RESTORATION pass (v2 text build).

Rebuilds every translated STAGE record from the ORIGINAL Japanese using the
FULL translations in tools/recNNN_en.py, with option-3 relocation for rows
whose English overruns the Japanese byte budget - healing the ~15,200 rows
that shipped budget-truncated (and were then skipped by the quotes pass
because their closing quote had been cut off, which is how the user spotted
them in the backlog).

Per record (the canonical 167 from analysis/recs_all.txt - v1.32 lesson:
always ALL of them, an omitted record reverts to Japanese):
  PASS SOURCES mirror apply_stage.py exactly, except tighten_en.json is
  DROPPED in full mode - its entries exist only to squeeze rows into their
  slots, which relocation makes unnecessary. namefix/passthrough quality
  overrides are KEPT.
    * T rows -> transform() (kagi quotes + glossary links, imported from
      apply_quotes_links_all) -> in-place if strictly < budget, else
      RELOCATE (append + repoint every 4-aligned ref + zero the old slot)
    * override-added rows, M1/M2/M3 missing-dialogue, objectives, EXTRA:
      shipped semantics; M2/M3 also get transform and may relocate (they
      are setText dialogue reached through string pointers)
  GUARDS kept from apply_stage: translatable() bytecode refusal, leading
  control-byte prefixes, ascii/menu encoding heuristic, strictly-<-budget
  NUL rule, touched[] + check_pointers_intact() run BEFORE the relocation
  phase (after it, only replace_ptr's accounted writes + zeroed slots
  differ), roundtrip assert, banlz_strict on every record at the end.

  COMPRESSION chain per record: greedy -> optimal -> CONSERVATIVE rebuild
  (shipped apply_stage semantics incl. tighten, transform only where it
  fits, no relocation) -> splice the record's slot bytes verbatim from the
  shipped srwz_alldlg.bin so no record can regress below what shipped.

Base ISO: iso/srwz_corridor2.bin (carries the three ELF patches: linkpos,
underline, backlog). STAGE region rebuilt from extracted/DATA_STAGE.BIN.
Output: iso/srwz_restore.bin + analysis/restore_report.json
"""
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import banlz_strict as bs
import apply_stage as A
from apply_quotes_links_all import transform, replace_ptr, log as qlog, CQ
from patch import encode as pencode

SECTOR, STAGE_LBA, STAGE_SIZE = 2048, 1651029, 3910128
BASE = 0x7566F0
WORK = r"E:\Projects\SRW Z\_work"
BASE_ISO = os.path.join(WORK, "iso", "srwz_restore.bin")
SHIP_ISO = os.path.join(WORK, "iso", "srwz_alldlg.bin")
# IN-PLACE since v2.01: srwz_restore.bin already carries the ELF patches plus
# COMPDATA/bazaar/vlabels/titlecards edits that live OUTSIDE the STAGE region.
# Copying from corridor2 again would wipe them; we only rewrite STAGE.
OUT_ISO = BASE_ISO


def _load(*names):
    d = {}
    for f in names:
        try:
            d.update(json.load(open(os.path.join(WORK, "analysis", f),
                                    encoding="utf-8")))
        except FileNotFoundError:
            pass
    return d


# Full mode keeps only the QUALITY overrides. Conservative mode adds the
# tighten truncations back (same merge order as apply_stage: tighten first,
# so a namefix/passthrough entry for the same key still wins).
KEEP_OVR = _load("namefix_en.json", "passthrough_en.json", "relayout_en.json")
TIGHTEN_ALL = _load("tighten_en.json", "namefix_en.json", "passthrough_en.json",
                    "relayout_en.json")


def lead_prefix(orig, off):
    """Leading control byte(s) (0x0C/0x01/0x04 glossary-link markers)."""
    lead = 0
    while (lead < 4 and off + lead < len(orig)
           and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
        lead += 1
    return bytes(orig[off:off + lead])


def has_ref(buf, off):
    """Is there a 4-aligned absolute pointer to BASE+off in the record?"""
    nb = struct.pack("<I", BASE + off)
    i = 0
    while True:
        j = buf.find(nb, i)
        if j < 0:
            return False
        if j % 4 == 0:
            return True
        i = j + 1


def dlg_mode(en):
    """apply_stage's dialogue/menu heuristic, verbatim."""
    first = en.split("\n", 1)[0].rstrip()
    is_dlg = ("\n" in en and len(first) <= 15
              and not first.endswith((".", "!", "?")))
    return "ascii" if is_dlg else "menu"


def enc_row(en, prefix, mode):
    return prefix + pencode(en, mode)


def trim_fit(en, prefix, mode, bud):
    """Shipped trim loop, generalized to a kagi closing bracket."""
    enc = enc_row(en, prefix, mode)
    while len(enc) >= bud and en:
        # NOTE: the old "..." -> fullwidth-ellipsis byte saver is gone on
        # purpose - one ellipsis style game-wide (see the T pass).
        if (en.endswith('"') or en.endswith(CQ)) and len(en) > 1:
            en = en[:-2] + en[-1]
        else:
            en = en[:-1]
        enc = enc_row(en, prefix, mode)
    return en, enc


def build(n, orig, rows, T, EXTRA, conservative, keep_ellipsis=False):
    """Build the (possibly extended) expanded record for rec n."""
    exp = bytearray(orig)
    touched = bytearray(len(orig))
    pending = []            # (off, zero_nbytes, enc) -> relocation phase
    st = {"inplace": 0, "reloc": 0, "trimmed": 0, "junk": 0,
          "skipped": 0, "restored": 0, "noref": 0}

    def place(off, bud, enc):
        exp[off:off + bud] = enc + b"\x00" * (bud - len(enc))
        touched[off:off + bud] = b"\x01" * bud

    ovr = TIGHTEN_ALL if conservative else KEEP_OVR

    # ---------------- T rows (the main dialogue pass)
    for idx, en in sorted(T.items()):
        r = rows[idx]
        off = r["offset"]
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        en = ovr.get("%d:%d" % (n, idx), en)
        # One ellipsis style game-wide: ASCII '...' on the baseline. The JP
        # fullwidth ellipsis (0x8163) hovers mid-line and clashed with ASCII
        # dots in the same sentence (user call, 2026-08-20). Relocation makes
        # the old 2-vs-3-byte saving irrelevant.
        if not keep_ellipsis:
            en = en.replace(u"…", "...")
        prefix = lead_prefix(orig, off)
        mode = dlg_mode(en)
        bud = r.get("budget", r["nbytes"])
        jp = r.get("text") or ""
        new = transform(jp, en, n, idx)
        cand = en if new is None else new
        enc = enc_row(cand, prefix, mode)
        if len(enc) < bud:
            place(off, bud, enc)
            st["inplace"] += 1
        elif not conservative and has_ref(orig, off):
            pending.append((off, r["nbytes"], enc))
            st["restored"] += 1
        else:
            # conservative, or no pointer ref to repoint. Shipped semantics:
            # transform only where it fits, then the trim loop.
            if new is not None:
                enc2 = enc_row(en, prefix, mode)
                if len(enc2) < bud:
                    place(off, bud, enc2)
                    st["inplace"] += 1
                    continue
                cand = en
            if not conservative:
                st["noref"] += 1
            en3, enc3 = trim_fit(cand, prefix, mode, bud)
            if len(enc3) < bud:
                place(off, bud, enc3)
                st["trimmed"] += 1
            else:
                st["skipped"] += 1

    # ---------------- override-added rows (keys not present in T)
    for k, en in sorted(ovr.items()):
        rr, ii = (int(v) for v in k.split(":"))
        if rr != n or ii in T or ii >= len(rows):
            continue
        r = rows[ii]
        off = r["offset"]
        if not A.translatable(orig, off):
            continue
        prefix = lead_prefix(orig, off)
        mode = dlg_mode(en)
        bud = r.get("budget", r["nbytes"])
        new = transform(r.get("text") or "", en, n, ii)
        for cand in ([new, en] if new is not None else [en]):
            enc = enc_row(cand, prefix, mode)
            if len(enc) < bud:
                place(off, bud, enc)
                st["inplace"] += 1
                break

    # ---------------- M1: missed in-battle/event dialogue (raw ASCII)
    for off, budget, key in A._MISSING_JP.get(n, []):
        en = A._MISSING.get(key)
        if not en:
            continue
        if not keep_ellipsis:
            en = en.replace(u"…", "...")
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        prefix = lead_prefix(orig, off)
        enc = prefix + en.encode("cp932", "replace")
        if len(enc) < budget:
            place(off, budget, enc)
            st["inplace"] += 1
        elif not conservative and has_ref(orig, off):
            pending.append((off, budget, enc))
            st["restored"] += 1

    # ---------------- M2: second-pass rows
    for off, bud, jpstr in A._M2_BY_REC.get(n, []):
        en0 = A._M2.get(jpstr)
        if not en0:
            continue
        if not keep_ellipsis:
            en0 = en0.replace(u"…", "...")
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        prefix = lead_prefix(orig, off)
        mode = dlg_mode(en0)
        new = transform(jpstr, en0, n, -off)
        cands = ([new] if new is not None else []) + [en0]
        done = False
        for cand in cands:
            enc = enc_row(cand, prefix, mode)
            if len(enc) < bud:
                place(off, bud, enc)
                st["inplace"] += 1
                done = True
                break
        if done:
            continue
        if not conservative and has_ref(orig, off):
            pending.append((off, bud, enc_row(cands[0], prefix, mode)))
            st["restored"] += 1
        else:
            en3, enc3 = trim_fit(en0, prefix, mode, bud)
            if en3 and len(enc3) < bud:
                place(off, bud, enc3)
                st["trimmed"] += 1

    # ---------------- M3: extractor-blind rows (ALWAYS ascii - see apply_stage)
    for off, bud, jpstr in A._M3_BY_REC.get(n, []):
        en0 = A._M3.get(jpstr)
        if not en0:
            continue
        if not keep_ellipsis:
            en0 = en0.replace(u"…", "...")
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        prefix = lead_prefix(orig, off)
        new = transform(jpstr, en0, n, -off)
        cands = ([new] if new is not None else []) + [en0]
        done = False
        for cand in cands:
            enc = enc_row(cand, prefix, "ascii")
            if len(enc) < bud:
                place(off, bud, enc)
                st["inplace"] += 1
                done = True
                break
        if done:
            continue
        if not conservative and has_ref(orig, off):
            pending.append((off, bud, enc_row(cands[0], prefix, "ascii")))
            st["restored"] += 1

    # ---------------- EXTRA dict (offset-keyed additions)
    for off, (budget, en) in sorted(EXTRA.items()):
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        enc = en.encode("cp932")
        if len(enc) < budget:
            place(off, budget, enc)
            st["inplace"] += 1

    # ---------------- mission objectives (menu-rendered, in-place only)
    off2idx = {r["offset"]: i for i, r in enumerate(rows)}
    for off, budget, jp in A._OBJ_BY_REC.get(n, []):
        if off2idx.get(off) in T:
            continue
        en = A._OBJ_EN.get(jp)
        if not en:
            continue
        if not A.translatable(orig, off):
            st["junk"] += 1
            continue
        # SAFETY: a raw ASCII 0x2E-0x3D or control byte in the ORIGINAL field
        # is a control code (dynamic placeholder), not a literal character.
        ob = bytes(orig[off:off + budget]).split(b"\x00")[0]
        if any(b < 0x20 and b != 0x0A or 0x2E <= b <= 0x3D for b in ob):
            continue
        enc = pencode(en, "menu")
        if len(enc) < budget:
            place(off, budget, enc)
            st["inplace"] += 1

    # Nothing outside our slots may have moved. Run BEFORE relocation: after
    # it, the only extra diffs are replace_ptr's pointer rewrites (counted,
    # value-checked by construction) and the zeroed old slots.
    A.check_pointers_intact(exp, orig, touched)

    # ---------------- relocation phase (option-3)
    rec = exp
    for off, nb, enc in pending:
        new_off = len(rec)
        tmp = bytearray(rec)
        tmp += enc + b"\x00"
        cnt = replace_ptr(tmp, BASE + off, BASE + new_off)
        if cnt < 1:                      # planned via has_ref; belt+braces
            st["noref"] += 1
            continue
        for x in range(off, off + nb):
            tmp[x] = 0
        rec = tmp
        st["reloc"] += 1
    return bytes(rec), st


def compress_cached(n, rec, flags, slot):
    cache = os.path.join(WORK, "analysis", "blob_cache2")
    os.makedirs(cache, exist_ok=True)
    h = hashlib.sha1(rec + bytes([flags or 0])).hexdigest()[:16]
    cp = os.path.join(cache, "rec%03d_%s.lz" % (n, h))
    if os.path.exists(cp):
        return open(cp, "rb").read()
    blob = banlz.compress_record(rec, flags)
    if len(blob) > slot:
        blob = banlz.compress_record_optimal(rec, flags)
    open(cp, "wb").write(blob)
    return blob


def main():
    t0 = time.time()
    stage = bytearray(open(os.path.join(WORK, "extracted", "DATA_STAGE.BIN"),
                           "rb").read())
    assert len(stage) == STAGE_SIZE
    with open(SHIP_ISO, "rb") as f:
        f.seek(STAGE_LBA * SECTOR)
        ship = f.read(STAGE_SIZE)
    recs = banlz.decompress_all(bytes(stage))
    starts = [r[0] for r in recs] + [len(stage)]
    rec_ids = [int(x) for x in
               open(os.path.join(WORK, "analysis", "recs_all.txt")).read().split()]

    report = {}
    for n in rec_ids:
        dec = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
        orig = open(dec, "rb").read() if os.path.exists(dec) else recs[n][1]
        assert orig == recs[n][1], "stage_dec/rec%03d.bin != JP stage" % n
        rows = json.load(open(os.path.join(WORK, "analysis",
                                           "rec%03d_script.json" % n),
                              encoding="utf-8"))
        py = os.path.join(WORK, "tools", "rec%03d_en.py" % n)
        spec = importlib.util.spec_from_file_location("r%d" % n, py)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        EXTRA = getattr(m, "EXTRA", {})

        slot = starts[n + 1] - starts[n]
        total, flags, at = banlz.parse_header(bytes(stage), starts[n])

        rec, st = build(n, bytearray(orig), rows, m.T, EXTRA, False)
        blob = compress_cached(n, rec, flags, slot)
        status = "full"
        if len(blob) > slot:
            # ASCII "..." is a byte longer than the fullwidth ellipsis; a few
            # ellipsis-heavy records tip over their slot from that alone.
            # Keeping the JP ellipsis in JUST those records beats regressing
            # them to conservative truncation (v2.01 lesson: recs 59/74/96/
            # 115/137 lost restored text over single bytes of "...").
            rec, st = build(n, bytearray(orig), rows, m.T, EXTRA, False,
                            keep_ellipsis=True)
            blob = compress_cached(n, rec, flags, slot)
            status = "full-jpellipsis"
        if len(blob) > slot:
            rec, st = build(n, bytearray(orig), rows, m.T, EXTRA, True)
            blob = compress_cached(n, rec, flags, slot)
            status = "conservative"
            if len(blob) > slot:
                stage[starts[n]:starts[n] + slot] = \
                    ship[starts[n]:starts[n] + slot]
                report[n] = {"status": "shipped-blob"}
                print("rec%03d: SHIPPED-BLOB fallback (%.0fs)"
                      % (n, time.time() - t0))
                sys.stdout.flush()
                continue
        rt, _ = banlz.decompress_record(blob, 0)
        assert rt == rec, "roundtrip failed rec%d" % n
        stage[starts[n]:starts[n] + slot] = blob + b"\x00" * (slot - len(blob))
        st["status"] = status
        st["grew"] = len(rec) - len(orig)
        st["blob"] = "%d/%d" % (len(blob), slot)
        report[n] = st
        print("rec%03d: %s  inplace=%d reloc=%d restored=%d trimmed=%d "
              "skip=%d grew=%d blob=%s (%.0fs)"
              % (n, status, st["inplace"], st["reloc"], st["restored"],
                 st["trimmed"], st["skipped"], st["grew"], st["blob"],
                 time.time() - t0))
        sys.stdout.flush()

    # whole-region verification
    chk = banlz.decompress_all(bytes(stage))
    assert all(x[1] is not None for x in chk)
    nprob = 0
    for n in range(len(chk)):
        t2, fl2, at2 = banlz.parse_header(bytes(stage), starts[n])
        nprob += len(bs.verify(bytes(stage), at2, t2)[1])
    print("strict problems total:", nprob)
    assert nprob == 0

    if OUT_ISO != BASE_ISO:
        shutil.copyfile(BASE_ISO, OUT_ISO)
    with open(OUT_ISO, "r+b") as f:
        f.seek(STAGE_LBA * SECTOR)
        f.write(bytes(stage))

    tot = {k: sum(r.get(k, 0) for r in report.values())
           for k in ("inplace", "reloc", "restored", "trimmed", "skipped",
                     "junk", "noref")}
    summary = {"totals": tot,
               "quoted_rows": qlog["quoted_rows"], "linked": qlog["linked"],
               "dequoted": qlog["dequoted"],
               "records": {str(k): v for k, v in sorted(report.items())},
               "link_miss": qlog["link_miss"], "wide": qlog["wide"][:400],
               "wide_total": len(qlog["wide"])}
    json.dump(summary, open(os.path.join(WORK, "analysis",
                                         "restore_report.json"),
                            "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("TOTALS:", tot)
    print("quoted=%d linked=%d dequoted=%d wide=%d"
          % (qlog["quoted_rows"], qlog["linked"], qlog["dequoted"],
             len(qlog["wide"])))
    print("wrote", OUT_ISO, "in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
