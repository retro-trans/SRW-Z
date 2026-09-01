# -*- coding: utf-8 -*-
"""Translate DATA/COMPDATA.BN (names, episode titles, bios) and splice it.

COMPDATA.BN = one banlz record that decompresses to a 524KB database bundle:
pilot records ([id][02][last 21B][first 22B][display 24B][stats]), the unit
display-name list (NUL-padded 8-aligned slots), episode-title list, profile
bios. Nothing is pointer-indexed (verified), so every edit is IN-PLACE
within each string's NUL-slot budget.

Names are patched by exact-field match: a JP key is replaced only where it
occupies a whole NUL-terminated field (preceded by NUL/0x02/record id after
NUL, followed by NUL) and the English fits the slot. Unit names use the
akurasu map over the unit-list region; pilot names over the whole record
(field-anchored matching keeps single-kanji keys safe).

Recompressed output usually EXCEEDS the original 144,990B slot (the factory
compressor is stronger), so the file is relocated into /DMY/DMY.BIN's
padding region and COMPDATA.BN's directory record (LBA+size, both-endian)
is repointed. Usage: patch_compdata.py <iso>
"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from compdata_en import PILOTS, TITLES, BIOS, SHORT, AMBIG
from patch import encode as _menc


def menu_bytes(en):
    """Menu-encode display text: raw 0x2E-0x3D (./0-9:;<=) are CONTROL CODES
    to the menu reader. "Type100" rendered as "TypeDijeh" on the upgrade
    screen: it drew "Type", swallowed "100" and the NUL as control+params,
    and ran on into the next name field. Every menu-drawn string must carry
    those characters fullwidth; strings without them encode identically."""
    return _menc(en, "menu")

SECTOR = 2048
ORIG_LBA, ORIG_SIZE = 1568198, 144990
NEW_LBA = 1823000                 # inside /DMY/DMY.BIN (LBA 1765044 + 122MB)
UNIT_LO, UNIT_HI = 0x6C000, 0x72000   # unit display-name list region
WPN_LO, WPN_HI = 0x66380, 0x6C000     # weapon display-name list region
TITLE_LO, TITLE_HI = 0x72000, 0x74000


def load_units():
    m = {}
    for line in open(r"E:\Projects\SRW Z\_work\analysis\akurasu_units.txt",
                     encoding="utf-8"):
        if "|" in line:
            jp, en = line.rstrip("\n").split("|", 1)
            m[jp] = en
    # composed forms seen in the table
    m["バルゴラ（１号機）"] = "Virgola Unit 1"
    m["バルゴラ（２号機）"] = "Virgola Unit 2"
    m["バルゴラ（３号機）"] = "Virgola Unit 3"
    m["抗体コーラリアン"] = "Coralian Antibody"
    return m


def field_replace(d, jp, en, lo=0, hi=None, stats=None):
    """Replace whole NUL-terminated fields equal to jp, budget permitting."""
    hi = hi if hi is not None else len(d)
    jb = jp.encode("cp932")
    eb = menu_bytes(en)
    n = 0
    i = d.find(jb, lo)
    while 0 <= i < hi:
        j = i + len(jb)
        prev = d[i - 1]
        if d[j] == 0 and (prev == 0 or prev == 0x02):
            k = j
            while k < len(d) and d[k] == 0:
                k += 1
            budget = k - i - 1
            eb2 = eb
            if len(eb2) > budget and jp in SHORT:
                eb2 = menu_bytes(SHORT[jp])
            if len(eb2) <= budget:
                d[i:i + budget] = eb2 + b"\x00" * (budget - len(eb2))
                n += 1
            elif stats is not None:
                stats.append((jp, en, budget))
        i = d.find(jb, i + 1)
    return n


def bio_replace(d, bios, lo=0, hi=None, stats=None):
    """Replace character-select bios, which are keyed by sha1(japanese).

    BIOS cannot be keyed by the japanese itself - that would commit japanese
    prose - so the lookup runs the other way round: walk the NUL-delimited
    fields actually present on the disc, hash each one, and translate the
    ones we hold an english line for.
    """
    hi = hi if hi is not None else len(d)
    n, i = 0, lo
    while i < hi:
        j = d.find(b"\x00", i)
        if j < 0 or j > hi:
            break
        if j - i > 20:
            try:
                jp = d[i:j].decode("cp932")
            except UnicodeDecodeError:
                jp = None
            if jp is not None:
                en = bios.get(
                    hashlib.sha1(d[i:j]).hexdigest()[:16])
                if en is not None:
                    n += field_replace(d, jp, en, max(0, i - 1), hi, stats)
        i = j + 1
        while i < hi and d[i] == 0:
            i += 1
    return n


def field_replace_prefixed(d, jp, en, lo=0, hi=None, stats=None):
    """Replace the NAME part of fields shaped [u16 id][name].

    Enemy designations appear twice: bare (メカブースト) and with a 2-byte binary
    id in front (\\x83\\x03 + メカブースト). field_replace deliberately refuses the
    second form - its `prev == 0 or prev == 0x02` guard is what stops us
    clobbering binary - but that prefixed record is the one the battle box
    actually shows, which is why メカブースト stayed Japanese on screen while the
    bare copy next to it was translated.

    So match the prefixed form explicitly and rewrite ONLY the text after the
    id, leaving the two id bytes untouched.
    """
    hi = hi if hi is not None else len(d)
    jb = jp.encode("cp932")
    eb = menu_bytes(en)
    n = 0
    i = d.find(jb, lo)
    while 0 <= i < hi:
        j = i + len(jb)
        if i >= 3 and d[j] == 0 and d[i - 1] != 0 and d[i - 2] != 0 \
                and d[i - 3] == 0:
            k = j
            while k < len(d) and d[k] == 0:
                k += 1
            budget = k - i - 1
            eb2 = eb
            if len(eb2) > budget and jp in SHORT:
                eb2 = menu_bytes(SHORT[jp])
            if len(eb2) <= budget:
                d[i:i + budget] = eb2 + b"\x00" * (budget - len(eb2))
                n += 1
            elif stats is not None:
                stats.append((jp, en, budget))
        i = d.find(jb, i + 1)
    return n


def field_replace_prefixed_whole(d, jp, en, lo=0, hi=None, stats=None):
    """Replace [u16 id][name] records where the WHOLE field matches.

    The safe fix for what field_replace_prefixed got wrong (v1.49 revert:
    it matched substrings and produced ミChiru/スRey). Here a match needs
    the ENTIRE NUL-delimited field to be exactly [2 id bytes][jp][NUL], so
    a name can never match inside a longer name. This is what the battle
    status name plate reads (ロラン stayed Japanese there while the bare
    copy 0x2E bytes later was 'Loran').
    """
    hi = hi if hi is not None else len(d)
    jb = jp.encode("cp932")
    eb = menu_bytes(en)
    n = 0
    i = d.find(jb, lo)
    while 0 <= i < hi:
        j = i + len(jb)
        # field must be exactly [id0 id1][jp]: NUL at j, field starts at
        # i-2, byte before the field (i-3) is NUL. The id's HIGH byte is
        # always tiny (observed 0x01-0x03) - no SJIS trail or ASCII byte is
        # <= 7, so a two-byte kana/letter can never masquerade as an id
        # (that masquerade is exactly how v1.49 minted スRey/ミChiru).
        if (i >= 3 and d[j] == 0 and 0 < d[i - 1] <= 7 and d[i - 2] != 0
                and d[i - 3] == 0):
            k = j
            while k < len(d) and d[k] == 0:
                k += 1
            budget = k - i - 1
            eb2 = eb
            if len(eb2) > budget and jp in SHORT:
                eb2 = menu_bytes(SHORT[jp])
            if len(eb2) <= budget:
                d[i:i + budget] = eb2 + b"\x00" * (budget - len(eb2))
                n += 1
            elif stats is not None:
                stats.append((jp, en, budget))
        i = d.find(jb, i + 1)
    return n


def main():
    iso_path = sys.argv[1]
    comp = open(r"E:\Projects\SRW Z\_work\extracted\DATA_COMPDATA.BN", "rb").read()
    recs = banlz.decompress_all(comp)
    d, _ = banlz.decompress_record(comp, recs[0][0])
    d = bytearray(d)

    over = []
    import json
    wmap = json.load(open(r"E:\Projects\SRW Z\_work\analysis\weapons_en.json",
                          encoding="utf-8"))
    from patch import encode as menc
    n_wpn = 0
    for jp, en in sorted(wmap.items(), key=lambda x: -len(x[0])):
        enb = menc(en, "menu")
        jb = jp.encode("cp932")
        i = d.find(jb, WPN_LO)
        while 0 <= i < WPN_HI:
            j = i + len(jb)
            if d[j] == 0 and d[i-1] == 0:
                k = j
                while d[k] == 0: k += 1
                budget = k - i - 1
                if len(enb) <= budget:
                    d[i:i+budget] = enb + bytes(budget - len(enb))
                    n_wpn += 1
            i = d.find(jb, i + 1)
    print("weapon fields:", n_wpn)
    # ITEMS/PARTS (region 0x65108-0x66380): names + effect/flavor descriptions,
    # drawn on menu screens -> menu-encode (fullwidth 0x2E-0x3D digits/punct).
    n_item = 0
    try:
        items_en = json.load(open(r"E:\Projects\SRW Z\_work\analysis\items_en.json",
                                  encoding="utf-8"))
        items_jp = json.load(open(r"E:\Projects\SRW Z\_work\analysis\items_jp.json",
                                  encoding="utf-8"))
        ibud = {it["off"]: it["budget"] for it in items_jp}
        for off_str, en in items_en.items():
            off = int(off_str)
            b = ibud.get(off)
            if b is None:
                continue
            enc = menc(en, "menu")
            if len(enc) <= b:
                d[off:off + b] = enc + bytes(b - len(enc))
                n_item += 1
    except FileNotFoundError:
        pass
    print("item fields:", n_item)
    # UI strings: leader-bonus effects/names, pilot stat help, search screen.
    # Offset-keyed and menu-encoded (same renderer as the item/parts screens).
    n_ui = 0
    try:
        from compdata_ui_en import COMPDATA_UI
        try:
            from compdata_ui_en_b import COMPDATA_UI_B
            COMPDATA_UI = dict(COMPDATA_UI)
            COMPDATA_UI.update(COMPDATA_UI_B)
        except ImportError:
            pass
        # SRWZ_SKIP_UI_FROM=<hex>: skip UI writes at/after this offset (bisect aid)
        _skip = os.environ.get("SRWZ_SKIP_UI_FROM")
        if _skip:
            _lo = int(_skip, 16)
            COMPDATA_UI = {k: v for k, v in COMPDATA_UI.items() if k < _lo}
            print("  (skipping UI offsets >= %#x)" % _lo)
        for off, en in COMPDATA_UI.items():
            e = d.index(b"\x00", off)
            k = e
            while k < len(d) and d[k] == 0:
                k += 1
            bud = k - off
            enc = menc(en, "menu")
            if len(enc) < bud:
                d[off:off + bud] = enc + bytes(bud - len(enc))
                n_ui += 1
    except ImportError:
        pass
    print("UI fields:", n_ui)
    # Pilot battle quotes (defeat / retreat lines). These render in the battle
    # message box through the DIALOGUE path, so they go in as raw ASCII - not
    # menu-encoded like the menu-screen strings above.
    n_bq = 0
    try:
        from battle_quotes_en import BATTLE_QUOTES
        try:
            from battle_quotes_en_b import BATTLE_QUOTES_B
            BATTLE_QUOTES = dict(BATTLE_QUOTES)
            BATTLE_QUOTES.update(BATTLE_QUOTES_B)
        except ImportError:
            pass
        for off, en in BATTLE_QUOTES.items():
            e = d.index(b"\x00", off)
            k = e
            while k < len(d) and d[k] == 0:
                k += 1
            bud = k - off
            enc = en.encode("cp932", "replace")
            if len(enc) < bud:
                d[off:off + bud] = enc + bytes(bud - len(enc))
                n_bq += 1
    except ImportError:
        pass
    print("battle quotes:", n_bq)
    # Library / help database (0x74000+): menu-rendered, but sequences like <0>,
    # <15> and [31] are BUTTON/ICON TOKENS built from bytes 0x2E-0x3D. Those must
    # stay raw - menu-encoding them to fullwidth would break the icon, the same
    # failure class as the 0x0C link markers. So encode text and tokens apart.
    import re as _re
    _TOK = _re.compile(r"(<-?\d+>|\[\d+\])")

    def _enc_lib(t):
        out = b""
        for part in _TOK.split(t):
            if not part:
                continue
            out += part.encode("cp932") if _TOK.fullmatch(part) else menc(part, "menu")
        return out

    n_lib = 0
    try:
        LIB = {}
        for _mod, _var in (("library_en", "LIBRARY_EN"), ("library_en_b", "LIBRARY_EN_B"),
                           ("library_en_c", "LIBRARY_EN_C"), ("library_en_d", "LIBRARY_EN_D"),
                           ("library_en_e", "LIBRARY_EN_E"), ("library_en_f", "LIBRARY_EN_F"),
                           ("library_en_g", "LIBRARY_EN_G"), ("library_en_h", "LIBRARY_EN_H")):
            LIB.update(getattr(__import__(_mod), _var))
        for off, en in LIB.items():
            e = d.index(b"\x00", off)
            k = e
            while k < len(d) and d[k] == 0:
                k += 1
            bud = k - off
            enc = _enc_lib(en)
            if len(enc) < bud:
                d[off:off + bud] = enc + bytes(bud - len(enc))
                n_lib += 1
    except ImportError:
        pass
    print("library/help fields:", n_lib)
    n_unit = 0
    for jp, en in sorted(load_units().items(), key=lambda x: -len(x[0])):
        n_unit += field_replace(d, jp, en, UNIT_LO, UNIT_HI, over)
    # The 117 mecha names load_units() never covered - the display-name list
    # runs 0x6D0C0..0x6EB58 and was only ~1/3 translated. Hand-authored canon
    # names (tools/units_en.py), NOT transliteration: Hepburn gives 'MajingaZ'
    # and 'Zanbotto3' for Mazinger Z and Zambot 3.
    #
    # Bounded to the NAME list on purpose. Past 0x6EBF0 the region holds 641 BGM
    # entries whose tail (ランド２, ケイ１ＥＶ, トリノミアス, エーデルＧ) are per-character
    # CUE IDENTIFIERS, not display text - the same trap that once rewrote 165
    # fields instead of 102. Do not widen this range.
    try:
        from units_en import UNITS as UNITS_EXTRA
        for jp, en in sorted(UNITS_EXTRA.items(), key=lambda x: -len(x[0])):
            n_unit += field_replace(d, jp, en, 0x6D000, 0x6EB80, over)
    except ImportError:
        pass
    # Ability/skill descriptions (0x6B8F0..0x6D0C0). Keyed by OFFSET, not by
    # string: these are prose, and several are near-identical (the HP/EN 10/20/30%
    # variants differ by one character), so a string-keyed replace would be
    # ambiguous. Each write re-checks that the slot still starts with Japanese
    # before touching it, so a shifted offset fails loudly instead of corrupting
    # a neighbour.
    n_abil = 0
    try:
        from abilities_en import ABILITIES
        for off, en in sorted(ABILITIES.items()):
            end = d.find(b"\x00", off)
            cur = bytes(d[off:end])
            try:
                cur_s = cur.decode("cp932")
            except UnicodeDecodeError:
                cur_s = ""
            if not any(u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿" for c in cur_s):
                print("  !! ability slot 0x%05X is not Japanese - skipped" % off)
                continue
            k = end
            while k < len(d) and d[k] == 0:
                k += 1
            budget = k - off - 1
            eb = menu_bytes(en)
            if len(eb) > budget:
                over.append((cur_s, en, budget))
                continue
            d[off:off + budget] = eb + b"\x00" * (budget - len(eb))
            n_abil += 1
        print("ability descriptions: %d fields" % n_abil)
    except ImportError:
        pass

    # Remaining pilot/character DB fields (DeepSeek, tools/db_deepseek.py).
    # OFFSET-keyed for the same reason as the abilities pass: 0..0x66380 is
    # mostly binary structures, and 448 of 1,112 "Japanese-looking" strings in
    # there are noise, so a string match is free to land inside binary. Each
    # write re-checks the slot still holds Japanese before touching it.
    n_db = 0
    try:
        _dbp = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "analysis", "db_apply.json")
        _db = json.load(open(_dbp, encoding="utf-8"))
        for off_s, en in _db.items():
            off = int(off_s)
            end = d.find(b"\x00", off)
            try:
                cur = bytes(d[off:end]).decode("cp932")
            except UnicodeDecodeError:
                continue
            if not any(u"぀" <= c <= u"ヿ" or u"一" <= c <= u"鿿" for c in cur):
                continue                      # already English or moved
            k = end
            while k < len(d) and d[k] == 0:
                k += 1
            budget = k - off - 1
            eb = menu_bytes(en)
            if len(eb) > budget:
                over.append((cur, en, budget))
                continue
            d[off:off + budget] = eb + b"\x00" * (budget - len(eb))
            n_db += 1
        print("pilot DB fields: %d" % n_db)
    except (FileNotFoundError, ValueError):
        pass

    n_pilot = 0
    for jp, en in sorted(PILOTS.items(), key=lambda x: -len(x[0])):
        n_pilot += field_replace(d, jp, en, 0, len(d), over)
    # the [u16 id][name] copies: what the in-battle STATUS PLATE shows
    # (ロラン/ガロード/アスラン stayed Japanese there). Whole-field match with
    # the id-high-byte<=7 guard - see field_replace_prefixed_whole.
    n_plate = 0
    for jp, en in sorted(PILOTS.items(), key=lambda x: -len(x[0])):
        n_plate += field_replace_prefixed_whole(d, jp, en, 0, 0x66380, over)
    print("status-plate pilot names:", n_plate)
    # The encyclopedia Characters list draws the PREFIXED copies of pilot names -
    # records shaped [u16 id][name]. field_replace refuses those on purpose (its
    # prev==0/0x02 guard is what keeps it out of binary), so the list showed
    # ルナマリア / ヨウラン / デュランダル in Japanese beside Jerid / Setsuko in
    # English. Rewrite only the text after the id, leaving the id bytes alone.
    # DISABLED 2026-08-17, immediately after adding it. field_replace_prefixed
    # only checks that a match sits 2 bytes after a NUL - it does NOT anchor to
    # the field start, so it matches SUBSTRINGS and mangles names mid-word:
    #   ミチル -> ミChiru   スレイ -> スRey   ビダン -> ビDan   ブラン -> ブRan
    # (レイ matched inside スレイ, ダン inside ビダン). That is safe only for the
    # narrow enemy-designation range it was written for, never as a bulk pass
    # over the whole 418 KB pilot database.
    n_title = 0
    for jp, en in sorted(TITLES.items(), key=lambda x: -len(x[0])):
        n_title += field_replace(d, jp, en, TITLE_LO, TITLE_HI, over)
    # ambiguous names: choose the English by an anchor within +-0x80
    n_amb = 0
    for jp, rules in AMBIG.items():
        jb = jp.encode("cp932")
        i = d.find(jb)
        while i >= 0:
            j = i + len(jb)
            if d[j] == 0 and d[i-1] in (0, 2):
                around = bytes(d[max(0, i-0x80):i+0x80])
                for anchor, en in rules:
                    if anchor in around:
                        k = j
                        while d[k] == 0: k += 1
                        budget = k - i - 1
                        eb = menu_bytes(en)
                        if len(eb) <= budget:
                            d[i:i+budget] = eb + b"\x00" * (budget - len(eb))
                            n_amb += 1
                        break
            i = d.find(jb, i + 1)
    print("ambiguous fields resolved:", n_amb)

    # SERIES / GLOSSARY list used by the ENCYCLOPEDIA screens (rec0 ~0x71C00).
    # SOUND SELECT tables (0x6EC00-0x71C40): BGM titles + voice-list names.
    # Field offsets/budgets from analysis/soundsel_fields.json (pristine
    # layout), EN from analysis/soundsel_en.json (romaji; -teki -> "(E)").
    # Menu-encoded; verify the JP bytes still sit at the offset first.
    n_snd = 0
    try:
        sfields = json.load(open(
            r"E:\Projects\SRW Z\_work\analysis\soundsel_fields.json",
            encoding="utf-8"))
        smap = json.load(open(
            r"E:\Projects\SRW Z\_work\analysis\soundsel_en.json",
            encoding="utf-8"))
        for fl in sfields:
            off, budget, jp = fl["off"], fl["budget"], fl["jp"]
            if off >= 0x71C40:
                continue
            en = smap.get(jp)
            if en is None:
                continue
            jb = jp.encode("cp932")
            if bytes(d[off:off + len(jb)]) != jb or d[off + len(jb)] != 0:
                print("  soundsel: offset drift at %#x (%r)" % (off, jp))
                continue
            enb = menc(en, "menu")
            if len(enb) > budget:
                enb = menc(en.replace(" ", ""), "menu")
            if len(enb) > budget:
                print("  soundsel NO FIT %#x %r -> %r (%d>%d)"
                      % (off, jp, en, len(enb), budget))
                continue
            d[off:off + budget] = enb + bytes(budget - len(enb))
            n_snd += 1
    except FileNotFoundError as e:
        print("  soundsel pass skipped: %s" % e)
    print("sound-select fields:", n_snd)

    # This is a SECOND copy of the series names - the ELF has its own table at
    # 0x33A0F8 which we already translate - and it is the one the character
    # entry's "Series" line actually reads, which is why that line stayed
    # Japanese long after the ELF table was English.
    n_ser = 0
    try:
        from zkn_names_en import SERIES, WORDS
        import json as _json, io as _io
        _src = _json.load(_io.open(
            r"E:\Projects\SRW Z\_work\analysis\name_source.json", encoding="utf-8"))
        # ONLY the series titles and glossary headwords. An earlier version
        # merged the whole 2,000-entry name_source in here and rewrote 165
        # fields instead of 102 - including entries like トリノミアス and
        # ケイ１ＥＶ that sit just before the list and look like internal
        # lookup IDs rather than display text. Never point a bulk replacer at a
        # byte range and hope everything in it is a label.
        smap = dict(WORDS)
        smap.update(SERIES)
        _src = None
        # This list spells Mazinger Z with a fullwidth HYPHEN (マジンガ－Ｚ) where
        # the rest of the game uses a long vowel mark (マジンガーＺ).
        smap.setdefault("\u30de\u30b8\u30f3\u30ac\uff0d\uff3a", "Mazinger Z")
        # Slots here are as small as 8 bytes; give the long ones a short form.
        smap.update({"\u76f8\u514b\u754c": "Mu Zone",          # 相克界, slot 8
                     "\u30d7\u30e9\u30f3\u30c8\u8a55\u8b70\u4f1a\u8b70\u9577":
                         "PLANT Chairman",
                     "宇宙科学研究所": "Space Science"})                      # slot 24
        for jp, en in smap.items():
            # MENU-ENCODE: this list is drawn by the 0x13A290 reader, where
            # raw 0x2E-0x3D are control codes - "Zambot 3" loses its digit.
            try:
                en = menc(en, "menu").decode("cp932")
            except Exception:
                pass
            # Range starts at the first series title (マジンガ－Ｚ), NOT earlier:
            # 0x71800-0x71C40 holds unrelated entries. Ends at 0x72270 where the
            # leader-bonus effect list begins - the old 0x72200 bound cut the
            # glossary list short and left リフ/ウィール/ＳＯＦ/ヴォダラク/
            # ジョン・ヘンリ/ＵＮ/グローリー・スター Japanese.
            n_ser += field_replace(d, jp, en, 0x71C40, 0x72270, over)
    except Exception as e:
        print("  series-list pass skipped: %s" % e)
    print("encyclopedia series/glossary list: %d fields" % n_ser)

    # ENEMY PILOT / generic crew designations (~0x24000-0x2C000). The PILOTS
    # pass only covers NAMED characters, so every generic enemy - 連邦軍兵,
    # ザフト艦長, エゥーゴ兵 - stayed Japanese, which is what the squad panel
    # shows for an enemy unit.
    n_ep = 0
    try:
        from epilot_en import EPILOT_EN
        for jp, en in EPILOT_EN.items():
            try:
                en = menc(en, "menu").decode("cp932")
            except Exception:
                pass
            # CLEARED of the chapter-2 stall. Suspected because the blank box had
            # no portrait and no name (a speaker-lookup failure) and this pass
            # landed in v1.27, the first broken build. Disproved directly: an
            # image built from v1.27 with ONLY STAGE.BIN reverted to v1.26 ran
            # clean while still carrying v1.27's COMPDATA. The real cause was the
            # _M2 pass writing over scenario bytecode (see apply_stage.translatable).
            n_ep += field_replace(d, jp, en, 0x24000, 0x2C000, over)
            # the [u16 id][name] copies - these are what the battle box reads
            n_ep += field_replace_prefixed(d, jp, en, 0x24000, 0x2C000, over)
    except Exception as e:
        print("  enemy-pilot pass skipped: %s" % e)
    print("enemy pilot designations: %d fields" % n_ep)

    n_bio = bio_replace(d, BIOS, 0, len(d), over)
    print("replaced: %d unit, %d pilot, %d title, %d bio fields"
          % (n_unit, n_pilot, n_title, n_bio))
    if over:
        seen = set()
        for jp, en, bud in over:
            if jp not in seen:
                print("  NO FIT: %s -> %s (budget %d)" % (jp, en, bud))
                seen.add(jp)

    # LATE UI PASS: the offset table must win over the JP->EN text passes
    # (they rewrite e.g. 特殊能力 -> "Abilities" everywhere, which overflows
    # the narrow search tabs). Re-apply COMPDATA_UI_B by offset, last.
    try:
        from compdata_ui_en_b import COMPDATA_UI_B as _LATE
        n_late = 0
        for off, en in _LATE.items():
            e = d.index(bytes([0]), off)
            k = e
            while k < len(d) and d[k] == 0:
                k += 1
            bud = k - off
            enc = menc(en, "menu")
            if len(enc) < bud:
                d[off:off + bud] = enc + bytes(bud - len(enc))
                n_late += 1
            else:
                print("  late-UI NO FIT %#x %r (%d >= %d)" % (off, en, len(enc), bud))
        print("late UI pass:", n_late)
    except ImportError:
        pass

    blob = banlz.compress_record(bytes(d))
    rt, _ = banlz.decompress_record(blob, 0)
    assert rt == bytes(d), "roundtrip failed"
    print("compressed: %d bytes (orig %d)" % (len(blob), ORIG_SIZE))

    with open(iso_path, "r+b") as iso:
        if len(blob) <= ORIG_SIZE:
            lba, size = ORIG_LBA, len(blob)
            iso.seek(lba * SECTOR)
            iso.write(blob + b"\x00" * (ORIG_SIZE - len(blob)))
        else:
            lba, size = NEW_LBA, len(blob)
            iso.seek(lba * SECTOR)
            iso.write(blob)
        # patch directory record (find "COMPDATA.BN;1" name in dir sectors)
        iso.seek(0)
        head = iso.read(4 * 1024 * 1024)
        key = b"COMPDATA.BN;1"
        p = head.find(key)
        assert p > 0, "dir record not found"
        rec = p - 33                        # name at +33 of the record
        cur_lba = struct.unpack_from("<I", head, rec + 2)[0]
        assert cur_lba in (ORIG_LBA, NEW_LBA), "unexpected dir LBA %d" % cur_lba
        iso.seek(rec + 2);  iso.write(struct.pack("<I", lba))
        iso.seek(rec + 6);  iso.write(struct.pack(">I", lba))
        iso.seek(rec + 10); iso.write(struct.pack("<I", size))
        iso.seek(rec + 14); iso.write(struct.pack(">I", size))
        print("dir record: LBA %d size %d %s"
              % (lba, size, "(relocated into DMY)" if lba == NEW_LBA else "(in place)"))

        # THE AUTHORITY: the game's own file table (\\DATA\\COMPDATA.BN;1
        # followed at +0x20 by [u32 LBA][u32 size_in_sectors]). ISO9660 is
        # ignored at load time; this table is what libcdvd uses.
        cn = head.find(b"COMPDATA.BN;1")
        while cn >= 0:
            if head[cn - 8:cn] == b"\\\\DATA\\\\":
                tbl_lba = struct.unpack_from("<I", head, cn + 0x20)[0]
                assert tbl_lba in (ORIG_LBA, NEW_LBA), "unexpected table LBA %d" % tbl_lba
                sectors = (size + SECTOR - 1) // SECTOR
                iso.seek(cn + 0x20); iso.write(struct.pack("<I", lba))
                iso.seek(cn + 0x24); iso.write(struct.pack("<I", sectors))
                print("file table: LBA %d, %d sectors" % (lba, sectors))
                break
            cn = head.find(b"COMPDATA.BN;1", cn + 1)
        else:
            raise SystemExit("internal file-table entry for COMPDATA not found")


if __name__ == "__main__":
    main()
