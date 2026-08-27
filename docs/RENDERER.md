# The dialogue glyph renderer — full trace (BLOCKER RESOLVED)

This is the result of the runtime trace described in `DEBUGGER_TRACE.md`. It
identifies the exact routines and instructions that turn a stored dialogue byte
into an on-screen glyph, why raw ASCII renders as blank boxes, and where the
ASCII→fullwidth patch goes.

All addresses are EE virtual addresses in the boot ELF `SLPS_258.87`
(PT_LOAD vaddr `0x100000`). Confirmed on PCSX2 2.6.3 against the SLPS-25887
"the Best" dump (Game CRC `6081EA7F`) with the chapter-1 English patch applied.

## How it was found

- Booted the patched build, reached the chapter-1 corridor scene (Setsuko
  route), saved a savestate on a displayed line.
- The decompressed script lives at `~0x75Exxxx`; a per-line pointer table at
  `0x759xxx` (0x20-byte stride) points at each line. The *currently displayed*
  line is expanded into a message-window object.
- Dumped EE RAM from the (uncompressed) savestate to locate the text, then used
  PCSX2 **memory read breakpoints** on the message buffer and walked the call
  stack. Confirmed each routine statically by disassembling the extracted ELF
  (`tools/pullelf.py` + `tools/mdis.py`).

## The message-window object

`MessageWindow::setText` at **`0x20C9B0`** (dispatched via a C++ vtable, base
`0x447848`; singleton pointer at `0x5A3F80`; object size `0x480`) copies the
line into the object at **`obj+0xC`**:

- if the line contains macros, it is expanded via `0x2011D0` → `0x201590`
  (the `$n`/`$F`/`$N` name-token expander; matches a 41-byte-stride token table);
- otherwise a plain `strcpy` (`0x1A0D88`).

Helper library routines seen constantly in the path: `strcpy` = `0x1A0D88` /
byte-tail loop `0x1A0E50`; `strlen` = `0x1A0EA0` / inner loop `0x1A0FA0`
(`lb` at `0x1A0FB4`). The **SJIS lead-byte classifier** is `0x2010B0` (only two
callers: the macro expander `0x2015F4` and the line-length/word-wrap measurer
`0x2229D0`); it is a *measuring* helper, not the renderer — confirming the
earlier note in `FINDINGS.md`.

## The render call chain (per frame)

```
scenario interpreter (0x1E5F20 dispatch)
  → … → 0x20C930 (vtable dispatch: lw t9,(s0); jalr)
    → 0x209420
      → 0x2212B0   line layout / word-wrap / half-vs-full-width decision
          → 0x220E70   per-token char fetch (calls 0x221030 word splitter)
          → 0x220DB0   draw one text segment at (x,y) with a font/style struct
              → 0x2254D0  set pen position (x,y)
              → 0x225290  glyph-draw dispatch (reads the width flag, sets scale)
                  → 0x13A290  innermost glyph blit — builds the GS sprite packet
                      (font sprite API cluster: 0x139A60/0x139D50/0x139E20/
                       0x139E90/0x139EA0/0x139EE0/0x139EF0)
```

## The half-width vs full-width decision (root cause #1)

In the layout routine `0x2212B0`, after fetching a byte:

```
0x22137C  slti  at, v0, 0x80      ; is the byte < 0x80  (i.e. ASCII / half-width)?
0x221380  beqz  at, 0x221398      ; >= 0x80 (SJIS lead) → full-width branch
0x221388  addiu v0, zero, 0x40    ; ASCII  → cell width 0x40 (half)
0x221390  sb    v0, -0x7e8c(gp)   ; store char cell width
0x221398  addiu v0, zero, 0x80    ; SJIS   → cell width 0x80 (full)
0x22139C  sb    v0, -0x7e8c(gp)
```

The gp-relative byte at **`gp-0x7e8c`** is the "current char cell width"
(`0x40` half / `0x80` full). It is consumed in `0x225290`
(`lbu v0,-0x7e8c(gp)` at `0x225300`/`0x22533C`) to pick the glyph cell scale and
to halve the UV/advance for half-width cells.

## The byte → glyph-texture mapping (root cause #2)

Inside the blit `0x13A290`:

