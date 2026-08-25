# -*- coding: utf-8 -*-
"""Generic stage-record translator/splicer.

Usage: apply_stage.py <iso> <recN> [<recN> ...]

For each record N: loads analysis/stage_dec/rec00N.bin +
analysis/rec00N_script.json + tools/rec00N_en.py (T = {row: en}), applies
in-place same-size row edits, HEALS the SE-cue table (cues fire when the
text printer reaches an exact byte position - a shorter translation strands
the cue and soft-locks the stage; see rec001 post-mortem), recompresses
into the record's slot in DATA/STAGE.BIN, and writes the STAGE region back
to the ISO. All requested records are spliced in one STAGE image.

The SE-cue table is found generically: the longest 8-aligned run of
[u32 = 0x750000+off within the record, u32 id < 0x400] entry pairs.
"""
import importlib.util
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
from patch import encode as pencode

SECTOR, STAGE_LBA = 2048, 1651029
WORK = r"E:\Projects\SRW Z\_work"

# Objective/condition strings (menu-rendered) per record: {rec: [(off, budget, jp)]}
_OBJ_BY_REC = {}
_OBJ_EN = {}
try:
    _oj = json.load(open(os.path.join(WORK, "analysis", "objectives_jp.json"), encoding="utf-8"))
    _OBJ_EN = json.load(open(os.path.join(WORK, "analysis", "objectives_en.json"), encoding="utf-8"))
    for _jp, _locs in _oj.items():
        for _rec, _off, _bud in _locs:
            _OBJ_BY_REC.setdefault(_rec, []).append((_off, _bud, _jp))
except FileNotFoundError:
    pass

# In-battle / event dialogue the original extraction missed, keyed "recNNN:off".
_MISSING = {}
try:
    from missing_dlg_en import MISSING_EN as _m1
    from missing_dlg_en_b import MISSING_EN_B as _m2
    _MISSING = dict(_m1)
    _MISSING.update(_m2)
except ImportError:
    pass
_MISSING_JP = {}
try:
    _mj = json.load(open(os.path.join(WORK, "analysis", "missing_dialogue_jp.json"),
                         encoding="utf-8"))
    for _rec, _lst in _mj.items():
        _MISSING_JP.setdefault(int(_rec[3:]), []).extend(
            (e["off"], e["budget"], "%s:%d" % (_rec, e["off"])) for e in _lst)
except FileNotFoundError:
    pass


# Second-pass rows: everything the original script sweep missed - short
# reactions, scene headers, and the glossary-keyword names that appear
# hundreds of times each. Keyed by the JAPANESE string, with every location
# listed, so one translation fills all of its occurrences.
_M2 = {}
_M2_BY_REC = {}
try:
    _m2loc = json.load(open(os.path.join(WORK, "analysis", "missing2_jp.json"),
                            encoding="utf-8"))
    for _f in ("missing2_en.json", "missing2_gloss.json"):
        try:
            _M2.update(json.load(open(os.path.join(WORK, "analysis", _f),
                                      encoding="utf-8")))
        except FileNotFoundError:
            pass
    for _jp, _locs in _m2loc.items():
        if _jp not in _M2:
            continue
        for _rec, _row, _off, _bud in _locs:
            _M2_BY_REC.setdefault(_rec, []).append((_off, _bud, _jp))
except FileNotFoundError:
    pass


# Third pass: dialogue the EXTRACTOR never saw, so it has no row in any
# recNNN_script.json and no earlier pass could reach it. strdump.dump() rejected
# 463 fields via `kana >= 1` (all-kanji lines like 花江「勝平！！」 and headers like
# ～駿河湾　漁港～), strict shift_jis (NEC extensions: ビアルⅠ世, ガンダムＭｋ－Ⅱ),
# and `jp_score >= 0.60` (headers are mostly U+3000 padding).
#
# Keyed by OFFSET, never by row index: re-extracting into script.json would
# renumber rows and silently invalidate the index-keyed T dicts across 167 files
# - the v1.32 mass-revert failure shape. See tools/gen_missing3.py.
_M3 = {}
_M3_BY_REC = {}
try:
    _m3loc = json.load(open(os.path.join(WORK, "analysis", "missing3_jp.json"),
                            encoding="utf-8"))
    _M3.update(json.load(open(os.path.join(WORK, "analysis", "missing3_en.json"),
                              encoding="utf-8")))
    for _rec, _rows in _m3loc.items():
        for _off, _bud, _jp in _rows:
            if _jp in _M3:
                _M3_BY_REC.setdefault(int(_rec), []).append((_off, _bud, _jp))
