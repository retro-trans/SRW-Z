# -*- coding: utf-8 -*-
"""Translate DATA/MTV_PROS.BIN (prologue + interlude narration) and splice it.

REWRITTEN 2026-08-17 after the previous version hung the game at the chapter
9 -> 10 narration (v1.50 shipped with this file reverted). Proven by bisecting
forward from the Japanese disc: an image differing ONLY by these 5 sectors
black-screened forever.

What the old version got wrong, and what this one guarantees:

  1. LINE COUNT. The viewer paginates on newlines and waits for the pages it
     expects. The old code wrote whatever line breaks the translator happened to
     type - rec0 carried 45 newlines in Japanese and 40 in English - so the
     sequence never completed. Here every payload is REFLOWED to the original's
     exact newline count, and the write is refused if it cannot be.

  2. NO TRUNCATION. The old code asserted `len(enc) <= size`, but a translation
     that exactly filled the chunk ended mid-word with no terminator (rec9
     @0x0406 ended 'e', rec2 @0x01C8 ended 'D'). Here anything that does not fit
     is REPORTED AND SKIPPED - that chunk keeps its Japanese, which is always
     safe - and the payload is space-padded to the original byte length.

Structure: 14 banlz records, each a 'vpro' viewer container. Prose lives in
'rawt' sub-chunks ([tag][u32 size][SJIS]); the neighbouring 'actv' sub-chunk
holds animation durations in ms (9000, 13000...), NOT a line count.
Line width is 44 half-width columns max in the original (fullwidth = 2).
Every line is indented with an ideographic space; that pattern is reproduced.

English is menu-encoded (0x2E-0x3D are control codes for the reader) and padded
with spaces to the ORIGINAL chunk size, so no header maths is needed.

Usage: patch_mtvpros.py <iso> [--dry]
"""
import os
import hashlib
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from patch import encode
from mtvpros_en import TEXTS

SECTOR = 2048
ORIG_LBA, ORIG_SIZE = 1573437, 9056
NEW_LBA = 1823100                    # inside /DMY/DMY.BIN, after COMPDATA
MAXCOL = 44                          # half-width columns, from the original
IDSP = u"　"


def cols(s):
    """Display width in half-width columns, AS MENU ENCODING WILL DRAW IT.

    encode(..., "menu") emits bytes 0x2E-0x3D (. / 0-9 : ; < =) as FULLWIDTH
    2-column glyphs (they are control codes for the reader otherwise). Counting
    them as 1 undercounted every line with a period or digit, so a line measured
    at 40 actually drew at 41 and soft-wrapped - the last +1 overflow in rec11.
    """
    w = 0
    for c in s:
        o = ord(c)
        w += 2 if (o > 0x7F or 0x2E <= o <= 0x3D) else 1
    return w


