# -*- coding: utf-8 -*-
"""Weapon names left as romaji, squashed, or spelled three different ways.

Reported from a screenshot of Virgola Glory's weapon list. The trigger was
ストレイターレット, which shipped under THREE spellings at once:

    ストレイターレット          Straight Turret
    レイ・ストレイターレット     Ray Straight Turret
    ブイ・ストレイターレット     Vee Straiterlet
    ハイ・ストレイターレット     High Sutoreitaretto     <- raw romaji

The reading is ストレイ + ターレット = "Stray Turret". It is NOT ストレート,
which is how "straight" is written, so "Straight Turret" was a misreading.
ブイ is the letter V, not the phonetic "Vee".

HOW THE REST WERE FOUND. The pools cannot be paired by offset or index -
COMPDATA is repacked, so the same address range holds 969 english fields
against 789 japanese ones, and aligning by index is what produced a fake
off-by-one before. Instead each name's EFFECTIVE value is resolved by asking
the disc which candidate is actually present, then the english is compared
against a romanisation of its own katakana. A translation diverges from the
romaji; a transliteration does not. That flagged 11, of which Kerberos,
Nefertem, Tristan, Sol Graviton Nova, Gagundura, Jinba and Zeraviton Sword
are correct names that merely look like romaji, and four were real.

WIDTH. These are all comfortably inside the column. The weapon-name column is
wide - a normal unit ships a 483px name ("High-Energy Cannon Aufprall
Dreizehn") - so the per-name japanese width that verify_ui_width.py uses is the
wrong budget here; it is right for a fixed-position UI fragment, not for a
list column sized once for the whole list. Every replacement below is still
kept at or under the width of the name it replaces.

Usage: fix_weapon_names.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import patch_compdata as pc

SEC = 2048
COMPDATA_LBA, COMPDATA_SECTORS = 1823000, 400
SRVC_LBA, SRVC_SECTORS = 1313214, 1700

WEAPONS = {
    # ストレイターレット, one spelling for all four
    "Straight Turret":      "Stray Turret",
    "Ray Straight Turret":  "Ray Stray Turret",
    "Vee Straiterlet":      "V Stray Turret",
    "High Sutoreitaretto":  "High Stray Turret",
    # left as romaji by the original pass
    "Ranbu Ring Disukyariba": "Rambling Discalibur",   # ランブリング・ディスキャリバー
    "Bit Rasuveto":           "Bit Rassvet",           # ビット・ラスヴェート
    "Banreon Grap Ru":        "Burn Leon Grapple",     # バーン・レオン・グラップル
    # squashed to fit a budget that was never the real one
    "Dif．MegaP．Gun":        "Diffuse Mega Particle Gun",   # 拡散メガ粒子砲
    "Toroidal MegaP．Gun":    "Toroidal Mega Particle Gun",  # トロイダル状防盾内蔵メガ粒子砲
    "AntiShip Beam":          "Anti-Ship Beam Cannon",       # 対艦用大型ビーム砲
    "BeamAsltCraft(R)":       "Beam Assault Craft (Rapid)",  # ビーム突撃機（連射）
}

# battle captions naming the attack aloud
CAPTIONS = {
    '"Ray Straight Turret, fire!!"': '"Ray Stray Turret, fire!!"',
    '"Ray Straight Turret, FIRE!!"': '"Ray Stray Turret, FIRE!!"',
}


def fix_compdata(f, write):
    f.seek(COMPDATA_LBA * SEC)
    raw = bytearray(f.read(COMPDATA_SECTORS * SEC))
    items = banlz.decompress_all(bytes(raw))
    # decompress_all appends an ERROR sentinel for the trailing bytes past the
    # last real record; its head is a string, so filter before sorting.
    heads = sorted(h for h, d in items if isinstance(h, int) and d is not None)
    hdr = heads[0]
    d = bytearray(items[0][1])
    n = 0
    for old, new in sorted(WEAPONS.items()):
        got = pc.field_replace(d, old, new, 0, len(d), None)
        flag = "" if got else "   <- NOT FOUND"
        print("   %-26s -> %-28s %d%s" % (old, new, got, flag))
        n += got
    if not write or not n:
        return n
    nxt = min([h for h in heads if h > hdr] or [len(raw)])
    blob = banlz.compress_record(bytes(d))
    if len(blob) > nxt - hdr:
        blob = banlz.compress_record_optimal(bytes(d))
    assert len(blob) <= nxt - hdr, "COMPDATA grew past its slot"
    raw[hdr:hdr + len(blob)] = blob
    for k in range(hdr + len(blob), nxt):
        raw[k] = 0
    after = [h for h, dd in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and dd is not None]
    assert after == heads, "record set changed"
    f.seek(COMPDATA_LBA * SEC)
    f.write(bytes(raw))
    return n


def fix_srvc(f, write):
    f.seek(SRVC_LBA * SEC)
    raw = bytearray(f.read(SRVC_SECTORS * SEC))
    n = 0
    for old, new in CAPTIONS.items():
        ob, nb = old.encode("cp932"), new.encode("cp932")
        assert len(nb) <= len(ob), "%r is longer than %r" % (new, old)
        i = 0
        while True:
            i = raw.find(ob, i)
            if i < 0:
                break
            # Hold the field's byte length. Scripted attack sequences are
            # fetched BY BYTE OFFSET from tables this tool does not rebuild,
            # so anything after this must not move.
            raw[i:i + len(ob)] = nb + b"\x00" * (len(ob) - len(nb))
            n += 1
            i += len(ob)
        print("   %-32s -> %s" % (old, new))
    if write and n:
        f.seek(SRVC_LBA * SEC)
        f.write(bytes(raw))
    return n


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    print("COMPDATA:")
    a = fix_compdata(f, write)
    print("SRVC:")
    b = fix_srvc(f, write)
    f.close()
    print("\n%d weapon field(s), %d caption(s)" % (a, b))
    if not write:
        print("(dry run - pass --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
