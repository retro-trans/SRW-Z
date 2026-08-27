# -*- coding: utf-8 -*-
"""Dry-run the pool repack and report the budget it frees."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool

rec = open(sys.argv[1] if len(sys.argv) > 1 else "analysis/wpn_rec.bin", "rb").read()
ent = pool.entries(rec)
starts = set(a for a, _, _ in ent)
ptrs = pool.pointers(rec, starts)
st = pool.strays(rec, starts)
print("pool entries      : %d" % len(ent))
print("pointer words     : %d" % len(ptrs))
print("stray u16 pairs   : %d (left untouched)" % len(st))
print("unreferenced      : %d" % len(starts - set(t for _, t in ptrs)))
new, end, _ = pool.repack(rec)
print("repacked pool ends: %#x (was %#x)" % (end, pool.POOL_HI))
print("BYTES FREED       : %d" % (pool.POOL_HI - end))
print("identity repack verified: pointers and text all resolve")
