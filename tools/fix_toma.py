# -*- coding: utf-8 -*-
u"""頭翅 is Toma, not "Touma", and never "Toutenshi" or "Head".

頭翅 reads トーマ - the Shadow Angels' front-line commander and
Apollonius' former partner. The whole faction is named with 翅 ("wing"):
音翅 オトハ, 両翅 モロハ, 双翅 フタバ, 詩翅 (Sirius' name after he
awakens). We already render those from their kana; 頭翅 was the one
spelled by transliteration instead.

**Akurasu is this project's naming baseline** and spells it **Toma** -
along with Otoha, Moroha, Futaba, Sirius de Alisia and Shadow Angels. Our
disc had "Touma" in 304 places, which is a wapuro long vowel, not the
baseline. See [[naming-baseline-wiki]]: never majority-vote or
transliterate, however consistent the majority is.

"Toma" is shorter than "Touma", so every renamed row SHRINKS and none can
overflow its slot. The rename is a byte replace inside each string, with
the tail pulled left and NUL-padded, so no string moves and no pointer
changes.

Then the rows where the name was lost outright. 88 prose mentions carried
it; 75 were right and these were not:

    「頭翅アアアアアアアアアッ！！」 -> "Zuuuushiiii!!"   a hallucinated scream
    「逃げやがったか、頭翅！」      -> "Go get 'em!"     inverts the line
    頭翅 (recap)                  -> "Toutenshi"       invented; 堕天翅+頭翅
    頭翅 (recap x3)               -> "Head"            the kanji, translated
    頭翅様 / 頭翅か                -> "Lord Head-Wing" / "Head-Wing's voice"
    頭翅の野郎                    -> "that Shadow Angel"  name -> faction

"Head" -> "Toma" is the same byte length, so the recap paragraphs keep
their wrapping exactly.

Left alone deliberately: rec21's 「頭翅様、今ひとつ…」 ("One more thing...")
would need 36 bytes against a 31-byte slot to restore the address, and
rec144/rec149 drop 「頭翅の言っていた」 as a condensation with 9 spare bytes.
Neither is wrong, only lossy.

Usage: fix_toma.py <iso> <jp-iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import fix_stranded_strings as F
import fix_struct_intrusions as X
import fix_shadow_angels as S      # rewrap()

SEC, LBA, SIZE = 2048, 1651029, 3910128
NL = "\n"

OLD, NEW = b"Touma", b"Toma"

# (record, locator substring, old, new) - all same-length or shorter, so
# none of them re-wraps anything.
EDITS = [
    (0, u"Toutenshi was already", u"Toutenshi", u"Toma", "prose"),
    (0, u"Shadow Angel led by Head", u"led by Head", u"led by Toma", "prose"),
    # this one is in TWO recap rows with identical text
    (0, u"Sirius, and Head achieved", u"and Head", u"and Toma", "prose"),
    (22, u"Lord Head-Wing", u"Lord Head-Wing", u"Lord Toma", "speaker"),
    (22, u"Head-Wing's voice", u"Head-Wing's voice", u"Toma's voice",
     "speaker"),
    (28, u"clashed with that Shadow Angel", u"that Shadow Angel",
     u"that bastard Toma", "speaker"),
    # 「頭翅アアアアアアアアアッ！！」 - nine ア, so nine a's.
    (101, u"Zuuuushiiii", u"Zuuuushiiii", u"Tomaaaaaaaaa", "speaker"),
    # 「逃げやがったか、頭翅！」 - Apollo shouting that Toma has fled.
    (136, u"Go get 'em!", u"Go get 'em!", u"So you ran, Toma!", "speaker"),
]


def strings(b):
    u"""(start, end) of every NUL-terminated printable run."""
    out, i, n = [], 0, len(b)
    while i < n:
        z = b.find(b"\x00", i)
        if z < 0:
            break
        if z > i:
            out.append((i, z))
        i = z + 1
    return out


def main():
    iso, jpiso = sys.argv[1], sys.argv[2]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    g = open(jpiso, "rb")
    g.seek(LBA * SEC)
    jp = [d for h, d in banlz.decompress_all(g.read(SIZE))
          if isinstance(h, int) and d is not None]
    g.close()

    touched = {}
    renamed = 0
    # ---- 1. the rename, every string in every record ----------------
    for rec, (h, d) in enumerate(live):
        eb = bytes(d)
        if OLD not in eb:
            continue
        hit = 0
        for s, z in strings(eb):
            if OLD not in eb[s:z]:
                continue
            new = eb[s:z].replace(OLD, NEW)
            d[s:s + len(new)] = new
            for x in range(s + len(new), z):
                d[x] = 0
            hit += 1
        if hit:
            renamed += hit
            touched[rec] = True
            print("  rec%-4d %d string(s) Touma -> Toma" % (rec, hit))

    # ---- 2. the rows that lost the name entirely --------------------
    fixed = 0
    for rec, locator, old, new, kind in EDITS:
      d = live[rec][1]
      # MATCH ON FLATTENED TEXT, and take EVERY match. A locator that
      # spans a wrap ("that Shadow\nAngel") matches nothing raw, and two
      # recap rows carry the same sentence, so `find` alone got one.
      targets = []
      for s, z in strings(bytes(d)):
        try:
            cur = bytes(d)[s:z].decode("cp932")
        except UnicodeDecodeError:
            continue
        if locator in " ".join(cur.split()):
            targets.append((s, z, cur))
      if not targets:
        print("  rec%-4d locator not found: %r" % (rec, locator))
        continue
      for s, z, cur in targets:
        eb = bytes(d)
        if kind == "speaker" and NL in cur:
            sp, _, body = cur.partition(NL)
            width = max(len(x) for x in body.split(NL))
            flat = " ".join(body.split()).replace(old, new)
            nxt = sp + NL + S.rewrap(flat, width)
        else:
            width = max(len(x) for x in cur.split(NL))
            nxt = S.rewrap(" ".join(cur.split()).replace(old, new), width)
        if old in " ".join(nxt.split()):
            print("  rec%-4d %r survived the replace, SKIPPED" % (rec, old))
            continue
        nb = nxt.encode("cp932")
        k = z
        while k < len(eb) and eb[k] == 0:
            k += 1
        if len(nb) > k - s - 1:
            print("  rec%-4d %d B > budget %d, SKIPPED"
                  % (rec, len(nb), k - s - 1))
            continue
        smask = X.safe_mask(bytes(jp[rec]))
        if not all(d[x] == 0 and smask[x] for x in range(z, s + len(nb))):
            print("  rec%-4d growth would cross structure, SKIPPED" % rec)
            continue
        pm = F.pointer_map(eb)
        if any(s < v < max(z, s + len(nb)) for v in pm):
            print("  rec%-4d a pointer aims inside this field, SKIPPED" % rec)
            continue
        d[s:s + len(nb)] = nb
        for x in range(s + len(nb), max(z, s + len(nb))):
            d[x] = 0
        d[s + len(nb)] = 0
        touched[rec] = True
        fixed += 1
        print("  rec%-4d %r -> %r" % (rec, old, new))

    print("")
    print("strings renamed Touma -> Toma : %d" % renamed)
    print("rows where the name was lost  : %d of %d" % (fixed, len(EDITS)))
    if not touched or not write:
        if touched:
            print("(dry run - pass --write to apply)")
        f.close()
        return 0
    for rec in sorted(touched):
        h = live[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(bytes(live[rec][1]))
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(bytes(live[rec][1]))
        assert len(blob) <= nxt - h, "rec%d over slot" % rec
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, "STAGE record set changed"
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("STAGE written")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
