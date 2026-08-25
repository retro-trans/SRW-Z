# -*- coding: utf-8 -*-
"""Term fixes resolved through the pointer, so RELOCATED rows are covered.

fix_body_terms matched a row by looking up the Japanese at the same offset. That
silently skips every row healed by option-3 relocation, because the Japanese has
nothing at the row's new offset - which is how three "Mykene" rows survived,
including Emperor Burai's introduction 「我こそは百鬼帝国のブライ大帝！」 shipping as
"Emperor Bray of the Mykene Empire": the wrong empire (百鬼 is Getter Robo Go's
Hyakki; ミケーネ is Great Mazinger's Mycenae, and the two rows that really do say
ミケーネ already read "Mycenae").

Each rule is conditioned on the Japanese so nothing unrelated is renamed, and
replacements may only shrink a row, never lengthen it.

Usage: fix_terms_pass.py <iso> [--dry-run]
"""
import glob
import io
import json
import multiprocessing
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TERMS = [
    (u"カガリ", "Kagari", "Cagalli"),
    (u"スカブ", "Skab", "Scub"),
    # scab is CASE-SENSITIVE - the capitalised form (70 rows) never
    # matched the original lowercase rule. Found by an agent, not by me.
    (u"スカブ", "Scabs", "Scubs"),
    (u"スカブ", "Scab", "Scub"),
    # エーデル = Edel (983 rows right). ~200 rows carry a misspelling.
    (u"エーデル", "Eidel", "Edel"),
    (u"エーデル", "Ederu", "Edel"),
    (u"エーデル", "Edele", "Edel"),
    (u"エーデル", "Eder", "Edel"),
    (u"テラール", "Terral", "Teral"),
    (u"アフロディア", "Afurodia", "Aphrodia"),
    # ガガーン: I first targeted "Gagaan" (30) - wrong direction,
    # "Gagarn" leads 99. Uncited name, so the dominant form wins.
    (u"ガガーン", "Gagaan", "Gagarn"),
    # ジーク = Zeke per the project name dictionary (db_en.json).
    (u"ジーク", "Zick", "Zeke"),
    (u"ジーク", "Zieg", "Zeke"),
    # ヒューギ uncited. I first scripted "Hughi" off a 6-row minority
    # because my scan missed "Hugy" (54 rows). Corrected: Hugy is the target.
    (u"ヒューギ", "Hughie", "Hugy"),
    (u"ヒューギ", "Hughi", "Hugy"),
    (u"ヒューギ", "Hyugi", "Hugy"),
    (u"ヒューギ", "Hugi", "Hugy"),
    # 大特異点 = the Great Singularity; "Grand" is same length.
    (u"大特異点", "Grand", "Great"),
    # ノルブ = Norb (Eureka Seven wiki). Corpus majority "Norbu" (100)
    # and "Norub" (74) are BOTH wrong; only 8 rows had it right. 148 of
    # the wrong ones are SPEAKER lines, so the nameplate is wrong too.
    (u"ノルブ", "Norbu", "Norb"),
    (u"ノルブ", "Norub", "Norb"),
    # リーナ uncited -> Lina (40) over Rina (10) / Reena (2).
    (u"リーナ", "Reena", "Lina"),
    (u"リーナ", "Rina", "Lina"),
    (u"ランドシップ", "landship", "Landship"),
    (u"ランドシップ", "Londo Ship", "Landship"),
    (u"百鬼", "Hundred Demons", "Hyakki"),
    (u"\u767e\u9b3c", "Mykene", "Hyakki"),          # 百鬼 = Hyakki, not Mycenae
    (u"\u30b9\u30ab\u30d6", "scabs", "Scubs"),      # スカブ = Scub (glossary term)
    (u"\u30b9\u30ab\u30d6", "scab", "Scub"),
    (u"\u30f4\u30a9\u30c0\u30e9\u5bae", "Vodarac", "Vodara"),   # 宮 = the palace
    (u"ロゴス", "LOGOS", "Logos"),      # ロゴス is a name, not an acronym
    (u"シュラン", "Schran", "Shuran"),  # シュラン uncited; plain transliteration, corpus majority
    (u"シュラン", "Schlann", "Shuran"),
    (u"シュラン", "Schlan", "Shuran"),
    (u"シュラン", "Schuran", "Shuran"),
    (u"カイメラ", "Chimaera", "Chimera"),
    (u"カイメラ", "Kaimera", "Chimera"),
    (u"カイメラ", "Kaimela", "Chimera"),
    # レーベン = Lowen (Löwen, "lions" - he pilots the Chaos Leo).
    # Shipped four ways: Leben 219, Raven 118, Lowen 92, Leven 49.
    (u"レーベン", "Leben", "Lowen"),
    (u"レーベン", "Raven", "Lowen"),
    (u"レーベン", "Leven", "Lowen"),
    # ツィーネ = Ziene Espio. Shipped as Tsine 189, Ciene 19.
    (u"ツィーネ", "Tsine", "Ziene"),
    (u"ツィーネ", "Ciene", "Ziene"),
    # ザイデル = Seidel Rasso (Gundam X). Shipped Zaidel 33, Zeidel 5.
    (u"ザイデル", "Zaidel", "Seidel"),
    (u"ザイデル", "Zeidel", "Seidel"),
    (u"ザイデル", "Zaydel", "Seidel"),
    (u"ザイデル", "Zeydel", "Seidel"),
    (u"パプテマス", "Papthimas", "Paptimus"),
    (u"パプテマス", "Papetmas", "Paptimus"),
    (u"パプテマス", "Papetmus", "Paptimus"),
    (u"ランスロー", "Darwell", "Darrow"),
    # ヴォダラク (the order) = Vodarac; ヴォダラ宮 (the place) = Vodara.
    # Conditioned on WHICH japanese term is present - both spellings are
    # correct in their own rows, so an unconditioned rule would break one.
    (u"ヴォダラク", "Vodalak", "Vodarac"),
    (u"ヴォダラク", "Vodorak", "Vodarac"),
    (u"ヴォダラク", "Vodarak", "Vodarac"),
    (u"ヴォダラ宮", "Voddara", "Vodara"),
    # NOTE: do NOT map ロラン "Laura" -> Loran. 「僕の事をローラと
    # 呼ぶのはやめ」 = "Stop calling me Laura!" - the alias is deliberate.
    (u"ロラン", "Rolan", "Loran"),
    # 風見 = Kazami (380 rows); "Kazuki" (22, incl. 13 SPEAKER lines) is a
    # misreading of the kanji - it puts the wrong name on the nameplate.
    (u"風見", "Kazuki", "Kazami"),
]


