"""Find dialogue regions in STAGE.BIN.

Dialogue is Shift-JIS interrupted by short control-code gaps (speaker tags,
line breaks, pauses). So: find SJIS runs, merge any separated by a small gap,
and keep the merged regions that carry enough text to be real dialogue.
"""
import sys
import json

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from sjisscan import is_lead, is_trail
from scenedump import decode_tolerant


def runs(data, min_chars=2):
    out = []
    i, n = 0, len(data)
    while i < n - 1:
        if is_lead(data[i]) and is_trail(data[i + 1]):
            start = i
            c = 0
            while i < n - 1 and is_lead(data[i]) and is_trail(data[i + 1]):
                i += 2
                c += 1
            if c >= min_chars:
                out.append((start, i))
        else:
            i += 1
    return out


def merge(spans, max_gap):
    if not spans:
        return []
    out = [list(spans[0])]
    for s, e in spans[1:]:
        if s - out[-1][1] <= max_gap:
            out[-1][1] = e
        else:
            out.append([s, e])
    return out


def main(path, out_path=None, max_gap=12, min_jp=20):
    data = open(path, "rb").read()
    regions = merge(runs(data), max_gap)
    recs = []
    for s, e in regions:
        raw = data[s:e]
        txt, jp = decode_tolerant(raw)
        if jp >= min_jp:
            recs.append({"offset": s, "nbytes": len(raw), "jp": jp, "text": txt})
    print("%d dialogue regions, %s Japanese chars"
          % (len(recs), "{:,}".format(sum(r["jp"] for r in recs))))
    if recs:
        print("offset range 0x%X .. 0x%X" % (recs[0]["offset"], recs[-1]["offset"]))
    if out_path:
        json.dump(recs, open(out_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("written to %s" % out_path)
    for r in recs[:4]:
        print("\n--- 0x%08X  %d bytes  %d JP ---" % (r["offset"], r["nbytes"], r["jp"]))
        print(r["text"][:360])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
