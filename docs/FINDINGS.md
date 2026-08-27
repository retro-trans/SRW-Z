# Reverse-engineering findings

## Disc

- CHD v5, one MODE1 data track, logical size 4,492,412,928 bytes.
- Volume ID `SLPS_25887` (the "PlayStation 2 the Best" reprint, not the
  original SLPS-25679 pressing). Any patch built here is keyed to this dump.
- Boot ELF: `SLPS_258.87`, EE MIPS, entry `0x100008`, single PT_LOAD at vaddr
  `0x100000` (file offset `0x1A80`).

## Where the text lives

| File | Contents | Encoding |
|---|---|---|
| `DATA/STAGE.BIN` | 205 LZ records — scenario prose, stage synopses | LZ (see LZ_FORMAT.md) |
| `DATA/HSFC.BIN` | 4 LZ records — stage synopses | LZ |
| `BTL/SRVC.BIN` | ~1.08M chars battle dialogue | **uncompressed**, `.SEG`-indexed |
| `MAP/MAPNAME.BIN` | 195 map names, fixed 256-byte stride | plain SJIS, no pointers |
| `SLPS_258.87` | UI: skills, series titles, system messages | plain SJIS in the ELF |

`STAGE.BIN` record 1 is the Setsuko-route stage 1 (314 strings). Records are
addressed by a fixed slot; a recompressed record must fit its original slot and
is zero-padded to fill it.

## Scenario bytecode

- Interpreter at `0x1E5F20` — dispatches on the first byte of each command.
  Text-print commands (types 0–4) go through a C++ vtable (`lw $t9, 0x14($t9);
  jalr`).
- SJIS classifier at `0x2010B0` — tests the lead-byte ranges `0x81–0x9F` and
  `0xE0–0xFC`. This is a string *measuring* helper, not the glyph renderer.

## String indexing is offset-based (important)

A grow-test settled this: keep the record valid but **lengthen one early
string** so every later string shifts. In-game, line 142 (grown) rendered
correctly but the shifted lines 143/144 went blank. There is no contiguous
offset/length table anywhere in the record (checked as u16/u32, absolute and
relative). Conclusion: string offsets are embedded **inline in the scenario
bytecode**.

Consequences:
- In-place replacement must preserve each string's **exact byte length**
  (`apply_stage1.py` pads to the original `nbytes`). This is safe and verified.
- Growing strings is not safe without also rewriting every inline offset
  operand.
- **Fullwidth-in-data is not viable**: fullwidth English is 2 bytes/char (same
  as Japanese), and English needs more characters than the original, so only
  9/306 stage-1 strings fit their byte budgets, and the whole record overflows
  its compressed slot.

## Font / rendering

- The dialogue font is **fullwidth Shift-JIS only**; it has no half-width ASCII
  glyphs. Raw ASCII English renders as blank boxes.
- **Fullwidth Latin renders correctly** — proven by injecting a fullwidth test
  line (`Ｄｅｎｚｅｌ / ＴＥＳＴ`) into a live dialogue slot and seeing it draw
  cleanly in PCSX2.
- So the fix is an **ELF renderer patch**: keep compact half-width data and
  remap ASCII → the existing fullwidth glyph at draw time. This matches the
  documented approach of other PS2 SRW fan patches (e.g. camd11's OG Gaiden,
  which added a VWF + font width table into dead ELF space).
- Locating the exact glyph routine by static signature search did **not**
  converge — the byte constants involved (`-0x81` = the `& ~0x80` flag idiom,
  `-0x40`, `0x7F`, `0xBC`) are too common and produced only false positives
  (flag masking, pointer loads, 3D matrix math). The reliable path is a PCSX2
  debugger memory-breakpoint on the decompressed dialogue buffer, stepping out
  to the reader.
- **RESOLVED (runtime trace, see `RENDERER.md`).** The full render chain is
  `0x2212B0` (layout) → `0x220DB0` (segment draw) → `0x225290` (glyph dispatch)
  → `0x13A290` (glyph blit). Two mechanisms make ASCII blank:
  1. Layout `0x2212B0` sets a cell-width flag `gp-0x7e8c` = `0x40` (half) when
     `byte < 0x80` (`slti at,v0,0x80` @ `0x22137C`), else `0x80` (full).
  2. Blit `0x13A290` forms a 2-byte SJIS code `lead<<8|trail` (@ `0x13A600`)
     and indexes the font by the **lead byte** through a per-bank jump table at
     `0x433E30` (`lead-0x81`, valid `0x81..0x88`). ASCII lead `< 0x81` selects
     no glyph → blank box. Fullwidth Latin (`0x8260`–`0x8279` Ａ–Ｚ, etc.) is
     handled, which is why the fullwidth test line drew.
- **Patch site:** translate ASCII → fullwidth SJIS (0x82 bank) at the byte read
  `0x13A390` and force `gp-0x7e8c = 0x80`. Details + conversion table in
  `RENDERER.md`.

## Emulator automation

`tools/drive.ps1` sends keystrokes to the PCSX2 window (`keybd_event`; arrow
keys need `KEYEVENTF_EXTENDEDKEY`). `tools/capture.ps1` grabs the window via
`PrintWindow` with `PW_RENDERFULLCONTENT` (captures the GPU surface). Boot the
raw ISO for fast iteration:

```
pcsx2-qt.exe -fastboot -batch -- "srwz_en.bin"
```

PCSX2 v2 default pad: arrows = d-pad, Z/X/A/S = face buttons (Cross/Circle/
Square/Triangle vary by profile — this project used K=Cross, L=Circle,
I=Triangle), Enter = Start.