def reflow_fit(text, n_lines, indent_flags, maxcol):
    """Wrap `text` into EXACTLY n_lines lines, as evenly as the Japanese was.

    The viewer paginates on newlines, so the line COUNT is a hard constraint -
    but the first version reached it by splitting the widest line in half, which
    left the prose visibly ragged (rec0 bounced between 15 and 44 columns where
    the Japanese held a steady 40-42).

    So choose the breaks properly: minimum-raggedness wrapping by dynamic
    programming. dp[k][j] = best cost for the first j words on k lines, with a
    line's cost the square of its unused columns. The last line is free, as in
    ordinary typesetting, so a short final line is not penalised.

    Returns None if the words cannot occupy exactly n_lines within `maxcol` -
    the caller then leaves that chunk Japanese, which is always safe.
    """
    words = text.split()
    m = len(words)
    if m == 0 or n_lines <= 0 or m < n_lines:
        return None                     # fewer words than lines: cannot comply

    wl = [cols(w) for w in words]
    # Cap at THIS chunk's own original max width, not a global constant. Each
    # narration screen has its own usable width; a line even 1-3 columns wider
    # than the original soft-wraps in the viewer, adding a display line and
    # desyncing pagination -> the chapter-10 interlude hung on exactly that
    # (rec11 ran 2 columns over). Staying <= the original width can never wrap.
    room = [maxcol - (2 if (i < len(indent_flags) and indent_flags[i]) else 0)
            for i in range(n_lines)]

    # width of words[i:j] joined by single spaces
    def span(i, j):
        return sum(wl[i:j]) + (j - i - 1)

    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n_lines + 1)]
    back = [[-1] * (m + 1) for _ in range(n_lines + 1)]
    dp[0][0] = 0.0
    for k in range(1, n_lines + 1):
        cap = room[k - 1]
        for j in range(k, m + 1):
            best, bi = INF, -1
            for i in range(k - 1, j):
                if dp[k - 1][i] == INF:
                    continue
                w = span(i, j)
                if w > cap:
                    continue            # this line would overflow
                slack = 0.0 if k == n_lines else float(cap - w) ** 2
                c = dp[k - 1][i] + slack
                if c < best:
                    best, bi = c, i
            dp[k][j] = best
            back[k][j] = bi
    if dp[n_lines][m] == INF:
        return None

    cuts, j = [], m
    for k in range(n_lines, 0, -1):
        i = back[k][j]
        cuts.append((i, j))
        j = i
    cuts.reverse()

    out = []
    for idx, (i, j) in enumerate(cuts):
        pre = IDSP if (idx < len(indent_flags) and indent_flags[idx]) else ""
        out.append(pre + " ".join(words[i:j]))
    return "\n".join(out)


