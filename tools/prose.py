"""Separate real scenario prose from compiled bytecode in STAGE.BIN records.

Prose records are dense: most of their bytes are Shift-JIS text. Bytecode
records only contain incidental characters. Density (jp*2 / nbytes) splits
them cleanly.
"""
import sys
import json

rows = json.load(open(sys.argv[1], encoding="utf-8"))
min_density = float(sys.argv[2]) if len(sys.argv) > 2 else 0.55

for r in rows:
    r["density"] = (r["jp"] * 2.0) / max(1, r["nbytes"])

prose = [r for r in rows if r["density"] >= min_density]
prose.sort(key=lambda r: r["offset"])

print("%d/%d records are prose (density >= %.2f)" % (len(prose), len(rows), min_density))
print("total Japanese: %s chars" % "{:,}".format(sum(r["jp"] for r in prose)))
if prose:
    print("offset range: 0x%X .. 0x%X" % (prose[0]["offset"], prose[-1]["offset"]))

out = sys.argv[3] if len(sys.argv) > 3 else None
if out:
    json.dump(prose, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written to %s" % out)

print("\n=== FIRST 3 PROSE RECORDS ===")
for r in prose[:3]:
    print("\n--- 0x%08X  %d bytes  %d JP  density %.2f ---"
          % (r["offset"], r["nbytes"], r["jp"], r["density"]))
    print(r["text"][:420])
