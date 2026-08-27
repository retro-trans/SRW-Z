# -*- coding: utf-8 -*-
"""Generate the final weapon-name map (weapons_en.json) with slot fitting.

Pipeline: CANON lookup > vocabulary tokenizer > romaji fallback, then
model-number joining, duplicate-word cleanup, and budget fitting against
each slot using MENU encoding (digits/./:;= are 2-byte fullwidth). Names
that still exceed their slot go through ABBREV transforms, then SHORT_W
overrides; anything unresolved is reported and left Japanese.
"""
import json
import re
import sys

sys.path.insert(0, ".")
from weapon_words import CANON, WORDS

# U+3000 separates a model number from what follows ("ＧＡＵ２５Ａ　２０ミリ").
# weapon_words maps it to a plain space, which the run-joiner below cannot tell
# from a space it inserted itself - so it merged across it and produced
# "MMI-GAU25A20mm". Map it to a sentinel that is not alphanumeric, so the joiner
# treats it as a hard boundary, and restore it at the end of translate().
WORDS = dict(WORDS)
HARDSEP = ""
WORDS[u"　"] = HARDSEP
from kata_romaji import romanize
from patch import encode

KATA = re.compile(u"[\u30A0-\u30FF]")
keys = sorted(WORDS, key=len, reverse=True)

ABBREV = [
    ("Cannon Cannon", "Cannon"),
    ("Gun Gun", "Gun"),
    ("All-Out Attack", "Full Attack"),
    ("High-Energy", "HE"),
    ("Long-Range", "LR"),
    ("Electromagnetic", "EM"),
    ("Machine Gun", "MG"),
    ("Particle Cannon", "P.Cannon"),
    ("Autocannon", "AutoGun"),
    ("Cannon", "Gun"),
    ("Assault", "Aslt"),
    ("Missile", "Msl"),
    ("Launcher", "Lnchr"),
    ("Attack", "Atk"),
    ("Detachable Integrated-Control High-Speed Mobile Armament Group Network System", "DRAGOON System"),
]

SHORT_W = {
    "電撃放射": "Discharge",
    "火炎弾（連射）": "Flame (R)",
    "７６ミリ速射砲": "76mm RapidGun",
    "月光蝶": "M-Fly",
    "主砲": "Cannon",
    "副砲": "SubGun",
    "機銃": "MG",
    "機関砲": "AutoGun",
    "大剣": "GtSword",
    "電撃": "Shock",
    "爆雷": "D.Chg",
    "変形": "Morph",
    "盾装備": "Shield",
    "剣装備": "Sword",
    "海ヘビ": "Snake",
    "円月輪": "M.Ring",
    "星空剣": "StarSwd",
    "天使剣": "Angel",
    "光の槍": "LSpear",
    "手刀": "Chop",
    "隠し腕": "Arms",
    "無双剣": "MusouSw",
    "熱放射": "HeatRad",
    "火炎弾": "Flame",
    "荷粒子砲": "ChP.Gun",
    "メガ粒子砲": "MegaP.Gun",
    "拡散メガ粒子砲": "Dif.MegaP.Gun",
    "連装砲": "TwinGun",
    "低反動砲": "LR-Gun",
    "速射砲（連射）": "RapidGun (R)",
    "誘導機動ビーム砲塔システム": "Guided Beam Turrets",
    "毒ガス火炎": "GasFlame",
    "放電攻撃": "Discharge",
    "一斉砲撃": "Bombard",
    "反重力ストーム": "A-Grav Storm",
    "重力子臨界": "GravCrit",
    "逆念写爆破": "Rev.Psy.Blast",
    "無限交差拳": "MugenCrossFst",
    "嫉妬変性劍": "JealousySword",
    "超３Ｄ無限拳": "S.3D MugenFst",
    "不幸斷絶拳": "MisfortuneFst",
    "大ジャンプ突撃": "JumpCharge",
    "電磁ムチ": "EM Whip",
    "電磁ムチ連打": "EM Whip Barrage",
    "機動兵装ポッド": "Armament Pod",
    "ビーム突撃銃": "BeamAsltGun",
    "ビーム突撃機（連射）": "BeamAsltCraft(R)",
    "超ベガトロンビーム砲": "S.Vegatron Beam",
    "百鬼戦闘機一斉攻撃": "Hyakki Full Atk",
    "対艦用大型ビーム砲": "AntiShip Beam",
    "トロイダル状防盾内蔵メガ粒子砲": "Toroidal MegaP.Gun",
    "必殺無双剣": "Hissatsu Musou",
}


