# -*- coding: utf-8 -*-
"""Build a side-by-side Japanese/English comparison table as a single HTML file.

Run it on YOUR OWN copies. Nothing here ships the original script: you point it
at the Japanese image you dumped and at a translated one, and the comparison is
generated locally.

    python tools/build_compare.py japanese.chd translated.chd compare.html

Accepts .chd, .bin, .iso or .cue. A .chd is extracted with chdman, which must be
on PATH or in tools/.

YES, IT NEEDS TWO IMAGES. An earlier version of this text offered
analysis/english_script.json as the english side. It never worked and could not
easily: that file is keyed by (record, byte offset) in OUR PATCHED layout, and
apply_english_script.py says plainly that applying it to a virgin japanese image
does not fully work, because rows that outgrew their slot were relocated and
their pointers do not exist on a clean disc. Pairing needs the english record's
real bytes, so it needs a real english image.

That is one command away, not a second download - apply the release patch to a
copy of your japanese dump and point this at both:

    xdelta3 -d -s japanese.iso SRWZ-English-vX.Y.Z.xdelta english.iso
    python tools/build_compare.py japanese.iso english.iso compare.html --rec 127

Use --rec for real work. The whole script is 68,628 rows and about 14 MB of
HTML; one record is a scenario, which is the unit anyone actually proofreads.

HOW ROWS ARE PAIRED, and why the tool tells you which

A translated row that outgrew its slot was relocated to the end of its record
and the pointer that referenced it was rewritten, so the same text is at a
DIFFERENT offset in the two images. Pairing therefore goes through the pointer
table, not the offset:

  pointer      a 4-aligned word in the JP record points at the JP string; the
               word at the SAME POSITION in the EN record points at the English.
               This is the reliable case.
  same-offset  no pointer references that string, so the tool assumes the
               English sits where the Japanese did. True for rows that never
               moved; WRONG if the row moved and the slot was cleared.
  suspect      paired, but the English is empty or does not look like text.

Every row carries its method in the output and can be filtered on it. An earlier
tool in this project silently used the same-offset guess for everything and
mispaired roughly 30% of rows while looking authoritative
(analysis/review/EXPORT_TRUST.md) - hence showing the method rather than hiding
it.

Usage:
  build_compare.py <jp> <en> <out.html> [--dialogue] [--rec N]
"""
import io
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

BASE = 0x7566F0
KAGI = u"「"
NULB = b"\x00"
IDSPACE = u"　"
JP_RE = re.compile(u"[぀-ゟ゠-ヿ一-鿿]")
EXPAND = {"$F": "x" * 14, "$n": "x" * 7, "$f": "x" * 7, "$l": "x" * 6}


def ecols(s):
    for k, v in EXPAND.items():
        s = s.replace(k, v)
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def find_chdman():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "chdman.exe"), os.path.join(here, "chdman"),
              "chdman.exe", "chdman"):
        try:
            subprocess.check_output([c, "--help"], stderr=subprocess.STDOUT)
            return c
        except Exception:
            continue
    return None


def as_image(path, tmpdir):
    """Return a path to a raw image, extracting a .chd if needed."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".bin", ".iso", ".img"):
        return path
    if ext == ".cue":
        base = os.path.splitext(path)[0]
        for e in (".bin", ".img"):
            if os.path.exists(base + e):
                return base + e
        raise SystemExit("cannot find the .bin next to %s" % path)
    if ext != ".chd":
        raise SystemExit("unsupported input: %s" % path)
    chdman = find_chdman()
    if not chdman:
        raise SystemExit("chdman not found - extract %s yourself, or put chdman "
                         "in tools/" % os.path.basename(path))
    out = os.path.join(tmpdir, os.path.basename(path) + ".bin")
    cue = os.path.join(tmpdir, os.path.basename(path) + ".cue")
    sys.stderr.write("extracting %s ...\n" % os.path.basename(path))
    subprocess.check_call([chdman, "extractcd", "-i", path, "-o", cue,
                           "-ob", out, "-f"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def load(path):
    f = open(path, "rb")
    f.seek(LBA * SECTOR)
    items = banlz.decompress_all(f.read(SIZE))
    f.close()
    return items


def s_at(buf, off):
    if not (0 <= off < len(buf)):
        return None
    e = buf.find(b"\x00", off)
    if e == -1:
        e = len(buf)
    try:
        return buf[off:e].decode("cp932")
    except Exception:
        return None


def pair_record(jb, eb):
    """Yield (jp_off, jp_text, en_off, en_text, method)."""
    ptr = {}
    for i in range(0, len(jb) - 4, 4):
        v = struct.unpack_from("<I", jb, i)[0] - BASE
        if 0 <= v < len(jb):
            ptr.setdefault(v, []).append(i)
    i = 0
    while i < len(jb):
        j = jb.find(b"\x00", i)
        if j == -1:
            j = len(jb)
        if j - i > 2:
            jt = s_at(jb, i)
            if jt and JP_RE.search(jt):
                eo, method = None, "same-offset"
                for p in ptr.get(i, []):
                    if p + 4 <= len(eb):
                        v = struct.unpack_from("<I", eb, p)[0] - BASE
                        if 0 <= v < len(eb):
                            eo, method = v, "pointer"
                            break
                if eo is None:
                    eo = i
                et = s_at(eb, eo)
                if et is None or not et.strip():
                    method = "suspect"
                    et = et or ""
                yield (i, jt, eo, et, method)
        i = j + 1


HTML_HEAD = u"""<!doctype html>
<meta charset="utf-8">
<title>SRW Z — Japanese / English comparison</title>
<style>
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e2e2e2;--head:#f6f6f6;
      --ptr:#0a7d3f;--same:#9a6b00;--sus:#b3261e;--hl:#fff3b0}
