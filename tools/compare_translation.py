# -*- coding: utf-8 -*-
"""Check this translation against the original, using only your own disc.

Point it at your japanese copy - .chd, .iso, .bin or .cue - and it writes an
HTML page with the japanese on the left and our english on the right, so anyone
can judge whether the translation is any good without taking our word for it.

    python tools/compare_translation.py "Super Robot Taisen Z (Japan).chd"
    python tools/compare_translation.py game.iso --rec 127 -o rec127.html
    python tools/compare_translation.py game.iso --only untranslated

You do NOT need a patched image. build_compare.py does, because it pairs the two
scripts live through the pointer table; this uses analysis/translation_pairs.json
instead, where that pairing was done once and stored keyed by JAPANESE offset.
That file holds no japanese text - only offsets into the disc you already own.

Three kinds of row, and the difference matters:

    translated          we have english, paired by the game's own pointer
    not translated      paired, but that row is still japanese in our build
    no confident match  we cannot prove which english line goes with it. NOT
                        the same as untranslated - it almost certainly IS
                        translated, we just cannot demonstrate which line.

83,000 rows is not something to scroll, so the page has a filter bar - toggle
the three kinds, or search either language - and --only writes a smaller file
containing just one kind.

Usage: compare_translation.py <japanese image> [--rec N] [--only KIND] [-o out]
"""
import io
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from build_compare import as_image, s_at, JP_RE
from rewrap_dialogue import LBA, SECTOR, SIZE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = os.path.join(ROOT, "analysis", "translation_pairs.json")
KANA = re.compile(u"[ぁ-ゟァ-ヿ]")
KAGI = u"「"
KINDS = ("translated", "untranslated", "unmatched")


def looks_like_a_line(s):
    """Is this a line of script, or bytes that happened to decode?

    A record's pointer table and padding are valid cp932 too, so "contains a
    japanese character" lets through things like コ$減d-( and 、察@< - all from
    the low offsets of rec0, which is exactly where the pointer table lives.
    Real dialogue has kana in it, or an opening quote bracket.

    Applied ONLY to rows we could not pair. Anything in the pairs file is known
    to be a real row and is shown unconditionally, so this can never hide a
    translation - which matters, or it would drop short but genuine strings
    like a bare speaker name."""
    s = s.strip()
    if len(s) < 4 and KAGI not in s:
        return False
    return KAGI in s or len(KANA.findall(s)) >= 3


HEAD = u"""<!doctype html>
<meta charset="utf-8">
<title>SRW Z - translation check</title>
<style>
 :root{--bg:#fff;--fg:#111;--line:#e3e3e6;--head:#f6f6f8;--miss:#b3261e;
       --todo:#9a6b00;--chip:#eceef2}
 @media (prefers-color-scheme:dark){
   :root{--bg:#15171c;--fg:#e6e6e6;--line:#2c3038;--head:#1e2127;--miss:#ff7b72;
         --todo:#e0b040;--chip:#262a32}}
 body{background:var(--bg);color:var(--fg);margin:0;
      font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
 header{position:sticky;top:0;background:var(--head);padding:12px 20px;
        border-bottom:1px solid var(--line);z-index:2}
 h1{margin:0 0 6px;font-size:17px}
 .sub{opacity:.7;font-size:13px;margin-bottom:8px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 .bar label{background:var(--chip);border-radius:999px;padding:3px 11px;
            font-size:13px;cursor:pointer;user-select:none}
 .bar input[type=search]{flex:1;min-width:180px;padding:5px 10px;font-size:14px;
   border:1px solid var(--line);border-radius:6px;background:var(--bg);
   color:var(--fg)}
 #count{font-size:12px;opacity:.6;white-space:nowrap}
 table{border-collapse:collapse;width:100%%} td{vertical-align:top;
   padding:9px 20px;border-bottom:1px solid var(--line);white-space:pre-wrap}
 td.n{width:5.5em;opacity:.45;font-variant-numeric:tabular-nums;font-size:12px}
 td.jp{width:44%%} td.en{width:44%%}
 .miss{color:var(--miss);font-style:italic}
 .todo{color:var(--todo);font-style:italic}
 body.h-translated tr.translated,
 body.h-untranslated tr.untranslated,
 body.h-unmatched tr.unmatched{display:none}
 tr.q{display:none}
</style>
<header>
 <h1>Super Robot Taisen Z &mdash; translation check</h1>
 <div class="sub">%s &middot; the left column is <code>record:offset</code> for <code>analysis/row_fixes.json</code></div>
 <div class="bar">
  <label><input type=checkbox data-k=translated checked> translated (%d)</label>
  <label><input type=checkbox data-k=untranslated checked> not translated (%d)</label>
  <label><input type=checkbox data-k=unmatched checked> no confident match (%d)</label>
  <select id=r><option value="">every record (%d)</option>%s</select>
  <input type=search id=q placeholder="search japanese or english...">
  <span id=count></span>
 </div>
</header>
<style id=rf></style>
<table id=t>
"""

