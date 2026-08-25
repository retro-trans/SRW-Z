# -*- coding: utf-8 -*-
"""SRVC caption text polish v2 (in-place, same-length).

v2 RULES (0.8.1.7): the caption renderer treats ASCII '.' (0x2E) and ','
(0x2C) as CONTROL codes - a caption page STOPS at the first one ('"Well'
for '"Well, we're...', a bare '"' for '"..."'). That is why the original
translation used fullwidth periods; v1 of this tool converting them to
ASCII dots was WRONG (0.8.1.6 regression). Engine-safe forms, chosen for
looks as well:

    '...' (runs of 3+ dots) -> single-cell ellipsis 0x8163  (compact -
           also fixes the old wide-spaced ". . ." complaint)
    lone '.'                -> fullwidth 0x8144
    ','                     -> fullwidth 0x8143

Trailing literal \n stripping (the orphan blank/quote page fix) is kept
from v1. Only pure-English fields are touched; all edits are re-padded
with spaces to the exact original extent so SEG offsets stay valid.

Usage: patch_srvc_polish.py <iso>   (idempotent)
"""
import sys

SRVC_LBA, SECTOR = 1826000, 2048
SRVC_SECTORS = 1624

FW_ELLIPSIS = b"\x81\x63"
FW_PERIOD = b"\x81\x44"
FW_COMMA = b"\x81\x43"
NL = b"\x5c\x6e"                       # literal backslash-n


def polish_field(txt):
    body = txt.rstrip(b" ")
    pad = len(txt) - len(body)
    i = 0
    ascii_seen = False
    while i < len(body):
        b = body[i]
        if body[i:i + 2] in (FW_PERIOD, FW_ELLIPSIS, FW_COMMA):
            i += 2
            continue
        if 0x20 <= b < 0x7F:
            if b != 0x20:
                ascii_seen = True
            i += 1
            continue
        return None                    # not pure English -> leave alone
    if not ascii_seen:
        return None
    # normalize existing fullwidth punctuation back to ASCII first
    new = body.replace(FW_ELLIPSIS, b"...").replace(FW_PERIOD, b".")
    new = new.replace(FW_COMMA, b",")
    # strip trailing newline escapes / fold them into a closing quote
    if new.endswith(NL + b'"'):
        new = new[:-3] + b'"'
    while new.endswith(NL):
        new = new[:-2]
    # re-encode punctuation engine-safe. Fullwidth glyphs carry their own
    # trailing whitespace visually, so ", " / ". " collapse byte-neutrally -
    # that keeps tight fields (no padding left) convertible too.
    out = bytearray()
    j = 0
    while j < len(new):
        c = new[j]
        if c == 0x2E:
            k = j
            while k < len(new) and new[k] == 0x2E:
                k += 1
            run = k - j
            out += FW_ELLIPSIS * (run // 3) + FW_PERIOD * (run % 3)
            j = k
            if j < len(new) and new[j] == 0x20 and run % 3:
                j += 1                    # ". " -> fullwidth period alone
        elif c == 0x2C:
            out += FW_COMMA
            j += 1
            if j < len(new) and new[j] == 0x20:
                j += 1                    # ", " -> fullwidth comma alone
        else:
            out.append(c)
            j += 1
    new = bytes(out)
    if new == body:
        return None
    if len(new) > len(body) + pad:
        return "OVER"
    return new + b" " * (len(body) + pad - len(new))


def main():
    iso_path = sys.argv[1]
    with open(iso_path, "r+b") as iso:
        iso.seek(SRVC_LBA * SECTOR)
        d = bytearray(iso.read(SRVC_SECTORS * SECTOR))
        n = n_over = 0
        i = 0
        L = len(d)
        while i < L:
            if d[i] == 0:
                i += 1
                continue
            end = d.find(b"\x00", i)
            if end < 0:
                break
            new = polish_field(bytes(d[i:end]))
            if new == "OVER":
                n_over += 1
            elif new is not None:
                assert len(new) == end - i
                d[i:end] = new
                n += 1
            i = end + 1
        iso.seek(SRVC_LBA * SECTOR)
        iso.write(bytes(d))
    print("polished %d caption fields, %d skipped (no room)" % (n, n_over))


if __name__ == "__main__":
    main()
