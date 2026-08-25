"""Dump null-terminated Shift-JIS strings from any file, with byte offsets.

Output is TSV: offset, byte_length, text. The byte length is the hard budget
for in-place replacement -- a translation must fit inside it.
"""
import sys
import json


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def jp_score(text):
    """Fraction of real double-byte Japanese. Deliberately EXCLUDES half-width
    katakana (U+FF61-FF9F): raw MIPS code decodes as that by chance and floods
    the results with noise."""
    if not text:
        return 0.0
    good = 0
    for ch in text:
        if "぀" <= ch <= "ヿ":                      # hiragana + katakana
            good += 1
        elif "一" <= ch <= "鿿":                     # CJK ideographs
            good += 1
        elif "！" <= ch <= "｠":                      # fullwidth ASCII/punct only
            good += 1
        elif ch in "、。「」・ー":
            good += 1
    return good / len(text)


def has_halfwidth_noise(text):
    return any("｡" <= ch <= "ﾟ" for ch in text)


def dump(path, min_len=4, min_jp=0.60, min_chars=2):
    data = open(path, "rb").read()
    out = []
    pos = 0
    n = len(data)
    while pos < n:
        end = data.find(b"\x00", pos)
        if end == -1:
            break
        raw = data[pos:end]
        if len(raw) >= min_len:
            try:
                txt = raw.decode("shift_jis")
            except UnicodeDecodeError:
                txt = None
            kana = sum(1 for ch in (txt or "") if "぀" <= ch <= "ヿ")
            if (txt and len(txt) >= min_chars
                    and not has_halfwidth_noise(txt)
                    and kana >= 1                      # real text has kana; code noise doesn't
                    and jp_score(txt) >= min_jp):
                out.append({"offset": pos, "nbytes": len(raw), "text": txt})
        pos = end + 1
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    rows = dump(path)
    print("%s: %d Japanese strings" % (path, len(rows)))
    total = sum(r["nbytes"] for r in rows)
    print("  %s bytes of text" % "{:,}".format(total))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print("  written to %s" % sys.argv[2])
    for r in rows[:20]:
        print("   0x%08X (%3d B)  %s" % (r["offset"], r["nbytes"], r["text"][:56]))
