# -*- coding: utf-8 -*-
"""Weapon and attack names still shipping as raw romaji.

Keyed on the string CURRENTLY IN THE POOL, not on analysis/weapons_en.json -
that file is stale. A later fitting pass rewrote much of the pool (it already
holds "Tremble Horn", "Bandock Cannon", "Moon Ring", "Anti-Gravity Storm",
"Mega Particle Cannon"), so auditing the json reports ~200 problems that were
fixed long ago and misses the ones that are real. The disc is the only
truthful source; these were found by sweeping the pool itself.

Model numbers on disc are already correct and use FULL-WIDTH digits, which is
the menu encoding doing its job - do not "fix" those.

Left alone deliberately: romanised BGM titles (Jiyuu o Motomete, Shinku no
Yakoudan), character names, and enemy unit names (Gorugoru, Dangarun), which
are romanised on purpose.

Usage: fix_weapon_romaji.py <iso> [--write]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import patch_compdata as pc

SEC = 2048
LBA, SECTORS = 1823000, 400
FW = u"０１２３４５６７８９"

NAMES = {
    # katakana that was transliterated instead of translated
    "Nyu Hyper Bazooka":          "New Hyper Bazooka",      # ニュー
    "Minchi Drill":               "Mince Drill",            # ミンチ
    "Vulcan Farankusu":           "Vulcan Phalanx",         # ファランクス
    "Burakkarifuru Power":        "Brackary Full Power",    # ブラッカリィ・フルパワー
    "Furosuto Combination":       "Frost Combination",      # フロスト
    "Triple Mega Sonikku Cannon": "Triple Mega Sonic Cannon",   # ソニック
    "Wire Do Beam Rifle":         "Wired Beam Rifle",       # ワイヤード
    "High Mattofuru Burst":       "Hi-MAT Full Burst",      # ハイマット・フルバースト
    "Mitiafuru Burst":            "METEOR Full Burst",      # ミーティア・フルバースト
    "Mitia Saber":                "METEOR Saber",           # ミーティア
    "Mekkusu Thunder":            "Mex Thunder",            # メックス
    "Mekkusu Thunder (Rapid)":    "Mex Thunder (Rapid)",
    "Big O Final Suteji":         "Big O Final Stage",      # ステージ
    "Lightning Detoneita":        "Lightning Detonator",    # デトネイター
    "G Guradiusu Attack":         "G Gladius Attack",       # グラディウス
    "Fire Fisuto":                "Fire Fist",              # フィスト
    "Parusu Beam":                "Pulse Beam",             # パルス
    "Parusa Shoot":               "Pulsar Shoot",           # パルサー
    "Parusa Rifle":               "Pulsar Rifle",
    "Parusa Rifle (Rapid)":       "Pulsar Rifle (Rapid)",
    "Busuto Slash":               "Boost Slash",            # ブースト
    "Naitomea Strike":            "Nightmare Strike",       # ナイトメア
    "Biku Cannon":                "Beak Cannon",            # ビーク
    "Za Heat Crusher":            "The Heat Crusher",       # ザ・
    "Dekka Spanner":              "Decker Spanner",         # デッカー
    # compounds that dropped the standalone's english (the bare form is
    # already Aldore / Tristan in the same pool)
    u"MGX-２２３７ Arudoru Dual-Phase Beam Cannon":
        u"MGX-２２３７ Aldore Dual-Phase Beam Cannon",
    u"XM４７ Tori Stun": u"XM４７ Tristan",
    u"３ Twin Toraparuza Cannon": "Triple Trapulsar Cannon",
}


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    f = open(iso, "r+b" if write else "rb")
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SECTORS * SEC))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, dd in items if isinstance(h, int) and dd is not None)
    hdr = heads[0]
    d = bytearray(items[0][1])

    # An earlier pass relocated some of these into the tail padding and
    # repointed; the text left at the old offset is dead bytes nothing names.
    # Rewriting those would change nothing on screen, so skip anything with no
    # pointer to it - that is also how we tell "already fixed" from "to fix".
    import pool
    starts = set(o for o, _, _ in pool.entries(bytes(d)))
    named = set(t for _, t in pool.pointers(bytes(d), starts))

    fits, grow, absent, orphan = [], [], [], []
    for old, new in sorted(NAMES.items()):
        ob = old.encode("cp932")
        i = bytes(d).find(ob)
        if i < 0:
            absent.append(old)
            continue
        if i not in named:
            orphan.append(old)
            continue
        z = bytes(d).find(b"\x00", i)
        k = z
        while k < len(d) and d[k] == 0:
            k += 1
        slot = k - i - 1
        (fits if len(new.encode("cp932")) <= slot else grow).append(
            (old, new, slot))

    n = 0
    for old, new, slot in fits:
        got = pc.field_replace(d, old, new, 0, len(d), None)
        print("   %-34s -> %-32s %d" % (old, new, got))
        n += got
    print("\nfits in slot : %d (%d replaced)" % (len(fits), n))
    print("needs grow   : %d  %s" % (len(grow), [g[0] for g in grow]))
    print("not on disc  : %d  %s" % (len(absent), absent))
    print("already fixed: %d  %s (orphaned, replacement lives in the tail)"
          % (len(orphan), orphan))

    if not write or not n:
        f.close()
        if not write:
            print("(dry run - pass --write to apply)")
        return 0

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
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("COMPDATA written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
