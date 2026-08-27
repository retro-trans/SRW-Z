# Super Robot Taisen Z — scenario LZ format

The scenario text files (`DATA/STAGE.BIN`, `DATA/HSFC.BIN`) are stored as a
sequence of independently-compressed records using a custom varint-LZ scheme.
The decompressor was reverse-engineered from the boot ELF (`SLPS_258.87`):

- header parser: `0x1C6C40`
- core decompressor: `0x1C6D70`

Reference implementation (both directions) is `tools/banlz.py`, which
round-trips all 205 records of `STAGE.BIN` byte-for-byte.

## Varint

Values are packed 7 bits per byte, big-endian, with bit 0 of each byte acting
as the stop flag:

```
v = 0
do { v = (v << 7) | next_byte } while ((v & 1) == 0)
value = v >> 1
```

## Record header

```
varint total        # decompressed size in bytes
varint flags        # window = 1 << (((flags >> 1) & 0xF) + 8)
[varint skipped]    # present only if NOT(window >= total && (flags & 0x21)==1)
                    #   AND (flags & 0x40)
varint reserved     # always present
```

## Token stream (repeats until output reaches `total`)

Each group is a group-token, then literal bytes, then reference tokens:

```
group token T:
    lit  = T & 0x0F        # literal count; if 0 -> read varint
    nref = T >> 4          # reference count; if 0 -> read varint
literal bytes  x lit       # copied verbatim (always >= 1 per group)
if output not yet full:
    reference token R  x nref:
        d = R & 0x0F
        if (d & 1) == 0:              # low bit 0 => distance continues
            do { d = (d << 7) | next_byte } while ((d & 1) == 0)
        dist = d >> 1
        len  = R >> 4                 # if 0 -> read varint
        len += 1
        copy len bytes from output[-(dist+1)], overlap allowed, clamp to total
```

The final group may be literals-only (the decoder stops once output is full,
before consuming its reference nibble). The encoder in `banlz.py` writes a
nonzero reference nibble there to avoid a spurious varint read.

## Container companions

Some `.BIN` data files ship with a `.SEG` companion (e.g. `BTL/SRVC.BIN` +
`BTL/SRVC.SEG`). The `.SEG` is a `u32` array of block offsets into the `.BIN`,
the final entry being an EOF sentinel — so block *i* spans `[seg[i],
seg[i+1])`. `BTL/SRVC.BIN` is **uncompressed** battle dialogue (~1.08M JP chars)
and is not part of the LZ scheme.

## Encoding note

Game text uses **cp932**, not strict Shift-JIS — it includes NEC extensions
such as the Roman numeral `Ⅱ` in "Gundam Mk-Ⅱ". Python's strict `shift_jis`
codec silently drops those, so all tooling uses `cp932`.
