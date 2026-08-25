# -*- coding: utf-8 -*-
"""Rebuild the encyclopedia archives with translated text.

Chunks carry their own u32 length, so unlike the fixed-slot stage/ELF strings
the English is NOT limited to the Japanese byte count: a record is reassembled
at whatever size it needs and the archive's record offsets are rewritten.

Three things must move together or the game reads garbage:
  1. the record payload   - chunk lengths, plus DSIZ = end-24 and DATA = end-32
                            (each is "bytes following my own tag"), payload
                            zero-padded to align16(end)
  2. the archive          - records recompressed, each starting 16-byte aligned
  3. the ELF offset table - N+1 u32 at the addresses below, entry N being the
                            total file size sentinel.  This table is the only
                            way the game finds record N; leaving it stale is
                            the difference between a working dex and a hang.

Run with --selftest to rebuild with no translations applied: the payloads must
come back byte-identical to the originals, which is what proves the parse and
the writer agree.

Usage: zkn_build.py --selftest
       zkn_build.py <iso> --elf <in.elf> <out.elf> [--en analysis/zkn_en.json]
"""
import io, json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banlz
import zkn
from patch import encode as pencode

WORK = r"E:\Projects\SRW Z\_work"
SECTOR = 2048

# name -> (extracted file, ELF file-offset of the offset table, record count,
#          file-table entry offset in the ISO, original LBA, sector cap)
SETS = {
    "KW": ("DATA_MTVZKNKW.BIN", 0x32B980,  52, 0xE19C0, 1573442,  15),
    "PT": ("DATA_MTVZKNPT.BIN", 0x32A810, 411, 0xE19F0, 1573457, 144),
    "RT": ("DATA_MTVZKNRT.BIN", 0x32B390, 321, 0xE1A20, 1573601,  91),
}
# Free space inside /DMY/DMY.BIN padding, which the COMPDATA relocation already
# proved usable. Layout of that region, with room for the descriptions to grow
# (English runs larger than Japanese - translating 14 KW entries alone pushed KW
# past its original 15-sector slot):
#     1823000..1823074  COMPDATA (relocated, 74 sectors)
#     1823100..1823105  MTVPROS  (relocated)
#     1823200..1823300  KW   (100 sectors reserved)
#     1823300..1824000  PT   (700 - the biggest set, 411 records)
#     1824000..1824600  RT   (600)
# DMY ends around 1824614, so RESERVE_END is the hard ceiling.
RELOC = {"KW": 1823200, "PT": 1823300, "RT": 1824000}
RESERVE = {"KW": 100, "PT": 700, "RT": 600}
RESERVE_END = 1824600


def build_payload(orig_payload, overrides):
    """Reassemble one record's payload, replacing chunk text from `overrides`."""
    p = zkn.deobf(orig_payload)
    magic, kind, ver, chunks = zkn.parse(orig_payload)
    body = b""
    for tag, off, data in chunks:
        if tag in zkn.SCALAR:
            continue                      # DSIZ/DATA are recomputed below
        if tag in overrides:
            # MENU ENCODING IS MANDATORY HERE. The encyclopedia is drawn by the
            # 0x13A290 menu reader, where raw bytes 0x2E-0x3D ( ./0-9:;<= ) are
            # CONTROL CODES, not characters - the Japanese data proves it by
            # writing every digit and full stop FULLWIDTH (１８．０ｍ, Ｊｒ．).
            # Shipping raw ASCII made the renderer break the line at each '.'
            # and draw the remainder over the following line.
            data = pencode(overrides[tag], "menu")
        body += tag.encode("latin1") + struct.pack("<I", len(data)) + data
    end = 32 + len(body)
    out = (p[0:16]
           + b"DSIZ" + struct.pack("<I", end - 24)
           + b"DATA" + struct.pack("<I", end - 32)
           + body)
    out += b"\x00" * ((-len(out)) % 16)
    return zkn.obf(out)


