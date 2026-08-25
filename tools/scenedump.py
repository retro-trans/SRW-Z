"""Control-code-aware reader for DATA/STAGE.BIN scenario text.

STAGE.BIN interleaves Shift-JIS with single-byte control codes, so a plain
null-terminated reader shreds it. This walks the bytes, emitting text for
valid SJIS pairs and {XX} escapes for control bytes, so a record can be
round-tripped exactly.
"""
import sys
import json


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def is_trail(b):
    return 0x40 <= b <= 0x7E or 0x80 <= b <= 0xFC


def decode_tolerant(raw):
    """-> (display_text, japanese_char_count)"""
    out = []
    jp = 0
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if i + 1 < n and is_lead(b) and is_trail(raw[i + 1]):
            try:
                out.append(raw[i:i + 2].decode("shift_jis"))
                jp += 1
            except UnicodeDecodeError:
                out.append("{%02X}{%02X}" % (b, raw[i + 1]))
            i += 2
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            i += 1
        elif b in (0x0A, 0x0D):
            out.append("\n")
            i += 1
        else:
            out.append("{%02X}" % b)
            i += 1
    return "".join(out), jp


def records(data, min_jp=6):
    """Split on runs of nulls; keep chunks with enough Japanese to be prose."""
    recs = []
    i = 0
    n = len(data)
    while i < n:
        while i < n and data[i] == 0:
            i += 1
        start = i
        # a record ends at 2+ consecutive nulls
        while i < n:
            if data[i] == 0 and i + 1 < n and data[i + 1] == 0:
                break
            i += 1
        raw = data[start:i]
        if raw:
            txt, jp = decode_tolerant(raw)
            if jp >= min_jp:
                recs.append({"offset": start, "nbytes": len(raw),
                             "jp": jp, "text": txt})
    return recs


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    recs = records(data)
    print("%d scenario records, %s Japanese chars"
          % (len(recs), "{:,}".format(sum(r["jp"] for r in recs))))
    if len(sys.argv) > 2:
        json.dump(recs, open(sys.argv[2], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("written to %s" % sys.argv[2])
    for r in recs[:6]:
        print("\n--- 0x%08X (%d bytes, %d JP) ---" % (r["offset"], r["nbytes"], r["jp"]))
        print(r["text"][:300])