def translate(name):
    if name in CANON:
        return CANON[name]
    parts, i = [], 0
    while i < len(name):
        for k in keys:
            if name.startswith(k, i):
                parts.append(WORDS[k])
                i += len(k)
                break
        else:
            c = name[i]
            if KATA.match(c):
                j = i
                run = ""
                while j < len(name) and KATA.match(name[j]) and not any(
                        name.startswith(k, j) for k in keys if len(k) > 2):
                    run += name[j]
                    j += 1
                parts.append(romanize(run))
                i = j
            elif c in "０１２３４５６７８９":
                parts.append(chr(ord(c) - 0xFF10 + 0x30))
                i += 1
            elif c.isascii():
                parts.append(c)
                i += 1
            elif "Ａ" <= c <= "Ｚ":
                parts.append(chr(ord(c) - 0xFF21 + 0x41))
                i += 1
            elif "ａ" <= c <= "ｚ":
                parts.append(chr(ord(c) - 0xFF41 + 0x61))
                i += 1
            else:
                return None
    out = ""
    for p in parts:
        if out and out[-1].isalnum() and p[:1].isalnum():
            out += " "
        out += p
    out = " ".join(out.split())
    # Join model numbers. The tokenizer emits every fullwidth letter and digit
    # as its own token, so "ＭＭＩ－ＧＡＵ２５Ａ" arrives as "M M I - G A U 2 5 A".
    #
    # This used to pair them up with re.sub(r"\b(x) (x)\b"), which matches
    # NON-OVERLAPPING pairs: (M,M)(G,A)(U,2)(5,A) -> "MM I-GA U2 5A". The next
    # pass then cannot help, because nothing is a single character any more.
    # It shredded 77 model numbers - MMI-GAU25A, MA-BAR72, MMI-M633, M181SE.
    # Join whole RUNS of single tokens instead, then bind across the hyphen.
    out = re.sub(r"(?<![A-Za-z0-9])(?:[A-Za-z0-9] )+[A-Za-z0-9](?![A-Za-z0-9])",
                 lambda m: m.group(0).replace(" ", ""), out)
    # "MMI - GAU25A" -> "MMI-GAU25A". Only the hyphen itself; do NOT try to also
    # pull the following word in, or "MA-BAR72 High-Energy Beam Rifle" collapses
    # into one run-on token.
    out = re.sub(r"([A-Za-z0-9]) *- *([A-Za-z0-9])", r"\1-\2", out)
    out = re.sub(r"(\d) ?mm\b", r"\1mm", out)
    out = out.replace("Cannon Cannon", "Cannon").replace("Gun Gun", "Gun")
    out = " ".join(out.replace(HARDSEP, " ").split())
    return out


def fit(jp, en, budget):
    if len(encode(en, "menu")) <= budget:
        return en
    if jp in SHORT_W and len(encode(SHORT_W[jp], "menu")) <= budget:
        return SHORT_W[jp]
    cur = en
    for a, b in ABBREV:
        if a in cur:
            cur = cur.replace(a, b)
            if len(encode(cur, "menu")) <= budget:
                return cur
    return None


def main():
    entries = json.load(open(r"E:\Projects\SRW Z\_work\analysis\weapons_jp.json",
                             encoding="utf-8"))
    out, nofit = {}, []
    for x in entries:
        jp, budget = x["jp"], x["budget"]
        en = translate(jp)
        if not en:
            nofit.append((jp, "untranslated", budget))
            continue
        fitted = fit(jp, en, budget)
        if fitted:
            key = jp
            prev = out.get(key)
            if prev is None or len(fitted) < len(prev):
                out[key] = fitted
        else:
            nofit.append((jp, en, budget))
    json.dump(out, open(r"E:\Projects\SRW Z\_work\analysis\weapons_en.json", "w",
                        encoding="utf-8"), ensure_ascii=False, indent=0)
    print("final map: %d names, no-fit: %d" % (len(out), len(nofit)))
    for jp, en, b in nofit:
        print("  NOFIT %2d %s -> %s" % (b, jp, en))


if __name__ == "__main__":
    main()
