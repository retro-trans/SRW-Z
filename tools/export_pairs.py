# -*- coding: utf-8 -*-
"""Export our English keyed by JAPANESE offset, so one disc is enough to compare.

build_compare.py needs two images: it pairs a japanese string to an english one
by following the pointer table through BOTH records. That is correct, but it
means anyone who wants to check the translation must first produce an english
image, and analysis/english_script.json cannot stand in - it is keyed by offsets
in OUR PATCHED layout, and apply_english_script.py says applying that to a
virgin japanese disc does not fully work.

So do the pairing ONCE, here, where both images exist, and record the result the
other way round:

    {record: {japanese_offset: "our english"}}

Now a reader with only their own japanese dump can look up every line: they have
the japanese offsets, and this supplies the english. tools/compare_translation.py
does exactly that.

This file contains NO japanese text - only offsets into a disc the reader
already owns - so it is publishable on the same terms as english_script.json.

Usage: export_pairs.py <japanese-image> <english-image> <out.json>
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from build_compare import pair_record, JP_RE
from rewrap_dialogue import LBA, SECTOR, SIZE


def records(path):
    f = open(path, "rb")
    f.seek(LBA * SECTOR)
    d = f.read(SIZE)
    f.close()
    return banlz.decompress_all(d)


def main():
    jp_path, en_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    J, E = records(jp_path), records(en_path)
    pairs, rows, weak, untr = {}, 0, 0, 0
    for i in range(min(len(J), len(E))):
        jb, eb = J[i][1], E[i][1]
        if jb is None or eb is None:
            continue
        got = {}
        for jo, _jt, _eo, et, method in pair_record(bytes(jb), bytes(eb)):
            if method != "pointer":
                # Only pointer-paired rows are recorded. A same-offset guess is
                # right for rows that never moved and wrong for every relocated
                # one, and publishing a guess as if it were a translation is
                # worse than publishing nothing.
                weak += 1
                continue
            if not (et and et.strip()):
                continue
            if JP_RE.search(et):
                # Still japanese: this row is not translated yet, and copying
                # it here would republish the original script - the publish
                # gate caught exactly that. Record it as an EMPTY string so
                # the reader is told "not translated yet" rather than being
                # shown nothing, without carrying the japanese across.
                got[str(jo)] = ""
                untr += 1
                continue
            got[str(jo)] = et
            rows += 1
        if got:
            pairs[str(i)] = got
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"note": "Our English keyed by JAPANESE string offset, so a "
                            "reader needs only their own japanese disc. No "
                            "japanese text is stored - a row still awaiting translation is "
                            "recorded as an empty string. Pointer-paired rows only.",
                    "pairs": pairs}, ensure_ascii=False, indent=0))
    print("records %d, english rows %d, marked untranslated %d, "
          "dropped %d unreliable pairings" % (len(pairs), rows, untr, weak))
    print("wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
