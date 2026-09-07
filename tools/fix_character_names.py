# -*- coding: utf-8 -*-
"""Spell each レイ by which one he/she is, and settle the Zeravire name.

Eureka Seven's Ray Beams stays "Ray"; SEED Destiny's Rey Za Burrel becomes
"Rey"; Amuro Ray and the Getter Rays are neither and are never touched.
ヒューギ・ゼラバイア is "Hugi" everywhere (98 spots still said "Hugy").

Every replacement is the same length as what it replaces, so nothing moves and
no pointer changes: the records are patched in place and recompressed into
their existing slots.

Usage: rey_fix.py [--write]
"""
import collections
import json
import os
import re
import sys

WORK = r'E:\Projects\SRW Z\_work'
sys.path.insert(0, os.path.join(WORK, 'tools'))
import banlz

SEC, LBA, SIZE = 2048, 1651029, 3910128
ISO = os.path.join(WORK, 'iso', 'srwz_cap.bin')
JPISO = os.path.join(WORK, 'iso', 'srwz.bin')

SEED = ['シン', 'アスラン', 'ルナマリア', 'キラ', 'タリア', 'デュランダル', 'ギルバート',
        'イザーク', 'ディアッカ', 'ミーア', 'ラクス', 'ハイネ', 'アーサー', 'カガリ',
        'ステラ', 'スティング', 'アウル', 'ネオ', 'ミネルバ', 'ザフト', 'インパルス',
        'フリーダム', 'ジャスティス', 'デスティニー', 'レジェンド', 'オーブ']
E7 = ['レントン', 'エウレカ', 'ホランド', 'タルホ', 'チャールズ', 'ドミニク', 'アネモネ',
      'デューイ', 'ストナー', 'ギジェット', 'ムーンドギー', 'ヒルダ', 'マシュー', 'ハップ',
      'ケンゴ', 'ゲッコーステート', 'ニルヴァーシュ', 'ビームス', 'コーラリアン', 'LFO']

TOKEN = re.compile(rb'(?<![A-Za-z])(Ray|Rey|Rei)(?![A-Za-z])')
KEEP = re.compile(rb'(Amuro|Getter)\s*$')   # bytes: a byte offset must never index a decoded string


def load(path):
    f = open(path, 'rb')
    f.seek(LBA * SEC)
    raw = f.read(SIZE)
    f.close()
    return raw


def recs(raw):
    return [(h, bytes(d)) for h, d in banlz.decompress_all(raw)
            if isinstance(h, int) and d is not None]


def fields(b):
    out = []
    i, n = 0, len(b)
    while i < n:
        if b[i] == 0:
            i += 1
            continue
        z = b.find(b'\x00', i)
        if z < 0:
            z = n
        t = b[i:z]
        if len(t) >= 2 and not any(c < 0x20 and c != 0x0A for c in t):
            out.append((i, t))
        i = z + 1
    return out


SEED_EN = [b'Shinn', b'Athrun', b'Luna', b'Kira', b'Talia', b'Durandal',
           b'Chairman', b'ZAFT', b'Minerva', b'Impulse', b'Destiny Gundam',
           b'Legend', b'Cagalli', b'Meer', b'Lacus', b'Heine', b'Stella',
           b'Neo ', b'Yzak', b'Dearka', b'Orb', b'Coordinator', b'FAITH']
E7_EN = [b'Renton', b'Eureka', b'Holland', b'Talho', b'Charles', b'Dominic',
         b'Anemone', b'Dewey', b'Stoner', b'Gidget', b'Moondoggie', b'Hilda',
         b'Matthieu', b'Hap', b'Gekko', b'Nirvash', b'Coralian', b'Beams',
         b'Vodarac', b'Ageha', b'trapar']


def series_of(text):
    """Which cast a line belongs to, judged on OUR english.

    The japanese cannot be reached by offset: our strings have been relocated
    since 0.9.38, so a japanese field at the same offset belongs to a
    different line entirely ([[pair-through-the-pointer-table]]). The english
    names the cast plainly, so read that.
    """
    seed = any(k in text for k in SEED_EN)
    e7 = any(k in text for k in E7_EN)
    if seed and not e7:
        return 'seed'
    if e7 and not seed:
        return 'e7'
    return None


