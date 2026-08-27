# Variable-width / half-width ASCII font (Z2-style) — plan & progress

Goal: replace the working-but-wide fullwidth-remap English (see `RENDERER.md`)
with true half-width, proportional glyphs like the SRW **Z2** fan translation.

## Research — how other teams do it

- **Precedent on the same engine family:** `z2hackman`'s **SRW Z2 (PSP)**
  English patch added **variable-width font support in v0.8.0** (May 2026) after
  an earlier fixed-width release. Same Banpresto SRW engine lineage as our Z
  (PS2) — proves VWF is viable here. Their font data is PSP-format, not directly
  reusable. (romhacking.net forum topic 41169; GBAtemp thread 335313.)
- **Standard VWF ASM recipe** (romhacking.net docs 770, GBAtemp PSP/PS2 VWF ASM
  thread 374967) — matches what we already reverse-engineered:
  1. find where the fixed glyph width is added to the X pen position,
  2. trace back to where that width is loaded,
  3. extend the executable with extra code + a per-character width table,
  4. inject a per-character width lookup.
  For a fullwidth-SJIS-only font: either add half-width glyphs, or map ASCII to
  existing glyphs (we did the latter for the shipped build).
- Tool others use: "Font Width Scanner" to find the fixed-width site. We already
  have it from the trace (`0x221638`/`0x221644`).

## Our approach: self-contained ASCII atlas

We could not locate the on-disc master dialogue font (it's a 4bpp glyph atlas in
GS VRAM at ~`0x1b0000`, uploaded at boot from an unidentified/likely-packed
source — KVMDATA/JTIM are portraits/UI/baked-English-menus, not it). So instead
of editing the master font, inject our **own** half-width ASCII atlas we fully
control, and branch the ASCII draw to it.

### Milestone 1 — glyph atlas + width table  ✅ DONE
`tools/make_ascii_font.py` renders ASCII 0x20–0x7E from a TTF (Tahoma 14px),
antialiased, quantized to 4bpp (16 levels, matching the game font format and
giving smooth edges). Outputs to `_work/font/`:
- `ascii_font.4bpp` — 256×96, 16×16 cells, 16 cols × 6 rows, 12288 bytes
- `ascii_widths.bin` — 95 bytes, per-glyph advance (avg 9.7px vs 16px cell)
- `ascii_font_preview.png` — visual check