def main():
    iso_path = sys.argv[1]
    dry = "--dry" in sys.argv
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "extracted", "DATA_MTV_PROS.BIN"),
        "rb").read()
    recs = banlz.decompress_all(src)

    queue = list(TEXTS)
    # Preserve the EXACT original file layout. The original records are 16-byte
    # aligned with a few zero bytes of padding after each; my first versions
    # packed them tight, shifting every offset - which hung the chapter-10
    # narration (this file is the story-so-far RECAP, not the prologue; the
    # prologue is the separate MTV_PROP.BIN, untouched). Rebuild into a buffer of
    # the original size and drop each recompressed record at its ORIGINAL offset.
    out = bytearray(len(src))
    starts = [r[0] for r in recs]
    spans = [(starts[i + 1] - starts[i]) if i + 1 < len(starts)
             else (len(src) - starts[i]) for i in range(len(recs))]
    n_done = n_skip = n_jprec = 0
    for ri, (s0, dat) in enumerate(recs):
        dat = bytearray(dat)
        j = 0
        while True:
            j = dat.find(b"rawt", j)
            if j < 0:
                break
            size = struct.unpack_from("<I", dat, j + 4)[0]
            jp_raw = bytes(dat[j + 8:j + 8 + size])
            jp_txt = jp_raw.decode("cp932", "replace")
            # Guards chunk ORDER: the chunk about to be overwritten must be
            # the one this english was written for, or a mis-ordered walk
            # splices narration into the wrong slot. The expected japanese is
            # stored as a HASH, not as text - it was only ever compared, never
            # read, and holding Banpresto's prologue verbatim is what made
            # check_publishable refuse the repo.
            nbytes, want, en = queue[0]
            got = hashlib.sha1(jp_raw[:nbytes]).hexdigest()[:16]
            assert got == want, "chunk order mismatch at rec%d +%#x (%s != %s)" % (ri, j, got, want)
            queue.pop(0)
            jp_lines = jp_txt.split(chr(10))
            flags = [ln.startswith(IDSP) for ln in jp_lines]
            chunk_maxcol = max(cols(l) for l in jp_lines)
            body = " ".join(l.lstrip(IDSP).strip() for l in en.split(chr(10)))
            fitted = reflow_fit(body, len(jp_lines), flags, chunk_maxcol)
            why = None
            if fitted is None:
                why = "cannot fit %d lines x %d cols" % (len(jp_lines), chunk_maxcol)
            else:
                enc = encode(fitted, "menu")
                if len(enc) > size:
                    why = "encoded %d > %d bytes" % (len(enc), size)
                elif fitted.count(chr(10)) != jp_txt.count(chr(10)):
                    why = "newline count %d != %d" % (fitted.count(chr(10)),
                                                      jp_txt.count(chr(10)))
            if why:
                print("  SKIP rec%-2d @%#06x (%s) - chunk stays Japanese"
                      % (ri, j, why))
                n_skip += 1
            else:
                dat[j + 8:j + 8 + size] = enc + b" " * (size - len(enc))
                n_done += 1
            j += 8 + size

        blob = banlz.compress_record(bytes(dat))
        if len(blob) > spans[ri]:
            # The fast compressor is not the last word. rec1 - the opening
            # prologue - missed its span by NINE bytes and so shipped in
            # Japanese, which is what a screenshot of the Rand prologue showed.
            # Every other tool here falls back to the optimal encoder on
            # overflow; this one did not.
            opt = banlz.compress_record_optimal(bytes(dat))
            if len(opt) < len(blob):
                blob = opt
        rt, _ = banlz.decompress_record(blob, 0)
        assert rt == bytes(dat)
        if len(blob) <= spans[ri]:
            out[s0:s0 + len(blob)] = blob        # rest of the span stays zero
        else:
            # recompressed record does not fit its original span -> keep the
            # original bytes verbatim; that record stays fully Japanese
            out[s0:s0 + spans[ri]] = src[s0:s0 + spans[ri]]
            n_jprec += 1
            print("  KEEP rec%-2d Japanese (recompressed %d > span %d)"
                  % (ri, len(blob), spans[ri]))
    assert not queue, "untranslated texts left: %d" % len(queue)

    # --- verify against the original before writing anything ---
    chk = banlz.decompress_all(out)
    bad = 0
    for ri, (s0, d0) in enumerate(recs):
        d1 = chk[ri][1]
        for tag in (b"rawt",):
            a = b = 0
            i = 0
            while True:
                i = bytes(d0).find(tag, i)
                if i < 0:
                    break
                sz = struct.unpack_from("<I", d0, i + 4)[0]
                t0 = bytes(d0[i + 8:i + 8 + sz]).decode("cp932", "replace")
                t1 = bytes(d1[i + 8:i + 8 + sz]).decode("cp932", "replace")
                if t0.count("\n") != t1.count("\n"):
                    print("  !! rec%d @%#x newline %d -> %d"
                          % (ri, i, t0.count("\n"), t1.count("\n")))
                    bad += 1
                i += 8 + sz
    print("translated %d rawt chunks, skipped %d; newline mismatches %d"
          % (n_done, n_skip, bad))
    print("new file %d bytes (orig %d)" % (len(out), ORIG_SIZE))
    if bad:
        raise SystemExit("REFUSING TO WRITE - pagination would break")
    if dry:
        print("dry run; nothing written")
        return

    with open(iso_path, "r+b") as iso:
        if len(out) <= ORIG_SIZE:
            lba, size = ORIG_LBA, len(out)
            iso.seek(lba * SECTOR)
            iso.write(out + b"\x00" * (ORIG_SIZE - len(out)))
        else:
            lba, size = NEW_LBA, len(out)
            iso.seek(lba * SECTOR)
            iso.write(out)
        iso.seek(0)
        head = iso.read(4 * 1024 * 1024)
        p = head.find(b"MTV_PROS.BIN;1")
        assert p > 0, "dir record not found"
        rec = p - 33
        cur = struct.unpack_from("<I", head, rec + 2)[0]
        assert cur in (ORIG_LBA, NEW_LBA), "unexpected LBA %d" % cur
        iso.seek(rec + 2)
        iso.write(struct.pack("<I", lba))
        iso.seek(rec + 6)
        iso.write(struct.pack(">I", lba))
        iso.seek(rec + 10)
        iso.write(struct.pack("<I", size))
        iso.seek(rec + 14)
        iso.write(struct.pack(">I", size))
        print("dir record: LBA %d size %d %s"
              % (lba, size, "(relocated)" if lba == NEW_LBA else "(in place)"))


if __name__ == "__main__":
    main()
