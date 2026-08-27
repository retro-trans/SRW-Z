# -*- coding: utf-8 -*-
"""Export the stage synopses as ENGLISH, keyed by scenario record.

analysis/stage_synopsis.json used to hold the JAPANESE synopsis for each record,
kept so a human could eyeball the record-to-synopsis match. That is the
publisher's prose, and this project does not redistribute it - the same rule
export_english_script.py follows for the dialogue. It was also redundant:
anyone who wants the japanese runs build_compare.py against their own japanese
disc and gets it locally.

So this writes OUR english instead, read from the image, and the file becomes
what it should have been - a translation artefact rather than a source dump.

WHERE IT COMES FROM. DATA_HSFC.BIN carries the intermission synopsis for each
stage as three ~50-byte lines, in stage order. build_compare.stage_synopses()
reassembles them, joining with a space (an english recap is hard-wrapped
mid-sentence, so joining bare produces "Koujiand Tetsuya") and folding the
fullwidth punctuation the menu renderer requires back to ASCII, because this is
a UI label rather than game data.

The record alignment was TESTED, not assumed - scoring each synopsis's katakana
against candidate records gave `record = synopsis + 1` a mean of 77.7 and a
ratio of 7.69, against 3.00 for +0 and 1.45 for -1. It is still inference, so
treat the number as a synopsis key rather than an authoritative stage number.

Usage: export_synopses.py <iso> [out.json]
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DEFAULT = os.path.join(ROOT, "analysis", "stage_synopsis.json")
JP = re.compile(u"[぀-ヿ一-鿿]")

NOTE = ("English stage synopses, read from DATA_HSFC.BIN in a patched image by "
        "tools/export_synopses.py. No original japanese: run "
        "tools/build_compare.py against your own japanese disc if you need the "
        "source text. Keyed by scenario record, where record = synopsis index "
        "+ 1 - an alignment tested by katakana overlap, not assumed.")


def main():
    iso = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bc", os.path.join(HERE, "build_compare.py"))
    bc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bc)

    syn = bc.stage_synopses(iso)
    if not syn:
        raise SystemExit("no synopses found - is %s a real image?" % iso)
    left = {k: v for k, v in syn.items() if JP.search(v)}
    if left:
        # Refuse rather than quietly writing japanese into a published file.
        print("REFUSING: %d synopses are still japanese: %s"
              % (len(left), sorted(left)[:8]))
        print("Translate DATA_HSFC.BIN first (patch_hsfc_recaps.py).")
        return 1
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"note": NOTE,
                    "synopses": {str(k): v for k, v in sorted(syn.items())}},
                   ensure_ascii=False, indent=1))
    print("wrote %s: %d synopses, 0 japanese characters"
          % (os.path.relpath(out, ROOT), len(syn)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
