# Custom half-width font — GS injection project

Goal: render English dialogue with real 12px half-width Latin glyph shapes
(no squish, no crop), by injecting our own glyph bitmaps into the game's font
and redirecting/retiming the Latin draws.

## Why this is the only route (all others exhausted — see VWF.md, RENDERER.md)
- Font has NO half-width Latin glyphs (blank boxes).
- Squishing fullwidth distorts; native half-width path crops.
- On-screen text samples a PER-LINE dynamic glyph cache (512x256 RT) rasterized
  from a master 4bpp font atlas in GS VRAM (~0x1b0000), uploaded at boot from an
  unidentified/packed source. So PCSX2 texture replacement is per-line
  (impractical) and the master source can't be edited on disc.

## Plan (milestones)
1. **Understand the font pipeline**: where the master font lives in VRAM, its
   format (4bpp + CLUT), how the atlas-build copies master→cache, and find a
   reusable GS texture-upload path (or the boot upload) we can hook/call.
2. **Author** 12px half-width Latin glyph bitmaps (0-9, A-Z, a-z) in the font's
   pixel format, embedded in the ELF (need ~6KB free space).
3. **Inject**: at scene init, DMA-upload our glyphs into VRAM — either overwrite
   the master font's Latin cells, or a free region + redirect the Latin source.
4. **Retime/space**: tighten the per-char advance (layout 0x221644) + dest width
   (dialogue path 0x13B304) for Latin so the 12px glyphs tile cleanly.
5. Test each step with a user-provided dialogue on screen (PINE read + capture).

## Status: FONT RENDERS (tight half-width, in-game) — blocked only on a two-pen
## ghost + word-wrap. Shipping build reverted to fullwidth pending that polish.
## Full working recipe + the exact blocker are in the "OUTCOME (2026-08-12)"
## section at the bottom. NOTE: several milestone-1 guesses below were WRONG and
## are corrected there (cache is 4bpp+CLUT PSMT4HL, NOT PSMCT32; a1/a2 are the
## dest text-origin, NOT the source-UV base).

## Milestone 1 findings (pipeline + upload) — DONE
- Screen samples a **32-bit RGBA (PSMCT32)** cache: TEX0 template at `0x3f85d0`
  = 512x256, TBW=8, PSM=0. So our atlas can be plain 32-bit RGBA — no CLUT.
- Cache VRAM base TBP0=4480 (~0x118000 bytes).
- **GIF-DMA send pattern** (reusable) at `0x1a781c`: `D2_QWC=0x1000A020`,
  `D2_MADR=0x1000A010` (packet phys addr), `D2_CHCR=0x1000A000 <- 0x101` (normal
  mode), then DMA-wait `jal 0x10d258`. We replicate this to upload our atlas.
- **Per-glyph texture base = struct+0x10/0x11** (patched into a GS reg in the
  flush at 0x13ADC4..). The **bhook already writes struct fields**, so we set the
  texture base + srcU/srcV + srcW=12 for Latin glyphs to sample our atlas; width
  via fhook2 (0x13B304). No draw-path rewrite needed.

## Remaining risks
- Free VRAM region for our atlas (upload once at scene init).
- Upload timing / not corrupting GS state.
- Exact struct+0x10/0x11 encoding of the texture base.
- Glyph coloring (does the prim tint the sampled texel, or use texel color).

## Milestone 3 plan locked (implementation started)
- **Atlas+code storage**: add ONE extra PT_LOAD (room in PH table: ends 0x1a74 <
  data 0x1a80) mapping our blob to **vaddr 0x1400000** (verified free/zero EE RAM,
  flags=RWX) — holds the glyph atlas + the DMA/redirect code. Unlimited space.
- **Upload**: replicate the GIF-DMA send (MADR=packet phys, QWC, CHCR=0x101, wait
  jal 0x10d258). Host->local GIFtag (A+D: BITBLTBUF/TRXPOS/TRXREG/TRXDIR) + IMAGE
  GIFtag + atlas data. Trigger once (guarded) from the setText hook.