except FileNotFoundError:
    pass


# Tightened rewrites for rows whose English overran its slot. An over-budget row
# is SKIPPED by apply_record, so the Japanese shipped - 231 lines were sitting
# Japanese for want of a few bytes each. Keyed "rec:row" and preferred over the
# T entry; see tools/gen_tighten.py (mechanical) and tighten_manual.py (authored).
_TIGHTEN = {}
# namefix_en.json is a SEPARATE file: gen_tighten.py rewrites tighten_en.json on
# every run and would otherwise wipe the name substitutions.
for _f in ("tighten_en.json", "namefix_en.json", "passthrough_en.json"):
    try:
        _TIGHTEN.update(json.load(open(os.path.join(WORK, "analysis", _f),
                                       encoding="utf-8")))
    except FileNotFoundError:
        pass


def find_cue_table(data):
    """Longest [u32 0x750000+off, u32 sid<0x400] run (legacy: single table)."""
    best = (0, 0)
    for start, cnt in find_all_cue_tables(data):
        if cnt > best[1]:
            best = (start, cnt)
    return best


def find_all_cue_tables(data, minlen=3):
    """ALL [u32 0x750000+off, u32 sid<0x400] runs of >= minlen entries.

    Records carry SEVERAL such tables (SE cues, event/keyword-link triggers);
    each fires when the text printer reaches its byte offset. Healing only the
    longest (the original bug) stranded events in the others - a stranded
    deploy/setup trigger left chapter units unable to act. We heal every table.
    """
    n = len(data)
    tabs = []
    i = 0
    while i + 8 <= n:
        ptr, sid = struct.unpack_from("<II", data, i)
        if 0x750000 <= ptr < 0x750000 + n and sid < 0x400:
            st = i
            cnt = 0
            while i + 8 <= n:
                ptr, sid = struct.unpack_from("<II", data, i)
                if 0x750000 <= ptr < 0x750000 + n and sid < 0x400:
                    cnt += 1
                    i += 8
                else:
                    break
            if cnt >= minlen:
                tabs.append((st, cnt))
            else:
                i = st + 8
        else:
            i += 4
    return tabs


def check_pointers_intact(exp, orig, touched):
    """Assert we changed nothing outside the slots we deliberately wrote.

    Every edit this tool makes is an in-place, same-size slot overwrite, so the
    record's layout never moves and NOTHING needs repointing. The scenario
    bytecode - including the absolute string pointers the engine walks to find
    each message - must come through byte-identical. `touched` is marked by
    every writer in apply_record, so any diff outside it is a bug.

    This is the guard that would have caught heal_cues corrupting bytecode
    pointers for eleven versions; see its docstring.
    """
    assert len(exp) == len(orig), "record length changed - pointers would break"
    bad = [i for i in range(len(orig)) if orig[i] != exp[i] and not touched[i]]
    assert not bad, ("%d byte(s) changed outside written slots, first at %s"
                     % (len(bad), bad[:8]))


def _unused_pad_end_markers(exp, rows, tabs):
    """Pad English back to the Japanese byte length where a cue sits exactly on
    the Japanese terminator (base+nbytes).

    Such a cue is the message's own END-OF-MESSAGE marker. Shorter English stops
    at its own NUL and never reaches it, so the message never gets its end
    signal - in rec001 row 99 (Setsuko's line before she attacks Quattro) the
    line simply never appeared: no box at all in v1.0-v1.04, a BLANK box in
    v1.05+ once the marker was also being dragged into the text.

    Padding with trailing spaces puts the terminator exactly where the marker
    is, making the row structurally identical to the Japanese - and because the
    match test below is `o < base+nbytes`, the marker itself is then left
    untouched, as are the row's mid-text cues. Only 21 rows project-wide need
    this (204 bytes total); trailing spaces are invisible.

    Must run BEFORE any retargeting, while the targets are still original.
    """
    tgt = set()
    for start, cnt in tabs:
        for k in range(cnt):
            ptr, _ = struct.unpack_from("<II", exp, start + k * 8)
            tgt.add(ptr - 0x750000)
    n = 0
    for r in rows:
        base, nb = r["offset"], r["nbytes"]
        bud = r.get("budget", nb)
        if base + nb not in tgt or nb >= bud:
            continue                    # no end marker, or no room for the NUL
        end = exp.index(b"\x00", base)
        if end - base >= nb:
            continue                    # English already reaches the marker
        exp[end:base + nb] = b" " * (base + nb - end)
        n += 1
    return n