```
0x13A390  lbu   v0,(s4)           ; read a text byte, s4++
0x13A398  ...   == 0x0A ?         ; newline handling
0x13A3B8  v1 = v0 - 0x2E
0x13A3C0  if (v1 < 0x10) → jump table at 0x433E50   ; control codes 0x2E..0x3D
          ; otherwise fall through to the normal-glyph path:
0x13A5F8  lbu   a0,(s4)           ; read the SECOND byte (SJIS trail), s4++
0x13A600  sll   v0, v0, 8         ; v0 = lead << 8
0x13A608  or    v0, v0, a0        ; v0 = full 2-byte SJIS code (lead<<8 | trail)
...       range checks on v0, e.g.:
0x13A6C0  ori   at, zero, 0x827a  ; fullwidth Latin UPPER Ａ..Ｚ  = 0x8260..0x8279
0x13A6CC  ori   v1, zero, 0x8260
0x13A6F8  ori   at, zero, 0x82f2  ; fullwidth lower / digits block  (0x8281..)
0x13A7A4  sh    v0, 0x60(0x70000000)   ; store the 2-byte code into the packet
0x13A7AC  lbu   a0, 0x61(0x70000000)   ; take the LEAD byte
0x13A7B0  v0 = lead - 0x81
0x13A7B4  if (v0 < 8) → jump table at 0x433E30   ; per-bank (0x81..0x88) UV calc
          ; each bank handler computes the font-texture row/col from the code,
          ; e.g. 0x13A7D8: v0 = code - 0x8000 - 0x140
```

**The renderer indexes the font purely by the 2-byte SJIS code.** Fullwidth
Latin (`0x8260`–`0x8279` = Ａ–Ｚ, `0x8281`–`0x829A` = ａ–ｚ, digits `0x824F+`)
have real glyphs, which is why the injected fullwidth test line rendered. A raw
ASCII byte has a lead byte `< 0x81`, which is **not** in the `0x81..0x88` bank
jump table, so no glyph texture is selected → the blank box. (And with the
`0x40` half-width flag it would also be scaled to a half cell that the font has
no art for.)

## The patch (IMPLEMENTED — `tools/patch_renderer.py`)

**Status: working, verified in PCSX2** — chapter-1 corridor dialogue renders
English as fullwidth glyphs (e.g. `Jerid "Hey. You there..."`,
`セツコ "...Do you mean me, sir?"` with the Japanese speaker name intact on the
same line).

The engine already draws 2-byte fullwidth glyphs perfectly, so the fix converts
ASCII to its fullwidth-SJIS twin **in the message buffer**, upstream of the
whole renderer, rather than inside the glyph blit.

**Hook:** `MessageWindow::setText` (`0x20C9B0`) — the method that copies a line
into the message object at `obj+0xC`. Its first two instructions are replaced
with `j <cave>; nop`. The cave reimplements setText:

1. call `NEEDEXP` (`0x200F80`); if it returns a context, `EXPAND` (`0x2011D0`)
   the line into a stack scratch buffer, else `strcpy` (`0x1A0D88`) into it;
2. **per-character convert** scratch → `obj+0xC`:
   - 2-byte SJIS lead (`0x81..0x9F`, `0xE0..0xFC`) → copy both bytes verbatim
     (Japanese, incl. `$name` expansions, passes straight through);
   - single high byte (`0xA0..0xDF` half-width kana, `≥0xFD`) → copy verbatim;
   - `0x0A` and other `<0x20` controls → copy verbatim;
   - printable ASCII `0x20..0x7E` → look up 2-byte fullwidth code in a table.

Because the conversion targets the **RAM message buffer** (not the scenario
data), the offset/byte-length constraint from `FINDINGS.md` is untouched — the
stored strings stay compact half-width ASCII. And because the renderer now
receives genuine 2-byte SJIS, both the `0x22137C` width decision and the
`0x13A290` glyph lookup do the right thing automatically (no need to touch
`gp-0x7e8c` or the blit).

**ASCII → fullwidth SJIS table** (0x82 bank; built via cp932 in the patcher):
  - `'A'..'Z'` (0x41..0x5A) → `0x8260 + (c-0x41)`
  - `'a'..'z'` (0x61..0x7A) → `0x8281 + (c-0x61)`
  - `'0'..'9'` (0x30..0x39) → `0x824F + (c-0x2F)`  (`0x8250`=０ … `0x8259`=９)
  - space → `0x8140`; punctuation per cp932, except `"`→`0x8168` and `'`→`0x8166`
    (cp932 maps those into the `0xEE` NEC bank, which is **not** in the renderer's
    `0x81..0x88` UV table and would render blank — so they are overridden).

**Why per-character, not a whole-string gate:** many chapter-1 lines contain
`$n`/`$F` name macros, and the default player name is Japanese (セツコ). A
whole-string "convert only if pure ASCII" gate would leave every such line
blank. Per-character conversion passes the Japanese name through and converts
the English around it. Risk of mistranslating a literal `0x2E..0x3D` control
byte inside a Japanese string was checked against all 205 STAGE.BIN records:
of 73,962 Japanese text runs, only 12 contain any such byte (all a single
leading `:`), i.e. message text effectively never uses `0x2E..0x3D` inline.