def build_record(orig_rec, overrides, cap=False, limit=None):
    """Trim description chunks so the payload fits a size limit.

    cap=True       cap to each record's OWN original Japanese payload. THIS IS
                   THE ONE THAT WORKS - see the DSC2_DEDUP note below for the
                   evidence. Use it together with DSC2_DEDUP so the trimming
                   falls on duplicated bytes instead of real text.

                   The cap is STRICT: a payload exactly EQUAL to the Japanese
                   one crashes the game (2026-08-22). Symptom: the entry opens
                   normally from the library but crashes the emulator when
                   opened from a 《term》 link in dialogue. Every keyword whose
                   link worked (Titans 1168/1200, AEUG 1488/1520, Glory Star
                   528/544) was under; both that crashed (UN 1008/1008, Trapar
                   1360/1360) were exactly at it. Same class as v1.31: an
                   exact-budget fill leaves nothing after the data and the
                   reader runs into the next field.
    limit=<bytes>  cap to a fixed size. Kept only because it was a bisect step;
                   a set-wide record limit does NOT prevent the crash.

    Trimming always eats DSC2 before DSCR, so the primary description is the
    last thing to lose bytes.
    """
    orig_pay = zkn.payload_of(orig_rec)
    pay = build_payload(orig_pay, overrides)
    target = len(orig_pay) if cap else limit
    if target and len(pay) >= target:
        ov = dict(overrides)
        for tag in ("DSC2", "DSCR"):
            while len(pay) >= target and len(ov.get(tag, "")) > 40:
                t = ov[tag]
                cut = t.rfind("\n", 0, len(t) - 1)
                ov[tag] = t[:cut] if cut > 40 else t[:len(t) * 3 // 4]
                pay = build_payload(orig_pay, ov)
        hdr = struct.pack("<8I", 1, 32, 0, len(pay), len(pay), 0, 0, 0)
        return hdr + pay
    if cap and len(pay) >= len(orig_pay):
        ov = dict(overrides)
        # shorten DSC2 first (it duplicates DSCR), then DSCR
        for tag in ("DSC2", "DSCR"):
            while len(pay) >= len(orig_pay) and len(ov.get(tag, "")) > 40:
                t = ov[tag]
                cut = t.rfind("\n", 0, len(t) - 1)
                ov[tag] = t[:cut] if cut > 40 else t[:len(t) * 3 // 4]
                pay = build_payload(orig_pay, ov)
    hdr = struct.pack("<8I", 1, 32, 0, len(pay), len(pay), 0, 0, 0)
    return hdr + pay


def selftest():
    ok = bad = 0
    for key, (fn, _, n, _, _, _) in SETS.items():
        for ri, rec in zkn.records(os.path.join(WORK, "extracted", fn)):
            rebuilt = build_record(rec, {})
            if rebuilt == rec:
                ok += 1
            else:
                bad += 1
                if bad <= 3:
                    print("  MISMATCH %s rec%d: %d vs %d bytes"
                          % (key, ri, len(rebuilt), len(rec)))
    print("selftest: %d identical, %d mismatched" % (ok, bad))
    return bad == 0


def set_limit(key):
    """Largest Japanese payload in the set - the size a shared record buffer
    would have been allocated for."""
    fn = SETS[key][0]
    return max(len(zkn.payload_of(rec)) for _, rec in zkn.records(
        os.path.join(WORK, "extracted", fn)))


# THE RULE, established by bisect: EVERY RECORD'S PAYLOAD MUST BE <= ITS OWN
# ORIGINAL JAPANESE PAYLOAD. Nothing else predicts the crash -
#     capped to own size, archive 344,672  -> WORKS
#     per-set record limit, archive 422,848 -> hangs   (same max record size)
#     DSC2-deduped, archive 277,808         -> crashes (SMALLER archive!)
# so it is neither the max record size nor the total archive size.
#
# Two settings work together to satisfy it almost for free:
#   DSC2_DEDUP  - DSC2 is a second description variant; making it a copy of DSCR
#                 removes its independent text.
#   cap=True    - trim to the original size, taking it out of DSC2 FIRST.
# Because DSC2 is then only a duplicate, the trimming lands almost entirely on
# redundant bytes: 19 characters of DSCR lost across all 784 records (0.008%).
DSC2_DEDUP = True


def build_archive(key, en, cap=True, use_limit=False):
    """Return (archive_bytes, [offsets] + [total_size])."""
    fn = SETS[key][0]
    lim = set_limit(key) if (use_limit and not cap) else None
    blobs, offs, cur = [], [], 0
    ntrim = 0
    for ri, rec in zkn.records(os.path.join(WORK, "extracted", fn)):
        ov = en.get(key, {}).get(str(ri), {})
        if DSC2_DEDUP and ov.get("DSCR") and ov.get("DSC2"):
            ov = dict(ov)
            ov["DSC2"] = ov["DSCR"]
        new = build_record(rec, ov, cap, lim)
        if lim and len(new) - 32 >= lim - 16 and ov:
            ntrim += 1
        blob = banlz.compress_record(new)
        rt, _ = banlz.decompress_record(blob, 0)
        assert rt == new, "roundtrip failed %s rec%d" % (key, ri)
        offs.append(cur)
        pad = (-len(blob)) % 16
        blobs.append(blob + b"\x00" * pad)
        cur += len(blob) + pad
    if lim:
        print("  %s: record limit %d bytes, %d record(s) trimmed to fit"
              % (key, lim, ntrim))
    return b"".join(blobs), offs + [cur]


def orig_offsets(key):
    """Record offsets of the UNPATCHED archive - used to locate the ELF table."""
    d = open(os.path.join(WORK, "extracted", SETS[key][0]), "rb").read()
    return [r[0] for r in banlz.decompress_all(bytearray(d))]


def patch_elf(src, dst, tables):
    """Write each set's new offset table into the ELF.

    The table is located by SEARCHING for the original offset sequence rather
    than trusting a hard-coded file offset: the build chain inserts a PT_LOAD
    for the VWF renderer, and if that ever shifts the file layout a fixed
    offset would silently corrupt unrelated data instead of failing.
    """
    data = bytearray(open(src, "rb").read())
    for key, offs in tables.items():
        n = SETS[key][2]
        old = orig_offsets(key)
        # Locate by the ORIGINAL offset sequence; if this ELF has already had
        # its tables written by a previous run, look for that sequence instead,
        # so re-running the chain on its own output is not a hard error.
        i = -1
        for cand in (old[1:4], offs[1:4]):
            probe = struct.pack("<3I", *cand)
            i = data.find(probe)
            if i > 0:
                assert data.find(probe, i + 1) < 0, "%s probe ambiguous" % key
                break
        assert i > 0, ("%s offset table not found in %s (neither the original "
                       "nor an already-patched table)" % (key, src))
        base = i - 4                          # entry 0 (== 0) sits before it
        # entry N is the end sentinel: the archive's total size
        # Entry N is the end sentinel (total archive size). Accept the original
        # size or a previously written one - both prove we found a real table.
        sent = struct.unpack_from("<I", data, base + 4 * n)[0]
        orig_size = os.path.getsize(os.path.join(WORK, "extracted", SETS[key][0]))
        # A table written by an EARLIER run carries that run's own total, which
        # is none of the three values above (our text shrank since). Rather than
        # widen the whitelist, prove structurally that this really is an offset
        # table: entry 0 is zero, entries ascend, and the sentinel is the last
        # entry. A run of executable data cannot satisfy all three.
        cur = list(struct.unpack_from("<%dI" % (n + 1), data, base))
        structural = (cur[0] == 0
                      and all(cur[i] < cur[i + 1] for i in range(n))
                      and cur[-1] == sent)
        assert sent in (orig_size, offs[-1]) or sent == old[-1] or structural, (
            "%s sentinel %d is neither the original size %d nor a plausible "
            "archive size, and the table is not structurally valid "
            "- wrong table?" % (key, sent, orig_size))
        data[base:base + 4 * (n + 1)] = struct.pack("<%dI" % (n + 1), *offs)
        print("  %s table @0x%X: %d entries, total %d" % (key, base, n + 1, offs[-1]))
    open(dst, "wb").write(bytes(data))
    print("ELF written: %s" % dst)


def main():
    if "--selftest" in sys.argv:
        raise SystemExit(0 if selftest() else 1)
    iso_path = sys.argv[1]
    elf_in = elf_out = None
    if "--elf" in sys.argv:
        k = sys.argv.index("--elf")
        elf_in, elf_out = sys.argv[k + 1], sys.argv[k + 2]
    enp = os.path.join(WORK, "analysis", "zkn_en.json")
    if "--en" in sys.argv:
        enp = sys.argv[sys.argv.index("--en") + 1]
    en = json.load(io.open(enp, encoding="utf-8")) if os.path.exists(enp) else {}
    if not en:
        print("no translations at %s - building Japanese rebuild only" % enp)

    elf_edits = {}
    with open(iso_path, "r+b") as iso:
        for key, (fn, tab, n, ftent, olba, ocap) in SETS.items():
            arch, offs = build_archive(key, en)
            assert len(offs) == n + 1
            if len(arch) <= ocap * SECTOR:
                lba = olba
                iso.seek(lba * SECTOR)
                iso.write(arch + b"\x00" * (ocap * SECTOR - len(arch)))
                where = "in place"
            else:
                lba = RELOC[key]
                sec = (len(arch) + SECTOR - 1) // SECTOR
                # Never silently run into the next relocated file. Each set has
                # a reserved window inside the DMY padding; overflowing it would
                # corrupt a neighbour that still reads fine until the moment the
                # game loads it.
                assert sec <= RESERVE[key], (
                    "%s needs %d sectors but only %d are reserved at LBA %d - "
                    "re-plan the DMY layout" % (key, sec, RESERVE[key], lba))
                assert lba + sec <= RESERVE_END, (
                    "%s would end at LBA %d, past the DMY ceiling %d"
                    % (key, lba + sec, RESERVE_END))
                iso.seek(lba * SECTOR)
                iso.write(arch + b"\x00" * ((-len(arch)) % SECTOR))
                where = "relocated to DMY"
            sectors = (len(arch) + SECTOR - 1) // SECTOR
            iso.seek(ftent + 0x28)
            iso.write(struct.pack("<II", lba, sectors))
            print("%s: %d records, %d bytes (%s, LBA %d, %d sectors)"
                  % (key, n, len(arch), where, lba, sectors))
            elf_edits[key] = offs
    if elf_in:
        patch_elf(elf_in, elf_out, elf_edits)
    else:
        print("NOTE: --elf not given; the ELF offset tables are now STALE. "
              "The game will read past the end of every record.")


if __name__ == "__main__":
    main()
