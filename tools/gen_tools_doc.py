# -*- coding: utf-8 -*-
"""Generate TOOLS.md - one line per tool, grouped by what it is for.

Written as a generator rather than a hand-kept document because a hand-kept
index of 150+ tools is wrong within a week. Each entry's description comes from
the tool's own docstring, so the document cannot drift from the code: if a tool
is added, removed or re-documented, re-run this and commit the result.

    python tools/gen_tools_doc.py

The section blurbs below are the part a generator cannot write - they say which
tools matter and why, which is the thing a newcomer actually needs.
"""
import collections
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (heading, filename pattern, blurb)
SECTIONS = [
    ("The pipeline",
     r"^(extract_script|apply_script|export_english_script|apply_english_script"
     r"|build_compare)\.",
     "The five you need on day one. `extract_script` pulls every string out of "
     "an image YOU dumped into editable JSON; you translate the `text` fields; "
     "`apply_script` writes them back. Round-trip is exact - extract, change "
     "nothing, apply, and the image is byte-identical. The `english_script` "
     "pair moves this project's English in and out as standalone source, which "
     "is what makes the repo forkable without shipping the publisher's text."),

    ("Gates - run these before every build",
     r"^(verify_pointers|verify_elf_patches|integrity|check_publishable"
     r"|fix_dead_links|scan_visible_defects|verify_iso|verify_stage_iso"
     r"|verify_spirits)\.",
     "Each of these exists because something shipped broken. `verify_pointers` "
     "is the important one: the failure it catches produces an image that "
     "boots, plays, and freezes only when a save is loaded. `check_publishable` "
     "is the newest - it reads CONTENT rather than paths, so it can see the "
     "original japanese sitting inside an otherwise publishable file, which "
     "`.gitignore` cannot."),

    ("Libraries - imported, not run",
     r"^(banlz|banlz_strict|patch|pool|rewrap_dialogue|codes)\.",
     "`banlz` is the Banpresto LZ codec, ported from the boot ELF; almost "
     "everything else depends on it. `patch` holds the text encoder - note "
     "that ASCII 0x2E-0x3D are CONTROL CODES to the menu reader, so menu text "
     "must be encoded with `patch.encode(s, \"menu\")` rather than plain cp932. "
     "`pool` handles the COMPDATA string pool."),

    ("ISO plumbing",
     r"^(isolist|isoextract|bin2iso|splice_file|update_dirsize|diff_images"
     r"|pullelf|triage_iso)\.",
     "Reading and writing the disc itself: list the ISO9660 tree, pull a file "
     "out, splice one back in, fix the directory record when a file changes "
     "size, and diff two 3.5GB images at sector granularity."),

    ("Build and packaging",
     r"^(build_|stamp_|zkn_build|project_stats)",
     "`stamp_build` fingerprints every region the game loads, so \"what changed "
     "between these two builds?\" is answerable without extracting both CHDs - "
     "a question that once cost a day. `project_stats` measures translation "
     "coverage from the image rather than from any tool's report."),

    ("Translation data",
     r"_en\.py$|^(soundsel_names|weapon_words)",
     "Not tools - dictionaries. Mostly japanese term to english name, which is "
     "reference material rather than script: the japanese side is the LOOKUP "
     "KEY the patch tools match on, so it cannot be removed without breaking "
     "them."),

    ("Applying text to the image", r"^apply_", ""),
    ("Fixing specific defects", r"^fix_",
     "Each of these was written for one bug found by someone playing the game "
     "and noticing something wrong on screen. They are kept because the "
     "TECHNIQUE generalises even when the specific fix does not."),
    ("Patching the executable, art and UI", r"^patch_",
     "The largest family, because most of the UI is not text at all. Anything "
     "that cannot be found as cp932 anywhere on the disc is ART, and has to be "
     "repainted with the artwork's own palette indices."),
    ("Generators", r"^gen_", ""),
    ("Scanning and auditing", r"^(scan_|audit_|.*_audit|.*_report|status)", ""),
    ("Searching", r"^(find_|link_|why_)", ""),
    ("Font and texture work",
     r"(font|atlas|glyph|tim2|raster|swizz|vwf|hwatlas|micro)",
     "The font is HALF-WIDTH, not variable-width: the stamper writes a constant "
     "12 and the advance hook adds 1, giving a flat 13px pitch. See "
     "docs/VWF.md and docs/CUSTOM_FONT.md before touching any of this."),
    ("Battle voice lines (SRVC)", r"^srvc_",
     "Captions are free-length once the sequence records are repointed with "
     "`--free`, so there is no byte budget to fight."),
    ("Live instrumentation", r"^(pine_|.*monitor|.*\.ps1)",
     "PCSX2 is driven over its PINE socket to watch the running game - where a "
     "string is drawn, which code path renders it. See docs/DEBUGGER_TRACE.md."),
    ("Layout and re-wrapping", r"(rewrap|reflow|respace|tighten|fit|slice)",
     "Dialogue is 3 lines of 34 columns; scenario-chart recaps get 56."),
]