@media(prefers-color-scheme:dark){:root{--bg:#16181d;--fg:#e7e7e7;--mut:#9aa0a6;
      --line:#2c3038;--head:#1e2127;--ptr:#5fd08a;--same:#e0b040;--sus:#ff7b72;
      --hl:#4a4320}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);
       padding:12px 16px;z-index:5}
h1{font-size:15px;margin:0 0 8px;font-weight:600}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input,select,button{font:inherit;padding:6px 9px;border:1px solid var(--line);
     border-radius:6px;background:var(--bg);color:var(--fg)}
input[type=search]{min-width:260px;flex:1}
button{cursor:pointer}
.stat{color:var(--mut);font-size:12px;margin-left:auto}
table{border-collapse:collapse;width:100%;table-layout:fixed}
th{position:sticky;top:0;background:var(--head);text-align:left;font-size:12px;
   color:var(--mut);padding:7px 10px;border-bottom:1px solid var(--line);font-weight:600}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;
   white-space:pre-wrap;word-break:break-word}
td.jp{width:38%;font-family:"Yu Gothic","Hiragino Kaku Gothic ProN",Meiryo,sans-serif}
td.en{width:38%}
td.meta{width:8%;font-variant-numeric:tabular-nums;color:var(--mut);font-size:12px}
td.m{width:8%;font-size:12px;font-weight:600}
.pointer{color:var(--ptr)} .same-offset{color:var(--same)} .suspect{color:var(--sus)}
mark{background:var(--hl);color:inherit}
.over{color:var(--sus);font-weight:600}
footer{padding:14px 16px;color:var(--mut);font-size:12px}
.pg{display:flex;gap:6px;align-items:center;padding:10px 16px}
#syn{display:none;margin-top:8px;padding:8px 10px;background:var(--head);
     border-radius:6px;font-size:13px;color:var(--mut);line-height:1.7;
     font-family:"Yu Gothic","Hiragino Kaku Gothic ProN",Meiryo,sans-serif}
</style>
<header>
  <h1>Super Robot Taisen Z — Japanese / English comparison</h1>
  <div class="bar">
    <input type="search" id="q" placeholder="search japanese or english…">
    <select id="m">
      <option value="">every pairing method</option>
      <option value="pointer">pointer (reliable)</option>
      <option value="same-offset">same-offset (assumed)</option>
      <option value="suspect">suspect</option>
    </select>
    <select id="r"><option value="">every record</option></select>
    <label><input type="checkbox" id="d"> dialogue only</label>
    <label><input type="checkbox" id="o"> over 34 columns</label>
    <span class="stat" id="stat"></span>
  </div>
  <div id="syn"></div>
</header>
<table><thead><tr>
  <th>rec / off</th><th>Japanese</th><th>English</th><th>pairing</th>
</tr></thead><tbody id="tb"></tbody></table>
<div class="pg"><button id="prev">‹ prev</button>
  <span id="pgi"></span><button id="next">next ›</button></div>
