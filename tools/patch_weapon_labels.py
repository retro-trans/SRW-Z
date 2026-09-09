# -*- coding: utf-8 -*-
u"""Translate the weapon-panel labels the compiler inlined into MIPS code.

Four labels on the weapon panel are not text on the disc. The compiler
inlined them: each four bytes are carried in a lui/ori immediate pair and
stored into the display struct with an unaligned swl/swr pair, so
"格闘武器（　　）" exists only as sixteen bytes spread over eight
instruction immediates. No byte search of either disc image or of EE RAM
finds them - the sole contiguous copy is the one the routine writes at
runtime, which is why they survived every previous ELF text pass while
their siblings (MAP weapon, ALL weapon, PLA weapon, Beam weapon) were
translated years ago: those live in the normal string table at 0x443A40
and this routine strcpy's them in.

  +0x0e  weapon class      格闘武器（　　） / 射撃武器（　　）
  +0x30  weapon attribute  通常武器, and a dead 合体・ prefix

The empty full-width parens are padding - nothing in the routine ever
writes inside them - so the english drops them and uses the freed bytes
for the whole word, matching "MAP weapon" and friends.

Three of the four keep the original instruction layout and only change
imm16 fields, so nothing moves. 通常武器 needs one extra word: its branch
took the second half from $s0 (loaded as 武器 by whichever class branch
ran), which cannot stay shared once the two class labels differ. That
branch has six slots and a spare nop, so it is rebuilt to load both words
itself; its explicit terminator is dropped because "Normal" carries its
own NUL inside the second word.

No byte in any replacement lands in 0x2E-0x3D - those are control codes
to the menu blit, which is why none of these labels can use a digit or a
colon. See the halfwidth-digits note.

Entries carry the original and the patched word, so the tool is
idempotent, re-runnable on any ELF generation, and revertible.

Usage: patch_weapon_labels.py <iso> [--revert] [--check]
"""
import struct
import sys

VA2F = 0x1AD80          # file offset = va - VA2F  (ELF LBA 455)
V0, V1, A0, S0, S4 = 2, 3, 4, 16, 20


def lui(rt, imm):
    return 0x3C000000 | (rt << 16) | (imm & 0xffff)


def ori(rt, rs, imm):
    return 0x34000000 | (rs << 21) | (rt << 16) | (imm & 0xffff)


def addiu(rt, rs, imm):
    return 0x24000000 | (rs << 21) | (rt << 16) | (imm & 0xffff)


def sw(rt, off, rs):
    return 0xAC000000 | (rs << 21) | (rt << 16) | (off & 0xffff)


def words(text, n):
    u"""Pad `text` to n 4-byte words and return them as little-endian ints."""
    b = text.encode('cp932')
    if len(b) > n * 4:
        raise SystemExit('%r is %d bytes, budget %d' % (text, len(b), n * 4))
    b = b.ljust(n * 4, b' ')
    return [struct.unpack_from('<I', b, i * 4)[0] for i in range(n)]


# --- the class field, $s4+0x0e, 16 bytes, terminator already at +0x1e ----
def class_site(name, jp, en, va0, va1, va2, va3, jw):
    u"""Eight immediates: lui/ori into $v1, $s0, $v1, $v0."""
    w = words(en, 4)
    return (name, jp, en, [
        (va0[0], lui(V0, jw[0] >> 16),   lui(V0, w[0] >> 16)),
        (va0[1], ori(V1, V0, jw[0]),     ori(V1, V0, w[0])),
        (va1[0], lui(V0, jw[1] >> 16),   lui(V0, w[1] >> 16)),
        (va1[1], ori(S0, V0, jw[1]),     ori(S0, V0, w[1])),
        (va2[0], lui(V0, jw[2] >> 16),   lui(V0, w[2] >> 16)),
        (va2[1], ori(V1, V0, jw[2]),     ori(V1, V0, w[2])),
        (va3[0], lui(V0, jw[3] >> 16),   lui(V0, w[3] >> 16)),
        (va3[1], ori(V0, V0, jw[3]),     ori(V0, V0, w[3])),
    ])


MELEE = class_site(
    'class melee', u'格闘武器（　　）', u'Melee weapon',
    (0x390078, 0x390080), (0x390088, 0x39008C),
    (0x390098, 0x39009C), (0x3900A8, 0x3900B0),
    words(u'格闘武器（　　）', 4))
RANGED = class_site(
    'class ranged', u'射撃武器（　　）', u'Ranged weapon',
    (0x3900D0, 0x3900D4), (0x3900D8, 0x3900E0),
    (0x3900E8, 0x3900F0), (0x3900F8, 0x390100),
    words(u'射撃武器（　　）', 4))

# --- the attribute field, $s4+0x30 --------------------------------------
_cw = words(u'Combo', 2)
COMBO = ('attr combo', u'合体・', u'Combo', [
    # dead on every path we can trace (always overwritten by "Combo" or by
    # a strcpy from the 0x443A40 table) - translated anyway, it is free
    (0x390134, lui(V0, 0xcc91),        lui(V0, _cw[0] >> 16)),
    (0x390138, addiu(V1, 0, 0x4581),   addiu(V1, 0, _cw[1] & 0xffff)),
    (0x39013C, ori(A0, V0, 0x878d),    ori(A0, V0, _cw[0])),
])

_nw = words(u'Normal\x00', 2)
NORMAL = ('attr normal', u'通常武器', u'Normal', [
    (0x390290, lui(V0, 0xed8f),        lui(V0, _nw[0] >> 16)),
    (0x390294, ori(V0, V0, 0xca92),    ori(V0, V0, _nw[0])),
    # was sw $s0,52($s4) - $s0 held 武器, shared with the class branches
    (0x39029C, sw(S0, 0x34, S4),       lui(V0, _nw[1] >> 16)),
    # was sb $zero,56($s4) - the NUL now rides inside the second word
    (0x3902A0, 0xA2800038,             ori(V0, V0, _nw[1])),
    # was a nop
    (0x3902A4, 0x00000000,             sw(V0, 0x34, S4)),
])

SITES = [MELEE, RANGED, COMBO, NORMAL]


def main():
    iso = sys.argv[1]
    revert = '--revert' in sys.argv
    check = '--check' in sys.argv
    f = open(iso, 'rb' if check else 'r+b')
    bad = 0
    for name, jp, en, edits in SITES:
        have = []
        for va, orig, new in edits:
            f.seek(va - VA2F)
            have.append(struct.unpack('<I', f.read(4))[0])
        want = [e[2] for e in edits] if not revert else [e[1] for e in edits]
        cur = [e[1] for e in edits] if not revert else [e[2] for e in edits]
        if have == want:
            print(u'  %-14s already %s' % (name, u'japanese' if revert else en))
            continue
        if have != cur:
            print(u'  %-14s UNRECOGNISED - not touching it' % name)
            for (va, o, n), h in zip(edits, have):
                if h not in (o, n):
                    print(u'      %#08x is %08x, expected %08x' % (va, h, o))
            bad += 1
            continue
        if check:
            print(u'  %-14s NOT PATCHED (%s)' % (name, jp))
            bad += 1
            continue
        for (va, _o, _n), w in zip(edits, want):
            f.seek(va - VA2F)
            f.write(struct.pack('<I', w))
        print(u'  %-14s %s -> %s' % (name, jp, jp if revert else en))
    f.close()
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
