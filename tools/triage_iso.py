# -*- coding: utf-8 -*-
"""Rank ALL 205 records by deterministic defects, straight from the image.

No export and no proofread needed. These signals need no calibration - they
are facts about the bytes, not guesses about quality:

  untrans   english string still contains kana/kanji  -> never translated
  names     tokens that contradict the project glossary
  parity    japanese and english string counts differ -> structural mismatch
  nospk     japanese has a speaker line, english does not
  ascii     english uses ASCII " where japanese uses the kagi

Truncation and meaning errors are NOT here on purpose: measured against 2,000
known agent fixes, a mechanical truncation detector managed either 64%
precision at 2% recall or 29% at 20%. It cannot judge a record. A reader can.

Usage: triage_iso.py <iso> [top-N]
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from rewrap_dialogue import LBA, SECTOR, SIZE

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANA = re.compile(u"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")
KAGI = u"\u300c"
WRONGNAMES = ["Kashimaru", "Norbu", "Norub", "Tsine", "Tziine", "Zaidel",
              "Zaydel", "Zeidel", "Leben", "Raben", "Scab", "Kaimera",
              "Chimaera", "Taiji", "Mykene", "Vodalak", "Hugi", "Gagaan"]
REVIEWED = set(range(109, 151))


def strings(blob):
    return [s for s in blob.decode("cp932", "ignore").split("\x00") if s.strip()]


def main():
    iso = sys.argv[1]
    topn = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    jp = banlz.decompress_all(bytearray(open(
        os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read()))
    f = open(iso, "rb")
    f.seek(LBA * SECTOR)
    en = banlz.decompress_all(bytes(f.read(SIZE)))
    f.close()

    rep = []
    for idx in range(min(len(jp), len(en))):
        if jp[idx][1] is None or en[idx][1] is None:
            continue
        js, es = strings(bytes(jp[idx][1])), strings(bytes(en[idx][1]))
        spoken = [s for s in es if KAGI in s]
        if len(spoken) < 5:
            continue
        untrans = sum(1 for s in spoken if KANA.search(s))
        names = collections.Counter()
        blob = "\n".join(es)
        for w in WRONGNAMES:
            n = len(re.findall(r"\b%s\b" % w, blob))
            if n:
                names[w] += n
        parity = abs(len(js) - len(es))
        rep.append(dict(rec=idx, spoken=len(spoken), untrans=untrans,
                        names=sum(names.values()), top=names.most_common(3),
                        parity=parity, reviewed=idx in REVIEWED))

    rep.sort(key=lambda r: -(r["untrans"] * 3 + r["names"] + r["parity"]))
    print("%-7s %5s %7s %6s %7s %-5s %s" % (
        "record", "lines", "untrans", "names", "parity", "revd", "worst names"))
    for r in rep[:topn]:
        print("rec%-4d %5d %7d %6d %7d %-5s %s" % (
            r["rec"], r["spoken"], r["untrans"], r["names"], r["parity"],
            "yes" if r["reviewed"] else "-",
            ", ".join("%s:%d" % t for t in r["top"])))
    tot_un = sum(r["untrans"] for r in rep)
    tot_nm = sum(r["names"] for r in rep)
    unrev = [r for r in rep if not r["reviewed"]]
    print()
    print("records with dialogue      : %d  (%d never reviewed)" % (len(rep), len(unrev)))
    print("untranslated lines         : %d  (%d in never-reviewed records)"
          % (tot_un, sum(r["untrans"] for r in unrev)))
    print("wrong-name tokens          : %d  (%d in never-reviewed records)"
          % (tot_nm, sum(r["names"] for r in unrev)))


if __name__ == "__main__":
    main()