TAIL = u"""</table>
<script>
var rows=document.querySelectorAll('#t tr'), q=document.getElementById('q'),
    count=document.getElementById('count'), timer=null;
document.querySelectorAll('.bar input[type=checkbox]').forEach(function(c){
  c.onchange=function(){
    document.body.classList.toggle('h-'+c.dataset.k, !c.checked);
  };
});
function run(){
  var s=q.value.trim().toLowerCase(), n=0;
  for(var i=0;i<rows.length;i++){
    var hit=!s||rows[i].textContent.toLowerCase().indexOf(s)>=0;
    rows[i].classList.toggle('q',!hit);
    if(hit)n++;
  }
  count.textContent=s?(n+' matching'):'';
}
q.oninput=function(){clearTimeout(timer);timer=setTimeout(run,180);};
var r=document.getElementById('r'), rf=document.getElementById('rf');
r.onchange=function(){
  rf.textContent=r.value?('#t tr:not([data-r="'+r.value+'"]){display:none}'):'';
};
</script>
"""


def esc(s):
    return (s.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
             .replace(u">", u"&gt;"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit(__doc__)
    src = args[0]
    only_rec = None
    if "--rec" in sys.argv:
        only_rec = int(sys.argv[sys.argv.index("--rec") + 1])
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        if only not in KINDS:
            raise SystemExit("--only must be one of: %s" % ", ".join(KINDS))
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

    n = {k: 0 for k in KINDS}
    per = {}
    body = []
    for i in range(len(recs)):
        if only_rec is not None and i != only_rec:
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
                    v = got.get(str(k))
                    eo, en = (v if isinstance(v, list) else (None, v))                         if v is not None else (None, None)
                    ident = u"%d:%d" % (i, eo if eo is not None else k)
                    if en:
                        kind = "translated"
                        cell = esc(en)
                    elif en == "":
                        kind = "untranslated"
                        cell = u'<span class="todo">not translated yet</span>'
                    elif looks_like_a_line(jt):
                        kind = "unmatched"
                        cell = u'<span class="miss">no confident match</span>'
                    else:
                        k = z + 1
                        continue
                    n[kind] += 1
                    per[i] = per.get(i, 0) + 1
                    if only is None or kind == only:
                        body.append(
                            u"<tr class=%s data-r=%d><td class=n>%s</td>"
                            u"<td class=jp>%s</td><td class=en>%s</td></tr>"
                            % (kind, i, ident, esc(jt), cell))
            k = z + 1

    sub = u"%s &middot; %s" % (
        esc(os.path.basename(src)),
        (u"showing only: %s" % only) if only else u"%d rows" % sum(n.values()))
    opts = u"".join(u'<option value="%d">record %d (%d)</option>' % (i, i, c)
                    for i, c in sorted(per.items()))
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        (HEAD % (sub, n["translated"], n["untranslated"], n["unmatched"],
                 sum(n.values()), opts))
        + u"\n".join(body) + u"\n" + TAIL)
    print("translated %d, not translated yet %d, unmatched %d"
          % (n["translated"], n["untranslated"], n["unmatched"]))
    if only:
        print("wrote only '%s' rows" % only)
    print("wrote %s (%.1f MB) - open it in a browser"
          % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
