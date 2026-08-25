# -*- coding: utf-8 -*-
"""Fill apply_stage's blob cache in PARALLEL.

apply_stage compresses each record on one core, and compression - especially the
optimal DP parse it falls back to when the greedy result misses the slot - runs
about a minute per record. Re-applying ~115 records therefore costs roughly two
hours of wall clock on a machine that is otherwise idle.

The cache is keyed purely by content (rec%03d_<sha1(exp)>.lz), so the blobs can
be produced in any order by any process. This computes them across a process
pool and writes the cache files; a subsequent apply_stage run then hits the
cache for every record and finishes in the time it takes to splice.

Usage: prewarm_stage.py <rec> [<rec> ...]
       prewarm_stage.py --changed        (uses analysis/recs_changed.txt)
"""
import hashlib
import io
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

WORK = r"E:\Projects\SRW Z\_work"
CACHE = os.path.join(WORK, "analysis", "blob_cache")


def _compress(job):
    """Runs in a worker process: compress one record and write its cache file."""
    import sys as _s
    _s.path.insert(0, os.path.join(WORK, "tools"))
    import banlz
    n, exp, slot, path = job
    t = time.time()
    blob = banlz.compress_record(exp)
    how = "greedy"
    if len(blob) > slot:
        blob = banlz.compress_record_optimal(exp)
        how = "optimal"
    with open(path, "wb") as f:
        f.write(blob)
    return n, len(blob), slot, how, time.time() - t


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if "--changed" in sys.argv:
        p = os.path.join(WORK, "analysis", "recs_changed.txt")
        ids = [int(x) for x in io.open(p, encoding="utf-8").read().split()]
    else:
        ids = [int(a) for a in sys.argv[1:]]
    if not ids:
        raise SystemExit("no records given")

    import banlz
    import apply_stage as A

    os.makedirs(CACHE, exist_ok=True)
    stage = bytearray(open(os.path.join(WORK, "extracted",
                                        "DATA_STAGE.BIN"), "rb").read())
    recs = banlz.decompress_all(stage)

    # Building the expanded records is cheap; do it here so the workers only
    # have to compress (and so apply_record's chatter stays in one process).
    jobs = []
    hits = 0
    devnull = io.StringIO()
    real_stdout = sys.stdout
    for n in ids:
        sys.stdout = devnull
        try:
            exp = A.apply_record(n)
        finally:
            sys.stdout = real_stdout
        s1 = recs[n][0]
        s2 = recs[n + 1][0] if n + 1 < len(recs) else len(stage)
        slot = s2 - s1
        h = hashlib.sha1(bytes(exp)).hexdigest()[:16]
        path = os.path.join(CACHE, "rec%03d_%s.lz" % (n, h))
        if os.path.exists(path):
            hits += 1
            continue
        jobs.append((n, bytes(exp), slot, path))

    workers = max(1, (os.cpu_count() or 4) - 2)
    print("%d records: %d already cached, %d to compress on %d workers"
          % (len(ids), hits, len(jobs), workers))
    if not jobs:
        print("nothing to do - apply_stage will be all cache hits")
        return

    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for n, nb, slot, how, dt in ex.map(_compress, jobs):
            done += 1
            flag = "" if nb <= slot else "   !! OVERSIZE"
            print("  [%3d/%3d] rec%03d %6d/%-6d %-7s %5.1fs%s"
                  % (done, len(jobs), n, nb, slot, how, dt, flag))
    print("compressed %d records in %.1f min" % (len(jobs), (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
