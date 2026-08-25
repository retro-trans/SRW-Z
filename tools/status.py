# -*- coding: utf-8 -*-
"""Translation state, measured from the BUILT ISO rather than from tool logs.

Counts what a player would actually see: for every text field in the shipped
image, is it English or still Japanese? Tool-side counts ("N rows applied") can
overstate coverage, because a row that fails its budget is skipped and silently
keeps its Japanese bytes.
"""
import os
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORK, "tools"))
import banlz

SEC = 2048
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "iso", "srwz_fix3.bin")


def is_jp(s):
    """Kana/kanji ONLY, and only for strings that are real text.

    Two traps this avoids, both of which produced badly wrong numbers earlier:
      - counting the fullwidth ASCII block (U+FF01-FF60) as Japanese flags our
        OWN English output as untranslated, because the SRVC encoder writes
        '．．．' for an ellipsis (11,170 false hits).
      - counting any string that merely decodes as Shift-JIS pulls in binary
        ('c逗', 'ｱ-逗'), which is how 519 DB structures looked like text.
    """
    if not any(u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿" for c in s):
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 and c != "\n":
            return False
        if 0xFF61 <= o <= 0xFF9F:          # halfwidth katakana = decoded noise
            return False
    # >=2 Japanese chars, no short-string exemption. Allowing a single kana/kanji
    # let 1,794 binary records through ('烝s', '@ピ', '0鋭', 'p郭') and reported
    # the pilot DB as 69% translated when every real string in it was done.
    nj = sum(1 for c in s if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿")
    return nj >= 2


def is_binary(s):
    """True for a string that only looks like text."""
    good = sum(1 for c in s
               if u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿"
               or 0x20 <= ord(c) < 0x7F or 0xFF01 <= ord(c) <= 0xFF60
               or c in u"　、。「」・ー…")
    return good / float(max(len(s), 1)) < 0.6


def walk(data, minlen=4):
    i = 0
    while i < len(data):
        j = data.find(b"\x00", i)
        if j < 0:
            break
        if j - i >= minlen:
            raw = bytes(data[i:j])
            try:
                yield i, raw.decode("cp932")
            except UnicodeDecodeError:
                pass
        i = j + 1


f = open(ISO, "rb")

# ---------- STAGE ----------
f.seek(1651029 * SEC)
stage = bytearray(f.read(3910128))
recs = banlz.decompress_all(stage)
work = set(int(x) for x in
           open(os.path.join(WORK, "analysis", "recs_all.txt")).read().split())

d_en = d_jp = h_en = h_jp = 0
jp_examples = []
for n, (off, data) in enumerate(recs):
    if n not in work:
        continue
    for o, s in walk(data):
        # a dialogue line is Speaker\n「…」 in Japanese but Speaker\n"…" once
        # translated - matching only 「 counts every English line as absent
        quote = ("\n" in s and (u"「" in s or '"' in s))
        head = (u"～" in s or u"〜" in s) and len(s) >= 6
        if not (quote or head):
            continue
        jp = is_jp(s)
        if head and not quote:
            if jp:
                h_jp += 1
            else:
                h_en += 1
        else:
            if jp:
                d_jp += 1
                if len(jp_examples) < 8:
                    jp_examples.append((n, o, s))
            else:
                d_en += 1

print("=" * 62)
print("SCENARIO DIALOGUE  (STAGE.BIN, %d records)" % len(work))
tot = d_en + d_jp
print("  lines English : %6d / %6d  (%.1f%%)" % (d_en, tot, 100.0 * d_en / tot))
print("  lines Japanese: %6d" % d_jp)
print("SCENE HEADERS")
th = h_en + h_jp
print("  English : %4d / %4d  (%.1f%%)" % (h_en, th, 100.0 * h_en / max(th, 1)))
print("  Japanese: %4d" % h_jp)

# ---------- COMPDATA ----------
f.seek(1823000 * SEC)
blob = bytearray(f.read(74 * SEC))
cd, _ = banlz.decompress_record(blob, 0)
# Sub-regions measured separately. Lumping 0x6C000-0x72000 together reported
# "unit names 33.8%" when it actually mixes THREE things: ability-description
# prose, the unit display-name list, and 641 BGM entries whose tail are
# per-character cue IDENTIFIERS (ランド２, ケイ１ＥＶ, トリノミアス) that must never
# be rewritten. Weapon names end at 0x6B8F0, not 0x6C000.
regions = [("pilots/db", 0x00000, 0x66380),
           ("weapons", 0x66380, 0x6B8F0),
           # description block runs to 0x6D0C0 (the entry AT 0x6D060 is one of
           # them); real unit names are 0x6D0C0..0x6EB60, after which come the
           # 予備N unused placeholder slots. Drawing the line at 0x6D060/0x6EB80
           # reported "98.5%" when every actual name was done.
           ("abil.desc", 0x6B8F0, 0x6D0C0),
           ("unit names", 0x6D0C0, 0x6EB60),
           ("BGM/cues", 0x6EBF0, 0x71C40),
           ("ep titles", 0x72DA0, 0x73800)]
print("=" * 62)
print("COMPDATA")
for label, lo, hi in regions:
    en = jp = 0
    for o, s in walk(cd[lo:hi], 3):
        if is_binary(s):
            continue                       # structure, not text - not countable
        if is_jp(s):
            jp += 1
        else:
            en += 1
    t = en + jp
    print("  %-11s English %5d / %5d  (%.1f%%)" % (label, en, t, 100.0 * en / max(t, 1)))

# ---------- SRVC ----------
# SRVC RELOCATES when it grows (it did, to 1826000), so read the LBA from the
# game's own file table rather than the original 1313214 - otherwise this
# measures a stale copy and reports the file as untranslated.
import struct
f.seek(0)
_boot = f.read(0x120000)
_k = _boot.find(b"\\\\BTL\\\\SRVC.BIN;1")
if _k >= 0:
    _lba, _nsec = struct.unpack_from("<II", _boot, _k + 0x28)
else:
    _lba, _nsec = 1313214, 1618
print("(SRVC at LBA %d, %d sectors)" % (_lba, _nsec))
f.seek(_lba * SEC)
srvc = f.read(_nsec * SEC)
en = jp = 0
for o, s in walk(bytearray(srvc), 4):
    if is_binary(s):
        continue
    if is_jp(s):
        jp += 1
    else:
        en += 1
print("=" * 62)
print("SRVC (battle voice lines)")
print("  English %6d / %6d  (%.1f%%)" % (en, en + jp, 100.0 * en / max(en + jp, 1)))
f.close()

print("=" * 62)
print("sample of dialogue still Japanese:")
for n, o, s in jp_examples:
    print("   rec%03d @0x%05X %r" % (n, o, s[:52]))
