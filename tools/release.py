# -*- coding: utf-8 -*-
"""Cut a release: branch it, archive the source, attach everything.

A release is not just the patch. Someone finding this later needs the code that
built it and the optional extras, and needs them PINNED - `main` moves on, so a
patch with no matching source becomes unreproducible within a week. So every
version gets:

    release/vX.Y.Z            a branch pinned to the commit that built it
    SRWZ-English-vX.Y.Z.xdelta   the patch
    SRWZ-texture-pack.zip        optional crisper UI art
    SRWZ-source-vX.Y.Z.zip       the toolchain and translation at that version

The source archive comes from `git archive HEAD`, so it contains exactly what
is TRACKED - no disc image, no extracted game data, nothing .gitignore keeps
out. That is checked here rather than assumed, because this is the artefact
that gets downloaded.

Run it from a clean tree, after the patch is built and the release exists.

Usage: release.py <version> [--repo owner/name] [--dry]
       release.py 0.8.97
"""
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the patch, the pack and the source archive all live beside the working
# copy of the game, not next to the repo
WORK = os.path.join(os.path.dirname(ROOT), "SRW Z")
BAD = (".bin", ".chd", ".iso", ".cue", ".img", ".elf", ".exe", ".zip",
       ".7z", ".rar", ".xdelta", ".pss", ".msb")


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    ver = args[0].lstrip("v")
    dry = "--dry" in sys.argv
    repo = (sys.argv[sys.argv.index("--repo") + 1]
            if "--repo" in sys.argv else "retro-trans/SRW-Z")
    tag = "v" + ver
    branch = "release/" + tag

    dirty = run(["git", "status", "--porcelain"]).stdout.strip()
    if dirty:
        print("working tree is not clean - a release branch should pin exactly "
              "what shipped:\n%s" % dirty)
        if not dry:
            return 1

    # 1. the branch, pinned to HEAD
    have = run(["git", "rev-parse", "--verify", branch]).returncode == 0
    print("branch %s: %s" % (branch, "exists" if have else "creating"))
    if not have and not dry:
        r = run(["git", "branch", branch])
        if r.returncode:
            print(r.stderr.strip())
            return 1
    if not dry:
        run(["git", "push", "-q", "origin", branch])

    # 2. the source archive, from tracked content only
    src = os.path.join(WORK, "SRWZ-source-%s.zip" % tag)
    if not dry:
        r = run(["git", "archive", "--format=zip",
                 "--prefix=SRWZ-%s/" % tag, "-o", src, "HEAD"])
        if r.returncode:
            print(r.stderr.strip())
            return 1
        names = zipfile.ZipFile(src).namelist()
        bad = [n for n in names if n.lower().endswith(BAD)]
        if bad:
            os.remove(src)
            print("REFUSING: the source archive contains game data or "
                  "binaries: %s" % bad[:6])
            return 1
        print("source archive: %d files, %.1f MB, no game data"
              % (len(names), os.path.getsize(src) / 1048576.0))

    # 3. the texture pack, rebuilt so it matches this version
    pack = os.path.join(WORK, "_work", "dist", "SRWZ-texture-pack.zip")
    gen = os.path.join(ROOT, "tools", "build_texture_pack.py")
    if os.path.exists(gen) and not dry:
        run([sys.executable, gen])
    print("texture pack: %s" % ("found" if os.path.exists(pack) else "MISSING"))

    # 4. attach
    patch = os.path.join(WORK, "SRWZ-English-%s.xdelta" % tag)
    assets = [p for p in (patch, pack, src) if os.path.exists(p)]
    print("attaching to %s %s:" % (repo, tag))
    for a in assets:
        print("   %s" % os.path.basename(a))
    if dry:
        print("\n(dry run)")
        return 0
    r = subprocess.run(["gh", "release", "upload", tag] + assets +
                       ["--repo", repo, "--clobber"],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr.strip())
        return 1
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