def translatable(orig, off):
    """True if the ORIGINAL field at `off` is real script text, not bytecode.

    The extractor scans for Shift-JIS-looking byte pairs, and scenario bytecode
    is full of pairs that decode cleanly: 0x8375 is 'ブ', 0x8376 is 'プ', 0x8340
    is 'ァ'. So rows like rec002 row 0 ('P\\x83\\x75', budget 3) are offered as
    strings, get "translated" to "b", and the write lands on LIVE BYTECODE.

    That is the chapter-2 stall: v1.27 added the _M2 second pass, which wrote
    rec002 rows 0-4 ('Pブ'->'Pb', '\\x10プ'->'\\x10b', '0プ'->'０b' - the last one
    also flipped an ASCII '0' to fullwidth). The scene's dialogue command was
    corrupted, so the box came up with no portrait, no name and no text, and the
    script could not advance. Bisect: v1.26 clean, v1.27 broken, and an image
    built from v1.27 with only STAGE.BIN reverted to v1.26 ran clean.

    319 rows project-wide have this shape. Test the ORIGINAL bytes rather than
    each pass's key, so no pass can bypass it.

    Real script text has >=3 Japanese characters. Genuine 2-character names
    ('シン' -> 'Shinn') are kept only when the field is PURE Japanese; bytecode
    always carries a raw ASCII or control byte alongside its stray kana.
    """
    end = orig.find(b"\x00", off)
    if end < 0:
        end = len(orig)
    raw = bytes(orig[off:end])
    try:
        s = raw.decode("cp932")
    except UnicodeDecodeError:
        return False
    while s and ord(s[0]) < 0x20:      # 0x01/0x04/0x0C glossary-link markers
        s = s[1:]
    # U+2026 '…' MUST be counted. cp932 decodes the game's ellipsis (0x8163) to
    # U+2026, which sits outside every CJK range below, so '$n\n「………」' scored
    # only 2 (its two brackets) and was refused as bytecode - 33 genuine lines
    # in 33 records. Bytecode is unaffected: its stray kana are already counted,
    # so 'Pブ' still scores 1 and is still refused.
    EXTRA = u"…‥―─●○※"   # … ‥ ― ─ ● ○ ※
    nj = 0
    for ch in s:
        o = ord(ch)
        if (0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF
                or 0x3000 <= o <= 0x303F or 0xFF01 <= o <= 0xFF60
                or ch in EXTRA):
            nj += 1
    if nj >= 3:
        return True
    return nj >= 2 and nj == len(s)


def heal_cues(exp, rows):
    """DELIBERATELY DOES NOTHING. Kept so the call site and this note survive.

    For eleven versions this rewrote what it believed were SE cues: tables of
    [u32 0x750000+textoffset, u32 sound_id] that "fire when the text printer
    reaches a byte position", so a shorter English line was thought to strand
    them. Reading a PCSX2 save state taken on the actual blank box proved that
    model false in every part:

      * The record is loaded at RAM 0x7566F0 and the pointers on disc are
        ALREADY absolute RAM addresses - disc bytes equal RAM bytes at the same
        address, there is no relocation pass. So the base is 0x7566F0, not
        0x750000, and subtracting 0x750000 mis-reads every pointer by 0x66F0
        (26,352) - which, for a ~46 KB record, lands inside the dialogue by
        coincidence and made the "cues point into text" story look right.
      * They are not cues. 0x757180 -> rec+2704 holds `4b 00 00 00` - opcode
        0x4B, a 32-byte BYTECODE ENTRY, the same shape as the message entries at
        rec+7344/7376/7408 ([type,p,p,speaker_id][string_ptr,0,0,0]).
      * So this function was rewriting BYTECODE POINTERS to aim into the middle
        of dialogue. The engine then walked garbage instead of the next message
        entry, and the entry it built got a NULL string pointer - observed live
        at 0xC2DD80 - which is exactly the blank box: no name, no text, and
        button presses that go nowhere.

    NOTHING NEEDS REPOINTING. Every edit here is an in-place, same-size slot
    overwrite, so the layout never moves and every pointer stays valid. That is
    what check_pointers_intact() now enforces.

    Do not resurrect this without a save state showing a real stranded pointer.
    """
    return