- **Format/color**: atlas as **PSMCT32** (easy linear transfer). Redirect Latin
  glyphs' TEX0 -> our atlas (TBP0, PSM=0, TFX to tint by prim OR DECAL baked
  color), TCC=1 alpha, srcU/srcV -> our glyph, srcW=12; dest width via fhook2.
  (4bpp+CLUT avoided; color tuned via prim/baked, refined in test.)
- **Free VRAM** for atlas: try byte 0x380000 (DBP 0x3800); verify empirically (no
  display corruption), relocate if needed.
- Iterative: each test needs a user-provided dialogue on screen.

## Milestone 3a: code injection WORKS (verified)
- Extra PT_LOAD to 0x1400000 loads correctly. Two loader gotchas fixed:
  1. p_offset must be congruent to p_vaddr mod p_align (0x80) — pad file first.
  2. PCSX2 reads the ELF from disc using the **ISO directory-record size** —
     must bump that record's size or the appended blob is truncated (unread).
- GIF-DMA upload routine verified byte-correct in RAM (MADR=0x1000A010,
  QWC=0x1000A020, CHCR=0x1000A000<-0x101, STR-poll wait). One-shot trampoline
  from setText -> upload -> renderer cave (0x188470).

## HARD CONSTRAINT (learned the hard way)
- The boot ELF occupies disc LBA 455..2150 (1696 sectors, exactly full; ~1784
  slack bytes). IOPRP310.IMG follows at LBA 2151. **Enlarging the ELF past
  0x350000 bytes overwrites IOPRP and corrupts boot.** So either:
  (a) keep the ELF <= 0x350000 -> atlas must be **compact** (1bpp ~1.2KB,
      expand to PSMCT32 at runtime into free EE RAM 0x1410000+), OR
  (b) relocate the ELF to free disc sectors + update the dir record LBA+size.
  Going with (a): 1bpp atlas + runtime bit-expand, no disc relocation.

---

## OUTCOME (2026-08-12) — font renders in-game; blocked on two-pen ghost

The custom half-width font WORKS: authored 62 glyphs, DMA-uploaded to VRAM at
boot, and each Latin dialogue glyph is redirected (texture + UV + width + pitch)
to our atlas, correctly colored by the game's own CLUT. Tight-pitch text is
readable but has a residual **two-pen ghost** (doubled/interleaved letters) that
is not yet clean, plus **word-wrap breaks mid-word**. Deliverable stays fullwidth
until those are solved. Tools: `tools/gen_hwatlas.py`, `tools/patch_hwfont.py`,
`tools/patch_flushlog.py` (live struct logger), `tools/pine_dump.py`,
`tools/update_dirsize.py`, nav `tools/nav_*.ps1`.

### Corrected pipeline facts (live-verified via PINE logging + pokes)
- Glyph cache is **4bpp PSMT4HL (PSM=0x24) + CLUT**, NOT PSMCT32. TEX0 template
  at `0x3f85d0` = `0x0004d00624021180`: TBP0=4480, TBW=8, TW=9(512), TH=8(256),
  CBP=9856. `struct+0x11`(=0x24) OR'd into PSM field, `struct+0x10`(=0x0c) into
  CSA (CLUT sub-palette) = the **text-color** lever. TBP0 is from the (constant)
  template -> ONE shared cache for all glyphs; they differ only by UV.
- Flush builds TEX0 = `template | (struct+0x11<<20) | (struct+0x10<<56)` (raw
  words decoded; capstone MIPS shift-decode is WRONG — read raw).
- Per-glyph 0x20 struct: dest=`+0/+2`, source-UV=`+4/+6`, size=`+0xc/+0xe`,
  tex=`+0x10/+0x11`, draw-path=`+0x12`, free Latin flag=`+0x13`, outline=`+0x1c`.
