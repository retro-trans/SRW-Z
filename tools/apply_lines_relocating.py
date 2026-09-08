# -*- coding: utf-8 -*-
u"""Apply new dialogue text, relocating a line when it no longer fits its slot.

apply_stage_json.py refuses anything larger than the slot it found. That is
right for ordinary edits, but some rows were TRUNCATED by an earlier pass -
their japanese is a full sentence and their english is a fragment like "Alan!"
with zero spare bytes - so restoring the real line always needs more room than
the slot has.

This tool writes in place when it fits and otherwise moves the field into free
text space and repoints it, with the same guards the bracket pass uses:

  * only NUL runs the JAPANESE holds text or text padding in are usable, so a
    string is never written over structure (that froze stage 19);
  * a gap never starts on the zero that TERMINATES the string before it;
  * a word whose japanese target is not text is never repointed (that broke
    enemy turns in 0.9.67);
  * a row with a pointer aimed inside it is skipped, because moving it would
    strand that pointer;
  * afterwards every untouched pointer must still resolve to the same text.

Usage: apply_lines_relocating.py <fixes.json> [--write]
       fixes.json = {"rec:hash:occ": "Speaker\\n「text」", ...}
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import reflow_dialogue as R
import export_proofread as EP
import fix_stranded_strings as F
import fix_struct_intrusions as X
import restore_brackets as RB
import apply_stage_json as A

SEC, LBA, SIZE = 2048, 1651029, 3910128
ISO, JPISO = 'iso/srwz_cap.bin', 'iso/srwz.bin'
NL = '\n'


def main():
    fixes = json.load(open(sys.argv[1], encoding='utf-8'))
    write = '--write' in sys.argv
    adv = R.load_adv(ISO)

    f = open(ISO, 'r+b' if write else 'rb')
    f.seek(LBA * SEC)
    raw = bytearray(f.read(SIZE))
    live = [(h, bytearray(d)) for h, d in banlz.decompress_all(bytes(raw))
            if isinstance(h, int) and d is not None]
    heads = sorted(h for h, _ in live)
    fj = open(JPISO, 'rb')
    fj.seek(LBA * SEC)
    jpraw = fj.read(SIZE)
    fj.close()
    jp = [d for h, d in banlz.decompress_all(jpraw)
          if isinstance(h, int) and d is not None]

    byrec = {}
    for k in fixes:
        byrec.setdefault(int(k.split(':')[0]), []).append(k)

    inplace = moved = 0
    failed = []
    touched = {}
    for rec in sorted(byrec):
        d = live[rec][1]
        eb = bytes(d)
        jb = bytes(jp[rec])
        key_of = A.keys_of(eb, jb, rec)
        off_of = {v: k for k, v in key_of.items()}
        bm = R.boxmap(d)
        pm = F.pointer_map(eb)
        smask = X.safe_mask(jb)
        protected = X.struct_words(jb, smask)
        before = {w: F.text_at(eb, v) for v, ws in pm.items() for w in ws
                  if w not in protected}
        # gaps are computed AFTER the in-place writes below, in phase 2
        moved_words = set()
        changed = False
        pending = []
        for k in byrec[rec]:
            off = off_of.get(k)
            if off is None:
                failed.append((k, 'key not found in this record'))
                continue
            zt = eb.find(b'\x00', off)
            if any(off < v < zt for v in pm):
                failed.append((k, 'a pointer aims inside this field'))
                continue
            # NOT EVERY FIELD IS A 3-LINE DIALOGUE BOX. Four rows (rec1 x2,
            # rec25 x2) are long-form encyclopedia prose wrapped at about 36
            # columns over 15-25 lines, with no speaker plate. wrap_field would
            # read their first line as the speaker and rewrap the rest into
            # three long dialogue lines - silently, since a short enough entry
            # still comes out under the 3-line ceiling. Refuse them here, at
            # the one choke point every sweep goes through, rather than relying
            # on each caller to remember.
            if eb[off:zt].count(b'\n') > 3:
                failed.append((k, 'long-form prose, not a 3-line dialogue box'))
                continue
            over = bm.get(off, 1) == 1
            nf, nl = A.wrap_field(fixes[k], over, adv)
            nb = nf.encode('cp932', 'strict')
            if nl > 3:
                failed.append((k, '%d lines, more than the box allows' % nl))
                continue
            z = d.find(b'\x00', off)
            e = z
            while e < len(d) and d[e] == 0:
                e += 1
            slot = e - off - 1
            pending.append((k, off, nb, slot))

        # TWO PHASES, like restore_brackets. Everything that already fits is
        # written FIRST, because such a write can grow a field into padding a
        # gap list had counted as free. Relocating against a gap list taken
        # before those writes hit the 'gap is not free' assertion and aborted
        # the whole run. Then the movers go LARGEST FIRST, so the long lines
        # get the big runs instead of finding them spent on short ones.
        for k, off, nb, slot in pending:
            if len(nb) <= slot:
                d[off:off + slot + 1] = nb + b'\x00' * (slot + 1 - len(nb))
                moved_words.update(pm.get(off, []))
                inplace += 1
                changed = True
        gaps = RB.free_gaps(d, jb)
        for k, off, nb, slot in sorted(pending, key=lambda x: -len(x[2])):
            if len(nb) <= slot:
                continue
            if RB.relocate(d, jb, off, nb, pm, protected, gaps, moved_words,
                           smask):
                moved += 1
                changed = True
            else:
                failed.append((k, 'needs %d bytes, slot %d, no gap free'
                               % (len(nb), slot)))
        if changed:
            for w in protected:
                assert d[w:w + 4] == eb[w:w + 4], \
                    'rec%d structure pointer %#x moved' % (rec, w)
            nd = bytes(d)
            for w, t in before.items():
                nv = struct.unpack_from('<I', nd, w)[0] - F.BASE
                got = F.text_at(nd, nv)
                if w in moved_words:
                    assert got is not None, \
                        'rec%d word %#x stopped resolving' % (rec, w)
                else:
                    assert got == t, \
                        'rec%d word %#x no longer resolves to its text' % (rec, w)
            touched[rec] = bytes(d)

    print('written in place : %d' % inplace)
    print('relocated        : %d' % moved)
    print('could not apply  : %d' % len(failed))
    for k, why in failed:
        print('   %s  %s' % (k, why))
    print('records touched  : %s' % sorted(touched))
    if not touched or not write:
        if touched:
            print('(dry run - pass --write to apply)')
        return 0

    for rec in sorted(touched):
        h = live[rec][0]
        nxt = min([x for x in heads if x > h] or [len(raw)])
        blob = banlz.compress_record(touched[rec])
        if len(blob) > nxt - h:
            blob = banlz.compress_record_optimal(touched[rec])
        assert len(blob) <= nxt - h, 'rec%d over slot' % rec
        raw[h:h + len(blob)] = blob
        for x in range(h + len(blob), nxt):
            raw[x] = 0
    after = [hh for hh, x in banlz.decompress_all(bytes(raw))
             if isinstance(hh, int) and x is not None]
    assert after == heads, 'STAGE record set changed'
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print('STAGE written')
    return 0


raise SystemExit(main())
