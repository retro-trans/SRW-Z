"""Byte-budget-safe in-place patcher.

Replaces a string at a known offset with new text, never exceeding the original
byte length. This needs no pointer rewriting at all, so it is safe on any file
including the boot ELF -- nothing downstream shifts.

Two encodings are supported because it is not yet verified which the game's
font can render:
    ascii     - half-width; compact, normal for translations
    fullwidth - maps A-Z/0-9/punct into the fullwidth block, which the game
                demonstrably renders (the original map names use it)
"""
import sys


def to_fullwidth(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == " ":
            out.append("　")
        elif 0x21 <= o <= 0x7E:
            out.append(chr(o + 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def encode(text, mode="ascii"):
    if mode == "fullwidth":
        text = to_fullwidth(text)
    if mode == "menuhw":
        # Same control-code problem as "menu" (0x2E-0x3D are commands in the
        # 0x13A290 reader), but solved with the HALF-WIDTH private glyphs
        # instead of the fullwidth forms: '.' and 0-9 have cells in the
        # patch_hwfont atlas, so emit those 2-byte private codes directly.
        # Costs the same 2 bytes and renders 12px instead of a 24px gap -
        # "Rudder 15" stops looking like "Rudder １５". The five characters
        # with no atlas glyph (/ : ; < =) fall back to fullwidth.
        # NOTE: 0x85xx is an UNASSIGNED cp932 row, so this branch has to build
        # bytes itself - the private codes cannot round-trip through str.
        from patch_hwfont import HW_MAP
        hw = dict(HW_MAP)
        out = bytearray()
        for ch in text:
            o = ord(ch)
            if 0x2E <= o <= 0x3D and o in hw:
                out += bytes([hw[o] >> 8, hw[o] & 0xFF])
            elif 0x2E <= o <= 0x3D:
                out += chr(0xFF00 + o - 0x20).encode("cp932")
            else:
                out += ch.encode("cp932")
        return bytes(out)
    if mode == "menu":
        # Menu/system strings (drawn by the 0x13A290 reader): byte values
        # 0x2E-0x3D are CONTROL CODES there (./0-9:;<=), so those characters
        # must be encoded as their fullwidth forms; ASCII letters stay 1 byte
        # (the MHOOK pair-remap in patch_hwfont renders them half-width).
        out = []
        for ch in text:
            o = ord(ch)
            if 0x2E <= o <= 0x3D:
                out.append(chr(0xFF00 + o - 0x20))     # fullwidth form
            else:
                out.append(ch)
        text = "".join(out)
    return text.encode("cp932")


class Patcher(object):
    def __init__(self, data):
        self.data = bytearray(data)
        self.applied = 0
        self.skipped = []

    def replace(self, offset, original_bytes, new_text, mode="ascii", pad=b"\x00"):
        """Overwrite the string at `offset`. `original_bytes` is the byte
        length of the original string (not counting its terminator)."""
        try:
            enc = encode(new_text, mode)
        except UnicodeEncodeError as e:
            self.skipped.append((offset, new_text, "unencodable: %s" % e))
            return False
        if len(enc) > original_bytes:
            self.skipped.append(
                (offset, new_text, "too long: %d > %d bytes" % (len(enc), original_bytes)))
            return False
        self.data[offset:offset + original_bytes] = enc + pad * (original_bytes - len(enc))
        self.applied += 1
        return True

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.data)

    def report(self):
        print("  applied: %d" % self.applied)
        if self.skipped:
            print("  SKIPPED: %d" % len(self.skipped))
            for off, txt, why in self.skipped[:15]:
                print("    0x%08X  %-40s %s" % (off, txt[:40], why))