<footer>
  <b>pointer</b> — paired through the pointer table; reliable.
  <b>same-offset</b> — no pointer referenced this string, so the English is
  assumed to sit where the Japanese did. Correct for rows that never moved,
  wrong if the row was relocated.
  <b>suspect</b> — paired, but the English is empty or does not look like text.
  <br>Generated locally from your own images. Neither script is distributed with
  this tool.
</footer>
<script>
const ROWS=
"""

HTML_TAIL = u""";
const PAGE=200;let page=0,view=ROWS;
const tb=document.getElementById('tb'),q=document.getElementById('q'),
      m=document.getElementById('m'),r=document.getElementById('r'),
      d=document.getElementById('d'),o=document.getElementById('o'),
      stat=document.getElementById('stat'),pgi=document.getElementById('pgi');
const recs=[...new Set(ROWS.map(x=>x[0]))].sort((a,b)=>a-b);
for(const x of recs){const e=document.createElement('option');e.value=x;
  const c=(typeof CAST!=='undefined')?CAST[x]:null;
  e.textContent='rec'+x+(c&&c.cast?' — '+c.cast:'');r.appendChild(e);}
function synFor(x){const c=(typeof CAST!=='undefined')?CAST[x]:null;
  return (c&&c.syn)?c.syn:'';}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function hl(s,t){if(!t)return esc(s);const i=s.toLowerCase().indexOf(t.toLowerCase());
  if(i<0)return esc(s);return esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+t.length))+
  '</mark>'+esc(s.slice(i+t.length));}
function apply(){const t=q.value.trim(),mm=m.value,rr=r.value;
  view=ROWS.filter(x=>{
    if(mm&&x[5]!==mm)return false;
    if(rr&&String(x[0])!==rr)return false;
    if(d.checked&&!x[2].includes('\\u300c'))return false;
    if(o.checked&&!x[6])return false;
    if(t&&!(x[2].toLowerCase().includes(t.toLowerCase())||
            x[4].toLowerCase().includes(t.toLowerCase())))return false;
    return true;});
  page=0;draw();}
function draw(){const s=page*PAGE,part=view.slice(s,s+PAGE);
  tb.innerHTML=part.map(x=>'<tr><td class="meta">rec'+x[0]+'<br>'+x[1]+'</td>'+
    '<td class="jp">'+hl(x[2],q.value.trim())+'</td>'+
    '<td class="en'+(x[6]?' over':'')+'">'+hl(x[4],q.value.trim())+'</td>'+
    '<td class="m '+x[5]+'">'+x[5]+'</td></tr>').join('');
  const sy=r.value?synFor(r.value):'';const se=document.getElementById('syn');
  se.textContent=sy;se.style.display=sy?'block':'none';
  stat.textContent=view.length.toLocaleString()+' of '+ROWS.length.toLocaleString()+' rows';
  pgi.textContent='page '+(page+1)+' / '+Math.max(1,Math.ceil(view.length/PAGE));}
q.oninput=apply;m.onchange=apply;r.onchange=apply;d.onchange=apply;o.onchange=apply;
document.getElementById('prev').onclick=()=>{if(page>0){page--;draw();}};
document.getElementById('next').onclick=()=>{
  if((page+1)*PAGE<view.length){page++;draw();}};
