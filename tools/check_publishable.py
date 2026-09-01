# -*- coding: utf-8 -*-
"""Refuse to publish the original japanese script.

`.gitignore` keeps the disc and the extracted files out of the repo, but it can
only match PATHS. It cannot see japanese prose sitting inside a .py or .json
that is otherwise perfectly publishable - which is exactly how 331 lines of the
original dialogue got in.

The project's own policy is already written down, in the tools themselves:

    extract_script.py  "it reads the image YOU dumped from YOUR OWN copy of the
                        game, so the original japanese never has to be
                        redistributed"
    build_compare.py   "Nothing here ships the original script."

So shipping japanese text is not only a risk, it is redundant: anyone who wants
the japanese side runs extract_script.py against their own disc.

WHAT COUNTS. The test is not "contains japanese" - that would fail the glossary,
which is 1,004 legitimate term pairs, and every tool that matches on a name like
レーベン or カイメラ. The test is a RUN of japanese prose: RUN_CHARS or more
japanese characters unbroken by latin text. At the default of 20 that catches
every dialogue line and every synopsis, and passes all 1,004 glossary entries
(their longest run is 15 - a product name) and every name literal in the tools.

    check_publishable.py            check the whole working tree
    check_publishable.py --staged   check only what is staged (pre-commit hook)
    check_publishable.py --strip    remove offending entries from rec*_en.py

Exit code 1 if anything is found, so it works as a git hook:

    printf '#!/bin/sh\\nexec python tools/check_publishable.py --staged\\n' \\
        > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
"""
import os
import re
import subprocess
import sys

RUN_CHARS = 20
# japanese, plus the punctuation that appears inside a run of it
JP = u"぀-ヿ一-鿿、。「」　！？（）・…"
RUN = re.compile(u"[%s]{%d,}" % (JP, RUN_CHARS))
ENTRY = re.compile(r"^\s*(\d+)\s*:\s*(['\"])")
SKIP = (".png", ".jpg", ".gif", ".pdf", ".zip", ".exe", ".bin", ".chd")


ANY_JP = re.compile(u"[぀-ヿ一-鿿]")


def offenders(text):
    return RUN.findall(text)


LATIN = re.compile(r"[A-Za-z]")


def untranslated(ln):
    """Is this payload entry an UNTRANSLATED row, rather than a translated one?

    The run test alone is not enough in a payload: a short line of dialogue is
    still the original script - 「あれ…」 is three characters - so length cannot
    be the test here.

    But "contains japanese" is much too broad, and getting this wrong destroys
    work. Plenty of entries are translated and merely keep a japanese SPEAKER:

        551: 'メール\\n"That's enough, you two!"'

    The body there is english; メール is a name, and names are fine. Dropping it
    would throw away a real translation. So an entry counts as untranslated only
    when it is SUBSTANTIALLY japanese - japanese present and almost no latin."""
    return (ENTRY.match(ln) and ANY_JP.search(ln)
            and len(LATIN.findall(ln)) < 3)


def bad_entries(text):
    return [ln for ln in text.split("\n") if untranslated(ln)]


def walk(root, staged):
    if staged:
        out = subprocess.run(["git", "diff", "--cached", "--name-only",
                              "--diff-filter=ACM"],
                             capture_output=True, text=True, cwd=root).stdout
        return [f for f in out.split() if not f.lower().endswith(SKIP)]
    # WHAT WOULD BE PUBLISHED IS WHAT GIT TRACKS, not what sits on disk.
    # os.walk was used here and could not tell the two apart, so a translation
    # table deliberately kept local - gitignored, and read by name_map.py only
    # "if still present in the tree" - was reported as unpublishable forever.
    # release.py archives with `git archive HEAD`, so tracked files are exactly
    # the right set. Falls back to a walk outside a git checkout.
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                         cwd=root)
    if out.returncode == 0 and out.stdout.strip():
        return [f for f in out.stdout.split("\n")
                if f.strip() and not f.lower().endswith(SKIP)]
    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for n in names:
            if n.lower().endswith(SKIP):
                continue
            files.append(os.path.relpath(os.path.join(base, n), root))
    return files


def strip_file(path):
    """Drop rec*_en.py entries whose VALUE is japanese prose.

    Such an entry would write japanese over japanese - a no-op at best - so
    removing it loses nothing. Only whole `<index>: '<text>',` lines are
    removed, so the dict stays valid."""
    lines = open(path, encoding="utf-8").read().split("\n")
    keep, dropped = [], 0
    for ln in lines:
        if untranslated(ln):
            dropped += 1
            continue
        keep.append(ln)
    if dropped:
        open(path, "w", encoding="utf-8", newline="\n").write("\n".join(keep))
    return dropped


def main():
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip() or "."
    staged = "--staged" in sys.argv
    strip = "--strip" in sys.argv
    bad, total, stripped = [], 0, 0

    for rel in walk(root, staged):
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            continue
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        runs = offenders(t) + bad_entries(t)
        if not runs:
            continue
        if strip and re.search(r"_en\.py$", rel):
            n = strip_file(p)
            stripped += n
            print("  stripped %-24s %d entries" % (rel, n))
            runs = offenders(open(p, encoding="utf-8").read()) + bad_entries(open(p, encoding="utf-8").read())
            if not runs:
                continue
        bad.append((rel, len(runs), max(runs, key=len)))
        total += len(runs)

    if strip:
        print("\nremoved %d untranslated entries" % stripped)
    if not bad:
        print("clean: no japanese prose runs of %d+ characters" % RUN_CHARS)
        return 0
    print("\nREFUSING: %d japanese prose run(s) in %d file(s)" % (total, len(bad)))
    for rel, n, worst in sorted(bad, key=lambda x: -x[1]):
        print("   %-40s %4d run(s), longest %3d: %s"
              % (rel, n, len(worst), worst[:40]))
    print("\nThe japanese side is regenerated locally with extract_script.py /"
          "\nbuild_compare.py against your own disc - it must not be committed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
