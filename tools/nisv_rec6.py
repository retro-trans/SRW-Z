# -*- coding: utf-8 -*-
"""Parser for NISVDATA rec6 - the in-game help / tutorial book.

rec6 is NOT a flat string table.  A naive NUL-split appeared to chop
paragraphs mid-word because the renderer does no wrapping at all: the japanese
was pre-wrapped when the game was authored and every VISUAL LINE is its own
absolutely-positioned run.

    rec6    := u32 count ; u32 base ; entry[count] ; section...
    entry   := u32 offset (relative to `base`) ; u32 size
    section := u16 body_length ; run... ; NUL padding to `size`
    run     := u8 kind ; u8 attr ; u16 x ; u16 y ; u16 flag ; cp932 ; NUL

kind  2 = body text, 4 = heading/label
attr  0 = plain, 0x06 = title, 0x0e = keyword (drawn highlighted)

y advances by 11 per visual line.  A run continuing on the SAME line as the
one before it simply carries a larger x - which is how a highlighted keyword
sits inline in a sentence (keyword at x=38, remainder of the sentence at
x=190).

Because every section carries its own length prefix AND its size lives in the
index, a section can be re-laid-out and even resized when we translate; we are
bound only by the total size of the record, not by the japanese line breaks.
"""
import struct

HDR = struct.Struct("<BBHHH")
LINE_H = 11


class Run(object):
    __slots__ = ("kind", "attr", "x", "y", "flag", "text")

    def __init__(self, kind, attr, x, y, flag, text):
        self.kind, self.attr, self.x, self.y = kind, attr, x, y
        self.flag, self.text = flag, text

    def pack(self):
        return (HDR.pack(self.kind, self.attr, self.x, self.y, self.flag)
                + self.text.encode("cp932") + b"\x00")

    def __repr__(self):
        return "Run(k=%d,a=%#04x,%d,%d,%r)" % (self.kind, self.attr, self.x,
                                               self.y, self.text)


class Section(object):
    __slots__ = ("index", "off", "size", "runs")

    def __init__(self, index, off, size, runs):
        self.index, self.off, self.size, self.runs = index, off, size, runs

    def body(self):
        return b"".join(r.pack() for r in self.runs)

    def text(self):
        """The section as readable prose, one visual line per element."""
        return [r.text for r in self.runs]


def parse(b):
    """Return (sections, base).  Section 0 is binary and comes back
    with runs=None - it is not a text page."""
    count, base = struct.unpack_from("<II", b, 0)
    entries = [struct.unpack_from("<II", b, 8 + 8 * i) for i in range(count)]
    out = []
    for i, (off, size) in enumerate(entries):
        a = base + off
        blob = b[a:a + size]
        try:
            n = struct.unpack_from("<H", blob, 0)[0]
            if n == 0 or n + 2 > size:
                raise ValueError
            runs, j = [], 2
            while j < n + 2:
                # earlier in-place patches shortened a label and left NUL
                # padding behind it; a real header never starts with 0.
                while j < n + 2 and blob[j] == 0:
                    j += 1
                if j >= n + 2:
                    break
                kind, attr, x, y, flag = HDR.unpack_from(blob, j)
                if kind not in (2, 4):
                    raise ValueError("bad run kind %d at %#x" % (kind, j))
                z = blob.find(b"\x00", j + HDR.size)
                if z < 0 or z >= n + 2:
                    raise ValueError
                runs.append(Run(kind, attr, x, y, flag,
                                blob[j + HDR.size:z].decode("cp932")))
                j = z + 1
            if j > n + 2:
                raise ValueError
        except (ValueError, UnicodeDecodeError, struct.error):
            runs = None
        out.append(Section(i, a, size, runs))
    return out, base


def build(b, sections):
    """Re-emit into a copy of `b`, keeping every section in its slot."""
    out = bytearray(b)
    for s in sections:
        if s.runs is None:
            continue
        body = s.body()
        blob = struct.pack("<H", len(body)) + body
        if len(blob) > s.size:
            raise ValueError("section %d overflows: %d > %d"
                             % (s.index, len(blob), s.size))
        out[s.off:s.off + s.size] = blob + b"\x00" * (s.size - len(blob))
    return bytes(out)
