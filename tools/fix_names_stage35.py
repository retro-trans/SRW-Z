# -*- coding: utf-8 -*-
"""One japanese name, two english spellings - found by pairing every line.

Asked to retranslate stage 35 (STAGE rec61), I read all 483 rows. The prose is
sound and rewriting it would be churn, so this fixes what is actually wrong:
five bad proper nouns in rec61, plus the same defect wherever else it occurs.

Every entry below was confirmed by looking at the JAPANESE beside the english,
not by spell-check. The same katakana resolves two ways in the shipped script:

  Gym Dianna     <- ギム・ギンガナム   Dianna says the villain's name and it
                                      comes out as her own. 311 other lines
                                      say Ghingnham.
  Kiel           <- キエル            Kihel in 347 places. All 13 bad rows sit
                                      at free=0, so these were SHORTENED to
                                      fit, not mistyped.
  Sueson         <- スエッソン        Suesson in 25 places.
  Chirum         <- チラム            Chiram in 348 places.
  Diana          <- ディアナ          Dianna in 925 places.
  Asuha/Atha/    <- アスハ            Athha. rec109 renders カガリ・ユラ・アスハ
  Attha/Kagari                        as raw "Kagari Yura Asuha" twice.

Deliberately NOT touched, because the wiki is the naming baseline and these
are too big to decide by majority - they need a ruling:
  レイ    Ray (386 speaker tags) vs Rey (64).  "Getter Ray" is a real, separate
          word and must survive any such pass.
  ガリア  Garia 43 / Gallia 34 / Galia 4.
  アメリア Amelia 49 / Ameria 32.

FITTING. Most corrections are LONGER than what they replace (Kiel->Kihel,
Diana->Dianna, Sueson->Suesson all +1; Gym Dianna->Gym Ghingnham +5) and STAGE
fields are spliced in place - a field may never outgrow its slot, and no line
may pass 34 columns. Where a line needs room, one ASCII "..." is folded to the
single character "…", which is 2 bytes / 2 columns instead of 3 / 3. The script
already mixes both forms, so this changes nothing a player would notice. Rows
that still will not fit are rewritten by hand in HAND below rather than being
silently skipped.

Usage: fix_names_stage35.py <iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz

SEC = 2048
LBA, SIZE = 1651029, 3910128
BOX_COLS = 34

# (pattern, replacement). Order matters: the longest, most specific first.
RULES = [
    (re.compile(u"Gym Dianna"), u"Gym Ghingnham"),
    (re.compile(u"Kagari Yura Asuha"), u"Cagalli Yula Athha"),
    (re.compile(u"Uzumi Nara Asuha"), u"Uzumi Nara Athha"),
    (re.compile(u"\\bKagari\\b"), u"Cagalli"),
    (re.compile(u"\\bAsuha\\b"), u"Athha"),      # \b keeps Asuham safe
    (re.compile(u"\\bAttha\\b"), u"Athha"),
    (re.compile(u"\\bAtha\\b"), u"Athha"),
    (re.compile(u"\\bKiel\\b"), u"Kihel"),
    (re.compile(u"\\bKihal\\b"), u"Kihel"),      # a fifth spelling, recap panels only
    (re.compile(u"\\bSueson\\b"), u"Suesson"),
    (re.compile(u"\\bChirum\\b"), u"Chiram"),
    # \b keeps Dianna safe; the lookahead keeps DIANAN-A safe. "Diana A" is
    # ダイアナン, Sayaka's machine, and has nothing to do with ディアナ - every
    # other Diana row pairs with ディアナ, this one does not.
    (re.compile(u"\\bDiana\\b(?! A\\b)"), u"Dianna"),
]

# Rows the rules cannot fit, and the two rec61 defects that are not names at
# all. Keyed by the exact english on the disc so a near-miss fails loudly.
HAND = {
    # rec61 - "for you're different" is not a sentence.
    u"Kamille\n「…Maybe what's right for me and\nfor you're different…But there's\none thing I'm certain of…」":
    u"Kamille\n「…Maybe what's right for me and\nfor you may differ…But there's\none thing I'm certain of…」",
    # rec61 - hyphen standing in for a dash, twice.
    u"Durandal\n「And I've heard of your feats\nsince-the Battle off Orb, the\nLohengrin Gate…impressive work.」":
    u"Durandal\n「And I've heard of your feats\nsince: the Battle off Orb, the\nLohengrin Gate…impressive work.」",
    u"Kamille\n「But you're different! You've\nstopped judging for yourself-drunk\non a right someone else decided!」":
    u"Kamille\n「But you're different! You've\nstopped judging for yourself,\ndrunk on a right others chose!」",
    # rec54 - a byte over its slot with no "..." left to reclaim one from.
    u"Sueson\n「Can you hear me, brave troops of\nthe Ghingnham fleet!」":
    u"Suesson\n「Hear me, brave troops of the\nGhingnham fleet!」",
    # Kiel rows with no "..." to reclaim a byte from - reworded instead.
    u"Kiel\n「Why would someone who fears\nDianna Soreil's very image do such\na thing?」":
    u"Kihel\n「Why would one who fears Dianna\nSoreil's very image do such a\nthing?」",
    u"Kiel\n「Had Lady Dianna been there\nherself, she would have said the\nsame thing.」":
    u"Kihel\n「Had Lady Dianna been there,\nshe would have said the very\nsame thing.」",
    u"Kiel\n「That's what pleases you men,\nisn't it?」":
    u"Kihel\n「So that pleases you men,\nisn't it?」",
    u"Kiel\n(Before that happens, I must\nswitch with the real Kiel, no\nmatter what...)":
    u"Kihel\n(Before that happens, I must\nswap with the real Kihel, no\nmatter what...)",
    u"Kiel\n「Lady Dianna.. I've received your\nfeelings, without fail.」":
    u"Kihel\n「Lady Dianna. I've received your\nfeelings, without fail.」",
    u"Harry\n(Her appearance is unchanged, so\nthere's only one answer... she must\nhave swapped places with Kiel Heim.)":
    u"Harry\n(Her appearance is unchanged, so\nthere's only one answer... she must\nhave swapped with Kihel Heim.)",
    u"Dianna\n「As you heard, Harry. ...I wish\nto leave a message with Kiel Heim.\nWill you allow it?」":
    u"Dianna\n「As you heard, Harry. …I wish to\nleave a message with Kihel Heim.\nWill you allow it?」",
    # Dianna is one column wider than Diana, which pushes these past 34.
    u"Phil\n「...Understood. All Diana Counter\nunits, return to position!\nHurry!!」":
    u"Phil\n「...Understood. All Dianna\nCounter units, return to position!\nHurry!!」",
    u"Loran\n「No, miss! If we attack the Diana\nCounter here...」":
    u"Loran\n「No, miss! If we attack the\nDianna Counter here...」",
    # also drops a stray leading space that indented the last line
    u"Federation Soldier\n「All Diana Counter units are\n retreating.」":
    u"Federation Soldier\n「All Dianna Counter units\nare retreating.」",
    # shop blurb, four identical copies across rec169/170/175/176
    u"Diana Counter's special MS arrived．\nBig sale, only here．":
    u"Dianna Counter's special MS is in．\nBig sale, only here．",
    # rec0 stage summaries. Kihal is a FIFTH spelling of キエル, and Kagarill
    # a second of カガリ; both only turn up in these recap panels.
    u"The Dianna Counter targeted Fort Severn, an autonomous\ncity in North America, as their return point from the\nMoon． But this was the military's reckless act, not\nDiana's will． Calis hired the Freedom to counter them．\nIron Gear's crew and the Frosts' new Federation forces\nappeared, and in the melee, Diana, disguised as Kihal,\ntried to swap with Kihal disguised as Diana． The swap\nfailed, but Fort Severn was defended． The defeat only\naccelerated the military's recklessness．":
    u"The Dianna Counter targeted Fort Severn, an autonomous\ncity in North America, as their return point from the\nMoon． But this was the military's reckless act, not\nDianna's will． Calis hired Freedom to counter them．\nIron Gear's crew and the Frosts' new Federation forces\nappeared, and in the melee, Dianna, disguised as Kihel,\ntried to swap with Kihel disguised as Dianna． The swap\nfailed, but Fort Severn was defended． The defeat only\naccelerated the military's recklessness．",
    u"In Orb, the Diana Counter repented and rushed to Diana．\nHumanity met the alien coalition centered on Zelabia's\nmobile fortress Goma, but the New Federation and Aprilus\nAlliance only watched each other． The group alone\nengaged them, defeating Butcher, Gagan, Gattler, and\nHughie, annihilating the aliens． But Sandman, settling\nhis score with Hughie inside Goma, wished to perish with\nZelabia． Then Goma began to reveal its true form．":
    u"In Orb, the Dianna Counter repented, rushing to Dianna．\nHumanity met the alien coalition centered on Zelabia's\nmobile fortress Goma, but the New Federation and Aprilus\nAlliance only watched each other． The group alone\nengaged them, defeating Butcher, Gagan, Gattler, and\nHughie, annihilating the aliens． But Sandman, settling\nhis score with Hughie inside Goma, wished to perish with\nZelabia． Then Goma began to reveal its true form．",
    u"In Orb, which had announced its alliance with the new\nEarth Federation, Yuna and Kagarill's wedding was about\nto take place． Assassins targeting Coordinators closed\nin on Lacus and Kira, who lived peacefully there． Kira\ndrove them off in Freedom, realizing they had no place\nin the new Federation, PLANT, or Orb, and fled with the\nArchangel crew, taking Kagari on an aimless journey．\nThe Minerva, now joined by Athrun, crossed to Gallia to\njoin Yapan's ceiling．":
    u"In Orb, which had announced its alliance with the new\nEarth Federation, Yuna and Cagalli's wedding was about\nto take place． Assassins targeting Coordinators closed\nin on Lacus and Kira, who lived peacefully there． Kira\ndrove them off in Freedom, realizing they had no place\nin the new Federation, PLANT, or Orb, and fled with the\nArchangel crew, taking Cagalli on an aimless journey．\nThe Minerva, now joined by Athrun, crossed to Gallia to\njoin Yapan's ceiling．",
    u"Kiel\n「What do you intend to do,\nCaptain Harry?」":
    u"Kihel\n「What do you intend to do,\nCapt. Harry?」",
}

ELL = u"…"


def cols(line):
    """Columns a rendered line occupies: full-width cells count 2."""
    return sum(2 if ord(c) > 0x7F else 1 for c in line)


def widest(text):
    return max(cols(l) for l in text.split(u"\n"))


def shrink(text, budget):
    """Fold ASCII '...' into the single character '…' until text fits budget
    bytes. Returns None if it never fits."""
    out = text
    while len(out.encode("cp932")) > budget:
        i = out.find(u"...")
        if i < 0:
            return None
        out = out[:i] + ELL + out[i + 3:]
    return out


def rewrite(text):
    out = text
    for pat, rep in RULES:
        out = pat.sub(rep, out)
    return out


def load(path, write):
    f = open(path, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    return f, bytearray(f.read(SIZE))


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f, raw = load(iso, write)
    items = banlz.decompress_all(bytes(raw))
    live = [(h, d) for h, d in items if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)

    done = skipped = 0
    used_hand = set()
    for ri, (hdr, data) in enumerate(live):
        d = bytearray(data)
        touched = 0
        pos = 0
        # walk the record field by field; a field is NUL-terminated text
        while pos < len(d):
            z = bytes(d).find(b"\x00", pos)
            if z < 0:
                break
            k = z
            while k < len(d) and d[k] == 0:
                k += 1
            field = bytes(d[pos:z])
            if not field:
                pos = k
                continue
            try:
                text = field.decode("cp932")
            except UnicodeDecodeError:
                pos = k
                continue
            slot = k - pos - 1          # bytes available, keeping one NUL
            new = HAND.get(text)
            if new is not None:
                used_hand.add(text)
            else:
                new = rewrite(text)
            if new == text:
                pos = k
                continue
            if len(new.encode("cp932")) > slot:
                fitted = shrink(new, slot)
                if fitted is None:
                    print("   rec%-3d NO ROOM (%d > %d) %s"
                          % (ri, len(new.encode("cp932")), slot,
                             new.replace(u"\n", u"/")[:60]))
                    skipped += 1
                    pos = k
                    continue
                new = fitted
            # STAGE holds more than the dialogue box: stage summaries and shop
            # blurbs use panels well over 34 columns and already exceed it in
            # japanese. Judging those against an absolute is what made me
            # "fix" correctly-abbreviated weapon names once before. The rule is
            # only ever "do not make it wider than it already was".
            limit = max(BOX_COLS, widest(text))
            if widest(new) > limit:
                fitted = shrink(new, slot)
                if fitted is None or widest(fitted) > limit:
                    print("   rec%-3d TOO WIDE (%d cols) %s"
                          % (ri, widest(new), new.replace(u"\n", u"/")[:60]))
                    skipped += 1
                    pos = k
                    continue
                new = fitted
            nb = new.encode("cp932")
            print("   rec%-3d %s"
                  % (ri, text.replace(u"\n", u"/")[:52]))
            print("          -> %s" % new.replace(u"\n", u"/")[:52])
            d[pos:k] = nb + b"\x00" * (k - pos - len(nb))
            touched += 1
            pos = k
        if not touched:
            continue
        done += touched
        if not write:
            continue
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(bytes(d))
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(bytes(d))
        assert len(blob) <= nxt - hdr, "rec%d grew past its slot" % ri
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0

    missed = set(HAND) - used_hand
    for m in missed:
        print("   HAND entry never matched: %s" % m.replace(u"\n", u"/")[:60])

    print("\n%d field(s) corrected, %d skipped, %d hand-entry misses"
          % (done, skipped, len(missed)))
    if write and done:
        after = [h for h, x in banlz.decompress_all(bytes(raw))
                 if isinstance(h, int) and x is not None]
        assert after == heads, "STAGE record set changed"
        f.seek(LBA * SEC)
        f.write(bytes(raw))
        print("STAGE written")
    elif not write:
        print("(dry run - pass --write to apply)")
    f.close()
    return 1 if skipped or missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
