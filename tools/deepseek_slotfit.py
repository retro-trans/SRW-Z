# -*- coding: utf-8 -*-
"""Make a record fit its compressed STAGE slot by reverting the longest English
rows to Japanese (removing them from T) until the blob fits. Reverted rows stay
JP in-game and are logged to deepseek_review.json. Zero Claude cost.

Usage: deepseek_slotfit.py <N> [<N> ...]
"""
import importlib.util as u
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import apply_stage

WORK = r'E:\Projects\SRW Z\_work'
REV = WORK + r'\analysis\deepseek_review.json'


def bl(s):
    return len(s.encode('cp932', 'replace'))


def slot_for(n, stage_recs, stage_len):
    s1 = stage_recs[n][0]
    s2 = stage_recs[n + 1][0] if n + 1 < len(stage_recs) else stage_len
    return s2 - s1


def main():
    stage = bytearray(open(WORK + r'\extracted\DATA_STAGE.BIN', 'rb').read())
    recs = banlz.decompress_all(stage)
    rev = json.load(open(REV)) if os.path.exists(REV) else {}

    for a in sys.argv[1:]:
        n = int(a)
        slot = slot_for(n, recs, len(stage))
        p = 'rec%03d_en.py' % n
        s = u.spec_from_file_location('m%d' % n, p)
        m = u.module_from_spec(s)
        s.loader.exec_module(m)
        T = dict(m.T)
        wk = {r['i']: r for r in json.load(
            open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))}

        reverted = []

        def build_and_size():
            # write T to a temp module-like dict and run apply_record's expansion
            import importlib
            # monkey: reuse apply_stage.apply_record by writing T back to file each time is slow;
            # instead replicate expansion here.
            dec = WORK + r'\analysis\stage_dec\rec%03d.bin' % n
            rows = json.load(open(WORK + r'\analysis\rec%03d_script.json' % n, encoding='utf-8'))
            exp = bytearray(open(dec, 'rb').read())
            for idx, en in sorted(T.items()):
                r = rows[idx]
                enc = en.encode('cp932', 'replace')
                bud = r.get('budget', r['nbytes'])
                if len(enc) > bud:
                    continue
                off = r['offset']
                exp[off:off + bud] = enc + b'\x00' * (bud - len(enc))
            apply_stage.heal_cues(exp, rows)
            # GREEDY only (fast); greedy >= optimal size, so fitting greedy => apply fits
            return len(banlz.compress_record(bytes(exp)))

        size = build_and_size()
        # revert longest english rows (by encoded length) until it fits.
        # re-test every 15 reverts since even greedy compression isn't free.
        order = sorted((i for i in T), key=lambda i: -bl(T[i]))
        oi = 0
        while size > slot and oi < len(order):
            i = order[oi]
            oi += 1
            if i not in T:
                continue
            del T[i]
            reverted.append(i)
            if len(reverted) % 15 == 0:
                size = build_and_size()
        size = build_and_size()

        # write back
        lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue (DeepSeek)."""' % n,
                 "", "T = {"]
        for k in sorted(T):
            lines.append("    %d: %r," % (k, T[k]))
        lines.append("}")
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")

        key = 'rec%03d' % n
        entry = rev.get(key, {})
        prev = set(entry.get('jp_untranslated', []))
        allover = sorted(prev | set(reverted) | {i for i in wk if i in T and bl(T[i]) > wk[i]['budget']})
        entry['jp_untranslated'] = allover
        entry['over_count'] = len(allover)
        entry['slot_reverted'] = sorted(reverted)
        entry['note'] = ('DeepSeek. jp_untranslated stay Japanese in-game (byte budget '
                         'or slot-size); fix in a targeted Claude pass.')
        rev[key] = entry
        print("rec%03d: slot %d, final blob %d, reverted %d rows -> %d english / %d total"
              % (n, slot, size, len(reverted), len(T) - sum(1 for i in T if i in wk and bl(T[i]) > wk[i]['budget']), len(m.T)))

    json.dump(rev, open(REV, 'w'), indent=1)


if __name__ == "__main__":
    main()
