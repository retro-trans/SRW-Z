# -*- coding: utf-8 -*-
"""Fingerprint every region the game loads, so "what changed between two builds?"
is answerable instantly.

Written 2026-08-17, after the chapter-2 stall. That bug was found by extracting
two CHDs (~7 GB, ~15 min) and sector-diffing them, purely to learn that v1.26 ->
v1.27 changed STAGE.BIN and COMPDATA and nothing else. This makes that a lookup.

Do NOT infer build contents from file mtimes: a CHD's mtime is when the ~8 minute
build FINISHED, so back-dating it to guess which ELF shipped is unreliable - it
pointed at an innocent ELF diff while v1.26 and v1.27 actually shipped identical
ELFs.

Usage:
    python tools/stamp_build.py <iso> <version> [note...]   # record a build
    python tools/stamp_build.py --diff <verA> <verB>        # what changed
    python tools/stamp_build.py --list
"""
import hashlib
import json
import os
import struct
import sys

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(WORK, "analysis", "build_manifest.json")
SEC = 2048

# The regions the game actually reads. Sizes are the shipped extents; COMPDATA is
# read from wherever its dir record points (it gets relocated into DMY padding).
REGIONS = [
    ("ELF",       455,     3471624),
    ("SRVC",      1313214, None),
    ("MTV_PROS",  1573437, 9056),
    ("STAGE",     1651029, 3910128),
    ("MAPNAME",   1652939, None),
    ("COMPDATA",  1823000, None),
    ("ZKN_KW",    1823200, None),
    ("ZKN_RT",    1824000, None),
    ("ZKN_PT",    1573457, 136 * SEC),
    ("VT1",       1588772, None),      # title-card bank lives here
    ("KVMDATA",   1289810, None),      # UI word-sheets (bazaar, intermission)
    ("HSFC",      1568541, None),      # episode-recap bank (save screen)
    ("NISVDATA",  1568269, 272 * SEC),  # help book (rec6) + its contents (rec0)
]
# Last resort only. A fixed default silently TRUNCATES: COMPDATA is 74 sectors,
# so hashing 64 covered none of the episode-title region and reported v1.44 and
# v1.45 as identical when they were not. Real extents come from the ISO9660
# directory below; this is used only for an LBA the directory does not describe.
DEFAULT_LEN = 256 * SEC


def dir_sizes(f):
    """{start_lba: size_in_bytes} for every file, straight from the ISO9660 tree.

    Relocated files (COMPDATA lives in DMY padding) are covered because the
    patcher repoints their dir record, which is also what the game reads.
    """
    out = {}
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    stack = [(struct.unpack_from("<I", root, 2)[0],
              struct.unpack_from("<I", root, 10)[0])]
    seen = set()
    while stack:
        lba, ln = stack.pop()
        if (lba, ln) in seen:
            continue
        seen.add((lba, ln))
        f.seek(lba * SEC)
        data = f.read(ln)
        p = 0
        while p < len(data):
            rl = data[p]
            if rl == 0:
                p = (p // SEC + 1) * SEC
                continue
            e_lba = struct.unpack_from("<I", data, p + 2)[0]
            e_sz = struct.unpack_from("<I", data, p + 10)[0]
            flags = data[p + 25]
            nlen = data[p + 32]
            if flags & 2:
                if nlen > 1:
                    stack.append((e_lba, e_sz))
            else:
                out[e_lba] = max(out.get(e_lba, 0), e_sz)
            p += rl
    return out


def load():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {}


def game_table_lba(f, name):
    """Resolve a file's CURRENT LBA/size from the game's own table.

    Files relocate when they grow (SRVC moved to 1826000, COMPDATA to 1823000),
    and a hardcoded LBA then hashes a stale copy - which is exactly how a
    fully-translated SRVC still measured as 98% untranslated.
    Fields sit at name+0x28, NOT +0x20.
    """
    f.seek(0)
    boot = f.read(0x120000)
    k = boot.find(name)
    if k < 0:
        return None
    lba, nsec = struct.unpack_from("<II", boot, k + 0x28)
    if 0 < lba < 4000000 and 0 < nsec < 500000:
        return lba, nsec * SEC
    return None


RELOCATABLE = {
    "SRVC": b"\\\\BTL\\\\SRVC.BIN;1",
    "COMPDATA": b"\\\\DATA\\\\COMPDATA.BN;1",
    "ZKN_KW": b"\\\\DATA\\\\MTVZKNKW.BIN;1",
    "ZKN_RT": b"\\\\DATA\\\\MTVZKNRT.BIN;1",
    "ZKN_PT": b"\\\\DATA\\\\MTVZKNPT.BIN;1",
}


def stamp(iso, version, note):
    f = open(iso, "rb")
    sizes = dir_sizes(f)
    out = {}
    for name, lba, ln in REGIONS:
        if name in RELOCATABLE:
            hit = game_table_lba(f, RELOCATABLE[name])
            if hit:
                lba, ln = hit
        src = ("game-table" if name in RELOCATABLE and ln else
               "declared" if ln else
               "iso-dir" if lba in sizes else "DEFAULT")
        n = ln or sizes.get(lba) or DEFAULT_LEN
        f.seek(lba * SEC)
        data = f.read(n)
        out[name] = {
            "lba": lba,
            "bytes": len(data),
            "src": src,
            "sha1": hashlib.sha1(data).hexdigest(),
        }
    f.close()

    m = load()
    m[version] = {"iso": os.path.basename(iso), "note": note, "regions": out}
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=1, sort_keys=True)
    print("stamped %s (%s)" % (version, note or "no note"))
    for k, v in sorted(out.items()):
        print("   %-10s LBA %-8d %8d B  %-8s %s"
              % (k, v["lba"], v["bytes"], v["src"], v["sha1"][:12]))
    if any(v["src"] == "DEFAULT" for v in out.values()):
        print("   WARNING: some regions fell back to DEFAULT_LEN and may be "
              "truncated - their hashes can report false 'identical'")


def diff(a, b):
    m = load()
    for v in (a, b):
        if v not in m:
            sys.exit("no stamp for %s (have: %s)" % (v, ", ".join(sorted(m))))
    ra, rb = m[a]["regions"], m[b]["regions"]
    print("%s -> %s" % (a, b))
    if m[a].get("note"):
        print("   %s: %s" % (a, m[a]["note"]))
    if m[b].get("note"):
        print("   %s: %s" % (b, m[b]["note"]))
    print()
    same, changed = [], []
    for k in sorted(set(ra) | set(rb)):
        x, y = ra.get(k), rb.get(k)
        if not x or not y:
            changed.append("%-10s ONLY IN ONE BUILD" % k)
        elif x["sha1"] != y["sha1"]:
            changed.append("%-10s CHANGED  %s -> %s"
                           % (k, x["sha1"][:12], y["sha1"][:12]))
        else:
            same.append(k)
    if changed:
        print("CHANGED:")
        for c in changed:
            print("   " + c)
    else:
        print("CHANGED: nothing - these builds are identical")
    print("\nidentical: %s" % ", ".join(same))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--list":
        m = load()
        for v in sorted(m):
            print("%-20s %s" % (v, m[v].get("note", "")))
        return
    if sys.argv[1] == "--diff":
        diff(sys.argv[2], sys.argv[3])
        return
    stamp(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:]))


if __name__ == "__main__":
    main()
