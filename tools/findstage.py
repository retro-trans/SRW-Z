"""Identify which decompressed STAGE record holds which stage's dialogue,
by keyword census."""
import sys
import os
import glob

KEYS = {
    "setsuko": "セツコ",
    "toby": "トビー",
    "denzel": "デンゼル",
    "virgola": "バルゴラ",
    "lutetium": "ルテチウム",
    "rand": "ランド",
    "mail": "メール",
    "glory": "グローリー・スター",
    "dialogue": "「",
}
enc = {k: v.encode("shift_jis") for k, v in KEYS.items()}

rows = []
for path in sorted(glob.glob(sys.argv[1])):
    data = open(path, "rb").read()
    counts = {k: data.count(v) for k, v in enc.items()}
    rows.append((os.path.basename(path), len(data), counts))

print("%-12s %9s | %s" % ("record", "size", " ".join("%8s" % k for k in KEYS)))
for name, size, c in rows:
    if sum(v for k, v in c.items() if k != "dialogue") == 0:
        continue
    print("%-12s %9s | %s" % (name, "{:,}".format(size),
                              " ".join("%8d" % c[k] for k in KEYS)))