**Code cave — use dead code, NOT file-zero padding.** First attempt put the
routine in the only large zero-run in the loaded segment (`0x3F5760`). That
failed: a RAM dump showed the game uses that region as a **live data array** at
runtime and overwrote the code (all text went blank). File-zero padding in the
loaded segment can be BSS/globals. The working cave is a **dead function** at
`0x188470` (0x660 bytes), verified unreferenced by any `jal`, pointer word, or
`lui`+`addiu`/`ori` computed address — and code memory is never written at
runtime. The scratch buffer lives on the stack.

### Known follow-ups (cosmetic, non-blocking)
- **Line width:** fullwidth is double-wide, so long lines can overrun/clip
  (e.g. the `~Lutetium Base - Corridor~` header). Tighten the per-char pen
  advance (`lb v1,0x10(s5)` @ `0x221638`, added to X @ `0x221644` in `0x2212B0`)
  or shorten a few strings — do **not** grow stored data.
- **Default name:** romanize the default player name so `$n`/`$F` lines don't
  show Japanese kana amid English.

## Key addresses (quick reference)

| Addr | Role |
|---|---|
| `0x20C9B0` | `MessageWindow::setText` (vtable), writes line to `obj+0xC` |
| `0x2011D0` / `0x201590` | macro/name-token expander (`$n`,`$F`,`$N`) |
| `0x2010B0` | SJIS lead-byte classifier (measuring only) |
| `0x2212B0` | line layout / word-wrap; **half-vs-full width decision @ `0x22137C`** |
| `0x220DB0` | draw one segment at (x,y); loads font/style struct; per-char advance |
| `0x225290` | glyph-draw dispatch; reads width flag `gp-0x7e8c`; sets scale |
| `0x13A290` | **innermost glyph blit**; byte read @ `0x13A390`; 2-byte code @ `0x13A600`; font UV @ `0x13A7B0` |
| `gp-0x7e8c` | current char cell width (`0x40` half / `0x80` full) |
| `0x433E30` | per-bank (lead 0x81..0x88) font-UV jump table |
| `0x433E50` | control-code (0x2E..0x3D) jump table |
| `0x447848` | text/message-window vtable; singleton ptr `0x5A3F80`; obj size `0x480` |

## Flush 0x13ACA0 fully reversed (for true VWF)

The per-glyph 0x20-byte struct is turned into GS packets here. Key facts:

- **struct+0x10 is a TEXTURE register field**, NOT dest-width. It is `andi 0xff;
  dsll32 0x18` -> high byte of a 64-bit GS reg (with struct+0x11 vram page)
  at 0x13AD9C..0x13ADDC. Halving it corrupts texture sampling -> the **hardware-
  renderer wash-out** we saw. (My earlier `patch_font_destwidth.py` used the
  wrong lever; abandon it.)
- **Real dest-width is HARDCODED**: sprite right/bottom = x1+0x18 / y1+0x18 at
  `0x13AE5C addiu t3,t0,0x17` (t0 = struct+0 + 1) and `0x13AE68 addiu t0,t2,0x17`.
- **Each glyph draws a FILL sprite + an 8-sprite black OUTLINE** (drawn when
  struct+0x1c != 0): loop `0x13AF68..0x13AF8` (8 iters) then position tweaks
  `0x13AFB8..` subtracting **0x10 in X / 8 in Y** per outline copy. This outline
  is the contrast (readability on the light box) AND the source of the
  "black/white" mess when geometry/advance desync it.
- struct+0 = x1, struct+2 = y1 (dest); struct+4/+6/+0xc/+0xe/+8 build UV
  (source) coords with globals a1=-0x1cca(0x47), a2=-0x1ccc(0x47);
  struct+0x12 = "draw" flag; struct+0x1c = "has outline" flag.
- **Free struct bytes (never written by the blit): 0x13, 0x1d, 0x1e, 0x1f** ->
  usable as a per-glyph "is Latin/half-width" flag set in the blit and read in
  the flush.

### True-VWF plan (per-Latin-glyph, flag = struct+0x1d)
1. blit: write struct+0x1d = 1 for Latin codes (0x824F..0x829A, 0x8140) else 0.
2. flush dest-width: at 0x13AE5C/0x13AE68 use +0x0B instead of +0x17 when flag.
3. flush outline: halve the 0x10/8 outline offsets (0x13AFB8..) when flag.
4. advance/pitch: 0x0C main pen (0x13AAE8) + shadow/second pen for Latin.
5. UV: sample the left ~12px (needs squished art) OR minify 24->12 (condensed).

This is a multi-hook flush patch (register-tight; hook with `j`, not `jal`,
since flush ra is live; stack-save one scratch). Several build/test cycles.
