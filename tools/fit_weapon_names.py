# -*- coding: utf-8 -*-
"""Shorten weapon names that no longer fit the weapon-list column.

THE COLUMN SHOWS 17 HALF-WIDTH CHARACTERS, 221px. Measured off a screenshot
of Super Gundam: "Beam Rifle (Rapid)" is 18 characters and renders as "Beam
Rifle (Rapid" - the closing bracket is gone entirely, a whole character lost,
not a clipped sliver. "１４ Twin Missile Pod" loses its "d" the same way.
ビーム・ライフル（連射） is 12 full-width at 19px = 228px, so the japanese sits
just at the edge too; english simply has no room above 17 characters.

Do NOT use verify_ui_width.py's 21px full-width here; this panel advances 19px,
the same as the help book. And remember that '.' and the digits encode
FULL-WIDTH (they are control codes to this reader), so a full stop costs 19px,
not 13 - "Mega P. Gun" is barely cheaper than "Mega Particle Gun".

Pairing is by POINTER TABLE, not by offset or index: COMPDATA is repacked, so
the pools do not line up, but the pointer WORD POSITIONS do. That gives 9481
shared positions and an exact japanese/english pair for every name.

Only names that FIT IN JAPANESE and overflow in english are touched - those are
regressions. A handful of battleship weapons are over budget in japanese too
and are left exactly as they are.

Usage: fit_weapon_names.py <iso> [--write]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import patch_compdata as pc
import pool

SEC = 2048
JP_LBA, JP_SECTORS = 1568198, 80
EN_LBA, EN_SECTORS = 1823000, 400
WLO, WHI = 0x66380, 0x6C000
COL = 221


def px(s, F=19, H=13):
    return sum(F if ord(c) > 127 else H for c in s)


# Applied in order, only while the name is still over budget. Each is a
# contraction the game itself already uses somewhere, not an invention.
LADDER = [
    (" (Rapid)", " (R)"),
    (" (Wild)", " (W)"),
    ("(Rapid)", "(R)"),
    ("(Wild)", "(W)"),
    (" (Shotgun)", " (SG)"),
    ("High-Energy ", "HE "),
    ("Anti-Air ", "AA "),
    ("Electromagnetic ", "EM "),
    ("Ultra-Vibration", "U-Vibration"),
    ("Mega Particle Cannon", "Mega Particle Gun"),
    ("Particle Cannon", "Particle Gun"),
    ("Machine Gun", "MG"),
    ("Missile Launcher", "Missile Lnchr"),
    ("Projection System", "Projector"),
    ("Manipulator", "Manip"),
    ("Incendiary Shell Cannon", "Incendiary Cannon"),
    ("All-Out Attack", "All Atk"),
    ("Semi-Fixed", "Semi-Fix"),
    ("Dual-Phase Energy Cannon", "Dual-Phase Cannon"),
    ("Beam Assault Craft", "Beam Aslt Craft"),
    ("Guided Mobile Beam Turret System", "Guided Beam Turrets"),
    (" Cannon", " Gun"),
    (" Missile", " Msl"),
    ("Graviton", "Grav"),
    ("Boomerang", "Boomrang"),
    ("Launcher", "Lnchr"),
    ("Shoulder", "Shldr"),
    ("Satellite", "Satellt"),
    ("Spazer", "Spzr"),
    ("Barrage", "Barrge"),
    ("Attack", "Atk"),
    ("Bullet", "Blt"),
    ("Full Power", "Full Pwr"),
    ("Full Burst", "Full Brst"),
    ("Launch", "Lnch"),
    ("Assault", "Aslt"),
    ("Pressure", "Press"),
    ("Combination", "Combo"),
    ("Tomahawk", "Tmhawk"),
    ("Mazinger", "Mazingr"),
    ("Long Range", "LongRng"),
    ("Vegatron", "Vegatrn"),
    ("(NT-use)", "(NT)"),
    ("Dringing", "Dring"),
    ("Crusher", "Crshr"),
    ("Spiral", "Sprl"),
    ("Charge", "Chrg"),
    ("Walker Gallia", "W-Gallia"),
    ("Scissors", "Scissor"),
    ("Buster", "Bstr"),
    ("Cylinder", "Cylndr"),
    ("Homing", "Homng"),
    ("Grenade", "Grenad"),
    ("Rocket", "Rckt"),
    ("Double", "Dbl"),
    ("Triple", "Tri"),
    ("Vulcan", "Vulcn"),
    ("Particle", "Prtcl"),
    ("Beam ", "Bm "),
]

# Where the ladder cannot get there without mangling the name, say it outright.
MANUAL = {
    # Sized to 221px. Remember digits and '.' cost 19px, not 13.
    "Diffuse Mega Particle Cannon": "Diffuse Mega Gun",
    "Toroidal Mega Particle Cannon": "Toroidal Mega Gun",
    "Anti-Ship Beam Cannon":     "Anti-Ship Beam",
    "Beam Assault Craft":        "Beam Aslt Craft",
    "Beam Assault Craft (Rapid)": "Beam Aslt Crft(R)",
    "Sigma Breast Musou Sword":  "Sigma Brst Musou",
    "High Mega Particle Cannon": "High Mega Cannon",
    "Mega Particle Cannon":      "Mega Particle Gun",
    "Mega Particle Cannon (Rapid)": "Mega Prtcl Gun(R)",
    "Mobile Suit All-Out Attack": "MS All-Out Attack",
    "Mid-Range Laser Cannon":    "Mid-Range Laser",
    "Low-Recoil Cannon (Rapid)": "Low-Recoil Gun(R)",
    "Full-Power Bombardment":    "Full Bombardment",
    "Twin-Blade Beam Saber":     "Twin-Blade Saber",
    "Anti-Gravity Storm":        "Anti-Grav Storm",
    "Vampiric Silver Cross":     "Vamp Silver Cross",
    "Left-Arm Semi-Fixed Cutter": "L-Arm Fix Cutter",
    "Hissatsu Musou Sword":      "Hissatsu Musou",
    "Moonlight Butterfly":       "Moonlight Btrfly",
    "Mobile Armament Pod":       "Mobile Arms Pod",
    "Hyakki Great Typhoon":      "Hyakki Gt Typhoon",
    "Hyakki Fighter Volley":     "Hyakki Fghtr Atk",
    "Destruction Ray (Wild)":    "Destruct Ray (W)",
    "Particle Laser (Rapid)":    "Particle Laser(R)",
    "Charged Particle Cannon":   "Charged Particle",
    "Ultra-Vibration Crusher":   "U-Vibr Crusher",
    "Electric Discharge":        "Electric Dischg",
    "High-Output Beam Cannon":   "High-Output Beam",
    "Triple Trapulsar Cannon":   "Tri Trapulsar Gun",
    "Trapulsar Cannon Volley":   "Trapulsar Volley",
    "Big Wheel Rocket Punch":    "Big Wheel Punch",
    "Drill Pressure Punch":      "Drill Press Punch",
    "Sun Attack Wild Shot":      "Sun Attack (W)",
    "Black Southern Cross":      "Black South Cross",
    "Scorching Fire Gaol":       "Scorching Fire",
    "Cutting Manipulator":       "Cutting Manip",
    "Chogokin NZ Fragment":      "Chogokin NZ Frag",
    "Graviton Criticality":      "Graviton Critical",
    "Reverse Psychic Blast":     "Rev Psychic Blast",
    "Promised Millennium":       "Promised Millenn",
    u"Super ３D Mugen Punch":  u"Super ３D Punch",
    u"２ Twin Linear Gun":     "Twin Linear Gun",
    u"GAU１１１ Single Cannon": u"GAU１１１ Sgl Gun",
    u"MA-M９２ Zanki Blade": u"MA-M９２ Zanki Bld",
    u"Mk３９ Low-Recoil Cannon": u"Mk３９ Low-Recoil",
    u"Mk３９ Low-Recoil Gun (Rapid)": u"Mk３９ LowRecoil(R)",
    u"Mk３９ Low-Recoil Cannon (Rapid)": u"Mk３９ LowRecoil(R)",
}


def shorten(name, budget=COL):
    if name in MANUAL and px(MANUAL[name]) <= budget:
        return MANUAL[name]
    out = name
    for a, b in LADDER:
        if px(out) <= budget:
            break
        if a in out:
            out = out.replace(a, b)
    return out


def load(path, lba, secs):
    f = open(path, "rb")
    f.seek(lba * SEC)
    d = bytes(banlz.decompress_all(f.read(secs * SEC))[0][1])
    f.close()
    ent = pool.entries(d)
    return d, {o: t for o, t, _ in ent}, pool.pointers(d, set(o for o, _, _ in ent))


def dec(b):
    try:
        return b.decode("cp932")
    except Exception:
        return None


def main():
    iso = sys.argv[1]
    write = "--write" in sys.argv
    _, tj, pj = load("iso/srwz.bin", JP_LBA, JP_SECTORS)
    _, te, pe = load(iso, EN_LBA, EN_SECTORS)
    mj = {wp: t for wp, t in pj}
    me = {wp: t for wp, t in pe}

    pairs = set()
    for wp in set(mj) & set(me):
        o = mj[wp]
        if not (WLO <= o < WHI):
            continue
        a, b = dec(tj.get(o, b"")), dec(te.get(me[wp], b""))
        if not a or not b or "\n" in a or "\n" in b:
            continue
        # Item DESCRIPTIONS share this offset range with the names. They end in
        # a full stop and are drawn in a different, much wider panel, so they
        # must not be shortened to a weapon column they never appear in.
        if a.endswith(u"。") or b.endswith(u"．") or b.endswith("."):
            continue
        pairs.add((a, b))

    # Target the COLUMN, not the japanese. The two names in the report that
    # started this - Beam Rifle (Rapid) and １４ Twin Missile Pod - have
    # japanese that is ALSO over 221px, so a "fits in japanese" filter skips
    # exactly the ones on screen. Anything wider than the column is clipped,
    # whichever language put it there.
    # The standard is NEVER WIDER THAN THE JAPANESE IT REPLACED. Targeting the
    # 221px column alone is wrong: a quarter of the names are over it in
    # japanese too ("Sol Graviton Spiral Crusher Punch" is 399px), so this
    # game clips long attack names as a matter of course. But the two names in
    # the report ARE worse than their japanese - Beam Rifle (Rapid) is 234
    # against 228, １４ Twin Missile Pod is 259 against 228 - and that is the
    # part we put right.
    # BOTH conditions. Over the 221px column, so it is actually clipped on
    # screen, AND wider than the japanese it replaced, so the clipping is our
    # doing. Either alone is wrong: a quarter of the names are over the column
    # in japanese too and clip as designed (ソルグラヴィトンスパイラルクラッシャー
    # パンチ is 399px), while "Ion Cannon" at 91px is wider than イオン砲 by
    # 15px and clipped by nothing at all.
    plan, stuck = [], []
    for a, b in sorted(pairs):
        if px(b) <= COL or px(b) <= px(a):
            continue
        budget = max(COL, px(a))
        n = shorten(b, budget)
        if px(n) > budget:
            stuck.append((b, n, px(n)))
        elif n != b:
            plan.append((b, n))

    print("english wider than its japanese: %d"
          % len([1 for a, b in pairs if px(b) > px(a)]))
    print("shortened  : %d" % len(plan))
    print("still over : %d" % len(stuck))
    for b, n, w in stuck:
        print("   %4dpx %-32s -> %s" % (w, b, n))
    if "--list" in sys.argv:
        for b, n in plan:
            print("   %-34s -> %-30s %dpx" % (b, n, px(n)))

    if not write:
        print("\n(dry run - pass --write to apply)")
        return 0

    f = open(iso, "r+b")
    f.seek(EN_LBA * SEC)
    raw = bytearray(f.read(EN_SECTORS * SEC))
    items = banlz.decompress_all(bytes(raw))
    heads = sorted(h for h, dd in items if isinstance(h, int) and dd is not None)
    hdr = heads[0]
    d = bytearray(items[0][1])
    n = 0
    for old, new in plan:
        n += pc.field_replace(d, old, new, 0, len(d), None)
    print("\n%d field(s) replaced" % n)
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
    f.seek(EN_LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print("COMPDATA written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
