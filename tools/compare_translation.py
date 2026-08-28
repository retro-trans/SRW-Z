# -*- coding: utf-8 -*-
"""Check this translation against the original, using only your own disc.

Point it at your japanese copy - .chd, .iso, .bin or .cue - and it writes an
HTML page with the japanese on the left and our english on the right, so anyone
can judge whether the translation is any good without taking our word for it.

    python tools/compare_translation.py "Super Robot Taisen Z (Japan).chd"
    python tools/compare_translation.py game.iso --rec 127 -o rec127.html

You do NOT need a patched image. build_compare.py does, because it pairs the two
scripts live through the pointer table; this uses analysis/translation_pairs.json
instead, where that pairing was done once and stored keyed by JAPANESE offset.
That file holds no japanese text - only offsets into the disc you already own.

Only pointer-paired rows were stored, so every line shown here is matched by the
game's own reference rather than by guesswork. Rows that could not be paired are shown
too, marked "no confident match" - NOT "untranslated". They are almost always
translated; we simply cannot prove which japanese line goes with which english
one, and a check that presented a guess as a fact would be worthless.

Usage: compare_translation.py <japanese image> [--rec N] [-o out.html]
"""
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from build_compare import as_image, s_at, JP_RE
from rewrap_dialogue import LBA, SECTOR, SIZE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "translation_pairs.json")

HEAD = u"""<!doctype html>
<meta charset="utf-8">
<title>SRW Z - translation check</title>
<style>
 :root{--bg:#fff;--fg:#111;--line:#e3e3e6;--head:#f6f6f8;--miss:#b3261e;--todo:#9a6b00}
 @media (prefers-color-scheme:dark){
   :root{--bg:#15171c;--fg:#e6e6e6;--line:#2c3038;--head:#1e2127;--miss:#ff7b72;--todo:#e0b040}}
 body{background:var(--bg);color:var(--fg);margin:0;
      font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
 header{position:sticky;top:0;background:var(--head);padding:14px 20px;
        border-bottom:1px solid var(--line)}
 h1{margin:0;font-size:17px} .sub{opacity:.7;font-size:13px;margin-top:4px}
 table{border-collapse:collapse;width:100%%} td{vertical-align:top;
   padding:9px 20px;border-bottom:1px solid var(--line);white-space:pre-wrap}
 td.n{width:5em;opacity:.45;font-variant-numeric:tabular-nums;font-size:12px}
 td.jp{width:44%%} td.en{width:44%%}
 .miss{color:var(--miss);font-style:italic}
 .todo{color:var(--todo);font-style:italic}
</style>
<header><h1>Super Robot Taisen Z &mdash; translation check</h1>
<div class="sub">%s</div></header>
<table>
"""


def esc(s):
    return (s.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
             .replace(u">", u"&gt;"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit(__doc__)
    src = args[0]
    only = None
    if "--rec" in sys.argv:
        only = int(sys.argv[sys.argv.index("--rec") + 1])
    out = (sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv
           else "translation-check.html")
    if not os.path.exists(PAIRS):
        raise SystemExit("missing %s - it ships with the release" % PAIRS)
    pairs = json.load(io.open(PAIRS, encoding="utf-8"))["pairs"]

    tmp = tempfile.mkdtemp(prefix="srwzcheck")
    img = as_image(src, tmp)
    f = open(img, "rb")
    f.seek(LBA * SECTOR)
    recs = banlz.decompress_all(f.read(SIZE))
    f.close()

    rows = miss = todo = 0
    body = []
    for i in range(len(recs)):
        if only is not None and i != only:
            continue
        jb = recs[i][1]
        if jb is None:
            continue
        got = pairs.get(str(i))
        if not got:
            continue
        b = bytes(jb)
        k = 0
        while k < len(b):
            z = b.find(b"\x00", k)
            if z == -1:
                z = len(b)
            if z - k > 2:
                jt = s_at(b, k)
                if jt and JP_RE.search(jt):
                    en = got.get(str(k))
                    if en:
                        cell = esc(en)
                        rows += 1
                    elif en == "":
                        # paired, but this row is still japanese in our build
                        cell = u'<span class="todo">not translated yet</span>'
                        todo += 1
                    else:
                        cell = u'<span class="miss">no confident match</span>'
                        miss += 1
                    body.append(u"<tr><td class=n>%d:%d</td>"
                                u"<td class=jp>%s</td><td class=en>%s</td></tr>"
                                % (i, k, esc(jt), cell))
            k = z + 1

    sub = (u"%s &middot; %d lines paired by the game's own pointer, "
           u"%d not translated yet, %d could not be matched confidently"
           % (esc(os.path.basename(src)), rows, todo, miss))
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        (HEAD % sub) + u"\n".join(body) + u"\n</table>\n")
    print("%d translated, %d not translated yet, %d unmatched"
          % (rows, todo, miss))
    print("wrote %s (%.1f MB) - open it in a browser"
          % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
