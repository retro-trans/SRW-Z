# -*- coding: utf-8 -*-
"""Check the BATTLE VOICE LINES against the japanese, from your own disc.

compare_translation.py does this for the story script. This is the other half:
the ~19,000 lines characters shout during combat, which is where the errors
that survive are - they are short, they fit, they read fluently, and nothing
mechanical can tell that one of them is wrong.

The line that prompted this:

    ダーリン、嬉しそう…！   ->  "Darling, so happy...!"

嬉しそう is "you LOOK happy", said ABOUT someone else. The english made the
speaker happy instead. It is the right length, correctly punctuated, and
perfectly fluent - no detector will ever flag it. Only reading it beside the
japanese shows the subject is wrong.

Needs only YOUR japanese disc. Our english ships as
analysis/srvc_en_by_hash.json, keyed by sha1 of the japanese line, so no index
table and none of the original text has to be published: this hashes each line
on your disc and looks the translation up.

    compare_captions.py "Super Robot Taisen Z (Japan).chd"
    compare_captions.py game.iso --only untranslated -o todo.html

Usage: compare_captions.py <japanese image> [--only KIND] [-o out.html]
"""
import hashlib
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import srvc
from build_compare import as_image

LINES = os.path.join(ROOT, "analysis", "srvc_en_by_hash.json")
SECTOR = 2048
SRVC_LBA, SRVC_SECTORS = 1313214, 1618
SEG = os.path.join(ROOT, "extracted", "BTL_SRVC.SEG")
KINDS = ("translated", "untranslated")
CJK = re.compile(u"[぀-ヿ一-鿿]")
KANA = re.compile(u"[ぁ-ゟァ-ヿ]")
KAGI = u"「"
IDSP = u"　"


def looks_like_a_line(s):
    """Blocks hold more than speech - a character table lives in there too,
    and a bare 黶 or 驕 is not an untranslated caption. Same filter the story
    comparison needs: real speech has kana in it, or an opening bracket."""
    s = s.strip()
    if len(s) < 4 and KAGI not in s:
        return False
    return KAGI in s or len(KANA.findall(s)) >= 2

HEAD = u"""<!doctype html>
<meta charset="utf-8">
<title>SRW Z - battle voice lines</title>
<style>
 :root{--bg:#fff;--fg:#111;--line:#e3e3e6;--head:#f6f6f8;--todo:#9a6b00;
       --chip:#eceef2}
 @media (prefers-color-scheme:dark){
   :root{--bg:#15171c;--fg:#e6e6e6;--line:#2c3038;--head:#1e2127;--todo:#e0b040;
         --chip:#262a32}}
 body{background:var(--bg);color:var(--fg);margin:0;
      font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
 header{position:sticky;top:0;background:var(--head);padding:12px 20px;
        border-bottom:1px solid var(--line);z-index:2}
 h1{margin:0 0 6px;font-size:17px}
 .sub{opacity:.7;font-size:13px;margin-bottom:8px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 .bar label{background:var(--chip);border-radius:999px;padding:3px 11px;
            font-size:13px;cursor:pointer;user-select:none}
 .bar input[type=search]{flex:1;min-width:200px;padding:5px 10px;font-size:14px;
   border:1px solid var(--line);border-radius:6px;background:var(--bg);
   color:var(--fg)}
 #count{font-size:12px;opacity:.6;white-space:nowrap}
 table{border-collapse:collapse;width:100%%} td{vertical-align:top;
   padding:8px 20px;border-bottom:1px solid var(--line);white-space:pre-wrap}
 td.jp{width:48%%} td.en{width:48%%}
 .todo{color:var(--todo);font-style:italic}
 body.h-translated tr.translated,
 body.h-untranslated tr.untranslated{display:none}
 tr.q{display:none}
</style>
<header>
 <h1>Super Robot Taisen Z &mdash; battle voice lines</h1>
 <div class="sub">%s</div>
 <div class="bar">
  <label><input type=checkbox data-k=translated checked> translated (%d)</label>
  <label><input type=checkbox data-k=untranslated checked> not translated (%d)</label>
  <input type=search id=q placeholder="search japanese or english...">
  <span id=count></span>
 </div>
</header>
<table id=t>
"""

TAIL = u"""</table>
<script>
var rows=document.querySelectorAll('#t tr'), q=document.getElementById('q'),
    count=document.getElementById('count'), timer=null;
document.querySelectorAll('.bar input[type=checkbox]').forEach(function(c){
  c.onchange=function(){
    document.body.classList.toggle('h-'+c.dataset.k, !c.checked);};
});
function run(){
  var s=q.value.trim().toLowerCase(), n=0;
  for(var i=0;i<rows.length;i++){
    var hit=!s||rows[i].textContent.toLowerCase().indexOf(s)>=0;
    rows[i].classList.toggle('q',!hit); if(hit)n++;
  }
  count.textContent=s?(n+' matching'):'';
}
q.oninput=function(){clearTimeout(timer);timer=setTimeout(run,180);};
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
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        if only not in KINDS:
            raise SystemExit("--only must be one of: %s" % ", ".join(KINDS))
    out = (sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv
           else "battle-lines.html")
    if not os.path.exists(LINES):
        raise SystemExit("missing %s - it ships with the release" % LINES)
    en = json.load(io.open(LINES, encoding="utf-8"))["lines"]

    tmp = tempfile.mkdtemp(prefix="srwzcap")
    img = as_image(src, tmp)
    f = open(img, "rb")
    f.seek(SRVC_LBA * SECTOR)
    data = f.read(SRVC_SECTORS * SECTOR)
    f.close()
    blocks = srvc.parse(data, srvc.read_seg(open(SEG, "rb").read()))

    seen, rows, n = set(), [], {"translated": 0, "untranslated": 0}
    for b in blocks:
        if not getattr(b, "has_text", False):
            continue
        for s in b.strings:
            try:
                jt = s.decode("cp932")
            except Exception:
                continue
            key = jt.strip(u"「」")
            if not key.strip() or not CJK.search(key) or key in seen:
                continue
            if not looks_like_a_line(key):
                continue
            seen.add(key)
            # The worklist stores lines with the ideographic spaces around a
            # line break removed, the disc keeps them - so try the line as it
            # is, then without them. That one difference accounted for 6,910
            # lines reading "not translated" when they are translated.
            got = None
            for k in (key, key.replace(IDSP, u"")):
                got = en.get(hashlib.sha1(k.encode("cp932", "ignore"))
                             .hexdigest()[:16])
                if got:
                    break
            kind = "translated" if got else "untranslated"
            n[kind] += 1
            if only and kind != only:
                continue
            cell = esc(got) if got else u'<span class="todo">not translated</span>'
            rows.append(u"<tr class=%s><td class=jp>%s</td><td class=en>%s</td></tr>"
                        % (kind, esc(jt), cell))

    sub = u"%s &middot; %d lines" % (esc(os.path.basename(src)), sum(n.values()))
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        (HEAD % (sub, n["translated"], n["untranslated"]))
        + u"\n".join(rows) + u"\n" + TAIL)
    print("translated %d, not translated %d" % (n["translated"], n["untranslated"]))
    print("wrote %s (%.1f MB) - open it in a browser"
          % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
