# -*- coding: utf-8 -*-
"""Parallel full STAGE rebuild.

Records are independent, so apply+compress runs across all cores instead of
one-at-a-time. A no-cache full rebuild (every record changed) drops from ~80
minutes to a few. Output is identical to build_stage_variant.py full.

Usage: build_stage_par.py <iso> [workers]
"""
import glob, os, sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_stage as A
import banlz


def work(job):
    """(n, slot) -> (n, blob or None, msg). Runs in a worker process."""
    n, slot = job
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exp = A.apply_record(n)
            blob = A.compress_cached(n, exp, slot)
            rt, _ = banlz.decompress_record(blob, 0)
            assert rt == exp, "roundtrip fail"
    except Exception as e:
        return n, None, "FAIL %s" % e
    if len(blob) > slot:
        return n, None, "OVERSIZE %d>%d" % (len(blob), slot)
    return n, blob, buf.getvalue().strip().replace("\n", " | ")


def main():
    iso = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else max(1, (os.cpu_count() or 4) - 1)
    ids = sorted(int(os.path.basename(p)[3:6])
                 for p in glob.glob(os.path.join(A.WORK, "tools", "rec*_en.py")))
    stage = bytearray(open(os.path.join(A.WORK, "extracted", "DATA_STAGE.BIN"), "rb").read())
    recs = banlz.decompress_all(stage)

    jobs = []
    for n in ids:
        s1 = recs[n][0]
        s2 = recs[n + 1][0] if n + 1 < len(recs) else len(stage)
        jobs.append((n, s2 - s1))

    print("rebuilding %d records on %d workers..." % (len(jobs), workers), flush=True)
    applied = skipped = 0
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for n, blob, msg in ex.map(work, jobs):
            done += 1
            if blob is None:
                skipped += 1
                print("  rec%03d %s" % (n, msg), flush=True)
            else:
                s1 = recs[n][0]
                s2 = recs[n + 1][0] if n + 1 < len(recs) else len(stage)
                stage[s1:s2] = blob + b"\x00" * (s2 - s1 - len(blob))
                applied += 1
            if done % 25 == 0:
                print("  ...%d/%d" % (done, len(jobs)), flush=True)

    with open(iso, "r+b") as f:
        f.seek(A.STAGE_LBA * A.SECTOR)
        f.write(bytes(stage))
    print("applied=%d skipped=%d -> %s" % (applied, skipped, iso))


if __name__ == "__main__":
    main()