### Milestone 2 — inject atlas  ⏳ IN PROGRESS
**Font atlas found in EE RAM: `0x990600`, 512×480, 4bpp, 0x1E000 bytes**
(alloc'd+zeroed at init `0x13A0F4`; uploaded to VRAM by `0x1CD740` via `0x136330`
with width `0x200`=512). Rendered it (`_work/font/eefont_512x480.png` equiv): the
**top ~2 rows hold the fixed fullwidth Latin/digit block** (`0-9 A-Z / - ( )`)
that our current patch draws; below is the on-demand **kanji cache** (holds the
current on-screen sentence's glyphs).

Cleanest injection: replace the fixed **Latin block** in the atlas with our
half-width glyphs and address ASCII directly to those cells — needs the loader
that fills the Latin block (find the master source that seeds `0x990600` top),
OR a boot hook that overwrites those cells after fill. Alternatively place our
atlas in the unused lower/again region of the 512-wide sheet and add a new bank.
Open items: locate the Latin-block loader/master; per-glyph UV; swizzle for VRAM
upload (the game's own uploader handles it if we edit the EE-RAM atlas pre-DMA).

### Milestone 3 — branch ASCII draw to our atlas  ⏳ TODO
In the blit, for ASCII bytes (or a reserved code range we assign in setText),
set the texture source to our atlas and compute UV from `(char-0x20)` →
`col=idx%16, row=idx//16`. Reuse the existing 4bpp sprite path.

### Milestone 4 — per-character advance (the VWF)  ⏳ TODO
Advance site: `0x2212B0` uses `lb v1,0x10(s5)` (fixed cell width) @ `0x221638`,
added to X @ `0x221644` (segment-level; per-glyph advance is in the draw loop).
Inject a width-table lookup (`ascii_widths.bin`) so ASCII glyphs advance by
their real width. Keep full width for real Japanese (2-byte SJIS) glyphs.

## Full font pipeline (reverse-engineered)

```
font file (COMPRESSED) ── loaded to buffer at init
  └─ 0x1C6C40  decode  ┐
     0x10D570/0x10D898/0x11B2E0  decompress  ┘→ decoded 24×24 4bpp glyphs
        └─ decoded-glyph buffer  0x9AE610  (desc +0x1c58; 288 bytes/glyph)
           └─ 0x13C5C0  copy glyph → cache  0x990600  (512×480 4bpp, desc +0x1c50)
              └─ 0x143180 / 0x1CD740  DMA cache → GS VRAM (dest 0x1180, via 0x136330)
                 └─ 0x13A290  blit VRAM → screen (per-glyph sprite)
```

- Glyph cell is **24×24 4bpp = 288 bytes** (not 16×16). Atlas regenerated to
  match: `_work/font/ascii_font24.4bpp` (384×144), `ascii_widths24.bin`.
- Font init routine: `0x139F60`. Master is compressed (codecs `0x10D570` etc.).
- The cache `0x990600` holds a Latin/digit block + an on-demand kanji cache.

## Why full VWF is a multi-session build (honest assessment)

The font system is **dynamic, multi-buffer, and compressed**, which is hostile
to a one-shot static glyph swap:
- editing the master needs the (unknown) compression codec — avoid;
- the decoded/cache buffers are filled on demand, so a persistent swap needs a
  **boot-time hook that overwrites the decoded Latin glyphs after decode** and
  survives re-decode/upload;
- plus a **per-glyph advance** patch (width table) at the advance site.

### Refined injection plan (no need to touch the compressed master)
1. Boot-hook after `0x139F60` init completes → overwrite the fullwidth-Latin
   glyph slots in the decoded buffer with our 24×24 half-width glyphs
   (`ascii_font24.4bpp`). Requires the Latin glyph indices in `0x9AE610`.
2. Keep addressing them by the existing fullwidth codes (setText already emits
   those) — no UV/addressing change needed; they just render narrower.
3. Per-glyph advance: inject a width-table lookup at the advance site
   (`0x2212B0`, `lb v1,0x10(s5)` @ `0x221638`) for the Latin codes, full width
   for real kanji. Uses `ascii_widths24.bin`.
4. Build → test → iterate (spacing/baseline tuning).

Each step needs a build+PCSX2 test cycle, so this is several more work sessions,
unlike the contained setText patch.

## Build attempt 1 (boot-hook glyph swap) — findings

Implemented `tools/make_font_data.py` (1bpp glyph blob + confirmed JIS indices:
digits `0-9`=207–216, `A-Z`=224–249, `a-z`=257–282) and `tools/patch_font.py`
(boot-hook at font-init tail `0x13A23C` that expands the glyphs into the decoded
buffer). **It crashed at boot** — TLB miss / null load. Root cause: the chosen
code cave `0x1A1B18` is **not dead** — it's a relative-branch target
(`bne …,0x1a1b18` @ `0x1A1ABC`; `bltz …,0x1a1b18` @ `0x1A1ACC`) inside a live
function's tail path. My dead-code detector didn't account for intra-function
branch targets.

Fixed the detector (now excludes jal / data-ptr / computed-addr / **external
relative-branch** targets). Result: **the ELF has no single safe cave ≥ ~1.6 KB**
(largest is `0x188470` at 1632 B, already used by the setText patch; next is
`0x3B9400` at 1472 B). Total safe cave space ≈ 16.5 KB across 20 small holes.
The ~4.7 KB glyph blob does not fit any single cave.

Also confirmed the **master font is compressed** with a bespoke codec
(`0x1C6C40` bitstream decompressor — not banlz, not a simple 1bpp→4bpp expand),
so editing glyphs in the master file needs that codec reversed + a recompressor.

The working fullwidth build was restored to `srwz_en2.bin` after the crash.

## Remaining options (all real, none quick)
- **A. Crack the font codec** (`0x1C6C40`): decompress → edit Latin glyphs →
  recompress → reinject. Cleanest end result; biggest effort (reverse a custom
  compressor). No runtime code needed (+ small advance patch).
- **B. Multi-cave split boot-hook**: store the glyph blob across several verified
  caves (16.5 KB total available) with a chunk table in the hook. Full quality,
  no codec work, but fiddly hand-assembly across caves and more crash-prone
  build/test cycles.
- **C. Ship fullwidth + polish**: keep the working fullwidth build and just do
  the per-glyph advance/clip tuning. Not Z2-proportional, but done and safe.

## Build attempt 2 (multi-cave boot-hook, Option B) — findings

`tools/patch_font.py` rewritten to split the glyph blob across several
statically-"safe" caves with a chunk table in the hook. **Crashed at boot** —
emulog: `Trap exception at 0x0023c370`, i.e. the game *executed* my glyph data
in the `0x23C370` cave. That cave passed every static check (no jal / data-ptr /
computed lui+addiu / relative-branch ref, and its predecessor is `jr ra`+pad,
identical to the working `0x188470` cave). It is still reached at runtime —
almost certainly a `jalr` through a runtime-computed pointer that static analysis
can't see.

**Conclusion:** static cave-finding is not reliable here (2/2 non-setText caves
failed). `0x188470` (setText) is the only *proven* safe cave, found by luck.
Reliably placing the ~4.7 KB glyph blob needs either runtime cave verification
(exec-breakpoint each candidate — several slow boot cycles) or a different data
home. The working fullwidth build was restored after each crash.

### Revised options
- **A. Crack the font codec** (`0x1C6C40` bitstream): edit glyphs in the master
  file, recompress, reinject. No runtime code/data → no cave problem. Clean;
  biggest RE effort (reverse a custom compressor + write an encoder).
- **B-verify. Runtime-verify caves**: exec-breakpoint the ~20 candidate caves in
  one debugger boot, keep only the never-hit ones, then embed good glyphs.
  Makes B reliable; grindy.
- **B-squish. Code-only (no data)**: hook horizontally compresses each existing
  fullwidth Latin glyph to half-width in place — fits the one proven cave, fully
  reliable, but squished fullwidth glyphs look cramped (lower quality than
  purpose-drawn half-width).
- **C. Ship fullwidth + advance polish**: keep the working build; just tune
  spacing so long lines stop clipping.

## Build attempt 3 (B-squish, code-only) — WORKS

`tools/patch_font_squish.py`: code-only boot-hook (no data caves) placed in the
**spare space of the proven setText cave** (`0x188470+0x220`, after setText's
code+fullwidth-table). At font-init tail (`0x13A23C`) it horizontally condenses
each fullwidth Latin/digit glyph in the decoded buffer `0x9AE610` 2:1 into its
left 12 px (max of column pairs), clearing the right half, for index ranges
digits 207–216, A–Z 224–249, a–z 257–282.

Result (verified in PCSX2): **glyphs are now half-width** (`"2nd Lt. … sir."`
renders narrow), Japanese unchanged, stable, no crashes. (An early null-object
setText call logs a harmless TLB miss at boot; game continues.)

Gotcha fixed: the squish hook must sit **after setText's code AND its fullwidth
table** in the shared cave, else it clobbers the table and setText writes to a
null object.

Remaining: **advance/spacing** — each half-width glyph still occupies a fullwidth
cell, so letters are widely spaced. Closing the gap = the advance patch
(force half advance / width flag `gp-0x7e8c`=0x40 for the Latin codes, whose
squished art sits in the left half so half-UV sampling shows it correctly).

## Build attempt 4 (advance / tight spacing) — doubling artifact

`tools/patch_font_advance.py` hooks the blit's per-glyph X advance
(`addiu v0,v0,0x18` @ `0x13AAE8`, pen X in GS field 0x2c) to add 0x0C instead of
0x18 for the Latin/digit codes (0x824F–0x829A, 0x8140). Hook placed in the
setText cave's remaining space; assembles/injects cleanly.

**Result: each glyph renders doubled** (`Jerid`→`J ee rr i dd`,
`Hey`→`H ee yy`), i.e. two overlaid copies at different letter pitch. The
squish-only build (advance untouched) is clean, so the advance change is the
cause. Only one X-advance site exists in the blit, so it is not a second
unpatched advance — it is a deeper interaction (dialogue text is drawn in two
passes — shadow + main — and/or the 24px sprite dest width vs the 12px step;
resolving it needs more GS/blit RE than done here). Reverted to squish-only.

## Advance investigation — root cause found, clean fix blocked

Per-glyph X advance is `addiu v0,v0,0x18` @ `0x13AAE8` (pen X = GS field 0x2c).
Hooking it to add `0x0C`/`0x10` for Latin codes makes glyphs render **doubled/
ghosted**; the doubling *shrinks* as the advance approaches 0x18 and vanishes at
0x18. So the drawn glyph **sprite dest-width is 24px**, and any advance < 24
overlaps consecutive sprites (they alpha-blend, so both show).

- Forcing the native half-width flag `gp-0x7e8c`=0x40 (test) renders **clean but
  full-width** — it samples the left-half source but stretches to a 24px dest,
  so it does not compact.
- Tried to locate the sprite **dest-width** to halve it: the per-glyph draw is a
  compact command struct built in the EE display list (`~0x98BD90`, base from
  desc `0x46E388`), not raw GS regs, and the dest-width isn't an obvious field
  (`s0+0x11` = 0x24/0x2c is a VRAM-page selector by pen-Y, not width). The GS
  packet in scratchpad is transient (empty at savestate time). Pinning the
  dest-width needs **live GPU/GIF stepping** — beyond this pass.

**Net:** compact half-width needs `dest-width = advance = 12` set together for
Latin codes; the advance half is done, the dest-width half is blocked on deeper
GS RE. Clean options today are half-width-glyphs-with-wide-spacing (squish-only)
or full-width.

## Status
- Milestone 1 (atlas + width table + glyph blob) ✅.
- Half-width glyphs rendering in-game (B-squish, reliable) ✅.
- Tight/proportional advance ❌ — advance < sprite dest-width (24) → overlap
  ghosting; clean fix needs halving the GS sprite dest-width (live-GPU RE).
- Builds: `_work/patched/fullwidth_only.elf` (uniform full-width);
  `_work/patched/s2.elf` (setText+squish = half-width glyphs, wide spacing —
  currently in `srwz_en2.bin`).
- Full font pipeline reverse-engineered ✅ (compressed master → `0x1C6C40`
  decode → `0x9AE610` decoded buffer → `0x13C5C0` copy → `0x990600` cache →
  VRAM → blit `0x13A290`).
- Injection blocked on ELF cave space / master compression — see options A/B/C.
- Shipped fullwidth build (`RENDERER.md`) is the fully-playable fallback and is
  currently in `srwz_en2.bin`.

## Advance investigation — RESOLVED: dest-width is a struct field (static)

Continuing the trace past "needs live GPU/GIF stepping": the per-glyph sprite
**dest-width is not a hidden GS reg — it is a field in the 0x20-byte command
struct** that the blit `0x13A290` accumulates and the flush `0x13ACA0` turns
into GIF/GS packets.

In the blit's per-glyph packet write:

```
0x13AB48  lh  v1, 0x1c(s1)     ; s1 = font/style descriptor; +0x1c = glyph cell size
0x13AB4C  sb  v1, 0x10(s0)     ; struct+0x10 = dest size (same for every glyph => 24px)
```

Other struct fields (all from the descriptor s1, hence constant per font):
`+0x11` VRAM page (0x24/0x2c by pen-Y), `+0x12`←s1+0x4a, `+0x14`←s1+0x24,
`+0x18`←s1+0x28, `+0x1c`←s1+0x50, `+0`=penX, `+2`=penY. Struct stride 0x20
(`addiu s0,s0,0x20` @ `0x13AB9C`).

In the flush `0x13ACA0` (builds the GIF packet from the struct array):

```
0x13AD78  lbu t1, 0x10(a3)     ; a3 = struct; reads dest size back
0x13AD9C  andi t0, t1, 0xff
0x13ADA8  dsll32 t0, t0, 0x18  ; shifted into the GS XY/UV coordinate
```

**So dest-width = struct+0x10, written per-glyph at `0x13AB4C` from `s1+0x1c`.**
This is the field the earlier pass couldn't find. It can be halved *statically*
at the blit — no live-GPU stepping.

### Clean tight-half-width recipe (three coordinated halvings for Latin only)
For a Latin/digit code (scratchpad `0x70000000+0x60` in `0x824F..0x829A` /
`0x8140`), set all three to 12px; leave real kanji at 24:

1. **dest-width** — at `0x13AB4C`, write `s1+0x1c >> 1` (0x18→0x0C) to
   struct+0x10 for Latin. (This is the missing piece; the sprite itself becomes
   half-width, so a 0x0C advance no longer overlaps → kills the ghosting.)
2. **advance** — `0x13AAE8` `addiu v0,v0,0x18` → `0x0C` for Latin (already
   prototyped in `patch_font_advance.py`).
3. **source-UV** — the native half-width flag `gp-0x7e8c = 0x40` already halves
   the source sampling (via `0x139ef0`/`0x139a90`); set it for Latin so the
   sprite samples the left-12px squished art.

All three keyed on the same Latin-code test. Implementation note: the blit has
no spare inline bytes at `0x13AB4C`, so hook it (j to cave; recompute
`v1 = s1+0x1c`, halve if scratchpad+0x60 is Latin, `sb v1,0x10(s0)`, return).
Cave pressure is the known constraint (only `0x188470` proven safe) — the three
tweaks are tiny, so they fit alongside the existing setText/squish/advance code
in that cave, or share one Latin-detect helper. Needs a build+PCSX2 test pass
(which the dev loop on the main machine can do); the static unknown is now
closed.

### Two ways to use the dest-width fix (`tools/patch_font_destwidth.py`)

`patch_font_destwidth.py` hooks `0x13AB48/0x13AB4C` and writes a **halved
struct+0x10** (dest size) for Latin codes (assembles to 124 B in the setText
cave). Two ways to combine it:

- **X — condensed (simplest, no squish, no source flag).** Apply *only*
  dest-width + advance halving to the **unsquished** fullwidth glyphs. The GS
  sprite minifies the full 24px glyph into a 12px dest → letters are complete
  but horizontally condensed (2:1), spaced tight, no ghosting (dest == advance).
  Pipeline: `patch_renderer` → `patch_font_destwidth` → `patch_font_advance`
  (skip `patch_font_squish`). Quickest legible tight English.
- **Y — true half-width (best looking).** Keep `patch_font_squish` (art in left
  12px) and also force the native half-width **source** flag `gp-0x7e8c=0x40`
  for Latin so sampling takes only the left 12px, then dest-width + advance = 12
  give 1:1 purpose-proportioned glyphs. Needs the small flag hook
  (`patch_font_flag.py`, TODO) in addition to the three above.

Both still need a build + PCSX2 test pass on the dev loop. Option X requires no
new RE beyond this doc; Option Y adds only the flag hook. Either way the
"dest-width is unfindable / needs live-GPU stepping" blocker is closed — it's
struct+0x10 at `0x13AB4C`.

## Build attempt 5 (Option X: dest-width + dual-advance) — WORKS (tight half-width)

Resolved the ghosting. Two findings closed it:

1. **dest-width = struct+0x10** (written at 0x13AB4C from descriptor s1+0x1c).
   `patch_font_destwidth.py` halves it for Latin. **Isolation test** (dest-width
   only, advance untouched at 0x18) renders perfectly clean half-width glyphs
   with wide 24px spacing — confirming struct+0x10 IS the on-screen dest-width.

2. **There are TWO pens** (glyphs are drawn main + shadow). patch_font_advance
   only halved the MAIN pen (scratch 0x2c @ 0x13AAE8). The **shadow pen**
   (scratch 0x30) advances separately by scratch 0x38 at:
   `0x13AB70 lh a0,0x30(at) / 0x13AB78 lh v1,0x38(at) / 0x13AB7C addu v1,a0,v1 /
   0x13AB84 sh v1,0x30(at)`. Halving only the main pen made the two pens drift
   apart -> interleaved "ghost" doubling that worsened along the line (why
   smaller advance looked worse). `patch_font_shadowadv.py` halves the shadow
   advance to 0x0C for the same Latin codes so both pens track.

**Working Option X pipeline** (in-game verified, PCSX2, Setsuko corridor):
```
patch_renderer  ->  patch_font_destwidth  ->  patch_font_advance (0x0C)
                ->  patch_font_shadowadv (0x0C)
```
Result: tight, condensed, readable half-width English (e.g. Jerid "That's
right. That uniform... You're..."), no squish/atlas/codec work needed. All four
hooks live in the setText cave (0x188470): renderer ~0..0x140, shadow @+0x300,
main-advance @+0x400, dest-width @+0x500. Latin range on all three width hooks:
0x824F..0x829A (fullwidth digits/A-Z/a-z) + 0x8140 (space).

Note: `patch_font_advance.py` value changed 0x10 -> 0x0C to match dest-width.

### Remaining polish (cosmetic, non-blocking)
- **Word-wrap breaks mid-word** ("Jer"/"id"): the line-width measurer
  (layout 0x2212B0 / measurer 0x2229D0) still counts each Latin char as full
  width (0x18), so it wraps ~2x too early. Fix: make the wrap/measure width for
  Latin codes half. Then words won't split.
- Minor per-letter spacing evenness (fixed 0x0C advance is monospace-ish).

## Build attempt 6 (true dest-width) — half-width WORKS clean on hardware; tight pitch still blocked

Full flush RE (see RENDERER.md) fixed the wash-out. `patch_vwf1.py`:
- sets a per-Latin-glyph flag in **struct+0x1d** (free byte) in the blit;
- in the flush at **0x13AE5C** uses sprite right-edge `x1+0x0C` instead of
  `x1+0x18` when the flag is set -> **real** half-width dest (the earlier
  struct+0x10 lever was a texture register, which is why it washed out on the
  hardware renderer).

**Result (Vulkan/hardware, verified): clean, dark, readable half-width English**
("...Do you mean me, sir?"). This is the recommended VWF build:
`patch_renderer -> patch_vwf1`. Downside: pitch is still full (24px) so letters
have gaps (glyph 12px, advance 24px).

**Tight pitch remains blocked.** Reducing the main-pen advance to 0x0C on top of
the 12px dest still produces interleaved satellites ("D)( o))y"). Halving the
outline offsets globally (`patch_outline_half.py`, 48 sites in 0x13AFB0..0x13B300)
made no visible difference, so the satellites are NOT the 8-sprite outline — they
are a deeper fill/UV interaction (the source-coord pen scratch 0x30 / struct+4,
advancing by scratch 0x38, vs the tightened dest) that was not cleanly resolved.
Getting truly tight needs correlating the UV/source advance with the dest pitch
via live GS/GIF stepping.

### State of the deliverables
- **Fullwidth** (`patch_renderer` only): clean, readable, wide. Works everywhere.
- **Half-width** (`patch_renderer -> patch_vwf1`): clean, readable, ~half the
  width, works on hardware; letters have gaps (full pitch). RECOMMENDED VWF.
- Truly tight/proportional: blocked on the fill/UV-vs-pitch correlation.

## Build attempt 7 (STANDARD VWF, per research) — TIGHT, near-clean

Research (romhacking VWF docs 245, GBAtemp PSP-VWF 374967, PS2 Forbidden Siren 2
proportional patch RHDN 6265) says: don't shrink the sprite — keep the full
cell, reduce the pen advance, rely on left-aligned art + transparent right.
Also, "duplicate letters" in VWF = the game draws TWO pens (main + shadow) and
only one advance was reduced -> reduce BOTH.

Working chain (in-game verified, Vulkan): tight, readable half-width, Japanese
untouched (mixed English+JP-name lines correct):
```
patch_renderer            # ASCII -> fullwidth SJIS
patch_font_squish         # art squished into left 12px (right transparent)
patch_font_advance(0x0C)  # MAIN pen pitch
patch_font_shadowadv(0x0C)# SHADOW pen pitch (scratch 0x30 @0x13AB78) -- the
                          #   missing half; reducing only main -> doubling
patch_vwf_flag            # struct+0x1d Latin flag + struct+0x1c=0 (outline off
                          #   for Latin so its 8 copies don't smear)
```
Dropped: the sprite-shrink (patch_vwf1 dest-width) -- non-standard, caused the
tight-pitch satellites and hardware wash-out.

Remaining: minor residual doubling on some glyph shapes ("2nd"->"2dd") -- the
shadow sprite (struct+4, from scratch 0x30) has a fixed offset tuned for
full-width; it now tracks (both pens 0x0C) but the small offset still shows on
some letters. Candidate fix: for Latin, set struct+4 = struct+0 (collapse
shadow onto main) at the 0x13AB24 write, or tune the offset.

Cave layout (0x188470, 0x660): renderer 0..0x20A, squish 0x220..0x39C,
advance 0x400, vwf_flag 0x500, shadowadv 0x590.

## Why SRW Z is a harder VWF target than OG Gaiden (structural proof)

Question: did camd11 (OG Gaiden PS2 VWF) use GS dumps? No -- his changelog shows
the standard method: a per-character **font width table** in dead ELF space +
patching the dialogue renderer's advance. It worked cleanly because OG Gaiden's
text renderer is SIMPLE.

Structural comparison of the two boot ELFs (`tools/rendercmp.py`), counting
direct EE-scratchpad addressing (`lui reg,0x7000` -- SRW Z's font pipeline builds
GS packets in scratchpad 0x70000000):

| marker | SRW Z (SLPS_258.87) | OG Gaiden (SLPS_258.36) |
|---|---|---|
| lui $at,0x7000 (blit's reg) | 939 | 1 |
| lui *,0x7000 (any reg)      | 1034 | 55 |

~19x more direct scratchpad manipulation in SRW Z. SRW Z draws each glyph as a
scratchpad-built GS packet with a two-pen (main scratch 0x2c + shadow scratch
0x30) layout and an 8-sprite outline; OG Gaiden uses a conventional, much
simpler draw. This is why the width-table approach that gave camd11 clean
proportional text fights SRW Z (doubling/satellites): tight spacing must be
coordinated through the whole scratchpad two-pen + outline packet pipeline.

Conclusion: a clean proportional VWF for SRW Z is a genuinely harder GS-pipeline
project than OG Gaiden's, and realistically needs live GS-dump/GIF debugging to
correlate the packet coordinates -- the one thing camd11 did NOT have to do.
The fullwidth build (patch_renderer only) remains the clean, shippable result.

## What the two "pens" actually are (decisive test)

Test: froze the 2nd pen (patched shadow-advance @0x13AB78 to 0). Result in-game:
the whole line collapsed -- a couple of glyphs piled at the start, rest gone.
=> the 2nd pen is NOT a removable shadow. The two pens are the two coordinates
every GS sprite needs:
  - pen 1 (scratch 0x2c) = DESTINATION (screen XY),
  - pen 2 (scratch 0x30) = SOURCE (font-atlas UV position).
Freeze the source -> every glyph copies from the same atlas cell -> line vanishes.
Both essential; neither removable.

This explains the doubling/satellites definitively: it was DEST/SOURCE DESYNC,
never a drifting shadow. Shrinking dest spacing to 0x0C while the source still
stepped 0x18 through the atlas made each 0x0C-wide screen slot sample a 0x18-wide
atlas chunk -> it pulled in half of the NEIGHBORING glyph's atlas cell ("D oo yy"
= two atlas cells in one sprite). The earlier "black/white" was the separate dark
OUTLINE + light fill, unrelated to the pens.

=> Clean tight half-width requires shrinking the DEST and remapping the SOURCE UV
to the correct narrow atlas region per glyph, exactly in step -- the UV/atlas
geometry work that realistically needs a GS dump to nail pixel-perfect. Simple
advance/pitch patches can't do it because they desync dest vs source.

## PINE instrumentation findings (2026-08) — the atlas-corruption bug

Instrumented the glyph blit (`0x13A290`, contains the pen-advance at `0x13AAE8`)
with a RAM ring-buffer logger read live over PINE (tcp:28011). Key results:

- **One blit serves two passes.** The same function both (a) rasterizes glyphs
  from font ROM into the on-VRAM font *cache/atlas* (`s3==0`, non-textured:
  `0x13A318 beqz s3` skips texture-register setup; `srcU=0`, `srcW=16`), and
  (b) draws cached glyphs to screen (`s3!=0`, textured; `srcU` = each glyph's
  looked-up cache X, not a running pen).
- **Latin atlas is pre-built** as a contiguous sweep (space, `0x824F`..`0x829A`
  = 0-9 A-Z a-z) at **destX stride 24** in the ORIGINAL/fullwidth build.
- **The naive advance patch corrupts the atlas.** Reducing the `0x13AAE8`
  advance to 0x0C globally makes the *atlas-build* pen step 12 too, so 16px
  glyphs pack into 12px cells and **overlap in the cache** → every on-screen
  glyph then carries fragments of its neighbour (the `")("` satellites).
- **Fix (partial):** gate the advance reduction on `s3!=0` (screen only), so the
  atlas always builds at full 24px. Verified via PINE: atlas stride returns to
  24 (clean). This is also fail-safe (a mis-classified screen glyph just stays
  full-width, never corrupts).
- **Still unexplained:** with the atlas provably clean (stride 24) the *screen*
  Latin line still garbled at 12px dest pitch. The full-pitch build (dest-width
  12 + Latin outline-off, NO advance) renders perfectly clean but spread out, so
  dest-width + outline gating are correct; only the tight *screen* pitch breaks,
  and the reason is not the atlas. Needs a clean Latin-dialogue screen-pass
  measurement (destX/srcU per Latin glyph) to close out — blocked on reliable
  navigation to the ch1 dialogue (scripted key-timing desyncs on the intro
  cutscene). A PCSX2 save-state at that dialogue removes the blocker.

### Flush geometry (`0x13ACA0`, disassembled)
- dest x1 = `struct+0` (pen `0x2c`, written `0x13AAA4`); dest x2 hardcoded
  `x1+0x18` at `0x13AE5C` (patched to `x1+0x0C` for Latin via `struct+0x1d`).
- source: `U1=struct+4`, **`U2=U1+struct+0xc`** (source width), `V1=struct+6`,
  `V2=V1+struct+0xe` — source size is independent of dest width.
- outline = 8-sprite loop at `0x13AF60`, gated by `struct+0x1c` (both the 0x380
  reserve at `0x13AD80` and the draw loop at `0x13AF44`). Setting `struct+0x1c=0`
  for Latin cleanly removes it (verified on hardware renderer).

Tools: `_work/tools/patch_log.py` (ring logger, s3-filtered), `pine_read.py`
(PINE client + counter reset), `disasm.py` (capstone MIPS64 EE disassembler).

## RESOLVED diagnosis (2026-08) — pen-advance VWF hits an engine wall

Using a user-provided PCSX2 save-state at the ch1 dialogue as a reliable
measurement point + live PINE pokes (advance-immediate pokes invalidate the
recompiler and take effect; the flush/fhook block does not, so width can only be
tested by fresh boot), the tight-VWF garble was fully characterised:

- Fresh-boot measurements are all CORRECT: Latin `destX` stride = 12, `srcU`
  stride = 21, `srcW` = 21 (each glyph samples exactly its own atlas cell),
  `struct+0x1d` Latin flag = 1 (consistent), `struct+0x1c` outline = 0. Geometry
  says it should render clean.
- **Yet only pen pitch 24 renders cleanly.** Pitch 23/21/20/18/12 all garble,
  and the garble is *cumulative down the line* and present even when pitch > glyph
  width (i.e. with gaps, so it is NOT sprite overlap). Enabling the advance hook
  at pitch 24 is clean; the hook mechanism is sound.
- Conclusion: the dialogue font-cache pipeline only composites correctly when
  glyphs sit on their native **24px grid**. Reducing the pen advance breaks the
  21px→12px source **minification / cache sampling** (bleed masked by the gap at
  pitch 24, destructive once tightened). This is an engine constraint, not a
  fixable pen/width bug — the pen-advance + dest-width recipe that works on the
  Z2 *PSP* linear-framebuffer font does not translate to Z's PS2 GS texture-cache.

**Path that would actually work:** the custom half-width ASCII atlas (see "Our
approach" above) — render English glyphs into the cache at native ~12px cells
(no minification), source stride 12 / width 12, dest stride 12, so glyphs stay on
a self-consistent 12px grid with no scaling. Bigger piece of work (build the
atlas + redirect the ASCII glyph source), but sidesteps the sampling wall.

**Shipped:** the clean fullwidth-remap English build remains the deliverable;
it renders correctly and is the safe default on the disc.

## Final finding (2026-08) — split-glyph "two-pen" rendering, tight VWF blocked

Ruled out the remaining hypotheses on the save-state rig:
- **Not the cache we patched.** The screen samples a **21px source layer** (source
  pen 0x30 strides a hardcoded 21, `srcW`=21) that is *separate* from the 24px
  "0123ABC" master cache. Rebuilding that master at 12px (ungated advance +
  fhook) does NOT change the screen's 21px source stride, so the cache-reuse
  shortcut cannot reach what the screen reads.
- **Not bilinear.** Forced PCSX2 `filter=0` (Nearest): the garble is unchanged.
  So it is not minification/edge-bleed from texture filtering.
- **It is glyph *splitting*.** At max zoom each Latin glyph tears into separated
  half-strokes (an 'o' becomes `")("`), some glyphs surviving intact. The engine
  composes each glyph from pieces positioned by two pens on a 24px grid; reducing
  the dest pen stride pulls the halves apart. Every single-sprite measurement
  (destX=12, srcU=21, srcW=21, flag/outline correct) says "clean", yet it splits
  — the width/overlap model does not describe what the hardware draws.

Conclusion: tightening via pen/width patching is not viable on this engine. A real
tight VWF needs a **self-contained replacement path**: our own 12px ASCII glyph
bitmaps in GS-samplable memory + a fully custom source/dest setup for ASCII draws
(bypassing the two-pen 21px layer entirely). That is a standalone RE + GS-upload
implementation project, not a patch on the existing pipeline.

**Deliverable stands: the clean fullwidth-remap English build.** It renders
correctly; the disc default and `patch/srwz_ch1_en.xdelta` are this build.