apply();
</script>
"""


HSFC_LBA = 1568541


def stage_synopses(img=None):
    """Per-stage recap text keyed by STAGE record index.

    Reads HSFC from the IMAGE being compared (LBA 1568541), not from
    extracted/DATA_HSFC.BIN. The extracted copy is the untranslated Japanese
    original; patch_hsfc_recaps.py translates this bank, so reading the image
    gives the English recap when comparing against a patched build - which is
    what the header above the table should show.

    This game has no stage->record table: scenario titles are composed at
    runtime from format strings, which is why findstage.py identifies records by
    keyword census. But DATA_HSFC.BIN carries the intermission synopsis for each
    stage, three 50-byte lines per entry, in stage order.

    Aligning those to records was TESTED, not assumed. Scoring each synopsis's
    katakana against candidate records, versus a record 7 away:

        offset +0   mean 29.0   ratio 3.00
        offset +1   mean 77.7   ratio 7.69   <- record = synopsis + 1
        offset +2   mean 34.8   ratio 3.38
        offset -1   mean 16.3   ratio 1.45

    +1 wins decisively. It is still inference, so the text is shown as a
    synopsis and never as an authoritative stage number.
    """
    import collections
    raw = None
    if img and os.path.exists(img):
        try:
            f = open(img, "rb")
            f.seek(HSFC_LBA * SECTOR)
            raw = f.read(300000)
            f.close()
        except Exception:
            raw = None
    if raw is None:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(os.path.dirname(here), "extracted", "DATA_HSFC.BIN")
        if not os.path.exists(path):
            return {}
        raw = open(path, "rb").read()
    try:
        rec0 = banlz.decompress_all(bytearray(raw))[0][1]
    except Exception:
        return {}
    b = bytes(rec0)
    lines, i = [], 0
    while i < len(b):
        j = b.find(NULB, i)
        if j == -1:
            j = len(b)
        if j - i > 4:
            try:
                t = b[i:j].decode("cp932")
            except Exception:
                t = None
            # accept BOTH the japanese original and an english recap - the
            # bank is translated in a patched image, so requiring japanese
            # here would silently return nothing
            if t and (len(JP_RE.findall(t)) >= 4
                      or len(re.findall(r"[A-Za-z]", t)) >= 8):
                lines.append((i, t))
        i = j + 1
    g = collections.OrderedDict()
    for off, t in lines:
        g.setdefault((off - 182) // 150, []).append(t)
    out = {}
    for i, (k, v) in enumerate(sorted(g.items())):
        # Each entry is three 48-byte lines. Japanese needs no separator, but an
        # english recap is hard-wrapped mid-sentence, so joining bare produces
        # "Koujiand Tetsuya" / "asDouble Mazinger". Join with a space and
        # collapse, and fold the fullwidth punctuation the menu renderer
        # requires back to ASCII - this is a UI label, not game data.
        t = " ".join(x.strip() for x in v)
        t = t.replace(IDSPACE, " ")
        for fw, asc in ((u"．", "."), (u"，", ","), (u"！", "!"), (u"？", "?")):
            t = t.replace(fw, asc)
        out[i + 1] = " ".join(t.split())
    return out


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    jp_path, en_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    only_dlg = "--dialogue" in sys.argv
    only_rec = None
    if "--rec" in sys.argv:
        only_rec = int(sys.argv[sys.argv.index("--rec") + 1])

    tmp = tempfile.mkdtemp(prefix="srwzcmp")
    jp_img = as_image(jp_path, tmp)
    en_img = as_image(en_path, tmp)
    jp_items = load(jp_img)
    en_items = load(en_img)

    import collections
    rows, meth = [], {"pointer": 0, "same-offset": 0, "suspect": 0}
    cast = collections.defaultdict(collections.Counter)
    n = min(len(jp_items), len(en_items))
    for idx in range(n):
        if only_rec is not None and idx != only_rec:
            continue
        if jp_items[idx][1] is None or en_items[idx][1] is None:
            continue
        jb, eb = bytes(jp_items[idx][1]), bytes(en_items[idx][1])
        for jo, jt, eo, et, method in pair_record(jb, eb):
            if only_dlg and KAGI not in jt:
                continue
            meth[method] = meth.get(method, 0) + 1
            body = et.split("\n")[1:]
            over = bool(body) and max(ecols(l) for l in body) > 34
            parts = et.split(chr(10))
            if len(parts) > 1:
                sp = parts[0].strip()
                if sp and len(sp) < 24 and not sp.startswith(KAGI):
                    cast[idx][sp] += 1
            rows.append([idx, jo, jt, eo, et, method, 1 if over else 0])

    syn = stage_synopses(en_img)
    label = {}
    for idx in sorted(set(list(cast.keys()) + list(syn.keys()))):
        top = [n for n, _ in cast[idx].most_common(3)] if idx in cast else []
        label[idx] = {"cast": ", ".join(top), "syn": syn.get(idx, "")}
    io.open(out, "w", encoding="utf-8").write(
        HTML_HEAD + json.dumps(rows, ensure_ascii=False)
        + u";" + chr(10) + u"const CAST="
        + json.dumps(label, ensure_ascii=False) + HTML_TAIL)
    print("wrote %s" % out)
    print("  rows            : %d" % len(rows))
    for k in ("pointer", "same-offset", "suspect"):
        pc = 100.0 * meth.get(k, 0) / max(1, len(rows))
        print("  %-12s    : %6d  (%.1f%%)" % (k, meth.get(k, 0), pc))
    print("\nOpen it in a browser. Filter by pairing method - only 'pointer' "
          "rows are reliably matched.")


if __name__ == "__main__":
    main()