def apply_record(n):
    dec = os.path.join(WORK, "analysis", "stage_dec", "rec%03d.bin" % n)
    js = os.path.join(WORK, "analysis", "rec%03d_script.json" % n)
    py = os.path.join(WORK, "tools", "rec%03d_en.py" % n)
    orig = bytearray(open(dec, "rb").read())
    rows = json.load(open(js, encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("r%d" % n, py)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    exp = bytearray(orig)
    # Every byte this function writes gets marked here, so the guard at the end
    # can prove nothing else moved - in particular none of the scenario
    # bytecode's absolute string pointers (see heal_cues).
    touched = bytearray(len(orig))
    over = 0
    n_junk = 0
    for idx, en in sorted(m.T.items()):
        r = rows[idx]
        off = r["offset"]
        # never write over bytecode the extractor mistook for text (see translatable)
        if not translatable(orig, off):
            n_junk += 1
            continue
        en = _TIGHTEN.get("%d:%d" % (n, idx), en)
        # Preserve leading control byte(s) the translation dropped. A leading
        # 0x0C (and 01/04) marks a keyword/glossary-link field; the game parses
        # these at stage setup, and a stripped marker corrupts that parse -
        # which strands the chapter's units (they can't act). Re-prepend them.
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        prefix = bytes(orig[off:off + lead])
        # Menu/label rows (mission objectives, unit-list names) are drawn by the
        # 0x13A290 menu reader, which eats bytes 0x2E-0x3D (./0-9:;<=) as control
        # codes - so digits vanish. Encode those rows "menu" (fullwidth 0x2E-0x3D;
        # letters stay ASCII for the MHOOK). Dialogue rows (Speaker\n"quote") keep
        # raw ASCII for the setText cave. Heuristic: a row is dialogue iff its
        # first line is a short speaker name (<=15 chars, no sentence punctuation).
        first = en.split("\n", 1)[0].rstrip()
        is_dialogue = ("\n" in en and len(first) <= 15
                       and not first.endswith((".", "!", "?")))
        body = pencode(en, "ascii" if is_dialogue else "menu")
        enc = prefix + body
        bud = r.get("budget", r["nbytes"])
        if len(enc) > bud:
            print("  rec%03d OVER row %d: %d > %d (%r)" % (n, idx, len(enc), bud, en[:40]))
            over += 1
            continue
        # These fields are NUL-TERMINATED, so a row that fills its budget
        # EXACTLY writes zero padding and loses its terminator - the renderer
        # then reads on into the next row. 2,138 rows across the script sat at
        # exactly their budget. Trim one character rather than skip the row
        # (skipping would revert it to Japanese, which is worse); the last
        # character before a closing quote goes first so the quote survives.
        while len(enc) >= r["budget"] and en:
            # Spend the cheapest byte first: cp932 '…' (0x8163) is TWO bytes
            # where ASCII '...' is three, and it is the game's own glyph, so it
            # renders natively and narrower. 781 rows sit EXACTLY at budget and
            # would otherwise lose their last character - usually the closing
            # punctuation - for want of one byte.
            if "..." in en:
                en = en.replace("...", u"…", 1)
            else:
                en = (en[:-2] + en[-1]) if en.endswith('"') and len(en) > 1 else en[:-1]
            # rebuild the SAME way as above: a plain cp932 encode here would drop
            # the leading control byte (which strands the chapter's units) and
            # silently revert menu rows to ASCII, so digits become control codes.
            enc = prefix + pencode(en, "ascii" if is_dialogue else "menu")
        exp[off:off + r["budget"]] = enc + b"\x00" * (r["budget"] - len(enc))
        touched[off:off + r["budget"]] = b"\x01" * r["budget"]
    print("rec%03d: %d rows applied, %d over" % (n, len(m.T) - over - n_junk, over))
    # Overrides may ADD a row, not just replace one: the loop above iterates
    # m.T, so a row that was never translated at all (rec203's developer scene,
    # rec084 row 572) would never be visited. Apply those here.
    n_add = 0
    for _k, _en in _TIGHTEN.items():
        _r, _i = (int(v) for v in _k.split(":"))
        if _r != n or _i in m.T or _i >= len(rows):
            continue
        r = rows[_i]
        off = r["offset"]
        if not translatable(orig, off):
            continue
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        first = _en.split("\n", 1)[0].rstrip()
        is_dlg = ("\n" in _en and len(first) <= 15
                  and not first.endswith((".", "!", "?")))
        enc = bytes(orig[off:off + lead]) + pencode(_en, "ascii" if is_dlg else "menu")
        if len(enc) < r["budget"]:
            exp[off:off + r["budget"]] = enc + b"\x00" * (r["budget"] - len(enc))
            touched[off:off + r["budget"]] = b"\x01" * r["budget"]
            n_add += 1
    if n_add:
        print("  override-added rows: %d" % n_add)
    heal_cues(exp, rows)
    # EXTRA dict support (offset-keyed additions)
    if hasattr(m, "EXTRA"):
        for off, (budget, en) in m.EXTRA.items():
            if not translatable(orig, off):
                n_junk += 1
                continue
            enc = en.encode("cp932")
            # < budget, never <=: an exact fill leaves no NUL terminator
            if len(enc) < budget:
                exp[off:off + budget] = enc + b"\x00" * (budget - len(enc))
                touched[off:off + budget] = b"\x01" * budget
    # Mission-objective condition fields (menu-rendered): apply translated,
    # menu-encoded conditions to any field NOT already handled as a dialogue row.
    # A field is handled by the dialogue pass only if its row is actually IN T;
    # most objective rows were extracted but never translated (that is why stage
    # objectives stayed Japanese), so fill those here.
    off2idx = {r["offset"]: i for i, r in enumerate(rows)}
    n_obj = 0
    for off, budget, jp in _OBJ_BY_REC.get(n, []):
        if off2idx.get(off) in m.T:
            continue
        en = _OBJ_EN.get(jp)
        if not en:
            continue
        if not translatable(orig, off):
            n_junk += 1
            continue
        # SAFETY: Japanese objective text uses FULLWIDTH digits/punctuation, so a
        # raw ASCII byte in 0x2E-0x3D (./0-9:;<=) or any control byte in the
        # ORIGINAL field is a control code (e.g. a dynamic unit-name placeholder),
        # not a literal character. Menu-encoding would turn it fullwidth and break
        # the substitution, so leave those fields Japanese.
        ob = bytes(orig[off:off + budget]).split(b"\x00")[0]
        if any(b < 0x20 and b != 0x0A or 0x2E <= b <= 0x3D for b in ob):
            continue
        enc = pencode(en, "menu")
        # STRICTLY less than budget: these fields are NUL-TERMINATED, so an
        # exact fill writes zero padding and the terminator is lost - the
        # renderer then reads straight on into the next field. That is what put
        # "Annihilate all enemies。Defeat Shinn or Alex。" on one line in v1.31
        # (rec002: 24 bytes of English into a 24-byte slot). 43 slots did this.
        if len(enc) < budget:
            exp[off:off + budget] = enc + b"\x00" * (budget - len(enc))
            touched[off:off + budget] = b"\x01" * budget
            n_obj += 1
    if n_obj:
        print("  objectives: %d fields" % n_obj)
    # missed in-battle/event dialogue (rendered by setText -> raw ASCII)
    n_miss = 0
    for off, budget, key in _MISSING_JP.get(n, []):
        en = _MISSING.get(key)
        if not en:
            continue
        if not translatable(orig, off):
            n_junk += 1
            continue
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        enc = bytes(orig[off:off + lead]) + en.encode("cp932", "replace")
        if len(enc) < budget:
            exp[off:off + budget] = enc + b"\x00" * (budget - len(enc))
            touched[off:off + budget] = b"\x01" * budget
            n_miss += 1
    if n_miss:
        print("  missed dialogue: %d lines" % n_miss)
    # second-pass rows (see _M2 above)
    n_m2 = 0
    for off, bud, jpstr in _M2_BY_REC.get(n, []):
        en = _M2.get(jpstr)
        if not en:
            continue
        # this pass is what corrupted rec002 rows 0-4 in v1.27 (see translatable)
        if not translatable(orig, off):
            n_junk += 1
            continue
        # keep any leading control byte - 0x0C and friends mark a glossary link
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        first = en.split("\n", 1)[0].rstrip()
        is_dialogue = ("\n" in en and len(first) <= 15
                       and not first.endswith((".", "!", "?")))
        mode = "ascii" if is_dialogue else "menu"
        enc = bytes(orig[off:off + lead]) + pencode(en, mode)
        # These fields are NUL-TERMINATED, so an exact fill loses the terminator
        # and the renderer reads on into the next field. rec002 row 381 shipped
        # that way - 'Destroy all enemies in 2 turns' menu-encoded to exactly its
        # 31-byte slot. Trim a character rather than skip the row, so the
        # translation survives; the character before a closing quote goes first.
        while len(enc) >= bud and en:
            # cp932 '…' is 2 bytes vs 3 for '...' - spend that first (see the
            # dialogue pass above)
            if "..." in en:
                en = en.replace("...", u"…", 1)
            else:
                en = (en[:-2] + en[-1]) if en.endswith('"') and len(en) > 1 else en[:-1]
            enc = bytes(orig[off:off + lead]) + pencode(en, mode)
        if en and len(enc) < bud:
            exp[off:off + bud] = enc + b"\x00" * (bud - len(enc))
            touched[off:off + bud] = b"\x01" * bud
            n_m2 += 1
    if n_m2:
        print("  second-pass rows: %d" % n_m2)
    # third-pass rows: fields the extractor never saw (see _M3 above)
    n_m3 = 0
    for off, bud, jpstr in _M3_BY_REC.get(n, []):
        en = _M3.get(jpstr)
        if not en:
            continue
        if not translatable(orig, off):
            n_junk += 1
            continue
        lead = 0
        while (lead < 4 and off + lead < len(orig)
               and orig[off + lead] < 0x20 and orig[off + lead] != 0x0A):
            lead += 1
        # ALWAYS ascii: every _M3 row is dialogue-box content (speaker lines and
        # scene headers, both drawn by setText), so the dialogue/menu heuristic
        # must not be consulted. It misfires on speakers whose name ENDS in
        # sentence punctuation - '???' and 'D.O.M.E.' - and menu-encoding them
        # fullwidths their punctuation, which both looks wrong and doubles the
        # byte cost. That is what pushed rec064 0x05E00 to 98 bytes in a 96-byte
        # slot and left it Japanese.
        enc = bytes(orig[off:off + lead]) + pencode(en, "ascii")
        # strictly < bud: an exact fill loses the NUL and the renderer reads on
        if len(enc) < bud:
            exp[off:off + bud] = enc + b"\x00" * (bud - len(enc))
            touched[off:off + bud] = b"\x01" * bud
            n_m3 += 1
    if n_m3:
        print("  third-pass rows: %d" % n_m3)
    if n_junk:
        print("  BYTECODE rows refused: %d" % n_junk)
    check_pointers_intact(exp, orig, touched)
    return bytes(exp)


def compress_cached(n, exp, slot):
    """Compress exp for record n, caching by content hash so repeat applies
    skip the (slow) optimal parse for unchanged records."""
    import hashlib
    cache_dir = os.path.join(WORK, "analysis", "blob_cache")
    os.makedirs(cache_dir, exist_ok=True)
    h = hashlib.sha1(exp).hexdigest()[:16]
    cp = os.path.join(cache_dir, "rec%03d_%s.lz" % (n, h))
    if os.path.exists(cp):
        return open(cp, "rb").read()
    blob = banlz.compress_record(exp)
    if len(blob) > slot:
        blob = banlz.compress_record_optimal(exp)
    open(cp, "wb").write(blob)
    return blob


def main():
    iso_path = sys.argv[1]
    rec_ids = [int(a) for a in sys.argv[2:]]
    stage = bytearray(open(os.path.join(WORK, "extracted", "DATA_STAGE.BIN"), "rb").read())
    recs = banlz.decompress_all(stage)
    for n in rec_ids:
        exp = apply_record(n)
        s1 = recs[n][0]
        s2 = recs[n + 1][0] if n + 1 < len(recs) else len(stage)
        slot = s2 - s1
        blob = compress_cached(n, exp, slot)
        rt, _ = banlz.decompress_record(blob, 0)
        assert rt == exp, "roundtrip failed rec%d" % n
        if len(blob) > slot:
            print("  !! rec%03d OVERSIZE: %d > %d slot - SKIPPED (stays JP), "
                  "tighten its dialogue by ~%d bytes" % (n, len(blob), slot,
                  (len(blob) - slot) * 3))
            continue
        stage[s1:s2] = blob + b"\x00" * (slot - len(blob))
        print("  spliced rec%03d: %d into %d-byte slot" % (n, len(blob), slot))
    with open(iso_path, "r+b") as iso:
        iso.seek(STAGE_LBA * SECTOR)
        iso.write(bytes(stage))
    print("STAGE region written.")


if __name__ == "__main__":
    main()
