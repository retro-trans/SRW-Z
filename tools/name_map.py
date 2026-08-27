# -*- coding: utf-8 -*-
"""Ship the name maps as FINGERPRINTS, and rebuild them from your own disc.

The name tables key english on the japanese - `"斗牙": "Touga"` - because that
is how the patchers find the string: `patch_compdata.py` does
`d.find(jp.encode("cp932"))` and requires a NUL on both sides. So the japanese
is a SEARCH NEEDLE, not content. It still cannot be published: it is the
publisher's text, and shipping it breaks the rule the rest of the project keeps.

It does not have to be published, because it is one command away. The disc has
it, and a fingerprint is enough to find it again:

    export   {sha1(japanese)[:16]: "English"}     <- this is what ships
    rebuild  {japanese: "English"}                <- built locally, gitignored

A hash identifies the string without carrying it, so the map still works for
anyone with their own copy of the game, and nobody gets the japanese from us.

The patchers then load the REBUILT map and their matching logic is unchanged.

    name_map.py --export <jp-iso>    write analysis/name_map.json (ships)
    name_map.py --rebuild <jp-iso>   write analysis/_name_map_local.json (local)
    name_map.py --verify <jp-iso>    prove the rebuild reproduces the original

VERIFY IS THE POINT. A fingerprint map that silently resolves fewer names than
the table it replaced would quietly drop translations, so --verify compares the
rebuilt map against the original tables pair by pair and reports any it could
not recover.
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import banlz

COMPDATA_LBA, COMPDATA_LEN = 1823000, 74 * 2048
SHIP = os.path.join(ROOT, "analysis", "name_map.json")
LOCAL = os.path.join(ROOT, "analysis", "_name_map_local.json")
# (module, attribute) pairs holding japanese -> english
SOURCES = [("compdata_en", "PILOTS"), ("compdata_en", "TITLES"),
           ("compdata_en", "SHORT"), ("gen_missing3_en", "NAMES")]


def fp(b):
    return hashlib.sha1(b).hexdigest()[:16]


def original_pairs():
    """The japanese-keyed tables, if they are still present in the tree."""
    out = {}
    for mod, attr in SOURCES:
        p = os.path.join(HERE, mod + ".py")
        if not os.path.exists(p):
            continue
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod, p)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        except Exception:
            continue
        d = getattr(m, attr, None)
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(k, str) and isinstance(v, str):
                    out[k] = v
    return out


def find_compdata(iso):
    """COMPDATA is not at a fixed LBA.

    A virgin japanese disc has it at 1568198; this project's builds relocate it
    to 1823000 because it grew. So try both and keep whichever actually
    decompresses, rather than assuming one and failing on the other."""
    f = open(iso, "rb")
    for lba, ln in ((1568198, 160 * 2048), (COMPDATA_LBA, COMPDATA_LEN)):
        f.seek(lba * 2048)
        raw = f.read(ln)
        try:
            items = banlz.decompress_all(raw)
            if items and items[0][1]:
                f.close()
                return bytes(items[0][1])
        except Exception:
            pass
    f.close()
    raise SystemExit("could not find COMPDATA in %s" % iso)


def strings_in(iso):
    """Every NUL-terminated string in COMPDATA, as raw bytes."""
    plain = find_compdata(iso)
    out, i = [], 0
    while i < len(plain):
        z = plain.find(b"\x00", i)
        if z < 0:
            break
        if z > i:
            out.append(plain[i:z])
        i = z + 1
    return out


def export(iso):
    pairs = original_pairs()
    if not pairs:
        raise SystemExit("no japanese-keyed tables found - nothing to export")
    present = {fp(s) for s in strings_in(iso)}
    ship, missing = {}, 0
    for jp, en in pairs.items():
        h = fp(jp.encode("cp932", "ignore"))
        if h not in present:
            missing += 1
            continue
        ship[h] = en
    io.open(SHIP, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"note": "Name map keyed by sha1 of the japanese string, so "
                            "the original text is never redistributed. Rebuild "
                            "the usable map from your own disc with "
                            "tools/name_map.py --rebuild <iso>.",
                    "names": ship}, ensure_ascii=False, indent=1,
                   sort_keys=True))
    print("exported %d fingerprints -> %s" % (len(ship),
                                              os.path.relpath(SHIP, ROOT)))
    if missing:
        print("   %d pairs had no exact string in this image and were dropped "
              "(they never matched anyway - the patcher requires NULs on both "
              "sides)" % missing)


def rebuild(iso):
    if not os.path.exists(SHIP):
        raise SystemExit("no %s - run --export first" % os.path.basename(SHIP))
    ship = json.load(io.open(SHIP, encoding="utf-8"))["names"]
    out = {}
    for s in strings_in(iso):
        en = ship.get(fp(s))
        if en is not None:
            try:
                out[s.decode("cp932")] = en
            except Exception:
                pass
    io.open(LOCAL, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print("rebuilt %d of %d names -> %s"
          % (len(out), len(ship), os.path.relpath(LOCAL, ROOT)))
    return out


def verify(iso):
    pairs = original_pairs()
    if not pairs:
        print("original tables are gone; cannot compare. Rebuild only.")
        return rebuild(iso) and 0
    export(iso)
    got = rebuild(iso)
    present = {fp(s) for s in strings_in(iso)}
    recoverable = {k: v for k, v in pairs.items()
                   if fp(k.encode("cp932", "ignore")) in present}
    lost = [k for k, v in recoverable.items() if got.get(k) != v]
    print("\noriginal pairs                    : %d" % len(pairs))
    print("of those, present in this image    : %d" % len(recoverable))
    print("recovered by the fingerprint map   : %d" % (len(recoverable) - len(lost)))
    if lost:
        print("NOT recovered: %d  %s" % (len(lost), lost[:6]))
        return 1
    print("\nevery recoverable name round-trips - the japanese tables can go.")
    return 0


def main():
    if "--export" in sys.argv:
        return export(sys.argv[sys.argv.index("--export") + 1]) or 0
    if "--rebuild" in sys.argv:
        rebuild(sys.argv[sys.argv.index("--rebuild") + 1])
        return 0
    if "--verify" in sys.argv:
        return verify(sys.argv[sys.argv.index("--verify") + 1])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
