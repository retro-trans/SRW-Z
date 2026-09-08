"""Check SRVC block alignment and optionally emit a lossless aligned archive.

Usage:
    python tools/audit_srvc_alignment.py game.iso
    python tools/audit_srvc_alignment.py game.iso --emit-aligned output_dir

Reads the ISO only. Emission creates SRVC.BIN, SRVC.SEG and an audit JSON;
it does not patch the ISO. A later ISO splice must update directory sizes and
check the game's file-table sector capacity. Existing output files are refused.

Repair works on opaque block bytes, avoiding the heuristic text/index parser.
Only zero padding between blocks and the SEG offsets change. The original
archive aligns every block and its EOF sentinel to 16 bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from srvclib import getfile


def read_offsets(data, seg):
    if len(seg) < 8 or len(seg) % 4:
        raise ValueError("SEG must contain u32 block offsets and an EOF sentinel")
    offsets = list(struct.unpack("<%dI" % (len(seg) // 4), seg))
    if offsets[0] != 0 or offsets[-1] != len(data):
        raise ValueError("SEG start/EOF do not match the archive")
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        raise ValueError("SEG offsets are not monotonic")
    return offsets


def align_blocks(data, seg):
    offsets = read_offsets(data, seg)
    out = bytearray()
    new_offsets = [0]
    for start, end in zip(offsets, offsets[1:]):
        out.extend(data[start:end])
        out.extend(b"\0" * (-len(out) % 16))
        new_offsets.append(len(out))
    new_seg = struct.pack("<%dI" % len(new_offsets), *new_offsets)
    read_offsets(out, new_seg)
    for i, (start, end) in enumerate(zip(offsets, offsets[1:])):
        ns, ne = new_offsets[i:i + 2]
        if out[ns:ns + end - start] != data[start:end]:
            raise AssertionError("block payload changed")
        if any(out[ns + end - start:ne]) or ns % 16 or ne % 16:
            raise AssertionError("invalid alignment padding")
    return bytes(out), new_seg


def audit(data, seg):
    offsets = read_offsets(data, seg)
    starts = offsets[:-1]
    return {
        "blocks": len(starts),
        "bytes": len(data),
        "sectors": (len(data) + 2047) // 2048,
        "sha1_bin": hashlib.sha1(data).hexdigest(),
        "sha1_seg": hashlib.sha1(seg).hexdigest(),
        "misaligned_starts": {
            str(n): sum(o % n != 0 for o in starts) for n in (2, 4, 16)
        },
        "eof_mod16": offsets[-1] % 16,
        "first_bad_blocks": [
            {"block": i, "offset": o, "mod4": o % 4, "mod16": o % 16}
            for i, o in enumerate(starts) if o % 16
        ][:12],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("iso", type=Path)
    ap.add_argument("--emit-aligned", type=Path)
    args = ap.parse_args()
    data = getfile(str(args.iso), "/BTL/SRVC.BIN")
    seg = getfile(str(args.iso), "/BTL/SRVC.SEG")
    before = audit(data, seg)
    report = {"input_iso": str(args.iso.resolve()), "before": before}
    print(json.dumps(before, indent=2))
    if args.emit_aligned:
        new_data, new_seg = align_blocks(data, seg)
        report["after"] = audit(new_data, new_seg)
        report["added_zero_bytes"] = len(new_data) - len(data)
        report["block_payloads_preserved"] = True
        output = args.emit_aligned
        paths = [output / n for n in ("SRVC.BIN", "SRVC.SEG", "audit.json")]
        if any(p.exists() for p in paths):
            raise FileExistsError("output files already exist; use a fresh directory")
        output.mkdir(parents=True, exist_ok=True)
        with paths[0].open("xb") as f:
            f.write(new_data)
        with paths[1].open("xb") as f:
            f.write(new_seg)
        with paths[2].open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        print("Aligned files written to %s; added %d zero bytes; %d sectors" % (
            output.resolve(), report["added_zero_bytes"], report["after"]["sectors"]))
        print("All block payloads verified unchanged. Input ISO was read only.")
        return 0
    return int(bool(before["misaligned_starts"]["16"] or before["eof_mod16"]))


if __name__ == "__main__":
    raise SystemExit(main())