def vote(fe, fj, k, span):
    votes = [series_of(fj.get(fe[j][0], b''))
             for j in range(max(0, k - span), min(len(fe), k + span + 1))]
    return votes.count('seed'), votes.count('e7')


def nearest(fe, fj, k, span=40):
    """Series of the closest field that names one cast and not the other.

    Fields are in offset order, which follows scene order, so the nearest
    marker is the scene the line belongs to. A fixed window mis-calls
    crossover stages, where Rey Za Burrel speaks in a stage whose text is
    mostly Eureka Seven (rec25, rec29) and Ray Beams speaks in stages that
    also carry SEED text (rec148).
    """
    own = series_of(fe[k][1])
    if own:
        return own
    for d in range(1, span + 1):
        for j in (k - d, k + d):
            if 0 <= j < len(fe):
                s = series_of(fe[j][1])
                if s:
                    return s
    return 'seed'      # Rey Za Burrel is main cast; Ray Beams is a guest and
                       # always has her own cast named close by


def main():
    write = '--write' in sys.argv
    raw = bytearray(load(ISO))
    live = recs(bytes(raw))
    jpr = recs(load(JPISO))
    heads = sorted(h for h, _ in live)

    edits = collections.Counter()
    unresolved = []
    touched = {}
    for ri, (hdr, be) in enumerate(live):
        d = bytearray(be)
        bj = jpr[ri][1] if ri < len(jpr) else b''
        fe = fields(be)
        fj = {o: t for o, t in fields(bj)}
        beams_rec = (b'Charles' in be) or (b'Beams' in be)
        changed = False
        for k, (o, t) in enumerate(fe):
            if not (TOKEN.search(t) or b'Hugy' in t):
                continue
            # --- the Zeravire name: always "Hugi" ---
            for m in re.finditer(rb'Hugy', t):
                d[o + m.start():o + m.start() + 4] = b'Hugi'
                edits['Hugy->Hugi'] += 1
                changed = True
            # --- which レイ ---
            try:
                s = t.decode('cp932')
            except UnicodeDecodeError:
                continue
            for m in TOKEN.finditer(t):
                cur = m.group(1).decode()
                if KEEP.search(t[max(0, m.start() - 10):m.start()]):
                    edits['kept (Amuro/Getter)'] += 1
                    continue
                s = nearest(fe, fj, k)
                want = {'seed': 'Rey', 'e7': 'Ray'}.get(s)
                # Ray Beams only ever appears in the stages that carry her own
                # arc. Anywhere else the speaker plate is Rey Za Burrel, even
                # when a neighbouring line happens to name a Eureka Seven ship.
                if want == 'Ray' and not beams_rec:
                    want = 'Rey'
                if want is None:
                    unresolved.append((ri, o, cur, t[:70]))
                    continue
                if cur != want:
                    d[o + m.start():o + m.start() + 3] = want.encode()
                    edits['%s->%s' % (cur, want)] += 1
                    changed = True
                else:
                    edits['already %s' % cur] += 1
        if changed:
            assert len(d) == len(be)
            touched[ri] = bytes(d)

    print('records touched: %d' % len(touched))
    for k, v in sorted(edits.items()):
        print('   %-22s %d' % (k, v))
    print('unresolved (left alone): %d' % len(unresolved))
    for ri, o, cur, t in unresolved:
        print('   rec%-4d @%#07x %s %r' % (ri, o, cur, t))
    if not write:
        print('\n(dry run - pass --write to apply)')
        return 0

    for ri in sorted(touched):
        hdr = live[ri][0]
        nxt = min([h for h in heads if h > hdr] or [len(raw)])
        blob = banlz.compress_record(touched[ri])
        if len(blob) > nxt - hdr:
            blob = banlz.compress_record_optimal(touched[ri])
        assert len(blob) <= nxt - hdr, 'rec%d does not fit (%d > %d)' % (
            ri, len(blob), nxt - hdr)
        raw[hdr:hdr + len(blob)] = blob
        for x in range(hdr + len(blob), nxt):
            raw[x] = 0
    after = [h for h, x in banlz.decompress_all(bytes(raw))
             if isinstance(h, int) and x is not None]
    assert after == heads, 'STAGE record set changed'
    f = open(ISO, 'r+b')
    f.seek(LBA * SEC)
    f.write(bytes(raw))
    f.close()
    print('\nSTAGE written')
    return 0


raise SystemExit(main())