- Globals `a1/a2` at `0x46e334/0x46e336` (=2048) are the **dest text-block
  origin** (proven by live poke: changing a1 slid the whole line vertically,
  glyphs staying readable) — NOT the source-UV base as the flush disasm suggests.
- Source U/V for a glyph = `a1/a2 + struct+4/+6`, wrapped mod texture size; the
  cache packs a line's glyphs at 21px srcU stride (srcW=21, srcH=12; 2x vertical
  scale to the 24px dest sprite).

### The working injection (patch_hwfont.py, applied on the fullwidth ELF)
1. `gen_hwatlas.py`: 62 glyphs (0-9,A-Z,a-z), 12x12, 1bpp row-aligned = 1488 B
   (fits the ELF slack). Drawn at half vertical res (engine stretches 2x V).
2. PT_LOAD atlas + GIF header + one hook to **vaddr 0x1340000**.
3. TRAMP off setText (0x20C9B0): once — bit-expand 1bpp->4bpp into free RAM
   0x1400070, then GIF-DMA (PSMT4, 512x32) to a free VRAM page **TBP0=7000**;
   then `j` renderer cave 0x188470. (GIF DMA: MADR=0x1000A010 phys, QWC=0x1000A020,
   CHCR=0x1000A000<-0x101, STR-poll.)
4. BHOOK (blit 0x13AB68): if code is fullwidth Latin (0x8250-0x8259/0x8260-0x8279/
   0x8281-0x829A -> idx 0..61), set flag `+0x13=1`, outline off `+0x1c=0`, and
   override source UV to the atlas cell: `+4 = col*12 - 2048`, `+6 = row*16 - 2048`,
   `+0xc=+0xe=12` (COLS=42).
5. FLHOOK (flush 0x13B278; its delay 0x13B27C `addiu a0,a0,8` runs, so [a0-8] =
   the just-stored TEX0): for Latin, rewrite low32 -> TBP0=7000, PSM=0x14 (PSMT4).
   Reusing the CLUT auto-colors the glyphs correctly.
6. FHOOK2 (0x13B304): dest sprite right edge `t0+0x0B` (12px) for Latin.
7. ADV (blit pen 0x13AAE8) + SADV (shadow pen 0x13AB7C): halve `0x18->0x0C` for
   Latin so the line packs tight. ELF ends EXACTLY at 0x350000 (fills the 1696
   sectors); run `update_dirsize.py <iso> SLPS_258.87 0x350000` after inject.

### THE BLOCKER — residual two-pen ghost (unsolved)
Each dialogue glyph is drawn from TWO pens (main scratch 0x2c + a "shadow" pen
scratch 0x30, advanced by scratch 0x38 @0x13AB7C). At fullwidth pitch they
coincide (invisible); halving the advance makes them drift -> doubled/interleaved
letters. Halving the MAIN pen alone = heavy "JJ" doubling; halving BOTH (ADV+SADV)
reduced it to a light-but-still-visible ghost. NOT clean. Next attempts to try:
- Confirm whether the ghost is a 2nd struct/sprite per glyph (blit s0 advances
  0x20 = ONE struct/glyph, so it is likely TWO render PASSES or a shadow sprite in
  the flush) — instrument destX per glyph per pass to see the exact offset.
- If it's a shadow SPRITE: suppress it for Latin (like the outline `+0x1c=0`) or
  force the shadow pen == main pen, instead of chasing pen-advance sync.
- WORD-WRAP: the measure pass `0x2212B0` still advances fullwidth, so lines wrap
  mid-word. Halving there needs a RELIABLE current-char source; the `[sp+0x104]`
  reload at 0x221638 had NO effect (stale/wrong char) — find the correct one.
This is the "hard GS-pipeline, needs live GS/GIF stepping" part the notes warned
about. The clean-but-WIDE variant (drop ADV+SADV) has ZERO ghost but fullwidth
pitch (gaps) and is a valid fallback.