def _compress(args):
    idx, plain = args
    return idx, banlz.compress_record_optimal(plain)


def main():
    iso_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso_path, "r+b")
    f.seek(LBA * SECTOR)
    raw = bytearray(f.read(SIZE))
    items = banlz.decompress_all(bytes(raw))
    before = {o: bytes(d) for o, d in items if d is not None}
    edited, n, hits = {}, 0, []

    for p in sorted(glob.glob(os.path.join(WORK, "analysis", "review", "rec*.json"))):
        rec = int(os.path.basename(p)[3:6])
        rows = json.load(io.open(p, encoding="utf-8"))
        jb = bytes(jp[rec][1])
        eb = bytearray(items[rec][1])
        touched = False
        for r in rows:
            pairs = [(w, g) for k, w, g in TERMS if k in r["jp"]]
            if not pairs:
                continue
            off = r["off"]
            nb4 = struct.pack("<I", BASE + r["off"])
            for i in range(0, len(jb) - 4, 4):
                if jb[i:i + 4] == nb4 and i + 4 <= len(eb):
                    v = struct.unpack_from("<I", bytes(eb), i)[0] - BASE
                    if 0 <= v < len(eb):
                        off = v
                    break
            e = off
            while e < len(eb) and eb[e] != 0:
                e += 1
            try:
                cur = bytes(eb[off:e]).decode("cp932")
            except UnicodeDecodeError:
                continue
            nt = cur
            for w, g in pairs:
                nt = re.sub(r"\b%s\b" % re.escape(w), g, nt)
            if nt == cur:
                continue
            nb = nt.encode("cp932")
            if len(nb) > len(cur.encode("cp932")):
                continue
            k = e
            while k < len(eb) and eb[k] == 0:
                k += 1
            eb[off:k] = nb + b"\x00" * (k - off - len(nb))
            touched = True
            n += 1
            if len(hits) < 8:
                hits.append((rec, r["row"], cur.replace("\n", " | ")[:44],
                             nt.replace("\n", " | ")[:44]))
        if touched:
            edited[rec] = bytes(eb)
    print("rows fixed: %d in %d records" % (n, len(edited)))
    for h in hits:
        print("   rec%-4d row %-5d %s  ->  %s" % h)
    if dry or not edited:
        return
    pool = multiprocessing.Pool(max(1, (os.cpu_count() or 4) - 2))
    packed = dict(pool.map(_compress, list(edited.items())))
    pool.close(); pool.join()
    for rec, plain in edited.items():
        hdr = items[rec][0]
        blob = packed[rec]
        nxt = min([h for h, _ in items if h > hdr] or [len(raw)])
        assert len(blob) <= nxt - hdr, "rec %d grew past its slot" % rec
        raw[hdr:hdr + len(blob)] = blob
        for i in range(hdr + len(blob), nxt):
            raw[i] = 0
    check = {o: bytes(d) for o, d in banlz.decompress_all(bytes(raw)) if d is not None}
    assert set(check) == set(before), "record set changed"
    f.seek(LBA * SECTOR)
    f.write(bytes(raw))
    f.close()
    print("done")


if __name__ == "__main__":
    main()