NO_DOC = {
    "capture.ps1": "Screenshot capture helper for PCSX2.",
    "click.ps1": "Send a mouse click to the emulator window.",
    "drive.ps1": "Drive the emulator through a scripted input sequence.",
    "nav_charsel.ps1": "Navigate to the character-select screen.",
    "nav_corridor.ps1": "Navigate to the corridor scene.",
    "nav_tocorr.ps1": "Navigate toward the corridor scene.",
    "disasm.py": "Small MIPS disassembler used by the RE tools.",
}


def summarise(path):
    t = io.open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r'"""(.*?)"""', t, re.S)
    if not m:
        return ""
    d = m.group(1).strip()
    first = re.split(r"\n\s*\n", d)[0]
    return re.sub(r"\s+", " ", first).strip()


def main():
    files = sorted(n for n in os.listdir(HERE) if n.endswith((".py", ".ps1")))
    desc = {}
    for n in files:
        desc[n] = summarise(os.path.join(HERE, n)) or NO_DOC.get(n, "")

    seen, groups = set(), collections.OrderedDict()
    for head, rx, blurb in SECTIONS:
        g = [n for n in files if n not in seen and re.search(rx, n)]
        seen.update(g)
        groups[head] = (g, blurb)
    groups["Everything else"] = ([n for n in files if n not in seen], "")

    out = []
    w = out.append
    w("# The tools\n")
    w("Every script in `tools/`, what it is for, and how to run it. Generated "
      "from the tools' own docstrings by `tools/gen_tools_doc.py` - re-run it "
      "after adding or removing a tool rather than editing this file.\n")
    w("**If you are starting a translation**, you need five of them: "
      "`extract_script.py`, `apply_script.py`, and the three gates "
      "`verify_pointers.py`, `verify_elf_patches.py`, `integrity.py`. "
      "Everything else is there for when you hit the specific problem it "
      "solves. Start with [TRANSLATING.md](TRANSLATING.md).\n")
    w("Two warnings that are not obvious from any docstring:\n")
    w("* **Verify against the image, not against a tool's report.** Several "
      "bugs here were \"the fix existed and never reached the image\". A tool "
      "saying it applied 400 changes is not evidence the game changed.\n")
    w("* **Menu text is not cp932.** ASCII `0x2E-0x3D` are control codes to "
      "the menu reader, so digits and periods in menu strings must go through "
      "`patch.encode(s, \"menu\")`.\n")
    w("| Section | Tools |")
    w("| --- | ---: |")
    for head, (g, _b) in groups.items():
        if g:
            w("| [%s](#%s) | %d |"
              % (head, head.lower().replace(" ", "-").replace(",", "")
                 .replace("(", "").replace(")", "").replace("--", "-"), len(g)))
    w("")
    for head, (g, blurb) in groups.items():
        if not g:
            continue
        w("## %s\n" % head)
        if blurb:
            w(blurb + "\n")
        for n in g:
            d = desc.get(n, "")
            w("**`%s`**  \n%s\n" % (n, d if d else "_(no description)_"))
    txt = "\n".join(out).replace("\r\n", "\n").replace("\n", "\r\n")
    io.open(os.path.join(ROOT, "TOOLS.md"), "wb").write(txt.encode("utf-8"))
    print("wrote TOOLS.md: %d tools in %d sections"
          % (len(files), sum(1 for _h, (g, _b) in groups.items() if g)))


if __name__ == "__main__":
    main()
