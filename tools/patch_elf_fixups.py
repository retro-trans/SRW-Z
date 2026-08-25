# -*- coding: utf-8 -*-
"""Apply post-hoc corrections to the UI-string ELF (hwbuild/base_ui3.elf).

base_ui3.elf is a prebuilt artifact, so edits to elf_ui_en.py / ui_batch*.py do
not regenerate it. This step re-applies the affected slots on top, in place and
size-safe, so the shipped executable matches the sources.

FIXUPS so far - character-select blood type. The field holds 2 fullwidth glyphs;
the renderer expands each ASCII char to a fullwidth cell, so "Type A" rendered
~3x too wide and overflowed the field. That HUNG the game when the MALE hero was
selected (0x347A38 set = male profile, 0x347AA8 set = female). Keeping the text
inside the original byte length fixes it.

Usage: patch_elf_fixups.py <in.elf> <out.elf>
"""
import sys

ORIG = r"E:\Projects\SRW Z\_work\hwbuild\orig.elf"

FIXUPS = {
    0x347A38: "A", 0x347A40: "B", 0x347A48: "AB", 0x347A50: "O",   # male
    0x347AA8: "A", 0x347AB0: "B", 0x347AB8: "AB", 0x347AC0: "O",   # female
    # Robot encyclopedia spec labels. Same width trap: 全長/重量 are 2 fullwidth
    # glyphs (4 half-width widths) and 登場作品 is 4, but "Length"/"Weight"/
    # "From series" render 6/6/11 half-width wide and overlapped their values.
    # Encyclopedia spec/detail labels. These sit immediately left of their value
    # at a FIXED x, so the label must not exceed the Japanese width or it draws
    # over the value. Remember the menu encoder emits '.' FULLWIDTH (2 columns),
    # so "Len." is 5 columns wide, not 4 - the trailing dot cost more than the
    # letter it saved.
    0x33E0C8: "Len",           # 全長 (4 cols)
    0x33E0D0: "Wt",            # 重量 (4 cols)
    0x33E0B8: "Series",        # 登場作品 (8 cols) - fits
    0x33E0E8: "Nick",          # 愛称 (4 cols) - "Alias" was 5 and overlapped
    0x342208: "Nick",          # 愛称 (second copy)
    0x33E0F0: "Cast",          # 声優 (4 cols) - "Voice" was 5 and overlapped
    # Squad-info panel. Label and value share a ROW here, so a label wider than
    # the Japanese draws straight over its own value - the panel showed
    # "CaptaiAdjacent allies dmg -10%" and "DEF%No ChangRegen0%".
    0x345340: "Captain",       # 艦長効果 (8) - "Captain Bonus" was 13
    0x345ED8: "Captain",       # 艦長効果 (second copy)
    0x344A18: "Leader",        # 隊長効果 (8) - "Leader Bonus" was 12
    0x345350: "Leader",
    0x345EE8: "Leader",
    0x346268: "Leader",
    0x345EB8: "No Chg",        # 変化無し (8) - "No Change" was 9, one column over
    0x3401D0: "Air",           # 空専用 (6) - "Air-use" was 7
    0x340350: "Air",
    0x3404B0: "Air",
    0x340610: "Air",
    # Battle-result popup. The value is right-aligned in the same box, so a long
    # label collides with it - "Funds Gained" (12 half-width columns vs the
    # Japanese 獲得資金's 8) drew straight through the amount ("Funds Gai8480").
    0x342FD8: "Funds",         # 獲得資金
    0x3432E8: "Funds",         # 獲得資金 (second result screen)
    # Pilot stat radar chart (Unit tab, top right). Each axis label is ONE
    # fullwidth kanji = 2 half-width columns, and the left-hand labels sit hard
    # against the chart circle - so these must stay 2 characters. They echo the
    # 3-letter codes used for the same stats on the Pilot tab (ACC/RNG/EVD/SKL/
    # DEF/CQB); going to 3 here would overlap the circle.
    0x345370: "AC",            # 命 = 命中 accuracy
    0x345378: "RN",            # 射 = 射撃 ranged
    0x345380: "EV",            # 回 = 回避 evasion
    0x345388: "SK",            # 技 = 技量 skill
    0x345390: "DF",            # 防 = 防御 defence
    0x345398: "CQ",            # 格 = 格闘 melee
}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    og = open(ORIG, "rb").read()
    data = bytearray(open(src, "rb").read())
    assert len(data) == len(og), "size mismatch"
    for off, en in FIXUPS.items():
        end = og.find(b"\x00", off)
        slot = end - off                     # original byte length, never exceed
        # Clear the whole padded slot, not just `slot` bytes: the input ELF may
        # already hold a LONGER English string here, and writing a shorter one
        # over it would leave the tail behind ("Length" -> "Len." + stray "th").
        k = end
        while k < len(og) and og[k] == 0:
            k += 1
        enc = en.encode("cp932")
        assert len(enc) <= slot, "%#x: %r > %d bytes" % (off, en, slot)
        data[off:k] = enc + b"\x00" * (k - off - len(enc))
        print("  %#08x %-8r (fits %d B, slot %d)" % (off, en, slot, k - off))
    open(dst, "wb").write(bytes(data))
    print("fixups applied: %d -> %s" % (len(FIXUPS), dst))


if __name__ == "__main__":
    main()
