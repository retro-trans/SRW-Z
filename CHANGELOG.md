# SRW Z English — build changelog

One entry per CHD built, **including throwaway diagnostics**. Started 2026-08-17
at the user's instruction, immediately after the chapter-2 stall was fixed.

Why this file exists: that bug took six wrong theories and several days, and what
finally cracked it was knowing what differed between v1.26 (clean) and v1.27
(broken). Nothing was recorded, so answering that required `chdman extractcd` on
both CHDs (~7 GB, ~15 min) plus a sector-level diff. Entries below say *what
changed*, not just *what was intended* — v1.27's entry names both suspects on
sight.

## 0.8.97 (2026-08-27) - a line that named the wrong enemy

From a screenshot: a caption overflowing its box and ending `down Teral!"!"`.
The row had THREE faults, not one.

    stored : Kazuki / people of Io, make sure you take / down Teral!"!"
    japanese: 香月「頼むぜ、闘志也さん、テラル…！
                　イオの人達のためにも、
                　絶対に[JP name]を倒してくれよ！」

It had lost its first body line, doubled its terminator, and - the serious one
- named **Teral** as the target. Kazuki is asking Toshiya AND Teral to defeat
Gagan; the english turned an ally into the enemy. Now:

    Kazuki
    「I'm counting on you, Toshiya,
    　Teral! For the people of Io,
    　you have to take down Gagan!」

31/30/32 columns, written in place - 102 bytes into a 112-byte slot, so no
pointer moved.

### Two names that disagreed with themselves

テラル shipped as both Teral and **Teraru** - 85 battle captions used the
second. Akurasu spells it **Teral** ("The Secret of Enemy General Teral"), and
605 uses in the script already agreed, so the 85 are normalised.

ガガーン shipped as Gagan (x8) and **Gagaan** (x1). Akurasu's character list
for this series is unfinished, so this one follows the build's own majority
rather than the wiki - worth revisiting if the page is ever filled in.

### New: tools/fix_row.py

Screenshot bugs arrive one row at a time, so they get a tool. Corrections live
in analysis/row_fixes.json and each carries a `was` field that must match the
row currently on disc - if another pass already touched it, the fix is refused
instead of overwriting work. The 3-line/34-column box and cp932 are checked
before anything is written.

### Gates

    integrity.py                 problems: 0
    verify_elf_patches.py        all ELF patches present
    verify_pointers.py --against 81,286 resolving, 0 broken

## 0.8.96 (2026-08-27) - one character, eleven spellings

Reported from a screenshot: "here it's still Reben". It was worse than one
spelling - the same character shipped under ELEVEN:

    Lowen  1017   <- correct         Raven     3      Raeven    2
    Loewen   50                      Raben    20      Leben     3
    Reeven  126                      Reben     8      Lane      1
    Reeben   13                      Reuben    6      Reven     6

He is Chimera's レーベン・ゲネラール - Loewen General. German Loewen is "lion",
which is why he calls himself the young lion of the Chimera and pilots the
Chaos Leo. The SRW wiki spells him Loewen with the umlaut; the font is
half-width ASCII with no umlaut and the build already used "Lowen" 1017 times,
so everything is normalised to Lowen.

**232 corrections**: 92 dialogue rows, 140 caption fields.

Every dialogue match is conditioned on the row's JAPANESE containing レーベン,
resolved through the row's own pointer. That is not caution for its own sake -
116 uses of "Raven" in STAGE are a DIFFERENT character ("I am called Raven. I
hope you'll remember me."), and "Lane" and "Leben" are ordinary words. A blind
search-and-replace would have renamed all of them.

### Kaimera -> Chimera, finished this time

0.8.95 renamed カイメラ in the battle captions and left **38 in STAGE**, because
STAGE is banlz-compressed and a byte-level pass over the disc cannot see into
it. Fixed here: 38 occurrences, 36 rows, 14 records, all in place.

### Two captions the word-boundary rule could not reach

Captions store a line break as the two characters BACKSLASH and 'n', not 0x0A.
So in `"Don't mess with me,
Raben!"` the character before the R is the LETTER
n, `Raben` finds no word boundary, and the rename silently skipped it.
Swapping the literal `
` for a non-word sentinel around the regex fixed 11
fields, including the relocated SRVC copy.

Verified afterwards: 0 variants left in either caption region, 0 in STAGE.

### Also

`tools/rename_term.py` - renaming a term in STAGE has needed the same three
things every time (condition on the japanese, keep it inside the box, repoint a
row that no longer fits), so it is one parameterised tool now instead of
another one-off per name.

### Gates

    integrity.py                 problems: 0
    verify_elf_patches.py        all ELF patches present
    verify_pointers.py --against 81,286 resolving, 0 broken

## 0.8.95 (2026-08-27) - scenario-chart recaps, Chimera/Lowen, LIBRARY menu for real

Reported from a screenshot: "the scenario chart still have some bug lik missing
text here or Chimera is still translated as Kaimera". Two separate bugs, plus a
third found while fixing the second.

### The recaps were wrapped a third too narrow

The recap in the screenshot is COMPLETE in the data (382 bytes, rec0 0x004da0,
slot 480) - that shot caught the typewriter mid-draw, the corner still showing
"Speed Up". But measuring all 210 recaps found a real systematic fault:

    japanese line counts cluster at 10-11, max 22
    english  line counts spread to 25, and 113 of 210 use MORE lines than the
             japanese they replace
    english  max line width: mean 40, but the WIDEST already reach 56

The box is 56 columns - the japanese uses all of it and some english lines
already do - so most english was wrapped at ~38-40, wasting a third of the box
and spilling lines out of the bottom. Rewrapped to 56:

    recaps still longer than their japanese :  113 -> 0
    recaps that grow in bytes               :        0
    209 recaps rewrapped, 708 lines saved, 46 records rebuilt

Nothing grew, so every one went back into its own slot: no relocation, no
repointing, and the pointers repaired in 0.8.90 are untouched (81,286 resolving,
0 broken, checked with verify_pointers --against).

These live in STAGE.BIN, not HSFC - which is why find_row never showed them (it
only matches rows containing the opening quote bracket) and why searching HSFC,
COMPDATA and the ELF found nothing. HSFC holds the SHORT map-select one-liners
("AEUG raids Lutetium Base"), a different thing.

### Kaimera -> Chimera, and a FIFTH spelling of Lowen

8 battle captions read "Kaimera" for the faction. Fixing them exposed the other
half of the same line:

    "I am Raven General! The young lion of Kaimera!"
    JP: the speaker is Lowen General, not Raven

So "Raven General" is a fifth spelling of that name after Raben, Reeven and
Lowen. 12 captions corrected. Both replacements are the SAME LENGTH as what they
replace, so this was a byte substitution - no slot maths, no repointing, no
recompression. 20 of 20 verified.

SRVC exists TWICE in the image (the original extent, and the relocated copy
srvc_apply --free created), so the pass fixes every occurrence in the whole
image rather than one file's. Each hit is checked to sit inside a printable
NUL-terminated caption first, so a coincidental match in binary data cannot be
hit.

### The LIBRARY menu, patched in the ISO this time

0.8.94 repainted /DATA/JTIM.BIN image #5 - which looks exactly like this menu
but is NOT what the screen blits, so nothing changed in game - and the menu was
then translated with a PCSX2 texture replacement instead. That replacement is
not portable: PCSX2 dumped the page as 512x256 with no region field, so its hash
covers areas outside the art, and build_texture_pack correctly dropped it. A
replacement that cannot apply on another machine is not acceptable, so the art
itself had to be found.

Found by scanning the disc for the dump's own CLUT entries, then searching
inside the banlz records that the raw scan cannot see through:

    /DATA/NISVDATA.BIN   LBA 1568269, banlz record 0 (647,136 bytes plain)
    256x256, 8bpp, PSMT8-SWIZZLED
    pixels at 0x8c900, CLUT at 0x9c900 (the usual 0-7,16-23,8-15,24-31 tiling)

Confirmed by decoding it and matching the PCSX2 dump: 150 of 150 sampled pixels.
The 512x256 dump is the containing GS page, which is why no 512-wide layout ever
matched - the texture is 256 wide. Read and write both go through the swizzle
map, so the data is never deswizzled and reswizzled.

The CLUT is untouched; english is painted with the art's own palette indices,
sampled per row from the label being replaced and ranked by BRIGHTNESS (ranking
by frequency picks the shadow on rows where the glyph had more shadow than fill,
which drew dark bands through the letters). All six labels share ONE point size,
the largest that fits every one, so the menu still reads as a single menu.

    rec0 recompressed to 160,749 bytes in its 169,504-byte slot

The two LIBRARY replacement PNGs are retired - repainting the art moves its
hash, so they would no longer match anyway. The pack now drops only the three
prologue cards, as designed.

### Gates

    integrity.py                            problems: 0
    verify_elf_patches.py                   all ELF patches present
    verify_pointers.py --against            81,286 resolving, 0 broken

## 0.8.94 (2026-08-27) - the LIBRARY menu (art, not text)

The six LIBRARY entries are not text anywhere on the disc. Searching the whole
3.7GB image for ロボット大図鑑 / サウンドセレクト / シナリオチャート / 用語事典 /
キャラクター事典 returns NOTHING, and neither does every banlz archive (ZKN x3,
HSFC, MAPNAME) nor the ELF nor COMPDATA. They are pixels:

    /DATA/JTIM.BIN  LBA 1568664, image #5 at file offset 0x394150
    512x256, 8bpp palettised, 256-colour CLUT

Stored LINEARLY, not swizzled - tim2_dump reads it row-major and the result is
correct, unlike the OP title cards which are PSMT8-swizzled.

Each entry appears TWICE, identical but for colour: yellow (selected) right-
aligned to x=189, teal (normal) right-aligned to x=389. Both redrawn.

    ロボット大図鑑    -> Robot Data
    キャラクター事典  -> Character Data
    用語事典         -> Glossary
    サウンドセレクト  -> Sound Select
    シナリオチャート  -> Scenario Chart
    攻略 Q&A         -> Strategy Q&A

"Robot Data" / "Character Data" rather than the more literal "Robot
Encyclopedia" / "Character Encyclopedia": the label boxes are 159 and 186 px, so
the longer wording auto-fits to about 12px tall against 20-22px for the rest and
the menu stops looking like one menu. Consistent size beat literal wording.

### How

THE CLUT IS NEVER TOUCHED. English is painted with the artwork's own palette
indices, sampled per row from the label being replaced, so the vertical gradient
and drop shadow come out of the original art rather than being invented -
yellow 46 (240,248,136) down to 62 (224,200,0), teal 87 down to 85, shadow
33/65.

The first attempt ranked each row's indices by HOW OFTEN they occur and drew
dark bands straight through the letters: on any row where the original glyph had
more shadow than fill, the most common index IS the shadow. Ranking by
brightness fixed it.

Text is fitted inside the original bounding box and right-aligned to the same
edge, because the game blits each entry from its own UV rect and anything wider
would clip.

### Gates

`integrity` 0 problems. File size unchanged, TIM2 header intact, CLUT unchanged,
and 0 bytes differ outside the 512x256 index block.

## 0.8.93 (2026-08-27) - 250 rows attributed to the wrong character

tools/scan_speaker_mismatch.py reported 356 rows whose english speaker label
disagrees with its own japanese speaker group. rec53 shows the cause: five
consecutive ギンガナム lines are labelled Ghingnham, Dianna and Agrippa, and the
wrong ones carry the first character NAMED IN THE BODY - a pass took the speaker
from the sentence instead of the speaker field.

250 fixed, all in place:

    ギンガナム   -> Ghingnham   (was Dianna 16, Agrippa 2)
    サンドマン   -> Sandman     (was Leele 10, Eiji 6, Raven 5, Kazami 3)
    エウレカ    -> Eureka      (was Fudo 13)
    アポロ/レコア/サラ -> (was Fudo, 20 rows)
    ？？？     -> ???         (was ?, 16)
    シロッコ -> Scirocco, グエン -> Guin, ロラン -> Loran, クワトロ -> Quattro

This is NOT majority-voting a name. The replacement is the label the rest of
that character's own rows already carry, and each matches a form established
elsewhere - Ghingnham is fix_terms_grow's canonical spelling, Guin is Turn A's
Guin Sard Lineford. What changes is WHO is speaking, not how it is spelt.

### Left alone: 91 rows

82 are the same character spelt differently (Kiel/Kihel 13, Orba/Olba 12,
Quenstein/Quinstein 6, Astonaji/Astonage, Shran/Schlan). Choosing between those
belongs to the akurasu baseline, not to a count of occurrences. Separated from
the wrong-character rows by string similarity: below 0.55 they are different
people, above it they are spellings.

The other 9 have an ideographic space as the japanese speaker and an ASCII space
in english. Both render blank, nothing is reported, and rewriting them risks the
empty-speaker bug 0.8.85 fixed.

### The pointer gate cried wolf, and the gate was wrong

verify_pointers reported rec48 at 84.9% against an 85% threshold. The numerator
was UNCHANGED at 1087; the denominator grew 1264 -> 1280 because relocating rows
appends text and more 4-aligned words fall into range and look pointer-shaped.
The ratio drops with record size while nothing is broken. Lowering the threshold
would have been the wrong fix.

Added `verify_pointers --against <ref-iso>` instead: every pointer that resolves
in a known-good image must still resolve. Immune to size changes. Getting it
honest took three filters, each of mine being too loose:

    any in-range word                 815 "broken"  (text bytes as addresses)
    + non-empty target                 35 "broken"  (targets like '7', '+')
    + row-shaped target (newline, 6B)   0 broken    of 81,286

The old ratio check is unchanged. It is the check that caught v0.8.72's
save-load freeze at 26%, and it is better for it to cry wolf on a grown record
than to be weakened.

### Gates

`--against` 0 of 81,286 broken, `integrity` 0 problems, mismatches 341 -> 91.

## 0.8.92 (2026-08-26) - "Emperor Bry" -> "Emperor Burai"

Reported from a screenshot: Hidler says "Great Emperor Bry". ブライ is Getter
Robo's 百鬼帝国 ruler, Emperor Burai.

fix_terms_grow.py already renames ブライ from Bray, Brya and Brai. It does not
cover "Bry" - a FOURTH spelling - so 13 rows were left. Every match is
conditioned on the japanese containing ブライ, resolved through the row's
pointer, so nothing beginning "Bry" is renamed by accident. The rule is now in
fix_terms_grow.py so a later rename pass cannot reintroduce it.

Burai is two columns wider than Bry, which pushed one row over the 34-column
limit; it is re-wrapped rather than dropped:

    「Long live Great Emperor Burai!!」   ->   「Long live
                                              　Great Emperor Burai!!」

10 rows fixed in place, 3 relocated and repointed.

### One speaker as well

rec48 0x017a70 was attributed to "Burai" where the japanese speaker is 風見
(Kazami) - the body mentions 百鬼ブライ, so the speaker had been taken from the
sentence. Same bug tools/scan_speaker_mismatch.py reports across 356 rows.

### Gates

`verify_pointers --min 85` OK, `integrity` 0 problems, 0 rows still containing
"Bry".

## 0.8.91 (2026-08-26) - weapon-name review: 77 shredded model numbers, 39 loanwords

Full review of all 769 weapon-name entries, requested by the owner.

### The model-number bug (77 names)

gen_weapons.translate() joined model numbers with

    re.sub(r"([A-Za-z0-9]) ([A-Za-z0-9])", r"", out)

re.sub matches NON-OVERLAPPING pairs. The tokenizer emits every fullwidth char
as its own token, so "ＭＭＩ－ＧＡＵ２５Ａ" arrives as "M M I - G A U 2 5 A" and
pairs up as (M,M)(G,A)(U,2)(5,A) -> "MM I-GA U25A". The next pass cannot help
because nothing is a single character any more, so the loop exits satisfied.

    MMI-GAU25A  ->  MM I-GA U２ ５A        MA-BAR72  ->  MA-BA R７ ２
    MMI-M633    ->  MM I-M６ ３３           M181SE    ->  M１ ８１ SE
    200mm       ->  ２０ ０mm               127mm     ->  １２ ７mm

Fixed by joining whole RUNS of single tokens, then binding across the hyphen.
U+3000 (which separates a model number from its calibre) mapped to a plain
space, indistinguishable from an inserted one, so the joiner merged across it
and gave "MMI-GAU25A20mm"; it is now a non-alphanumeric sentinel, restored to a
space at the end of translate().

### Untranslated katakana (39 names)

23 distinct katakana words were being romanised rather than translated. Those
that are LOANWORDS - the japanese is a katakana rendering of an English, Latin
or German word - are recovered, which is not a naming decision:

    Ekusukariba -> Excalibur     Keruberosu -> Cerberus    Orutorosu -> Orthros
    Karidusu    -> Calidus       Arondaito  -> Arondight   Riniagan  -> Linear Gun
    Amuforutasu -> Amfortas      Igerushuterun -> Igelstellung
    Torenburu   -> Tremble       Bandokku   -> Bandock     Banka -> Bunker

グリフォン was going to become "Griffon" while the build already shipped
"Gryphon" for another entry; matched to Gryphon rather than introduce the same
word twice.

### What was deliberately NOT changed

Regenerating wholesale would have REGRESSED names the canon dictionary already
gets right - the generator produces "Merutoshawa" where the build ships "Melt
Shower", "Badogan" for "Bird Gun", "Shimita" for "Scimitar". Only two classes
were applied: pure re-spacing (identical characters) and katakana loanwords.
589 of 769 now match the generator exactly; the rest differ because the SHIPPED
name is better, or because fullwidth and ASCII digits compare unequal while
encoding identically.

All fixes are shorter than what they replace, so each was written into its
existing slot - no repack, which would have disturbed the pointers repaired in
0.8.90. Entry starts verified unchanged: 3,433 before and after.

### Left for a naming decision

8 names still contain romaji. Two are correct as they are - ヒャクライ (百雷) and
イカヅチ (雷) are japanese proper names. The other six have no obvious English:
Arudoru, Gagundura, Jinba, Potan, Toraparuza, and Baraena (which SHOULD be
Ballaena but needs 40 bytes in a 40-byte slot).

### Gates

`integrity` 0 problems, `verify_pointers --min 85` OK, pool entry starts
unchanged, Gryphon spelling consistent across both entries.

## 0.8.90 (2026-08-26) - repair 62 pool pointers broken by 0.8.81

### The bug I introduced

0.8.81 repacked the COMPDATA string pool to lift the weapon-name byte limit and
rewrote 9,483 pointers with it. 91 pointer-shaped words did NOT land on a string
start; I decided they were u16 pairs reading as addresses by coincidence, left
them alone, and wrote that justification into tools/pool.py and the changelog as
if it had been established.

It had not. Testing it: 60 of the 91 sit precisely on a pointer-table stride -
4 or 32 bytes from a confirmed pointer - so they are entries in the same tables.
They point at one of two things:

    +24 into 'Barrier Field'       into the NUL PADDING = an EMPTY string,
    +24 into 'Guidance Scenario'   which is how a BLANK SLOT is drawn
    +33 into 'MG X-2235 Karidusu'  a few bytes in = a deliberate substring

Repacking removed the padding and moved every string, so a pointer that used to
resolve to "" now lands in whatever text moved there, and a substring pointer
lands mid-way through something unrelated. One target has 38 references and
another 16, so this is not obscure. It was live in 0.8.81 through 0.8.89.

### The repair

The repack preserved entry ORDER and count, so entry i in a pre-repack image is
entry i now. tools/fix_pool_strays.py recovers each broken pointer's owning
string and its byte offset from iso/srwz_dlg.bin (2026-08-22, pre-repack) and
repoints it to the same offset in that string's new location. A padding pointer
goes to the string's own NUL terminator, so it resolves to "" exactly as before.

62 repaired, 34 correctly left alone (not on any stride - those really are u16
pairs). VERIFIED BY RESOLVING: all 62 now yield byte-identical text to the
pre-repack image, 0 differing.

### Lesson

The emptiness/coincidence argument was plausible and wrong, and it was recorded
as fact rather than as an assumption. The stride test that disproved it takes
one pass over data already in hand. tools/pool.py now runs it and reports any
stray sitting on a pointer stride instead of asserting they are all coincidence.

### Gates

`integrity` 0 problems, `verify_pointers --min 85` OK, all ELF patches present,
62/62 pointers resolve to their pre-repack text.

### Note

Contains everything up to 0.8.89, i.e. WITHOUT the VWF proportional advances -
those stay reverted pending the spirit-strip diagnosis. 0.8.89 remains available
as the single-variable test for that.

## 0.8.89 (2026-08-26) - VWF advance patch reverted (bisect)

Owner reported the spirit-command strip rendering as repeated vertical bars on
the squad and unit screens, and asked to roll the font change back to test
whether it is the cause. Advance hook at 0x78BA94 restored to stock
(`lhu t0,0xc(s0)` / `beq` / `addiu v1,t0,1`), trampoline and width table
cleared. Every glyph advances a flat 13px again, as before 0.8.84.

The atlas is unchanged (MS Gothic, restored in 0.8.88), so this build differs
from 0.8.82 only in the dialogue fixes of 0.8.85.

This is a BISECT STEP, not a diagnosis. The patch only ever changed the pen
advance for codes 0x8540..0x85C9; a wrong advance makes glyphs overlap, it does
not turn them into bar patterns, and the micro-glyph codes 0x85CA..0x85DB used
by the terrain icons are outside the patched range entirely. If the strip still
renders as bars, the cause is elsewhere and the advance patch can go back in.

### Gates

`verify_elf_patches` all present, `integrity` 0 problems, advance hook byte-
compared against stock.

## 0.8.88 (2026-08-26) - font rolled back to MS Gothic

0.8.87's BIZ UDGothic was tried in game and did not feel as good as MS Gothic
(owner call). Atlas restored from analysis/atlas_shipped.bin and the advance
table regenerated from it, since advances are measured FROM the atlas. Nothing
else changed - the advance hook, stamper and sprite-width cave are as they were.

### What the exercise established, for the record

  * Only faces with half-width (hankaku) Latin fit a 12px cell at 18px cap
    height. Tahoma/Verdana/Segoe UI/Meiryo/Yu Gothic are 9-11px too wide.
  * BIZ UDGothic and UD Digi Kyokasho fit; UD Digi is inherently thin (52%
    solid at every size). BIZ at cap 17 bias 20 measured objectively BETTER than
    MS Gothic (71% vs 65% solid ink, 10.8 vs 11.6 mean advance, w/W/m solid
    rather than grey, SIL OFL) and was still rejected on look. Measurements do
    not settle taste.
  * Softness is the QUANTISER, not the face: rasterise_font.py --bias lowers the
    64/128/192 thresholds so half-covered pixels round up. bias 0 -> 56% solid,
    bias 20 -> 71%.

### The real anti-aliasing finding

The jagged edges are NOT a resolution limit. The engine's master font is 4bpp -
SIXTEEN alpha levels - and the game's own japanese glyphs use all 16 (measured
from a RAM dump at the font base in BSS global 0x0046E3A8). Our Latin atlas
stores 2bpp, FOUR levels (0/5/10/15), purely to fit the cave. That is what makes
the edges look stepped.

Going to 16 levels fits, if the rows are stored variably - mean inked height is
16.7 of 24 rows:

    2bpp fixed 24 rows (today)          4968 B
    3bpp fixed 24 rows  (8 levels)      8280 B   fits, 715 spare
    4bpp variable height (16 levels)    7032 B   fits, 1963 spare

The cost is rewriting the stamper, which unpacks 2bpp into nibbles today and
would need to handle 4bpp plus a per-glyph top-row/height header. It runs on
EVERY setText, so it is the hot path - the same class of change that shipped
broken in 0.8.83. Not attempted here; simulate before writing.

tools/preview_16level.py renders 4-level vs 16-level side by side.

## 0.8.87 (2026-08-26) - font swapped to BIZ UDGothic

### Why

'w', 'W' and 'm' rendered as grey blurs (user report). Three vertical strokes
have to fit a ~10px ink box, so the middle stroke lands between pixel columns,
covers about half of each, and the 4-level quantisation keeps it grey.

### What was ruled out first

  * a wider cell - 16px would FIT the cave (6624 B of ~8995 available), but 12px
    is half the 24px japanese cell and all 68,340 rows are wrapped to that
    ratio. Widening means every line renders ~33% wider than it was wrapped for.
  * a nicer Latin face - at the required 18px cap height, Tahoma/Verdana/Segoe
    UI/Meiryo/Yu Gothic measure 9-11px TOO WIDE for the 12px cell. Only faces
    with half-width (hankaku) Latin fit. MS Gothic was not an arbitrary choice.
  * PCSX2 texture replacement - the dump settles it. The font is a 512x256
    DEMAND-DECODED cache page: four different hashes appeared in one scene, each
    holding whatever text had been shown ("Johannes「Touma... Let us hear the
    dream you saw.」", "~Atlandia~Katsuragi..."). A replacement is matched on
    that hash, so it would apply for one instant and differ per player.
  * an AI-generated sheet - two attempts, both rendered '?' as '2', both drawn
    on an ~11px grid where 8.71px was needed.

### What shipped

BIZ UDGothic, cap height 17, quantisation bias 20. Measured against MS Gothic:

    solid ink        65% -> 71%   (BOLDER, not softer)
    w / W / m        grey -> solid
    mean advance     11.6 -> 10.8 (8% tighter)
    edge clipping    0    -> 0
    missing glyphs   0    -> 0
    licence          Microsoft -> SIL OFL

The first attempt at cap 18 measured SOFTER (56% solid) and clipped 11 glyphs at
the cell edge. Both were process, not the face: cap 17 restores the right
bearing, and the softness was the quantiser rounding half-covered pixels DOWN.
`--bias` lowers those thresholds so they round up. UD Digi Kyokasho was tried
and rejected - 52% solid at every size, a textbook face with calligraphic stroke
variation, inherently thin.

The tighter advance is free: advances can only shrink against the old table, so
no line can widen and nothing needed rewrapping.

New tools: rasterise_font.py (any TTF -> atlas, --cap/--gap/--bias),
compare_atlases.py, font_texture.py (export/import the atlas as an editable
144x144 PNG, round-trip verified), set_atlas.py, export_font_sheet.py.

Reversible: the previous atlas is analysis/atlas_shipped.bin ->
`set_atlas.py <iso> analysis/atlas_shipped.bin --write`, then rerun
patch_vwf_widths.py (--revert then apply) so the advances match.

### Gates

`verify_elf_patches` all present, `integrity` 0 problems, trampoline simulated
over all 138 indices, atlas in image byte-compared against the candidate.

## 0.8.86 (2026-08-26) - the VWF trampoline was eating lowercase 'z'

Reported from a screenshot: the letterforms looked right but 'z' had noise along
its bottom edge.

### The bug

The glyph atlas runs 0x78A5B3 .. 0x78B91B (69 glyphs x 72 bytes). 0.8.84 put the
advance trampoline at 0x78B910 - ELEVEN BYTES INSIDE IT - and overwrote the
bottom rows of glyph 68, lowercase 'z'.

The freshness check did not catch it because those bytes ARE all zero: they are
the blank rows below 'z'. An all-zero block inside the atlas is not free space,
it is an empty part of a glyph. The check tested emptiness and inferred
availability, which is not the same thing.

It also corrupted the measurement: with garbage in its bottom rows 'z' measured
an ink right edge of 11 and an advance of 13 instead of its true 9 and 11.

### The fix

Trampoline moved to 0x78B91C, the first 4-aligned byte AFTER the atlas (66 free
bytes there, 52 needed). The table at 0x78C110 was always clear of it.

patch_vwf_widths.py now refuses any placement overlapping 0x78A5B3..0x78B91B,
and refuses a misaligned code address, instead of trusting a zero-fill test.

Verified by diffing the whole atlas against a pre-VWF build (iso/srwz_dlg.bin):
byte-identical, and glyph 68's tail is back to `f0 1a aa 50 00 00 ...`.

### Not a bug: 'w'

'w', 'W' and 'm' look washed out next to other letters. They need three vertical
strokes inside a 10px ink box, so the middle stroke falls between pixel columns
and the 4-level quantisation renders it at half intensity. Spacing is fine - all
three advance 12px, same as 'v', 'n', 'u'. Fixing it means redrawing those
glyphs, not changing advances.

tools/export_font_sheet.py dumps all 69 letterforms out of a built image.

### Gates

`verify_elf_patches` all present, `integrity` 0 problems, atlas diff clean.

## 0.8.85 (2026-08-26) - 18 location cards that rendered as an empty box

### The report

A screenshot showed a completely blank message box immediately before Johannes's
first line in the Atlandia scene, and its backlog entry was blank too.

### The cause

A row is `speaker
body`. Location cards and narration carry a FULLWIDTH SPACE
as the speaker line, so no name is drawn but the line still exists:

    JP  '　
　　...～アトランディア～'
    EN  '
            ~Atlandia~'

The translation dropped it, so the row begins with a bare 0x0A and the renderer
produces nothing at all - no name, no body, and an empty backlog entry.

20 rows are affected and every one is a scene-setting card: ~Nox, City Streets~,
~Argama Mess Hall~, ~Skull Moon Base - Great Hall~, ~Paradigm City Underground
Labyrinth~, ~Fortress Algol, Command Center~ and the rest. All of them have been
invisible.

scan_visible_defects.py checks for an empty BODY but never an empty SPEAKER
line, which is why nothing caught this. tools/scan_empty_speaker.py now does.

### The fix

Each row gets back exactly the leading whitespace its OWN japanese source had -
one or two fullwidth spaces, resolved through the pointer - with the body left
byte-identical. 18 fixed in place, none needed relocating.

Two rows that also open with 0x0A are deliberately left alone: rec84 0x011a31
and rec132 0x019910 are mid-string CONTINUATION FRAGMENTS. Both japanese sources
begin on a cp932 trail byte, so the pointer addresses the middle of a longer
line and that newline is a real line break.

### Noted, not fixed

Seven of these cards are ALREADY wider than 34 columns in the shipped image
(seven fullwidth spaces plus a long name) and may clip at the right edge. That
is a separate pre-existing defect. The first draft of the validator rejected
those rows because of it, which would have refused to fix a blank box over a
fault this pass does not touch; the check was narrowed to the speaker line only.

~Atlandia~ uses an ASCII `~` where the other cards use fullwidth `～`.

### Gates

`verify_pointers --min 85` OK, `integrity` 0 problems, all ELF patches present.
scan_empty_speaker: 20 -> 2 (both the intended continuations).

## 0.8.84 (2026-08-26) - proportional font, second attempt (advance-only)

0.8.83 SHIPPED BROKEN. Text collapsed into overlapping clusters - see the
screenshot report. Do not use it.

### What 0.8.83 got wrong

It changed two things it did not need to change:

  * the per-glyph width field the stamper writes (`sh t2,0xc(s0)`, constant
    0x0C at 0x78A2AC), and
  * the `width == 0x0C` test in the sprite-width cave at 0x78BAD0, nopped so
    that test would keep passing once widths varied.

That field is read by more than the pen advance. Rewriting it changed glyph
handling this patch has no business touching, and the result was a pile-up
consistent with an advance of ~1px. The dest-width nop is a second suspect;
neither was isolated, which is exactly the problem - two changes, one symptom.

### What 0.8.84 does instead

The stamper and the sprite-width cave are left COMPLETELY ALONE. The width field
stays 0x0C for every glyph, so everything that reads it behaves as it does
today, including the 0x78BAC0 test.

The ONLY change is the pen advance. The advance hook at 0x78BA60 ended with

    0x78ba94  lhu   t0,0xc(s0)          ; always 0x0C
    0x78ba98  beq   zero,zero,0x78bab0
    0x78ba9c  addiu v1,t0,1             ; 13px, every glyph

and those three instructions now jump to a 13-instruction trampoline at
0x78B910 that indexes a 69-byte table at 0x78C110 by (code - 0x8540) and returns
the glyph's own advance in v1. Bold/menu glyphs (indices 69..137) are the same
art dilated 1px right, so they get +2 instead of +1.

t0 is safe to clobber: the hook saves it at 0x78BA60 and restores it at 0x78BAB4.

Advance is ink right edge + 2, measured from the atlas actually stamped into the
master font (0x78A5B3, 72 B/glyph, 24 rows of 12px 2bpp). Range 7..12 against a
flat 13 - simulated over all 138 indices, MAX 13, so no advance can exceed the
current one, no line can get wider, and the 34-column wrap stays valid.

If this still collapses, the fault is the table memory at 0x78C110 rather than
the approach, and the next step is PINE rather than another guess.

Also: v1's `--revert` restored the code sites but left its trampoline and table
in the cave. Cleared before applying v2; v2's revert clears them.

### Gates

`verify_elf_patches` all present, `integrity` 0 problems. Stamper 0x78A2AC and
dest-width test 0x78BAD0 re-read from the image and confirmed stock.

### CONFIRMED IN GAME (user screenshot, 2026-08-26)

Renders correctly, and measurably proportional. Screen scale taken from the
pillarbox (920px game area / 640 = 1.4375), independent of the text:

    line                           fixed would be   prop predicts   MEASURED
    「Lord Shiruha, Lord Goushi,        520 px          461 px         441
    Touma won't run off.」              408 px          374 px         350

Within a few percent of proportional and 14-15% short of fixed; the measured
ends slightly UNDER-read (trailing commas and thin strokes fall below the
detection threshold), so the true widths are closer to prop still.

Worth measuring rather than eyeballing: if the table read had returned 12 the
advance would be 13 and the result would look identical to the old font, so
"renders correctly" alone does not distinguish success from a no-op.

This also confirms 0.8.83's culprit was the per-glyph width field, not the
dest-width nop and not the table memory.

## 0.8.83 (2026-08-26) - the Latin font is proportional

### What it was

Half-width, but NOT variable-width. patch_hwfont's stamper wrote a CONSTANT into
the per-glyph width field:

    0x78a2ac  addiu t2,zero,0xc      <- 12, for every glyph
    0x78a2b0  sh    t2,0xc(s0)

and the advance hook at 0x78BA60 reads that field and adds 1, so every Latin
glyph advanced exactly 13px regardless of shape - `l` took the same space as `W`.
The field is per-glyph and the hook already honoured it; only the constant stood
in the way. The tool names are misleading here: patch_vwf1.py / patch_font_
advance.py describe VWF as the GOAL, and what shipped was patch_hwfont.

### The change

  * a 69-byte width table in cave padding at 0x78C110, measured from the atlas
    actually stamped into the master font (0x78A5B3, 72 B/glyph, 24 rows of 12px
    2bpp). advance = ink right edge + 2, so `l`=7, `I`=8, `i`=9, `.`=10,
    `M`/`W`/`0`=12, against a flat 13 before.
  * 0x78A2AC -> `j 0x78B910`, a 15-instruction trampoline that indexes the table
    by code-0x8540 and adds 1px for the bold/menu half (indices 69..137, which
    the stamper makes by dilating the same art 1px right).
  * the sprite-width cave at 0x78BAC0 halved the drawn sprite only when the
    marker byte at +0x13 was 0xA7 AND the width field was exactly 0x0C. The
    marker test is correct and stays; the width test would now fail for every
    glyph that is not 12 wide and the sprite would draw 24px and ghost. Nopped.

THE ART IS NOT TOUCHED. Only the dead columns to the RIGHT of each glyph's ink
are removed, so every letter keeps its natural left bearing and no advance can
exceed the old 13px. No line can get wider: the 34-column wrap stays valid and
nothing can overflow. Measured on real dialogue, lines come out ~13% shorter.

Rejected the tighter variant (shift art flush-left, ~19%): it requires
re-authoring the glyph bitmaps or shifting pixels in the stamper, which runs on
every setText, and removing the left bearing makes narrow runs like `Illi` touch
unless the gap is widened again - which gives back most of the difference.

### Verification

The trampoline was SIMULATED over all 138 indices before writing
(tools/sim_vwf_tramp.py) - the recorded lesson from the micro-glyph work. That
caught nothing in the code but did catch two bugs while writing it: a filler
word encoded as `j 0` (a jump to address zero) and a branch that skipped to the
bold +1 instead of past it. Note MIPS branch targets are idx+1+imm.

Reversible: `patch_vwf_widths.py <iso> --revert`.

### Gates

`verify_elf_patches` all present, `integrity` 0 problems.

### Not verified

Underline/link positioning is computed in columns and will drift under variable
advances. The owner has said underlines can be dropped in favour of coloured
text, so this build does not address them - if glossary underlines look wrong,
that is why.

## 0.8.82 (2026-08-26) - 35 dialogue rows that were cut off mid-sentence

### The report

A backlog screenshot showed Zushi's line as `Zushi / "As you` and stopped. The
stored row was exactly that - 13 bytes.

### Why

The japanese `頭翅
「御意…」` fits a 16-byte slot; `Zushi
「As you wish...」` is 24
and does not. Whoever fitted it swapped the 2-byte kagi for a 1-byte ASCII quote
to buy a byte, then cut the sentence. 32 rows are damaged the same way -
`Kappei "Kazuki.`, `Keiko "Kappei..`, `Kouji "A sin...`, `Gengoro "Rumors`, plus
longer lines from Sandman and Umee.

No existing scanner could see it. Each row is a single line, under 34 columns,
with no literal escape and no japanese left, so every check passed. What is
wrong is the QUOTING - tools/scan_broken_quotes.py now checks exactly that.

The budget was not real. STAGE rows are addressed by absolute pointers
(BASE 0x7566F0) exactly like the COMPDATA pool in 0.8.81, so a row that outgrows
its slot is appended to the record and repointed. 10 rows fit in place, 22 were
relocated. Two rows in rec185 are left unclosed on purpose: the JAPANESE has no
closing bracket there either, so mirroring the source is correct.

### Three more, and a worse bug behind them

scan_broken_quotes also found rows with a DUPLICATED TAIL, where a longer
replacement was written over a shorter string without clearing the leftovers:

    「...Moonlight Butterfly?!」ly?!」
    「...the Moon's Dianna!」nna!」

All three are ギンガナム lines shipped as "Dianna". rec106 had Ghingnham calling
himself head of "House Dianna" where the japanese says ギンガナム家, and rec119's
english was not a truncation but an unrelated line about the Moonlight
Butterfly - neither survives contact with the source, so both were retranslated.

That is not three rows. tools/scan_speaker_mismatch.py groups every row by its
japanese speaker and reports 356 disagreements, splitting in two:

  * wrong character - ギンガナム as Dianna (22), サンドマン as Leele/Eiji/Raven/
    Kazami (24), エウレカ/アポロ/レコア/サラ as Fudo (33), シロッコ as Agrippa.
    The label is the first name mentioned in the BODY, so a pass took the
    speaker from the sentence instead of the speaker field.
  * romanisation - Kiel/Kihel, Olba/Orba, Elche/Elchi, Schlan/Shran and ~40 more

Only the first half is mechanical. The second needs the akurasu baseline per
name; picking the group majority would be exactly the majority-voting the owner
has ruled out. Both are left for a later build.

### Process

Two runs were cut off with nothing written before the cause was found: the job
outlives a background command, so compression is now CACHED per record
(analysis/_lzcache, keyed by the plain record's sha1) and each run resumes.
One earlier run also died to SIGPIPE from piping a long build through `tail` -
the same mistake already recorded against piping chdman through `head`.

### Gates

`verify_pointers --min 85` OK (worst 85.1%), `integrity` 0 problems, all ELF
patches present. scan_broken_quotes: ascii_quote 250 -> 218, unbalanced 5 -> 2
(both remaining are the deliberate rec185 mirrors).

## 0.8.81 (2026-08-26) - the weapon-name byte budget is gone

### What the budget actually was

Weapon names had been fitted into the exact byte length of the Japanese string
they replaced, which is why the list showed `MusouSw`, `HeatRad`, `SubGun`. The
2026-08-26 shift experiment proved the slots could not simply be grown: making
`MusouSw` into `Musou Sword` left the next entry rendering as `ord` - bytes 8..10
of the new string.

Every static search for the reference had failed: not an index, not a
record-relative offset, not offset/8, and God Sigma's six-weapon index sequence
appeared nowhere in the 3.7 GB image at any stride. The conclusion recorded at
the time - "computed at runtime, needs live instrumentation" - was wrong.

### Where it was

Found by dumping EE RAM instead of searching the disc. The string pool loads at a
hardcoded `0x006D6800`, so a name is referenced by an ABSOLUTE PS2 ADDRESS like
`0x0073D628` - which is why every relative encoding searched for came up empty.
File bytes and RAM bytes at the pointer tables are byte-for-byte identical, so
nothing is relocated at load; the table ships inside COMPDATA.

    0x00904 .. 0x61658   pointer tables (9,483 pointer words)
    0x61680 .. 0x7FF00   string pool    (3,433 entries, 8-byte aligned)

The two regions never overlap, every pool string is referenced by at least one
pointer, and nothing outside COMPDATA holds a pointer into the pool - checked
against the ELF on disc and a 32 MB RAM dump. The apparent external hits are all
u16 pairs whose high half is 0x0074 (`00 a2 74 00`), not pointers.

### The change

tools/pool.py repacks the pool and rewrites every pointer with it, so a name may
now be any length. Repacking also reclaims slack: the pool ends at 0x7A8F0,
leaving 22,032 free bytes.

48 names are restored to their full form - `Musou Sword`, `Heat Radiation`,
`Secondary Gun`, `Moonlight Butterfly`, `Charged Particle Cannon`. A name is
changed ONLY where it is provably a budget casualty (recomputing
`fit(jp, translate(jp), budget)` reproduces exactly what shipped). 34 names that
were hand-edited after generation are left alone - without that guard the pass
would have reverted `Vascud Crisis` to the tokenizer's `Basukudokuraishisu`.

16 names stay abbreviated for now: they exceed a 24-column display cap, which is
the width proven by the shipped `Sigma Breast Musou Sword`. The cap is
conservative - `M1 07 Baraena Kai 2 Twin Beam Gun` (33 cols) already ships - and
can be raised once a build confirms the real limit visually.

Text is written with the MENU encoding, not cp932: the 0x13A290 reader treats
0x2E-0x3D as control codes, so `75mm Autocannon` has to carry fullwidth digits.

### Gates

`verify_pointers --min 85` OK (worst record 85.1%), `integrity` 0 problems, all
ELF patches present, pool re-read after write: 3,433 entries, 0 unreferenced.

## 0.8.79 (2026-08-26) - glossary decisions finally reach the script

### The gap

41 name corrections were researched against akurasu on 2026-08-25 and recorded
in analysis/glossary_sources.json. Only FOUR were propagated to the game. For a
day the database said one thing and the player saw another, and it was reported
as "names corrected" - which was true of the DB and false of the image.

Now applied, 1371 replacements across 110 records:

    Olson  -> Orson   520      Runa   -> Luna    392
    Kiel   -> Kihel   ~350     Reeven -> Lowen    30
    Misha  -> Micha    48      Gonjii -> Gonzy    24
    Tiptree-> Tiptory  19      Teraru -> Teralu    1

### NOT renamed: Dianna Soreil

"Soreil" appears 137 times and a rule was written to change it to "Sorel".
Checking the corpus first showed every instance is Dianna SOREIL (Turn A),
which akurasu spells exactly that way; only Eureka Seven's ドミニク・ソレル is
"Dominic Sorel", and his name was already right. The rule was removed. This is
the third ambiguity of the day after メサ and サラ - a name that is correct in
one series and wrong in another cannot be renamed globally.

### A bug this build introduced and then fixed

fix_terms_global.py could only write a replacement that was shorter or equal,
so Kiel->Kihel (one byte longer) was impossible image-wide. It now writes into
the whole SLOT - the string plus its NUL padding - which 346 of 347 Kiel rows
already had spare.

The first version of that change used `len(enc) <= slot`, which let a string
fill the slot COMPLETELY and consume its own NUL terminator. Rows then ran into
the next string and merged two lines of dialogue:

    Kihel「That's the Mechanical Angel, Aquarion...」??? 「So you fuse

13 rows merged, 15 more pushed over 34 columns. scan_visible_defects.py caught
it immediately - it had been 0 in all eight categories and jumped to 28 - and
the image was restored from the 0.8.78 CHD rather than repaired in place.

The check is now STRICTLY less, so the terminator always survives, and the 16
rows that cannot take the extra byte are REPORTED and left alone rather than
squeezed. A visibly-old spelling beats an invisibly-corrupt row.

12 rows that Kihel pushed to 35 columns were re-wrapped.

### Verified

68,340 rows / 0 defects in all eight categories · 205/205 records · 0 dead
links · all ELF patches present · pointer gate OK · every spirit distinct ·
integrity 0 problems.

## 0.8.78 (2026-08-26) - three bugs from screenshots

### 1. Literal backslash-quote in dialogue

Tekkouki rendered `Selling out that \\"researcher's soul\\" he named!?`.
scan_visible_defects.py checked for literal backslash-n and backslash-t but NOT
backslash-quote, so it survived every sweep. 2 rows, both rec47. ASCII " is
already used 73 times in dialogue (and ' 42,383 times), so the font renders it.
The scanner now checks every escape a JSON/py source can leak.

### 2. "Raben" in the character index

COMPDATA.BN is a THIRD place character names live, after the STAGE dialogue and
the ZKN library. Fixing those two left the in-game index still showing "Raben"
where both say "Lowen".

Auditing COMPDATA against the whole glossary found 56 stale names, not one:

    Olson -> Orson x14      Raben -> Lowen x6     Soreil -> Sorel x5
    Teraru -> Teralu x4     Kiel -> Kihel x4      Runa -> Luna x4
    Suesson -> Sweatson     Tiptree -> Tiptory    Shuran -> Schlan
    Gonjii -> Gonzy         Misha -> Micha        Cherudim -> Cherubim

It also exposed a FOURTH spelling of レーベン - "Reeven" - in the variant
table beside "Reeven 2" and "Reeven P".

Names are replaced only where they occupy a whole NUL-terminated field, or are
the first/last word of one ("Orguss II Olson", "Reeven 2"). That matters:
COMPDATA holds the BGM title "Lonely Runaway", and a naive Runa->Luna would
have made it "Lonely Lunaway". Verified preserved.

### 3. Report popup overlapping the unit name

The popup composes three strings around the unit name, and two exceeded the
width the Japanese occupied:

    0x346c70  "Next time "                  10 cols, budget 6
    0x346c80  "enters the upgrade screen,"  26 cols, budget 20

10 columns of overflow, so the text collided with "Destiny Gundam". Now "When "
and "next opens upgrades," - both inside budget. Sizing came from measuring the
JAPANESE originals at the same offsets, which fit by definition.

Most other strings on that screen measured NARROWER than the Japanese they
replaced, so they are not overflow; the remaining upgrade-screen artifacts
(the icon overlapping "Gain Jamming") look like fixed-position icons placed for
the Japanese padding, and are NOT fixed here.

### Verified

68,340 rows / 0 defects in all 8 categories · 205/205 records · 0 dead links ·
all ELF patches present · pointer gate OK · every spirit distinct ·
integrity.py 0 problems.

## 0.8.77 (2026-08-25) - 194 rows of trailing garbage, 6 untranslated lines

`tools/scan_visible_defects.py` added: scans every STAGE record for things a
PLAYER sees, straight off the image, so it covers all 205 records and does not
depend on the export pairing (~30% wrong, see EXPORT_TRUST.md).

First run over 68,340 dialogue rows:

    trailing garbage after the closing quote   194
    column overflow                             11
    untranslated japanese                        5
    empty body                                   1
    line overflow / placeholders / escapes /
    mojibake                                     0

### The 194

Rows rendering junk after the proper closer:

    ...separate room...」」       ...Black History!」!」
    ...transformation!?」?」    ...broken robot army!」 v

That is a shrink-without-padding write: an older pass replaced a longer string
with a shorter one and never NUL'd the tail, so the remnant still renders to the
next NUL. Every tool written 2026-08-24/25 pads its slack; something older did
not.

Only 11 of the 194 overflowed the box, which is why nothing had ever noticed
them - the junk usually fits.

### Two checks that mattered more than the fix

**Nested quotes.** Cutting at the first 」 would delete real dialogue in a row
with two quoted spans. Guard added: only cut rows with exactly ONE 「. The
count stayed at 194, proving none were at risk.

**The stray 'v'.** 83 rows ended 」v, too systematic to assume garbage - if 'v'
were a control byte, cutting it would break dialogue flow in 83 places.
Measured the whole corpus: 68,257 rows end clean at 」, 83 carry a 'v'. At
0.12% that is damage, not syntax.

### Also fixed

- rec18 Loran's scream, rec177-180 "This is the last bazaar" (x4, with a
  Japanese speaker name), rec203 Bright - six untranslated lines
- rec116 shortened; "lift-board lessons from Holland...」" is 35 columns on its
  own, so no re-flow fits it and the text had to give

### Verified

68,340 rows, ZERO defects in all eight categories. 205/205 records, 0 dead
links, all ELF patches present, pointer gate 94.49%, every spirit distinct.

## 0.8.76 (2026-08-25) - spirit command: Analyze was showing as Scan

Two different spirits both displayed as **Scan**:

    0x3373D8  "Scan"     Reveals an enemy squad's stats.          <- correct
    0x337408  "Scan"     Target enemy squad's attack and
                         defense -10% for one turn.               <- should be Analyze

`tools/ui_batch2.py` already had `0x337408: "Analyze"` - the patch never
reached the image, and "Analyze" appeared NOWHERE in the ELF.

The slot is exactly 8 bytes ("Scan" + 4 NULs) and "Analyze " is exactly 8, so
it was written in place. The 2 bytes that follow are 0x85DA, the private
micro-glyph cell for this spirit, and patch_micro_glyphs maps SPIRITS[16]
分 -> "An" at PRIV_BASE+16 = 0x85DA. That confirms the record really is
分/Analyze and only the name string was wrong - the menu abbreviation was
already right.

Verified: all ELF patches present, pointer gate OK, 205/205 records,
0 dead links, "Scan" and "Analyze" now 1 occurrence each.

## 0.8.75 (2026-08-25) - glossary DB researched; library and script names aligned

### The glossary DB now records WHERE each name came from

`analysis/glossary_sources.json` gives every one of the 1000 entries a status,
a source and a note. Before this build, 6 entries cited a source. Now:

    cited 112 | corrected 11 | chosen 3 | owner-decided 4
    ambiguous 3 | DEFERRED 1 | corroborated ~310 | legacy-unverified ~560

`corroborated` means only "matches our own script", which is circular - it is
NOT evidence. `legacy-unverified` means inherited with no recorded source.

### Source precedence (see docs/TECHNICAL.md)

akurasu is NOT one voice - its own pages disagree (ツィーネ is "Ziene" on the
Pilot Database and "Tsuine" on the Banpresto Originals List; メール is "Mel"
then "Mail"). Order: Z/Pilot_Database, then Z/Unit_Database, then other akurasu
pages, then series wikis LAST. Eight names were "corrected" from Wikipedia
against the baseline and had to be reverted.

### Names corrected in the library (66 fields) and script

- レーベン Raven/Raben -> **Lowen** (akurasu 'Löwen General'; cp932 has no ö)
- シュラン Shuran -> **Schlan** (270 script rows; owner-confirmed)
- ロゴス Logos -> **LOGOS** (174 script rows + the bank entry)
- カシマル Kashmar -> **Kashmir** (35 script rows)
- リフ Ref -> **Lifting** + the 《Ref》 link renamed with it
- 7 Western names were written surname-first: Gym Ghingnham, Andrew Waltfeld,
  Jason Beck, Jack Oliver, Kyarin Flick, Hughes Gauli, Klein Sandman
- units: Chaos Leoh, Chaos Caper, Dianan A, Lady Command, Kuuraiou, Groma,
  Bolinoak Samahn, Corin Kapool, Galbaldy β, Cherubim Soldier, Tekkouki
- Eureka Seven: Gonzy, Ken-Goh, Linck, Micha, Dominic Sorel
- Turn A: Kihel, Miashei, Sweatson Stero, Lily, Teteth
- also Duke Fleed, Emperor Burai, Schwarzwald, Aphrodia, David, Luna,
  Rena Rune, Orson, Shaya Thoov, Mimsy Laaz

### Three names must NEVER be renamed globally

サラ = Sala Tyrrell / Sara Zabirov / Sara Kodama. レイ = Ray Beams / Rey Za
Barrel. メサ = Mesa (God Sigma), NOT Jerid's surname - renaming it to "Messa"
for consistency would have renamed the wrong character in the wrong series.
Marked `ambiguous`; a flat jp->en map cannot express "depends which series".

### A glossary term and its 《term》 links are ONE edit

Renaming a bank entry without its links leaves a DEAD link, and a dead link
CRASHES the scene. This build hit that twice: 《Ref》 died when the library
rebuild renamed the bank, and 《LOGOS》 died when the script was renamed before
the bank. Both were caught by the link audit BEFORE building.

Order matters: rename the BANK first. A bank entry with no incoming links is
harmless; a link with no bank entry crashes.

ウィール -> "Wheel" is DEFERRED for exactly this reason: 《Vodarac Wheel》 is
live in the dialogue and is not worth the risk for one entry.

### Verified

205/205 records · 0 dead links · all ELF patches present · pointer gate 94.49%
(worst record 85.1%, unchanged by every pass) · library coverage 98.2/100/100
with Japanese 74/0/0 · 1 remaining DB conflict, deferred by decision.

## 0.8.74 (2026-08-24) - fullwidth punctuation, done properly this time

`fix_fullwidth.py` REWRITTEN. The version that shipped as 0.8.72 rebuilt each
record with `" ".join(parts)`, sliding every byte after an edit leftwards
while the pointer table kept the old offsets. This one rewrites each
NUL-terminated string in place and re-pads the slack with NULs, so every offset
is preserved exactly.

- 256 dialogue lines, 730 fullwidth characters -> ASCII, in 54 records
- Map is exactly `．！？，` -> `. ! ? ,`; only rows carrying 「 or （ AND Latin
  letters are touched, so menu-drawn rows (where 0x2E-0x3D are control codes)
  are left alone

Proof it is not a repeat of 0.8.72 - the pointer gate is unchanged by the pass:

    before   129329 pointers, 122198 land on a string start (94.48%)
    after    129319 pointers, 122198 land on a string start (94.49%)
    worst record 85.1% both times; corrupt 0.8.72 had rec5 at 26%

Verified: 205/205 records, 0 fullwidth left in dialogue, 0 literal backslash-n,
0 stale spellings, 0 dead links, all ELF patches present, gate OK at --min 85.

### Library audit (findings only - NOT fixed in this build)

`tools/zkn_audit.py` added. The ZKN payloads are XOR-0x5E obfuscated, so
decompress+cp932 yields noise and any search over it silently finds nothing.
Reading them properly through zkn.parse found:

- 6,629 fullwidth punctuation characters across 784 library entries
- wrong names: PT rec275 "Kashimal Barre" (= Kashmir Valle), rec388 Norbu,
  rec40 Teraru, rec409 Tsine, rec205 Zeidel, and Gagaan x8 in descriptions
- KW rec3 "Mu Dimension" vs "Rivalry Zone" in 30 dialogue lines - the reason
  those 5 glossary links were dead
- KW rec45 "Ref" names the board, not the sport; the entry describes Lifting

Fix prepared at `analysis/zkn_en_current_fixed.json`, built FROM THE IMAGE's own
text (4,279 fields, 1,585 changed). NOT from analysis/zkn_en.json: 1,181 of its
fields hold an older, worse revision than what shipped, so a blanket rebuild
would regress them.

## 0.8.73 (2026-08-24) - REPLACES the corrupt 0.8.72

0.8.72 is WITHDRAWN. Do not play it, do not distribute the patch.

### What went wrong

`fix_fullwidth.py` corrupted 58 records. It rebuilt each record as
`" ".join(parts)` after shortening strings, so every byte after an edit
shifted LEFT while the pointer table kept the old offsets. It also ran
`decode("cp932","ignore")` over the WHOLE record - binary included - which
silently DROPS undecodable bytes.

Symptom: the game booted and New Game played fine, but loading a memory-card
save froze - the save resumes into one of the damaged records.

Every check in the build gate passed on 0.8.72: 205/205 records decompressed,
all strings NUL-terminated, record LENGTH unchanged (the tail was NUL-padded),
0 dead links, all ELF patches present, chdman SHA1 verified. None of them looked
at whether pointers still addressed the strings.

New gate: `tools/verify_pointers.py` scores the share of pointers landing on the
START of a NUL-terminated string. Run it before EVERY build:

    python tools/verify_pointers.py <iso> --min 85

Baseline 94.5% overall, worst record 85.1%. On corrupt 0.8.72 rec5 read
118/451 (26%) against 451/451 healthy. `fix_fullwidth.py` is quarantined under
tools/quarantine/ as .BROKEN.

### Contents

Identical to 0.8.71, plus the literal backslash-n fix ONLY:

- 113 rows unescaped across rec104/107/131/135/136/139/149 (163 occurrences),
  rejoined and re-wrapped to 34 columns. Length-preserving, verified by the new
  pointer gate at 94.49% vs 94.48% before the pass.
- The fullwidth punctuation change is NOT in this build and will not return
  until it is rewritten to edit strings in place.

Verified: 205/205 records, 0 literal backslash-n, 0 stale spellings, 0 dead
links, all ELF patches present, pointer gate OK at --min 85.

## 0.8.72 (2026-08-24) - WITHDRAWN, CORRUPT - do not use

- Fullwidth punctuation converted to ASCII in dialogue only: 256 lines, 730
  characters, 54 records. Map is exactly `．！？，` -> `. ! ? ,`. Verified all 256
  rows carry 「, so no menu-drawn row was touched (in menu rows ASCII 0x2E-0x3D
  are control codes and fullwidth is CORRECT). Shrinks 2 bytes -> 1 and 2 display
  columns -> 1, so it can never overflow a slot or a line.

- Literal backslash-n unescaped across ALL 205 records: 113 rows in rec104,
  107, 131, 135, 136, 139, 149 (163 occurrences). These rendered the characters
  
 to the player inside the dialogue box - caught by a user screenshot.
  `fix_literal_nl.py` had reported 0 because it only reads the 26 exported
  records; rec104/107/136 alone held 134 of them. New
  `fix_literal_nl_global.py` scans the image instead. Unescaping ADDS a display
  line and would have pushed 58 rows past the 3-line box, so each body is
  rejoined and re-wrapped to 34 columns. 0 rows skipped.

Verified after applying: 205/205 records, 0 stale spellings, 0 dead links,
0 fullwidth punctuation left in dialogue, 0 literal backslash-n in dialogue.

## 0.8.71 (2026-08-24) - crash fix, canonical names finished, cp932 boundary bug

### Fixed a scene crash I introduced

Five `《Rivalry Zone》` glossary links pointed at no keyword-bank entry. A
`《term》` that does not resolve CRASHES the scene, so every build since the
Overlap -> Rivalry Zone rename shipped five potential crashes. `fix_dead_links.py`
unwrapped all five to plain text; the audit now reports 0 dead links against the
52-entry bank.

### cp932 word-boundary bug in fix_terms_global.py

The rules matched `NAME` against RAW cp932 BYTES. The trail byte of 「 is
0x75 - ASCII 'u', a word character - so the boundary never fired on a name that
OPENS a line of speech, which is the most common place a name appears. Every rule
in the tool was silently skipping those rows; the pass reported success while
doing nothing there. Matching now runs on decoded text, per NUL-terminated
string, preserving record length exactly so all pointers stay valid.

Caught only because a post-run count showed 9 `Katsura`, 2 `Norbu`, 1 `Tsine`
surviving a pass that claimed to be clean. Verify by counting the image, never by
trusting a tool's own report.

NOT yet audited: `fix_terms_pass.py`, `fix_rank.py` and any other byte-matching
tool may carry the same defect. This image is verified by direct string counts,
so its result stands regardless.

### Names (wiki-canonical, all 205 records)

- `Kashimaru` -> **Kashmir** (85) - a man, not a woman; a screenshot showed a
  gender flip downstream of the wrong name
- `Katsura` -> **Kei** (桂 = Kei Katsuragi); the surname Katsuragi (62) is
  correctly untouched
- `Barre` -> **Valle**, `Zaidel/Zaydel/Zeidel` -> **Seidel**, `Tsine` -> **Ziene**,
  `Norbu/Norub` -> **Norb**
- 総統 -> **Supreme Commander** (17)
- Stale spellings remaining: **0**

### Also

- Proofreading batches 41-43 applied; 26 records changed, plus 13 placeholder
  repairs and the 416 unreviewed thought lines
- Term sweep: 60 rows across 21 records
- One `apply_fixes` rejection was correct - rec112 row 160 is a menu-drawn row,
  where ASCII 0x2E-0x3D are control codes

### Process errors this build

- A missing `if __name__ == "__main__":` guard in two new multiprocessing tools
  caused a fork explosion on Windows that saturated the machine for ~7 hours.
  Guards added to 8 tools.
- I then misread the resulting CPU starvation as a hung job and started a SECOND
  writer against the same image. Harmless only by luck - both computed the same
  result from the same input. Never two writers.
- Ran the global name pass BEFORE `apply_fixes` instead of after. Agent fixes come
  from stale exports, so 13 old spellings were carried back in. Pipeline order is
  agents -> apply_fixes -> name scripts, and it is in BASE_RULES for this reason.

### Verification

205/205 records decompress · 0 dead links · 0 stale spellings · all ELF
patches present

## 0.8.70 (2026-08-23) - proofreading batches 2-7, canonical names, Rivalry Zone

### Names now come from the wiki, not from our data

Project rule, at the user's instruction: every name and glossary term takes its
established English form from akurasu.net / the SRW wiki. Deriving names from
the katakana or from a majority vote across our own corpus is forbidden -
majority vote is actively WRONG here:
    桂     ships as Katsura 157 / Kei 114  -> canonical is Kei (Kei Katsuragi)
    ツィーネ  ships as Tsine 165 / Ciene 16   -> canonical is Ziene (Ziene Espio)
    鉄甲鬼   ships as Tekkoki 11 / Tekkaki 8 -> canonical is Tekkouki
    レーベン  ships as Leben 172 / Raven 93   -> canonical is Lowen

レーベン is "Lowen" (Löwen, German for lions - the character is lion-themed, and
his Chimera unit uses German animal codenames: Löwen/lion, Ziege/goat,
Schlange/snake). I argued from phonetics that it was "Leben" and was wrong; the
wiki says Lowen General. The same source settled Edel Bernal's rank, which was
shipping SIX ways (准将 as Vice Admiral, Commodore, Colonel, General, Brigadier
General, Major General): she is a Brigadier General of the New Earth Federation
ARMY's Chimera Special Forces, so "General Edel" in address.

apply_names.py: 3,518 speaker lines renamed across 128 records - game-wide, not
just the DeepSeek set. Three groups excluded ON PURPOSE and recorded in the
tool: レイ (Ray Beams and Rey Za Barrel are BOTH レイ and every record mixes
both casts - needs per-line context), シュラン ("Schlan" was inferred from the
German pattern, not cited, so the shipping "Shuran" stands), メーテル
(rationale did not check out).

相克界 was "Overlap", a term I invented. The established English is "Rivalry
Zone" (MNeidengard's SRW Z walkthrough, whose definition matches the in-game
entry). rename_term.py rewrote 31 strings, 2 popup titles and 5 links as one
atomic pass - a linked term cannot be renamed piecemeal, because the popup title
and the 《term》 must match exactly or the link is dead.

### Proofreading

Batches 2-7: 36 Sonnet agents, 80 rows per slice, ~2,900 rows proofread, 423
fixes applied. Model choice measured, not assumed: on an identical slice Opus
found 42 fixes to Sonnet's 20 for fewer tokens, but Opus draws the weekly quota
~5x faster, so Sonnet is ~1.8x more efficient per fix - which is what matters
under a quota. Opus is reserved for judgement calls.

Representative catches no script could make: 隣接 ("adjacent") shipped as "dock
with the Eternal", a wrong gameplay instruction; 口ほどでもない inverted so a
taunt reads as praise; お任せします ("I leave it to you") as "Leave that to me";
Edel Bernal called "he" twice though she is female; 「アサキム・ドーウィン達」 split
into "Asakim and Dowin", inventing a character; ヤーパンの天井 (a place) as "the
top of Japan"; 昔の男 ("an old flame") as "old man".

### TWO BUGS OF MINE, and how they were caught

1. fix_body_terms.py built its substitution rules from groups.json, which lists
   every spelling a speaker has EVER shipped under - including junk from
   mis-parsed rows. From ONE such line it derived "Ghingnham -> Dianna" and
   fired it on every row mentioning ディアナ, rewriting real names in prose AND
   speaker lines, and turning a 《Ghingnham》 link into 《Dianna》 - a DEAD link,
   i.e. a crash.
2. apply_fixes.rebase() fell back to the whole agent string when a fix had no
   speaker line, appending it after the existing speaker and duplicating the
   tail ("...」.」").

Caught by re-running the link audit after the pass: dead links went 0 -> 1. That
single number was the only signal. 97 rows were repaired by word-aligned
reversal and 37 rebuilt from the pre-session exports (none of which had an agent
fix, so nothing good was lost). rebase() now REFUSES a single-line fix instead
of guessing. Final state: 109 links, 0 split, 0 dead; 68,339 dialogue rows with
0 over three lines and 9 over 34 columns (all pre-existing).

### Guards added, each after a near-miss

  * make_slices no longer sends MENU-DRAWN rows (no 「) to agents, and
    apply_fixes refuses them: in glossary descriptions and objectives the
    fullwidth ．and ４ are CORRECT, because that reader treats ASCII 0x2E-0x3D
    as control codes. Two agents proposed "fixing" them to ASCII.
  * Ranks and terminology are normalised centrally at apply time. Four agents
    each "standardised" 准将 from their own 80-row window and picked four
    different answers; two agents took opposite positions on ヴォダラ宮 (the
    palace, "Vodara") vs ヴォダラク (the order, "Vodarac") within minutes.
  * 百鬼 is Hyakki (Getter Robo Go), never Mykene (ミケーネ, Great Mazinger).
    8 rows were already wrong, so an agent "unified" three CORRECT rows to the
    mistake. ミケーネ appears 0 times in the corpus.

### Found, not yet fixed

109 rows OUTSIDE the DeepSeek records carry pre-existing damage of the same
shape: a duplicated closing quote plus a name substitution, e.g.
「クライン・サンドマン」 (Klein Sandman) shipping as "Klein Eiji" - the speaker's own
name pasted over another character's.

## 0.8.69 (2026-08-23) - DeepSeek proofreading, first two batches

The 26 records translated by DeepSeek (20,464 rows, ~228,000 words, about 28%
of the script) are being proofread against the Japanese. Fixes are applied as
IN-PLACE splices - never by re-running restore_full.py, which regenerates STAGE
from the Japanese and would wipe every in-place edit made since v2.01.

### Free passes (no model cost)

  * ELLIPSES: 2,567 rows carried a two-dot ".." (3,110 occurrences) or the
    fullwidth "…" our own encoding rule forbids. The two-dot form is byte-budget
    damage - the trimmer dropped a dot to save one byte, back when rows could
    not grow. 1,911 fixed in place, 287 re-wrapped, 369 relocated.
  * ESCAPES: 336 rows contained a LITERAL backslash-n instead of a line break,
    so the player read "Sorry...\nAll I can do is apologize...". 195 rows used
    fullwidth "．" inside dialogue (correct for the menu reader, wrong here).
    523 rows fixed, 179 of them re-wrapped.

### Agent passes

Two batches of 6 Sonnet agents, 80 rows per slice: 916 rows proofread, 192
fixes applied, 1 rejected by the validator (36 columns - the agent miscounted).

Model choice was measured, not assumed. On an identical 120-row slice:
    Opus    120 rows examined, 42 fixes, 63,251 tokens
    Sonnet   96 rows examined, 20 fixes, 84,091 tokens
Sonnet used MORE raw tokens and found nothing Opus missed - its 20 fixes were a
strict subset. But Opus tokens draw the weekly quota roughly 5x faster, so per
unit of quota Sonnet is ~1.8x more efficient, which is what matters here. Opus
is reserved for judgement calls.

Sonnet silently reviewed 96 of 120 rows in that trial, so slices were cut to 80
and the brief now DEMANDS a coverage report. Every agent since has returned
full coverage.

What the agents caught that no script could:
  * meaning inversions - 口ほどでもない shipped as "isn't all talk after all"
    (enemy is tough) when it means the opposite; 「ザフトへの義理も立つ」 as "we owe
    ZAFT nothing" when it is "this also fulfils our obligation to ZAFT"
  * a wrong gameplay instruction - 隣接すれば ("when ADJACENT") shipped as "dock
    with the Eternal"
  * dropped proper nouns - Orb's ruling Attha family as "Asha"; "Turn X" as
    "Turn"; ランスロー大佐 as bare "Colonel"; 賢人会議 flattened to "the Council"
  * a misattribution putting Djibril's Council of Sages membership on Orb
  * hundreds of truncations: "on charges of!" (high treason), "we give our!"
    (lives), "If worst comes to!" (shoot it down)

### Open, and needing a decision

  * SPEAKER NAMES: 112 Japanese speakers ship under more than one English
    spelling, 1,310 lines on a non-dominant variant. ジ・エーデル has four (The
    Edel / Ji Edel / The Eder / The Eidel); レーベン has four (Leben / Raven /
    Leven / Raben). Worse, 風見 (Dr. Kazami) ships as "Kazuki" in 9 rows, which
    is a DIFFERENT character (香月) - a collision, not a variance. Proofreading
    cannot see this: the brief locks the speaker line, and an agent reading one
    80-row slice has no way to know "Raven" appeared as "Leben" three records
    earlier. 23 groups are clear misspellings and safe to normalise by script;
    89 need a judgement call (桂 splits Katsura 157 / Kei 114 - different
    readings, possibly different characters).
  * TRUNCATIONS: 516 rows still end on a word that cannot end a sentence
    ("the.", "of!", "your."). Agents fix them as they reach them; a targeted
    pass over just those rows would be far cheaper than a full proofread.

## 0.8.68 (2026-08-23) - menu labels that overran their fixed columns

Same defect class as 0.8.67, found by measuring instead of guessing. A label
sits in a column whose width was set by the Japanese: each fullwidth char is
21px, while our English glyphs advance ~13px. When the replacement is wider
than the kanji it replaced AND the next field is drawn at a fixed x, the label
runs straight through it.

HEADER: "~Spirit Command Select~" (23 glyphs) ran under the button hints, which
start about 18 glyphs in ("...Command Se○:Next"). Now "~Spirit Command~" (16),
matching its sibling "~OTHERS Command~".

SPIRIT NAMES share their column with the SP cost, drawn at a fixed x ~91px -
the user's screenshot shows "Intuiti20n", i.e. the number landing after 7
glyphs. Names must stay at 6 glyphs or fewer:
    Act Twice -> Twice     ２回行動      117px -> 65px
    Intuition -> Sense     直感         117px -> 65px
    Friendship -> Bonds    友情         130px -> 65px
    Resolve   -> Endure    不屈          91px -> 78px
    Courage   -> Brave     勇気          91px -> 65px
    Analyze   -> Scan      分析          91px -> 52px
    Confuse   -> Daze      かく乱         91px -> 52px

SKILL NAMES sit in a 147px column (リフテクニック = 7 fullwidth). "Ref Technique"
at 169px overflowed - visible in the level-up shot as "Reff TechniqueLFocus".
Now "Ref Tech" (104px). The other long skills are fine: their Japanese is long
katakana (Oversense 117 vs 147, Game Champ 130 vs 147, Negotiator 130 vs 147).

One more 効果 label at 0x346860 shortened to "Eff" (the 0.8.67 pass covered the
other five 4-column slots).

NOT swept blindly: 82 short Japanese labels were replaced by wider English in
the menu region, but most are menu ITEMS in wide rows ("Retreat", "Disband",
"Combine") where nothing is drawn beside them, and shortening those would cost
readability for no gain. Only labels with a field drawn at a fixed x next to
them actually clip, and that cannot be told from the strings alone - it needs a
screenshot. The 82 are listed in this entry's audit for future reference.

## 0.8.67 (2026-08-23) - Spirit Command labels fit their column

"Effect" and "Target" on the Spirit Command Select screen ran straight through
the value text ("EffeSquad move +2 until you move."). The Japanese labels are
効果 and 対象 - two fullwidth chars, so the screen draws the value at a FIXED x
about 42px in. Our English glyphs advance ~13px, so a 6-letter label needs
~78px. Shortened to "Eff" and "Tgt" (~39px); 4 letters would be 52px and
overlap again.

Applied to the five 4-column label slots in the ELF (both 効果/対象 pairs at
0x344BB8/0x344BC0 and 0x345180/0x345188, plus 効力 at 0x344A40). Left alone:
特殊効果 at 0x33D800 (8 columns) and 対効果 at 0x346850 (6 columns) have room
for the whole word.

NOT A BUG: the same screenshot showed a pilot named ジョゼフ, but that was an
older image a friend was playing. Verified for the record - ジョゼフ appears
NOWHERE in the current build: not raw anywhere in the 3.7 GB image, not in any
banlz bank (every file under 45 MB decompressed and searched), and not in any
memory card. "Joseph" is translated in COMPDATA in both the plain and the
0x01-prefixed record forms. The only original file still carrying the kana is
HSFC's voice-actor credits (ジョゼフ・ヨット / 佐藤せつじ), which is a credits
list, not a pilot card.

## 0.8.66 (2026-08-23) - every dropped glossary link audited and restored

User asked for a full check after spotting another unlinked term. Compared
every Japanese string carrying a 《term》 against the English at the same offset.
JP marks 131 links; we had 98. 27 were missing on our side, in three groups.

RESTORED (11): Glory Star, Scub Coral, Orb, Battle of Orb, Space Science
Laboratory, Siberian Railway, Ref, Summer of Love, Vodarac Wheel, Rau Le
Creuset, Ghingnham. Two causes:
  * the term was present but SPLIT across a line break, which kills the link
    ("Rau Le / Creuset", "Summer of / Love");
  * the translation PARAPHRASED it, so it no longer matched the entry name -
    "Orb Defense" vs Battle of Orb, "Space Science Lab" vs Space Science
    Laboratory, "Siberia Railway" vs Siberian Railway, "<Wheels>" vs Vodarac
    Wheel, and "You ref-board too, Renton?" vs Ref (now 「You do 《Ref》 too,
    Renton?」, matching 「レントン君も《リフ》をやるの？」).
relink_missing.py wraps with linked terms GLUED so a link can never be split.

LEFT UNLINKED ON PURPOSE (13, all record 203 - Amuro and Kamille trading SRW
trivia): オルファン, バルマー戦役, 金田伊功 have no keyword entry anywhere, and a
link with no entry is a DEAD link, which crashes.

SKIPPED (3): "Side ３" and "Evidence ０１" - entry names carry FULLWIDTH digits
(the bank is menu-drawn, where ASCII 0x2E-0x3D are control codes) and a link
must match the entry exactly, so linking would drag fullwidth digits into
dialogue that uses half-width. "PLANT Supreme Council Chairman" is 30 chars, so
《...》 is 34 columns - the whole box, no room for a sentence.

MISTRANSLATION FIXED: ゲンガナム was "Gendarme" in the bank. It is the Turn A
Gundam Moon dome city, and the entry's own description credits the "Ghingnham
family" - the dialogue already said Ghingnham. fix_ghingnham.py renames the
WORD and the description's first word; payload 624 bytes against a 672-byte cap,
no record moved, ELF offset table untouched.

ALSO REPAIRED: rec 5 carried a link that was both split across lines AND wrong -
"Second Battle of Jachin Due" where the entry is "２nd Battle of Jachin Due".
It could never have resolved. Markers removed rather than importing the
fullwidth digit.

AUDIT BUG worth remembering: the dead-link check extracted 《...》 with a regex
where '.' does not match a newline, so a SPLIT link was invisible to it and
survived two passes. The final audit uses re.S.

Final state: 109 links in dialogue, 0 split, 0 dead.

## 0.8.65 (2026-08-22) - one name for 相克界, and its links restored

User spotted the popup titled "Overlap" opening from a line that called the
same thing "Dimensional Rift". An audit found the keyword had TWELVE English
renderings across the script: Overlap, Dimensional Rift, Conflict Field,
Conflict Zone, the Rift, the barrier, the dimensional barrier, the Aether
Barrier, the Barrier, Interference, Cross-Realm, Mutual Exclusion World, and
"the walls between worlds".

unify_overlap.py: 28 lines rewritten to "Overlap" (the popup title), each
re-wrapped with the placeholder-aware wrapper and asserted to fit 3 lines x 34
columns and its byte slot. link_overlap.py caught one more, record 106's
"Cross-Realm" - missed by the first pass because that row was relocated, so its
offset no longer matches the Japanese.

Kept as-is: "Tch! Interference!" in records 87/89/94 is 邪魔 (someone butting
in), not 相克界.

LINKS RESTORED. The JP script marks 《相克界》 in 5 places (4 in rec 25, 1 in
rec 26); our English had lost the markers, so the term was plain text even
though Square still opened the entry. Added back as 《Overlap》.

Safety rule applied: a link whose scene carries no popup entry is a DEAD link,
and a dead link crashes the game. Only records 25 and 26 carry the Overlap
entry - and those are exactly the two the JP linked - so none of the added
links can be dead. Record 106 was renamed but deliberately NOT linked for this
reason. Audited after the fact: 98 links in dialogue, 0 without an entry in
either the keyword bank or their own scene.

Deferred: the opening-demo speaker names (スティング etc.) are still Japanese.
They live in BTL/OP0.BIN, a different bank from the captions - which is why the
quote renders in English under a Japanese name. User called it unimportant.

## 0.8.64 (2026-08-22) - glossary-link crash SOLVED + placeholder clipping

TWO SEPARATE BUGS, both found from user screenshots.

### 1. The 《term》 link crash (UN, Trapar)

The 0.8.63 payload-cap theory was WRONG - the user retested and it still
crashed. The emulator log gave the answer in one line:

    TLB Miss, pc=0x78bb08 addr=0x78fc1585 [load]

0x78bb08 is inside OUR cave: patch_backlog's CONVCOPY stub at 0x78BAF0,
6 instructions in, at `lbu $t3, ($t0)` - handed a source pointer of 0x78fc1585
(~2 GB, far outside the PS2's 32 MB).

Root cause, and it is NOT the keyword bank: a dialogue link does not read the
bank at all. Every scene carries its own copy of the entry inside its STAGE
record as [title]["source"][description] (the source string is missing on
some). The library reads the bank, the link reads this - which is why the same
entry opened fine from the menu and killed the emulator from a link, and why
every bank-side theory was a dead end.

26 of those descriptions had lines far past the box; several were a SINGLE
unbroken line - UN 398 bytes, Liff 426, FAITH 473, Trapar 531, Exodus 632.
The renderer copies a row into a ~520-byte stack buffer; CONVCOPY converts
ASCII to 2-byte private codes during that copy, so a 400-byte row wrote ~800
and smashed the caller's locals. With the hook reverted the same rows still
broke the stock renderer (VIF FIFO assertion on Trapar) - the unbroken line is
the defect, the hook only amplified it.

fix_popup_wrap.py: 93 strings re-wrapped to 38 columns across 10 records,
BYTE-NEUTRAL (only ' ' <-> '
'), so nothing moved and no pointer changed. 117
of the 122 over-wide strings had a Japanese counterpart at the same offset that
IS wrapped - that is how we know the breaks belong there. 72 of the 93 are
stage-recap summaries in rec 0 with the same defect.

Width note: the JP box is 48 COLUMNS (24 fullwidth chars), but our VWF English
glyphs advance 13px against fullwidth's 21px, so 48 ASCII columns is far wider
than the same box. Every correctly translated entry sits at 37-38 = 504/13.
Wrapping English at the Japanese column count would have moved the overflow,
not fixed it.

CONVCOPY hook restored afterwards (backlog stops breaking at periods again).

### 2. $ placeholders overflowed the box (148 strings)

Reported from a screenshot: 「This is Setsuko・Ohara of the Vir - clipped.
The stored line was 30 columns, comfortably inside the 34-column box:

    「This is $F of Glory Star. We

$F is a RUNTIME placeholder for the pilot's full name. The wrapper measured the
2-character token, not the 14 columns "Setsuko・Ohara" renders as, so the line
came out at 42. Same for $n (7), $f (7), $l (6).

fix_placeholder_wrap.py re-wraps with expansion-aware widths: 141 strings fixed
byte-neutrally. fix_hard_lines.py rewrote the remaining 8 with tighter wording
(they needed 4 lines otherwise). Verified: all 4,599 placeholder-bearing
strings now fit 3 lines x 34 columns once expanded.

$c is deliberately NOT handled - the squad name is player-entered and has no
bound; the Japanese script has the same exposure.

### Also

  * Popup titles translated (12 sites): 相克界 -> Overlap, ＵＮ -> UN,
    ＦＡＩＴＨ -> FAITH, ＳＯＦ -> SOF, 地球連合 -> Earth Alliance, Liff -> Ref.
    "Side ３" and "２nd Battle of Jachin Due" keep fullwidth digits - that popup
    is drawn by the menu reader, where ASCII 0x2E-0x3D are control codes.
  * リフ is "Ref" everywhere now: skill "Reff Technique" -> "Ref Technique"
    (ELF 0x336AE8), popup title "Liff" -> "Ref", "lift-boarding" -> "reffing".
  * 極 -> "Supreme" (SRW 30's localization, user call).
  * Asakim's 「全ては太極への道…」 relocated to full text: "All roads lead to
    Taikyoku..." (was budget-clipped to "All leads to Taikyoku").
  * Bar labels: Arial Narrow Bold, 2px ring, EP unclipped and raised 4px,
    SR Points matched to Funds (see 0.8.62).

PROCESS NOTE: multiprocessing does NOT work from a `python - <<EOF` stdin
script on Windows - the pool re-imports __main__ by path and dies with
"Invalid argument: '<stdin>'". Two passes appeared to hang for this reason, and
one of them held a stale STAGE that would have silently reverted a finished
pass had it completed. Write the script to a file before using a Pool.

## 0.8.63 (2026-08-22) - glossary-link crash: the exact-payload cap again

The UN glossary link crashed the emulator. Ruled out over several rounds, all
measured: dead links (0 remain), bank structure (52 entries parse, DSIZ/DATA
consistent), the ELF offset table (matches the archive byte-for-byte), the
file-table entry, encoding (no raw 0x2E-0x3D, no nested markers), padding, line
width and count, SRCE, and the texture pack. Swapping the UN description back
to the Japanese original did NOT stop the crash, which cleared the content.

The user's test cracked it: UN and Trapar both open fine from the LIBRARY and
both crash from a DIALOGUE LINK, while Titans, AEUG and Glory Star links work.
Payload sizes against each record's own Japanese payload:

    Titans      1168 / 1200   link works
    AEUG        1488 / 1520   link works
    Glory Star   528 /  544   link works
    Trapar      1360 / 1360   CRASH
    UN          1008 / 1008   CRASH

Every working entry is UNDER its cap; both crashing ones sit EXACTLY on it.
Same class as v1.31: an exact-budget fill leaves nothing after the data and the
reader runs into the next field. The library path evidently allocates
differently, which is why the same entry is fine from the menu.

17 keyword entries were at the cap and are now strictly under, trimmed out of
DSC2 (largely a truncated duplicate of DSCR): Space Science Laboratory,
Aldebaron, Mu Dimension, Kashim King, Side ３, Gendarme, Natural, Blue Cosmos,
PLANT, PLANT Supreme Council Chairman, Earth Alliance, Orb, Morgenroete Inc．,
Extended, Trapar, John Henry, UN. Blue Cosmos is linked in the SAME town scene
as UN and Trapar, so it was the next crash waiting. No record moved: archive
offsets unchanged, ELF table still matches.

zkn_build.py's cap is now STRICT (4 comparisons), so a rebuild cannot
reintroduce this. Audited the other banks: MTVZKNPT has 183 of 411 at cap and
MTVZKNRT 100 of 321 - left alone deliberately, since those are library-only and
the library renders at-cap entries fine (UN opened from the menu while at cap).

Also in this build:
  * 極 -> "Supreme" (SRW 30's localization; user call). It was the last
    untranslated skill name and lived in the ELF, not in any data file, which
    is why every data pass missed it. 8-byte slot, filled exactly.
  * Asakim's 「全ては太極への道…」 was "All leads to Taikyoku" - clipped to fit a
    32-byte slot. The row has 3 pointer refs, so it relocated (option-3):
    「All roads lead to Taikyoku...」, 33 columns. Budget-fitting a dialogue row
    was my error - relocation retired that constraint.

## 0.8.62 (2026-08-22) - intermission bar labels re-cut

The three English bar labels (EP / Funds / SR Points) were rebuilt from a
different face after they read as mush in-game.

Root cause of the mush: the cells are narrow (Funds has 43 usable px, SR
Points 83) and the renderer squeezed the type to fit - about 40% for Funds.
That collapses the counters: "n" came out as o##oo##o, i.e. the hole in the
middle was solid outline, so each letter was a dark blob with two light
stems. Fixed three ways:

  * Arial Narrow Bold replaces Times New Roman Bold. Condensed enough to fit
    at full height with no squeeze, and open-countered - scoring enclosed
    clear regions in "SR Points" gives Arial Narrow Bold 7, Impact 2,
    Calibri Bold 4. Its weight matches the game's own "BS." art.
  * ink_h is now a CEILING. render_cell steps the height down until the
    natural width fits, tolerating at most 10% squeeze (SQUEEZE = 1.10), and
    prints when it shrinks. Squeezing to fit is never done silently again.
  * Outline raised to 2px, but only ring 1 is grown everywhere. A counter is
    ~3px wide here, so a second inward ring would seal it; _exterior() flood-
    fills from the cell border and rings 2+ are confined to pixels connected
    to the outside. The glyph budget is also decoupled from OUTLINE, so a
    thicker ring no longer shrinks the letters.

EP was additionally being CLIPPED. Dumping the same cell from srwz_jpall.bin
shows the Japanese label occupying x146-165, rows 2-21, while ours painted
from x142 down to row 24 - everything outside that window is dropped, which
sheared the E's left edge. LABELS entries carry a left pad now; EP lands at
x146-165, rows 5-20 (4px higher, as asked). The window is only 16px wide, so
EP renders at 12px against Funds/SR Points at 14.

Sizes: EP 12px, Funds 14px, SR Points 14px (was 16 - it read visibly larger
than Funds).

## 0.8.56 (2026-08-22) - retranslation pass (captions are free-length now)

With the budget gone, swept for captions that were written TIGHT for it and
rewrote them at natural length. Detector (analysis/srvc_terse.json): EN
visible length vs JP visible length (a JP char is worth ~1.6 EN chars),
plus "JP has >=2 clause markers and EN has >=2 fewer", plus "EN lacks
terminal punctuation". 329 flagged; filtered to 118 with real content loss
(JP >= 12 chars AND ratio < 0.80); short interjections like うぅ…うぅ… ->
"Ugh..." are correctly NOT flagged.

123 lines rewritten. Representative repairs:
  第一種戦闘配備        "battle stations"    -> "Level One battle stations"
  恨むのなら、雇い主を   "Blame your employer" -> full two-clause sentence
  土木作業用のマシンが   "A work machine armed" -> "A machine built for
                                              construction work... and it's
                                              carrying weapons?!"
  女性が戦場に立つのは   "No women in battle"  -> "I cannot approve of a woman
                                              standing on a battlefield"
  ニュータイプ…黒歴史の闇に封印された力  restored (the whole second clause
                                       had been dropped)
Also folded in the four fixes staged earlier tonight: 320 "There you are!",
4953 Black History restored, 17101 keeps ためにも ("for this world's sake as
well"), and the Tannhauser opener "This ship will now commence its attack!".

Verified: the shipped SRVC is BYTE-IDENTICAL to an independently rebuilt
model (full translations + 56,956 repointed records), so nothing was clipped
or refitted at apply time.

## 0.8.55 (2026-08-22) - free-mode fix: 8,790 cells the shape detector missed

0.8.54 in-game: Tannhauser sequence CONFIRMED good, but a Saegusa bridge line
rendered as mojibake + "vG" - a mid-string read from a STALE record.

CAUSE: 0.8.54's cell detector pattern-matched PARSED STRINGS (a 6-byte string
+ empty, or the 4B+1B split). But any 0x00 byte inside a cell splits it
differently - f2 < 0x100 parses as 5B + two empties, a zero inside clip or
section splits elsewhere. 8,790 of 56,956 cells (15%) have such shapes; they
kept their old f2 while the pool moved under them.

FIX (tools/srvc_records.py rewritten): detection on RAW POOL BYTES - fit
anchors from unambiguous seed cells, then stride-walk +-8 bytes from every
seed, accepting cells whose trailing pad is 00 00 and whose f2 resolves under
the run's anchor (other block anchors tried at unit boundaries). Patch
positions map through the re-layout via slot-relative deltas (new_position).
56,956/56,956 cells resolved (the 1 holdout is misc data, not a record) and
chain-verified against the shipped bytes: anchor + f2 lands on the right
full-length caption for every record.

## 0.8.54 (2026-08-21) - FREE-LENGTH CAPTIONS - the byte budget is gone (user-confirmed in-game)

User: "find a way to store these text like dialogue so we don't need budget".
Done by decoding the sequence-record table completely instead of obeying it.

THE TABLE (tools/srvc_records.py)
  Each record is an 8-byte cell in the block pool: [u16 clip][u16 section]
  [u16 f2] + 2 NULs (f2 low byte 0x00 makes the parser see a 4B+1B split -
  same cell, f2 always at cell bytes +4..+5 in the serialized pool).
  f2 = target caption offset relative to an ANCHOR SLOT - the first quote of
  the record's own UNIT ([misc][records][quotes], several per block). The
  anchor is recovered per section by constant-fitting, block-majority vote
  for ambiguity. 48,166 of 48,167 records resolved; the holdout (block 162
  slot 3) is misc data, not a record.

THE REBUILD (srvc_apply --free)
  Translations applied at FULL length - no fitting, no clipping, no padding.
  After srvc.build() recomputes head/index, every record's f2 is repointed:
  new_f2 = new_off[target] - new_off[anchor], patched into the built bytes.
  All 1,418 lines clipped in 0.8.53 are restored to full text.
  File: 3,313,040 -> 2,925,942 B (unpadded English is shorter), still in
  place at LBA 1313214.

VERIFICATION
  Replayed the exact apply path (incl. 108 head-truncated replacements) and
  followed anchor+f2 through the shipped ISO bytes for every record:
  48,166/48,166 chains land on the right full-length caption, including the
  four Minerva/Tannhauser lines and the formerly-clipped Creation-is-
  destruction line. First verify attempt said 48,080 mismatches - that was
  the VERIFIER forgetting the head-truncated replacements, not the file.

RISK, stated honestly: this assumes the engine derives each anchor address
from data srvc.build() recomputes (index/head). 0.8.53 is the fallback if
any sequence type misbehaves. TEST: fire Tannhauser; also spot-check a few
other scripted attacks (Trider finisher, a GaoGaiGar sequence).

## 0.8.53 (2026-08-21) - SCRIPTED ATTACK SEQUENCES FIXED (real bug)

Found from a user screenshot of Minerva/Tannhauser. The English sequence read:
Talia "I cannot stop here." -> Arthur **the same line again** -> Talia " . . . "
-> Arthur `Lock on Tannhauser's course!"` **with no opening quote**. The
Japanese plays a different, coherent 4-6 line exchange.

ROOT CAUSE - and it corrects a belief this project held for months.
srvc_apply's docstring said "SRVC is not byte-budgeted". That is only half
true. Index-addressed captions (the random battle quotes) are free to change
length because srvc.build() recomputes those offsets. But the multi-line
exchange a weapon plays is fetched **BY BYTE OFFSET** from tables outside
SRVC that we do not rebuild. So a single over-long string slides every offset
after it inside its block. The missing opening quote is the fingerprint: a
read starting mid-string.

SCALE: 276,001 of 277,545 slots already kept their exact original byte length
(short lines were already padded). **1,544 did not** - 714 distinct lines,
15,294 bytes of growth - and each corrupted every sequence after it.

FIX
  - tools/srvc_fit.py: tiered shortener. Biggest lever is the ellipsis: in
    `menu` mode 0x2E-0x3D are CONTROL CODES, so every ASCII '.' ships as its
    fullwidth form (2 B) and "..." costs SIX; the Japanese ellipsis is one
    cp932 char (2 B) and is what the JP script uses anyway.
  - srvc_apply now ENFORCES the invariant: every string is exactly the
    original byte length, with `assert len(nb) == len(data)` on the whole file.
  - Result: SRVC.BIN is 3,313,040 B again (was +15,294) and is written back
    IN PLACE at LBA 1313214 - no relocation into DMY padding. SEG byte-
    identical to the original, 0 string-length mismatches, 0 block changes.

DEBT: 1,418 slots were auto-clipped to fit and read short. Median cut needed
was only 7 bytes (a trailing period or one redundant word), so these are quick
rewrites - work list in analysis/srvc_fitted.json.

NOT a bug, ruled out along the way: caption<->voice pairing (all 61,193 slots
verified against the JP original), the 0.8.52 "no sound" report (a per-game
PCSX2 ini carried OutputMuted=true, copied forward with the upscale setting).

## 0.8.52 (2026-08-21) - the re-wrap pass + caption fragment sweep

Two backlog items the user called in.

### RE-WRAP (the fullwidth-quote column bug, 0.8.46)
tools/rewrap_dialogue.py: 164 records, **10,146 strings re-wrapped** at the
correct metric (fullwidth = 2 columns). Byte-neutral - a line break just
replaces a space - so every string still fits its slot and nothing
downstream moves. Greedy wrapping is used deliberately: first-fit greedy
is OPTIMAL for line COUNT, so if it needs 4 lines no wrapping fits in 3.
Compression is the slow part (~1 KB/s), so the records go through a
10-process pool; the splice and the "every other record byte-identical"
check still happen once, in the parent.

**1,454 strings could NOT be re-wrapped** - their text genuinely does not
fit 3 x 34 columns and must be shortened. Listed in
analysis/rewrap_skipped.json with how far over each runs:
  <=5 cols over: 466 | 5-10: 698 | 10-15: 235 | 15+: 55
A mechanical contraction pass (cannot->can't, " - "->"-", etc.) was tried
and REJECTED: it fits only 27 of the 1,454 and produces "amazing-it",
"studied-left" - jammed words. These need real rewriting, in batches.
They are no worse than today (first line clips by one character).

### CAPTION FRAGMENTS (127 rewritten)
The 282-candidate list from 0.8.48, read rather than batch-applied, plus
two mechanical scans that turned up real damage:
  - MISTRANSLATIONS: 本艦の装甲を甘く見たな… was "Armor's weak..." (the
    OPPOSITE); 友軍機の援護を！ was "Cover me!" (wrong subject).
  - LOST SYMBOL: six captions dropped the ∀ - "That's  for you!",
    "is X's brother!", "I'll stop Turn X's M-Fly with !". Note ∀ IS
    cp932-encodable, so something else in the old pipeline ate it; all six
    now spell out "Turn A".
  - JAMMED WORDS from the old byte-fitter: "Notmy style,really...",
    "Sorry,butthis isn'toveryet!", "WhatifIdie,howyougonnaanswer?!".
    One had lost the 'n' from its break and rendered "ire 1 and 2!".
  - 418 captions ended with a trailing line-break marker (a blank line
    under the text) - stripped mechanically.
DETECTORS worth keeping: no-space-after-comma, double-space (finds
dropped symbols), a trailing break marker, and JP-has-particle vs
EN-is-2-words.


### TEXTURE PACK (tools/build_texture_pack.py)
Shareable now: `_work/dist/SRWZ-texture-pack.zip` - 65 PNGs + README +
a settings ini, ~1 MB. A friend copies the `textures` folder into their
PCSX2 user directory and turns on Load Textures.
  - Replacements are keyed by game SERIAL only, so ONE pack works for
    EVERY build - it does not need rebuilding per release.
  - PER-GAME SETTINGS are the opposite: keyed serial+CRC, and every ELF
    patch changes the CRC. The user's 4x upscale had SILENTLY reverted
    (their ini was bound to A88D37CA; they now run E1AD5133), which is
    also why the prologue cards looked missing. Copied the ini to the new
    CRC and the README tells players to set upscale GLOBALLY instead.
  - PCSX2 scans the replacements folder at game BOOT, so files added
    while it is running need a full restart, not a savestate load.
  - gen_hd_labels/gen_hd_menu need the PCSX2 dumps folder (only on the
    user's other machine), so the packer carries anything it cannot
    regenerate over from the live folder.

Verified after the re-wrap: over-wide dialogue strings dropped from
11,633 to 1,454 - exactly the set that needs text tightening, nothing
else left behind.

Build: "SRWZ v0.8.52.chd".

## 0.8.51 (2026-08-21) - generic soldiers get their full name back

User asked whether "Chiram Sldr" on the dialogue name plate needed to be
abbreviated at all. It did not: that form comes from compdata_en.py's
SHORT table, which exists because the UNIT-LIST name cell is tiny, but a
dialogue speaker name is part of the string itself
("Name
「text」") and is bounded only by that string's NUL slot.

83 instances across 8 factions - Chiram 34, Alliance 16, DC 12, Gaizock
10, Emaan 7, Fed. 2, Elder 1, Titans 1. 64 already had the 3 spare bytes.
The other 19 were tightened by a word rather than left inconsistent, e.g.
  "No choice! All units, attack!"       -> "Fine! All units, attack!"
  "It's coming from that machine..."    -> "It's from that machine..."
  "Sensor's reacting to this woman."    -> "Sensor's reacting to her."
  "savages from a backwater"            -> "backwater savages"
Result: zero "Sldr" left in STAGE dialogue.

The line in the screenshot itself is fine - 「さあ、特異点…こちらに来い」
really is "Now, singularity... come here."

NOTE: the unit-list name (COMPDATA) still reads "Chiram Sldr"; its cell
genuinely is too small, and re-running the COMPDATA patcher is not worth
the risk for one label (see 0.8.45 on apply_stage for why rebuilding from
stale sources is dangerous).

Build: "SRWZ v0.8.51.chd".

## 0.8.50 (2026-08-21) - the opening's series titles are art, and now English

User sent two PCSX2 texture dumps of the prologue cards (その日、世界は
崩壊した……). Confirmed they are pixels - the string is nowhere on the disc
in cp932, compressed or not. Hunting them taught us how this game stores
its text art, and that unlocked the OPENING TITLE CARDS.

DECODING PS2 TEXTURES (three things had to line up; write this down):
  1. the TIM2 picture header keeps width/height at +0x14, NOT +0x10 - a
     wrong read here reports nonsense like "256x1283";
  2. PSMT8 pixel data is SWIZZLED: block/column/byte mapping, the classic
     block=(y&~0xF)*w+(x&~0xF)*2, column=ypos*w*2+((x+swap)&7)*4 form;
  3. the 256-entry CLUT is stored TILED - 0-7, 16-23, 8-15, 24-31 within
     each group of 32 - so a straight read gives wrong colours.
tools/patch_op_titles.py does decode -> repaint -> re-swizzle in place.

OP0/OP1/OP2.BIN are one 512x512 PSMT8 each, holding 7/6/7 title strips of
~35 rows. Palette: 0 transparent, 23 white fill, 22 near-white, 6 dark
blue edge, 1 faint glow - English is painted with the SAME indices, so
the CLUT is untouched and the look matches exactly. Text is auto-shrunk
per strip to fit 512 px ("Mobile Suit Gundam: Char's Counterattack" lands
at 26 px, the rest sit at 34-37).
All 20 series translated, e.g. 超時空世紀オーガス -> Super Dimension
Century Orguss, 無敵鋼人ダイターン3 -> Invincible Steel Man Daitarn 3,
交響詩篇エウレカセブン -> Symphonic Psalms Eureka Seven.
Verified by reading the textures back out of the ISO through the same
swizzle path.

PROLOGUE CARDS: not on the disc in any reachable form (ruled out OP0-2,
JTIM, TICI, TBA, TRICMN, SIWP/SIPI/SIRB/SIBG, KVPDATA, AIDDATA, MTV_PROP
raw AND banlz; no wide 8-bit TIM2 in TCI/TBG/TRB/MTV_BGC/VEFF2DX/TWP), so
they go through PCSX2 TEXTURE REPLACEMENT instead - the same mechanism as
the intermission HD labels. The user supplied a dump filename, which is
what PCSX2 matches on:
  84d6382e3ee8a0af-b6f9a9ca4ec2e23c-00002693.png
    その日、世界は崩壊した…… -> "On that day, the world collapsed..."
tools/gen_intro_cards.py renders it 1024x512 RGBA, transparent ground,
Times serif at 34 px with a faint dark halo, text left edge x=118 / top
y=203 to sit exactly where the Japanese did, and writes it straight into
textures/SLPS-25887/replacements. The second card
(そして、新しい世界が始まる……) is authored and waiting on its dump name.

Build: "SRWZ v0.8.50.chd".

## 0.8.49 (2026-08-21) - 109 captions had a line break that never broke

Chasing three more user screenshots turned up a shipped defect.

*** THE LINE-BREAK MARKER IN CAPTIONS IS A LITERAL BACKSLASH-N ***
(two characters), NOT 0x0A - srvc_work.py documents this, and patch.py's
encode() passes text through unchanged, so a real newline is emitted as a
bare 0x0A that the box does not treat as a break. 109 entries in
srvc_en.json held a REAL newline and have therefore been rendering as one
long (clipping) line, including 187 - the Amuro line reworded back in
0.8.36 at the user's request. All 109 converted to the literal marker.
CHECK THIS after any bulk caption edit: no value may contain chr(10).

Also this build:
  - 5 katakana-English battle cries: ハブ・ア・ゴー was transliterated to
    "Have a go!" which reads as "give it a try" rather than a war cry ->
    "Here goes!"; シュート・アンド・シュート -> "Shoot, and shoot again!".
  - rec012 dialogue, 2 lines rewritten (both were also padded with
    FULLWIDTH periods - 2 columns each - which is what pushed them past
    the box edge):
      [JP source line, 41 columns]
        -> "...I'll add to my sins again. / All so that I can live."
      [JP source line, 57 columns]
        -> "This is where it begins... the / start of a tragedy. And
            then, a / fall into endless darkness."

INTRO CARDS (その日、世界は崩壊した…… etc.) - investigated, NOT text:
the string appears nowhere in the image in cp932, so it is pixels. Found
the likely home: OP0/OP1/OP2.BIN (LBA 1312162/1312292/1312422, one TIM2
each, 256x1024, 8bpp indexed) whose head byte says 7/6/7 images - 20
strips of ~72 rows, which matches a prologue card set. The data is PS2-
swizzled, so replacing it in-file means unswizzle + render + re-swizzle.
The cheap alternative is a PCSX2 texture replacement, which this project
already ships for the intermission labels - needs a texture dump from the
user to get the content hash.

Build: "SRWZ v0.8.49.chd" (supersedes the unshipped 0.8.47/0.8.48).

## 0.8.48 (2026-08-21) - caption quality pass (supersedes 0.8.47)

0.8.47 (skill-name widths) was built but never shipped; this build carries
it plus the caption work below.

User screenshot: 「Broke
armor!」 for 装甲を抜けたか！ - a two-word
fragment of a full sentence. Chasing that turned up a real defect class.

TEXT LOSS (2 captions): the English had NO letters at all -
  23064  効かないねっ！  ->  "!"     now "That won't work on me!"
  23067  並の腕だね！    ->  "!"     now "Your skills are nothing special!"
  (the two other no-letter entries are the game's own 無音 dummies)
Also 729 ∀を怒らせるな！ rendered as "Don't anger !" - the ∀ was dropped;
now "Don't make Turn A angry!" (spelling it out beats relying on the
symbol surviving the menu encoder).

Rewritten this build: 10228, 23064, 23067, 729, 699, 1991, 67.

DETECTORS worth reusing (the EN/JP length ratio alone is NOT enough - it
mostly surfaces shouts where terse English is correct, "Go!" for
いけぇーっ！):
  - no-letter English with a >=6 char JP source -> outright text loss (4).
  - JP contains a case particle (を/が/は/に/へ) and is >=8 chars, but the
    English is <=2 words and <=16 chars -> dropped-subject fragment.
    282 candidates; many are legitimately short shouts, so this list needs
    reading, not batch-applying.
  - ratio < 0.8: 38 lines, < 1.0: 144, < 1.2: 939.
The 282-line fragment list is the honest backlog for caption quality.

SRVC rebuild: 61,193 slots + 108 head-truncated, 0 left Japanese, now
1625 sectors at LBA 1826000 (7,511 spare sectors to the end of the image,
so there is room to keep growing).

Build: "SRWZ v0.8.48.chd".

## 0.8.47 (2026-08-21) - skill-name widths + Olson caption

SKILL PANEL (level-up / pilot screen): "Focused Attack" ran past the box.
The same table holds three more over-long names, all shortened to the
abbreviations already used elsewhere ("Chain Atk", "Support Atk",
"Ignore Size"):
  0x434918 Will Limit Break -> Will Cap Up
  0x434A28 Assist Attack    -> Assist Atk
  0x434A90 Focused Attack   -> Focus Atk
  0x434B30 Ignore Size Diff -> Ignore Size
Applied through tools/patch_elf_labels.py, and the SOURCE tables were
updated too (elf_ui_en.py for two, ui_batch2.py for the other two) so a
future re-apply of either cannot silently restore the long names.

CAPTION 12243: [JP source line, 46 columns] was
"Katsura maybe, but...
from behind? No good." - terse to the point of
being cryptic (a leftover of the byte-budget era; captions have had no
budget since the srvc_apply rebuild path). Now:
  "Maybe that'd work on Katsura, but
   you can't get me from behind!"      (33 / 29 cols, limit ~46)
srvc_apply rebuild: 61,193 slots + 108 head-truncated, 0 left Japanese,
SRVC relocated to LBA 1826000 (1624 sectors) as usual.

Build: "SRWZ v0.8.47.chd".

## 0.8.46 (2026-08-21) - the fullwidth-quote column bug

User screenshot: Olson's line clipped its last letter AND read stiffly.
Two separate faults, one of them systematic.

WIDTH: our wrapper counts CHARACTERS, but 「 and 」 are FULLWIDTH - two
columns each. So a quoted first line of exactly 34 characters is 35
COLUMNS and loses its last letter. That is the whole bug: the box is
~34 half-width columns (~442 px at ~13 px/char), and 「 costs 24.
Corpus sweep of all 205 records / 68,324 dialogue strings:
  11,633 strings have a >34-col line (or >3 lines)
  10,179 of them fix by RE-WRAPPING ALONE, byte-neutral (a break just
         replaces a space), needing no retranslation
   1,454 would need a 4th line, i.e. the text must be tightened first
       0 contain an unbreakable long word
Fixed in this build for record 12 only (the stage in the screenshot): 30
re-wrapped, 9 left alone because they would need a 4th line. The other
164 records are a follow-up pass - see analysis/overwide_lines.json.
NOTE for that pass: measure in COLUMNS (fullwidth = 2), not characters -
this is the same class of mistake as 0.8.14 wrapping at 37-40.

WORDING: [JP source line, 58 columns]
ばかりを追うとは…！」 was "Junius Seven bears down overhead, yet they
chase only their own nation's profit...!" - stilted. Now:
  「Junius Seven is falling on us,
  yet they think only of their own
  nation's gain...!」          (32/32/19 cols, 91 of 95 bytes)

Both edits went in through the safe splice pattern (decompress from the
CURRENT iso, edit, compress_record_optimal 12,806 B into the 12,928-byte
slot, verify all 204 other records byte-identical). See 0.8.45 for why
apply_stage.py must never be re-run.

Build: "SRWZ v0.8.46.chd".

## 0.8.45 (2026-08-21) - terrain zone names (probe) + deploy squad name

Two leftovers on the deploy panel.

1) SQUAD NAME "ブロンコⅡ" - the ONLY instance of that katakana on the whole
   disc, in STAGE record 12 at 0x84C8 (16-byte slot, sitting with the
   objectives and "Star 1/2/3", not with dialogue). -> "Bronco II".

   *** DO NOT RUN tools/apply_stage.py AGAIN ***
   I tried the documented flow (apply_stage with all 205 records). It
   rebuilds each record from analysis/stage_dec/*.bin - the ORIGINAL
   Japanese - and re-applies the EN tables, which are now STALE: every
   single record came out shorter (rec0 155,791 -> 152,336 B, and so on
   for ~200 records), i.e. it would have thrown away the 0.8.38 relayout,
   the glossary links and everything else applied to STAGE since. Caught
   by diffing all 205 decompressed records against a backup taken first,
   then restoring the region byte-for-byte.
   The safe pattern instead (used here): decompress the record FROM THE
   CURRENT ISO, edit in place, compress_record_optimal (12,808 B, fits the
   12,928-byte slot; the plain compressor gives 13,407 and does NOT fit),
   zero-pad the slack exactly as apply_stage does, then verify by header
   offset that all 204 other records are byte-identical before writing.
   ALWAYS back up the region and diff every record before writing STAGE.

2) TERRAIN ZONE NAME "荒地" - not in the ELF, COMPDATA, any banlz bank, or
   built from code immediates. A raw scan of the whole image finds those
   names only in MAPMODEL.BIN (LBA 1652964, 55 MB), in each map's node
   name table: short NUL-terminated names with 1-2 byte tags between them,
   mixed with the engine's own ASCII names like "Frame". The map-specific
   entries there (議会事堂, イノセントドーム) are exactly what that panel
   cycles, which is the evidence they ARE the displayed strings.
   tools/patch_mapmodel_terrain.py rewrites them IN PLACE, NUL-padded to
   the original length, so the 55 MB file keeps every internal offset:
     平地->Flat  荒地->Arid  道路->Road  宇宙空間->Space
     雪原->Snow  ビル街->City                        (69 instances)
   THIS IS A PROBE: if the panel shows "Arid", the hypothesis is confirmed
   and the rest of the vocabulary follows (candidate list dumped to
   analysis/mapmodel_jp_names.json - 1,111 distinct names seen >=2 times,
   most of them binary false positives that must NOT be touched).

Build: "SRWZ v0.8.45.chd".

## 0.8.44 (2026-08-21) - sixth strip variant + Regen labels

User screenshot (deploy/terrain panel): the two-row strip was still kanji
with a white "Fo" correctly aligned over 集 - i.e. the 0.8.43 alignment fix
works, but that panel draws variant [5] and STRIPS only listed five.
The variant table at 0x42C220 has SIX entries: [0]/[1] plain 16, [2]/[3]
with the "/" separator, [4]/[5] two-row (newline after the 8th). Added
0x442620. Verified exhaustively rather than by eye: a regex sweep for any
run of >=4 spirit kanji anywhere in the ELF now returns ZERO, and runs of
private codes returns 8.
LESSON (again, cf. the 20 'Armor' copies): never trust the first table -
sweep for the rest.

Also, terrain-effect panel: "HP Regen"/"EN Regen" collided with their own
+-0% value -> "HP Reg"/"EN Reg", BOTH copies of each (0x4421A0/0x4421B0
and 0x4444B8/0x4444C8 - one label table per screen, as usual).

Noted for later: the terrain NAME on that panel (荒地) is not in the ELF,
COMPDATA or MTV_PROS - a raw image scan finds it from LBA ~1655372
onward, i.e. in the per-map data past MAPNAME, many copies. Translating it
means touching map records, not a label table.

Build: "SRWZ v0.8.44.chd".

## 0.8.43 (2026-08-21) - white spirit overlay aligned (our own space hack)

User screenshot: the white "Fo" sat on top of the gray "Wa", one cell to
the left. Not a glyph problem - the PANEL draws two strings on the same
origin:
  gray  = the full strip (0x4425C0, the "/" variant, drawn via the 2-D
          accessor at 0x35E340 -> table 0x42C220[row][col])
  white = built by 0x35E370: strcpy the strip, then overwrite every slot
          the pilot does NOT have with the character at 0x42C268, and when
          the split applies, re-join the tail through "　%s" (0x442648).
Both fillers are a FULL-WIDTH SPACE - and patch_hwfont's SADV hook
deliberately advances 0x8140 by 13 px, because that space IS our English
word space. Our spirit cells advance by the engine's constant
(*(s16*)0x70000038, read at 0x13AB78), so the white string drew short and
walked left one cell by slot 5. This was ALREADY wrong with the kanji -
the screenshot only made it visible.
FIX: mask with a BLANK PRIVATE CELL (0x85DB, 23rd glyph-table entry, art =
72 zero bytes at 0x78C110) instead of the space. 0x85DB is outside the
half-width range and is not 0x8140, so it takes the identical advance path
as the pairs - alignment holds by construction, whatever that constant is.
Both fillers repointed: 0x42C268 and 0x442648.

Confirmed while reading the panel code (worth keeping):
  - spirit bit order is 0熱 1魂 2閃 3不 4鉄 5集 6必 7加 8迅 9覚 10手 11狙
    12直 13幸 14努 15乱 16分; each strip variant omits ONE index (the
    "phantom", 16 or 13) which the builder skips WITHOUT advancing.
  - the "／" in two variants is the game's own separator between
    self/ally spirits and the enemy-targeting ones (Confuse, Analyze).
  - patch_spirit_abbrev.py is now idempotent (byte-wise strip rewrite) and
    merges into the existing backup instead of overwriting originals.

Build: "SRWZ v0.8.43.chd".

## 0.8.42 (2026-08-21) - spirit micro-glyphs, private cells

0.8.41's string patch was WRONG and the screenshot showed why: the game
paints the pilot's own spirits in WHITE over the gray full list on a fixed
24 px pitch, so the gray "Fo" and the white "Fo" no longer sat on top of
each other, and the whole strip ran off the panel (two half-width advances
are 26 px, not 24). Only a full-width CELL can hold the pitch.

tools/patch_micro_glyphs.py (supersedes patch_terrain_glyphs.py) draws
both families through one hook:
  TERRAIN  空陸海宇水 -> AIR/GND/SEA/SPC/WTR, custom art (unchanged look)
  SPIRITS  17 pairs COMPOSED at run time from the half-width atlas -
     a kanji cell is 24 px and an atlas glyph is 12 px, so a pair needs no
     art at all, just two atlas indices (8 B/spirit instead of 168 B).
KEY DECISION - private codes, not the kanji's own cells: a master-font
cell is GLOBAL, and the still-Japanese tutorial bank writes 加/手/分/必/
集/直/不 359 times in ordinary sentences, which would have rendered as
"AcMeAn...". SJIS lead row 0x85 is unassigned, so the spirits get
0x85CA..0x85DA - just past patch_hwfont's half-width range (0x8540 +
NGLYPH 138 = 0x85CA), which means the blit hook does NOT flag them
half-width and they render as normal 24 px cells.
patch_spirit_abbrev.py now only repoints the UI: the five strip variants
and the per-record abbreviation slots (2 bytes -> 2 bytes, in place).
Va So Al Re Wa Fo St Ac Sw Aw Me Sn Di Lu Ga Co An, from this ELF's own
English spirit names. Kept from 0.8.41: 魂 -> Soul, 愛 -> Love, 絆 -> Bond
(bare-kanji record names) and the "Eff１/Eff２" weapon labels.

Storage, all 2bpp now (levels x5 = 0/5/10/15, the atlas's own format), so
one expansion loop serves both families and terrain art halved:
  ART 0x78BCD0 420 B | TABLE 0x78BE80 22 x 8 B | CODE 0x78BF40 456 B
  256 B cave spare.  Table row = [code u16][nrows u8][row0 u8][loff u16]
  [roff u16], offsets relative to ATLAS_VA.
VERIFIED BEFORE BUILDING by simulating the emitted MIPS (scratchpad
simglyph.py: a small interpreter for the ~20 opcodes used) against the
shipped cave bytes - all 22 cells byte-exact vs an independent expansion,
unlisted codes fall through untouched in 165 steps, and the rendered
cells were dumped to PNG and eyeballed. Worth reusing: this is much
cheaper than a build-and-boot cycle for cave code.

Build: "SRWZ v0.8.42.chd".

## 0.8.41 (2026-08-21) - spirit abbreviations as STRINGS (superseded by 0.8.42)

The spirit strip is a plain ELF STRING, not font-rendered art - no hook,
no glyph atlas needed. Five variants live at 0x442530..0x4425F0 (with and
without a full-width slash / a newline after the 8th), and each spirit's
record at 0x3FA290 (stride 0x10 = [name, kanji, desc, ?]) points at its
own 2-byte abbreviation slot.

KEY MEASUREMENT: two half-width cells (12 px each) are exactly one
full-width kanji (24 px). So a capital+lowercase pair - which is what the
modern SRW games print, per the user's reference screenshot - keeps BOTH
the byte length and the pixel width. Pure in-place string patch.

  Va Valor   So Soul    Al Alert   Re Resolve  Wa Wall
  Fo Focus   St Strike  Ac Accel   Sw Swift    Aw Awaken
  Me Mercy   Sn Snipe   Di Direct  Lu Luck     Ga Gain
  Co Confuse An Analyze
Shared slots stay shared, as in the original: Attune reuses St, Bless
reuses Lu, Cheer reuses Ga. 魂's record aliased its name AND kanji field
to one 16-byte slot, so the slot was split ("So" + "Soul" at +4) and the
record's name pointer repointed. Also translated the two other bare-kanji
names: 愛 -> Love, 絆 -> Bond.
tools/patch_spirit_abbrev.py (--revert via analysis/spirit_abbrev_jp.json).

WHY NOT the terrain-glyph technique the user asked about: art for 17
kanji is 17 x 168 B and the cave has 180 B free with the ELF unable to
grow (it ends at LBA 2150, the next file starts at 2151). Only a 2bpp
letter-composer would have fit - far more code and a worse result than
letters the font already draws.

Also: weapon screen "Effect １/２" ran into the effect name (user
screenshot), shortened to "Eff１/Eff２" - digits stay FULL-WIDTH because
0x2E-0x3D are control bytes to this renderer. tools/patch_elf_labels.py.

Build: "SRWZ v0.8.41.chd".

## 0.8.40 (2026-08-21) - combo-attack label; class labels deliberately skipped

Swept the WHOLE ELF for code-built JP text (scan every lui/ori/addiu
immediate, decode as an SJIS pair, group runs <= 0x30 apart): 173 hits,
almost all false positives (constants that happen to decode as rare
kanji). The real cluster is 0x390060-0x3902A0:
  0x39026C 合体攻撃  -> "Combo"   DONE (sw v1,48 / sw v0,52 / sw s0,56;
     s0 is NOT immediate-built, so the NUL goes inside word 2 and the
     uncontrolled third store lands harmlessly after the terminator)
  0x390290 通常攻撃  SKIPPED - only one immediate word before an
     uncontrolled sw s0,52; no way to place a terminator without adding
     instructions.
  0x390078 格闘武器（　　） / 0x3900D0 射撃武器（　　）  SKIPPED - written
     with unaligned swl/swr pairs into +0x0E..+0x1E, and the fullwidth
     spaces inside the parens sit at fixed byte offsets that another
     routine may fill in. ASCII would shift those slots.
Both skips need a proper trace of who writes into those buffers before
they are safe to touch.

Build: "SRWZ v0.8.40.chd" (local only + MEGA upload of 0.8.39 in flight).

## 0.8.39 (2026-08-21) - weapon effect names (code-built again)

User screenshot: weapon screen "Effect 2: バリア貫通". The string is on no
part of the disc - raw scan, COMPDATA, NISVDATA, HSFC, all MTV_*/ZKN_*
(at their RELOCATED LBAs - an early sweep read stale copies), STAGE: all
negative. It is assembled in CODE, same trick as 空専用/陸専用:
  0x390B18  サイズ補正無視  lui/ori pairs -> 4 sw at +300..+312 (16 B)
  0x390B78  バリア貫通      lui/ori pairs -> 3 sw at +300..+308 (12 B)
tools/patch_effect_strings.py rewrites the immediates to spell ASCII
(NUL-padded, letters+space only - 0x2E-0x3D are control bytes here):
  バリア貫通 -> "Pierce", サイズ補正無視 -> "Ignore Size".
FINDING METHOD (worth reusing): scan every lui/ori/addiu immediate in a
code window and decode it as a 2-byte SJIS pair - the characters show up
as immediates even though the string never appears contiguously. The
first attempt missed them by testing only single-char byte order; these
constants pack TWO characters per 32-bit word, so both halves must be
matched.

Build: "SRWZ v0.8.39.chd" (local only).

## 0.8.38 (2026-08-21) - dialogue actually fits the box now + menu widths

User screenshot: a relayout row clipped on the RIGHT. My 0.8.14 fix only
addressed HEIGHT (4 lines -> 3) and re-wrapped at 37-40 columns; the
over-map dialogue box is ~33-34. Evidence: 98% of untouched rows are
<= 34 chars with a hard cliff there (11,982 rows sit exactly at 34).
Re-fitted ALL 478 relayout rows to 3 lines x <= 34 cols. Auto-rules only
solved a handful, so ~470 lines were hand-trimmed ~10-15 chars each with
the meaning kept (analysis/relayout_short_en.json). Verified: max body
width 34, max body lines 3, zero overflow.
MENU WIDTHS (COMMAND list caps at 10 chars - "Objectives"/"Quick Save"):
  Battle Report -> Battle Log, Mass Formation -> Mass Form,
  Allies／Enemies -> Ally/Enemy (3 ELF strings), Chain Attack -> Chain Atk.
SEARCH SCREEN: tabs Abilities -> Ability, Squad Bonus -> Sq Bonus;
descriptions "<Searches for owners of...>" -> "<Find owners of...>";
untranslated button prompts ：決定/：選択/：検索/：戻る/：切換 -> OK/Select/
Search/Back/Switch (the fullwidth colon cost 2 bytes and blew the 8-byte
slot, so it was dropped - the button icon precedes them anyway).
TOOLING: patch_compdata now runs a LATE UI pass (re-applies the offset
table after the JP->EN text passes), because those passes rewrite e.g.
特殊能力 -> "Abilities" globally and were clobbering the narrow-tab fixes.

Build: "SRWZ v0.8.38.chd" (local only).

## 0.8.37 (2026-08-21) - undo the old byte-fit compression

User asked whether any voice lines had been budget-tightened. YES: the
old tools/srvc_bytefit.py shortened lines to fit byte budgets and wrote
the results straight back into analysis/srvc_en.json with NO log, so
there is no flag to look up - the damage has to be found statistically.
Measured EN/JP character ratio over 22,316 paired lines: median 1.75
(healthy), only 78 lines below 1.0 and 678 below 1.2. Reviewed all 78:
most are legitimately short battle shouts; 40 had lost real meaning and
were expanded (analysis/caption_terse.json holds the shortlist).
Also caught by the same pass: "Raben" -> "Reeven" in 37 lines and
"Kiel" -> "Kihel" (the project canon); "Marine Cutter/Missile/Beam" are
Kapool weapons, NOT the pilot Marin - left alone.
NOTE for future audits: ratio < 1.2 still holds ~600 mildly terse lines
if a deeper pass is ever wanted.

Build: "SRWZ v0.8.37.chd" (local only).

## 0.8.36 (2026-08-21) - caption phrasing (no more needless compression)

User: why "A kid with little real combat experience..." instead of
"So I'm up against a kid with little real combat experience...!"?
Correct - captions have had NO byte budget since the srvc_apply rebuild
path (offsets are recomputed, the file relocates); the ONLY limit is the
display box, ~46 columns x up to 3 lines. Old terse habits came from the
in-place byte-budget era.
RULE: translate captions naturally and completely; check each line is
<= 46 chars, do not compress for length.
Re-worded 187 / 26 / 2486 / 1028 / 889 accordingly.

Build: "SRWZ v0.8.36.chd" (local only).

## 0.8.35 (2026-08-21) - terrain micro-glyphs, take 2

Re-applied tools/patch_terrain_glyphs.py on the repaired ELF. The 0.8.32
crash is now attributed to the five stubs my cleanup wiped (fixed in
0.8.34), NOT to the BHOOK trampoline - the live PINE stamp of the same
art had already rendered correctly on the intermission screen.
Pre-build state verified explicitly: underline/linkpos/advance/flushA/
backlog stubs + both caption caves non-zero, terrain art re-rendered from
the ISO (545 inked pixels, reads AIR GND SEA SPC WTR), dead-jump audit
clean (now part of verify_elf_patches.py).
If this build crashes, the trampoline IS the problem and the next design
is the per-cell decoder hook at 0x1C6C40.

Build: "SRWZ v0.8.35.chd" (local only).

## 0.8.34 (2026-08-21) - REPAIR: wiped cave stubs restored

0.8.33 still crashed (on OPENING the load screen, not on loading). Cause
was NOT the terrain hook: while relocating the terrain art I ran a
"clear our region" step over 0x78B920-0x78C000, which also erased FIVE
unrelated stubs living there - underline (0x78B960), linkpos (0x78B9E0),
font-advance (0x78BA60), flush-path-A (0x78BAC0), backlog convcopy
(0x78BAF0). Their hooks still jal'd into zeros -> jump into dead memory
as soon as text with those features drew.
Recovered the exact 0x6E0 bytes from iso/srwz_corridor2.bin (same ELF
generation, verified by an anchor hash of the preceding atlas tail), then
re-ran patch_caption_paging for the two newer caves.
NEW SAFETY CHECK (run before every build from now on): scan all jal/j
targets in the main image that point into the cave and assert the target
word is non-zero. 11 entry points today, none dead.
LESSON: the cave is shared by SIX patches. Never blanket-zero cave space;
consult the CAVE MAP in memory and only touch your own range.

Build: "SRWZ v0.8.34.chd" (local only).

## 0.8.33 (2026-08-21) - terrain trampoline REVERTED (crash)

0.8.32 crashed PCSX2 when loading a save. The BHOOK trampoline is backed
out (patch_terrain_glyphs.py --revert restores BHOOK's displaced lui/lhu;
art+code are left in the cave, unreferenced and harmless). Caption fixes
from 0.8.32 are kept.
CRASH THEORY (to test next): the stamp writes 288 B at
font_base + cellindex*288, and 陸 alone is +1,245,312 B. Live PINE
stamping worked on the intermission (buffer was big enough there), but
the master-font buffer is a HEAP allocation whose size may differ per
scene - on the save/load screen the write likely lands outside it and
smashes the heap. Safer designs to try:
  (a) hook the per-cell DECODER (0x1C6C40) instead - it receives the
      game's own destination pointer, so the address is always valid;
  (b) sanity-gate the write (font ptr in EE range AND cell offset below
      an observed maximum);
  (c) give up on kanji cells and use private half-width codes with a
      renderer-side double-width flag.

Build: "SRWZ v0.8.33.chd" (local only).

## 0.8.32 (2026-08-21) - terrain micro-glyphs PERMANENT + caption fixes

TERRAIN (the SRW-30 look, now shipped): tools/patch_terrain_glyphs.py
stamps AIR/GND/SEA/SPC/WTR art into the master-font cells of 空陸海宇水.
  - trampoline: BHOOK+0 -> j TERR, BHOOK+4 -> nop; TERR compares the
    pending glyph code (0x70000060) against the 5 kanji, blanks the
    288-byte cell and copies 168 B of art into rows 8..21, then
    re-executes BHOOK's displaced lui/lhu and jumps to BHOOK+8.
  - no jal (ra untouched), only t0-t8 clobbered before BHOOK re-reads.
  - art 5 x 168 B at 0x78BCD0, cell-offset table at 0x78C018, code at
    0x78C038; cave PT_LOAD grown 0x1CE0 -> 0x2198 (max without resizing
    the ELF file). NOTE: 0x78B920-0x78BCC8 is the CAPTION PAGING caves -
    a first attempt overwrote them; patch_caption_paging.py now accepts
    the grown fsz and must be re-run if this patch is ever re-applied.
CAPTIONS (user spot-check): 実戦経験の少ない子供 was "A kid with no real
combat..." (dropped "experience", and 少ない = "little", not "no") ->
"A kid with little real combat experience...!"; 「シャアか？違う…！こいつは！」
tightened; Psycommu spelling. Em-dash U+2014 is NOT cp932-encodable -
use "..." instead (srvc_apply raises on it).

Build: "SRWZ v0.8.32.chd" (local only).

## 0.8.31 (2026-08-21) - movement Type strings finally fixed (code-built)

Why 陸専用 survived every pass: it is not a string at all. Two code sites
BUILD it from immediate constants and store it with unaligned swl/swr:
  0x389400  lui v0,0xEA90 / ori v1,v0,0xF38B (= 空専) / addiu v0,0x7097 (= 用)
  0x389420  same, ori 0xA497 (= 陸専)
Patched the immediates to spell ASCII instead (6 bytes max per site, the
last 2 via the addiu): 空専用 -> "Air", 陸専用 -> "Ground".
Also found MORE copies of the movement-type table (0x43E8D0, 0x43EA30)
beyond the three fixed in 0.8.29 - consistent with the per-screen table
duplication lesson.
STILL RAM-ONLY: the AIR/GND/SEA/SPC/WTR terrain micro-glyphs. Permanent
version needs a new branch in BHOOK (tools/patch_hwfont.py) that stamps
ARBITRARY kanji cells - cell = FONT + ((lead-0x81)*192 + trail-0x40)*288,
fullwidth art at 6 B/row x 24 rows (144 B/glyph, 5 glyphs = 720 B) - plus
add_ptload() can grow the cave, so space is available. Deferred: BHOOK is
the renderer's most fragile hook and deserves a fresh session + live test.

Build: "SRWZ v0.8.31.chd" (local only).

## 0.8.30 (2026-08-21) - label collisions fixed in ALL copies

0.8.29 shortened Armor/Squad in ONE table; the user's next screenshot
still showed the collisions. Root cause is the same redundancy that hid
陸専用: the ELF carries a separate label table per screen layout - 20
standalone 'Armor', 25 'Squad', 5 '(Squad)'. All shortened to Arm / Sq
(shortening can never break a layout, so blanket-patching is safe here).
RULE going forward: for ELF UI labels, always patch EVERY standalone
copy, never just the first hit.

Build: "SRWZ v0.8.30.chd" (local only).

## 0.8.29 (2026-08-21) - unit screen labels + movement types

From user screenshots:
- 'Armor'->'Arm', '(Squad)'->'Sq' (0x445E58 / 0x445E38): both collided
  with their numeric values.
- Movement-type strings: user correctly noted 専用 = "only", not "use".
  Found THREE partially-translated copies of the same table in the ELF
  (0x43E750, 0x43FAA0, 0x4443B0) - different code paths read different
  copies, which is why 陸専用 survived earlier passes. All normalized:
  AirOnly / GndOnly / Air/Wtr / Air/Sea.
  KEY LESSON: the unit records that hold these strings are built at MAP
  LOAD, so live ELF edits do not change an open screen - a reboot is
  required to verify.
TERRAIN MICRO-GLYPHS (live-tested, NOT yet permanent): AIR/GND/SEA/SPC/
WTR art stamped into the master-font cells for 空陸海宇水 via
tools/stamp_terrain_glyphs.py (PINE; cell = FONTBASE + ((lead-0x81)*192
+ trail-0x40)*288, FONTBASE = u32 at 0x46E3A8). User approved the look.
To ship: extend the setText stamper cave to cover these 5 cells (needs
~1440B art + a table loop; cave free space is only ~1080B, so the cave
PT_LOAD must grow into the ELF file tail at 0x34F020).

Build: "SRWZ v0.8.29.chd" (local only).

## 0.8.28 (2026-08-20) - caption quality pass (user-prompted)

User worried about caption quality after 3-line spot check. Proper random
sample (100 correctly-paired lines via srvc_work.json): ~2% real errors,
~4% awkward - far better than feared. Heuristic shortlist (over-short EN,
placeholders, name typos) found the real systemic bug: 79 lines where
DeepSeek returned NOTHING (EN = "..."/"
") - all filled by hand (the
entire Edel Bernal final-battle callout set, Cynthia/Overdevil lines,
Sand Rats, ship-crew barks). "Eder"->"Edel" in 17 lines. 4 awkward lines
from the sample rewritten. Applied via the FULL pipeline for the first
time since v2.00 (srvc_apply rebuild - no byte budgets - then polish/
kagi/line-fixes; SRVC grew to 1624 sectors, tools' extents bumped).

Build: "SRWZ v0.8.28.chd" (local only).

## 0.8.27 (2026-08-20) - caption corrections from user review

User flagged three battle captions; JP cross-check via index-aligned
fields against srwz_jpall.bin (new technique - the relocated SRVC's
offsets drift but field ORDER matches):
- 了解、牽制しておくわ！ -> was "I'll hold back." (meaning inverted;
  kensei = suppress the enemy) -> "Roger, covering fire!"
- 悪いけど…いただきっ！ -> was "Sorry, but…
mine!" (over-clipped) ->
  "Sorry…
I'll take it!" (both occurrences)
- [JP source line, 40 columns] -> "Emaan's devices, no matter
  how many!" verified FAITHFUL (JP dangles identically) - kept.
Speaker 桂 in captions comes from the COMPDATA pilot table - already
"Katsura" since 0.8.24 (user was on an older build).
tools/srvc_line_fixes.py holds the corrections (idempotent, extent-safe).
SRVC caption sweep result: zero JP lines remain in the live bank.

Build: "SRWZ v0.8.27.chd" (local only).

## 0.8.26 (2026-08-20) - Sound Select menu translated

All 640 JP fields in the Sound Select tables (COMPDATA 0x6EC00-0x71C40):
61 BGM titles (romaji per fan convention, budget-trimmed variants for
tight 7/15-byte slots) + 579 voice-list entries (185 base names romanized
in tools/soundsel_names.py, variant suffixes S/E/D/2... kept, -teki ->
"(E)"). Generator: analysis/soundsel_en.json; applied by a new
offset-guarded menu-encoded pass in patch_compdata (verifies JP bytes at
each offset before writing - drift-safe). Zero NO-FITs.
NEXT QUEUED: ?-button key-guide overlay strings (0x7CE00-0x7D5xx:
戻る/発進/再生/切換え/設定終了...), skill-condition fragments (0x7E200+:
反撃時/格闘武器/地形適応...), ability category names (0x74350+).

Build: "SRWZ v0.8.26.chd" (local only).

## 0.8.25 (2026-08-20) - Chiram Sldr + sound-select survey

Map popup showed pilot チラム兵 - added "Chiram Sldr" to PILOTS (matches
Titans Sldr convention). Decompressed-COMPDATA sweep (new technique -
earlier sweeps scanned the compressed blob) found the remaining JP:
Sound Select voice list (~300 katakana pilot names incl -テキ enemy
variants, 0x6F600-0x71C00), ~20 BGM titles (0x6EC40+), scattered UI verbs
(決定/戻る/外す/切換え/発進...). All queued for a dedicated batch.

Build: "SRWZ v0.8.25.chd" (local only).

## 0.8.24 (2026-08-20) - pilot name Katsura

Unit status screen showed pilot 桂 (Orguss) untranslated - added to
PILOTS in compdata_en.py (dialogue already used "Katsura" throughout),
reran patch_compdata (1162 pilot fields). Known JP still on that screen,
parked: the one-kanji spirit-command strip (熱魂閃... - 1-char cells,
same problem class as terrain kanji) and the 空陸海宇 terrain letters
(user vetoed 2-letter abbreviations; awaiting micro-glyph font work).

Build: "SRWZ v0.8.24.chd" (local only).

## 0.8.23 (2026-08-20) - recap panel render fix (first no-TEST build)

0.8.22 recaps rendered broken: the Info panel uses the caption-family
renderer, so ASCII '.' (0x2E) is a LINE-FEED control ("Moonrace." split
the line and overprinted row 3), and the panel is ~30 ASCII columns wide
(JP got 24 fullwidth cells) so 48-char lines ran off the edge.
Fix in patch_hsfc_recaps.py: wrap at 30 width-units (fullwidth=1.35),
encode ./,-:/digits as fullwidth SJIS; all 106 recaps rewritten to <=88
units (analysis/hsfc_recaps_en.json). Save-list header 'Stage'->'Ep.'
(was touching 'Turns'). Naming: per user, no more TEST suffix.

Build: "SRWZ v0.8.23.chd" (local only).

## 0.8.22 TEST (2026-08-20) - save screen: recaps translated + labels

User save/load screenshots: gold labels turned out to be TEXT (the ELF
table at 0x445D58, translated long ago) - the JP screenshot was from an
old build. Fixed the EN label collisions: Scenario->Stage, SR Point->
SR Pts, 0x445DA8 'Stage '->'Ep.', ' eps cleared'->' cleared'.
The synopsis paragraph: episode-recap bank found in HSFC.BIN rec0
(LBA 1568541) - 208 slots x 150B, three 48B+2NUL lines each; needles
spanning the 48-byte line breaks had defeated every prior search (the
save state + RAM gap-search cracked it). All 106 unique recaps freshly
translated (analysis/hsfc_recaps_en.json), 185 slots filled incl the
developer easter-egg placeholder ("contact Shiraishi"). Rebuilt via
tools/patch_hsfc_recaps.py (self-healing from pristine JP), blob
8588/9584. stamp_build now fingerprints HSFC.

Build: "SRWZ v0.8.22 TEST.chd" (local only).

## 0.8.21 TEST (2026-08-20) - harvested labels rolled back

User verdict on the 0.8.20 harvested letters: "it does not look good"
(they had assumed a real font existed; the 13px harvested caps read too
small next to BS.). Bar labels repainted with the v4 graded-outline
Georgia renders (0.8.19 style: EP / Funds / SR Points, baseline-aligned).
harvest_labels.py kept in tools/ for reference but NOT in the build
pipeline. Everything else unchanged from 0.8.20.

Build: "SRWZ v0.8.21 TEST.chd" (local only).

## 0.8.20 TEST (2026-08-20) - glyph-harvested bar labels

User suggestion: copy the ASCII from the same art source as "BS." instead
of rendering a PC font. There is no font file - but KVMDATA p04 carries
the same hand-drawn serif family in enough caps to spell the labels:
tools/harvest_labels.py cuts letters (outline+shadow included) from
"SIZE LMS UP MOON / TR I" (primary), D from "HARD", F from "FORMATION",
and composes EP / FUNDS / SR POINTS into the p05 cells (baselines tuned
live: EP bottom 24, FUNDS 22, SR POINTS 62; FUNDS at -2 spacing to fit).
p04/p05 CLUT tint differences render the gold accents correctly.
Supersedes the Georgia renders for these three cells (run harvest AFTER
patch_intermission_labels in rebuilds). Verified in-game via PINE.

Build: "SRWZ v0.8.20 TEST.chd" (local only).

## 0.8.19 TEST (2026-08-20) - graded label outlines (v4)

User asked for the JP glyphs' outline treatment on the EN labels. v4
renderer: fill(15) -> light inner AA(11) -> dark outline ring(8) ->
shadow(4), the layer structure sampled from the JP art. Applied to the
p05 status-bar labels (EP / Funds / SR Points); verified live - weight
now matches BS. Marquee remains Japanese (0.8.18 rollback) and displays
the JP-band-anchored EN card titles correctly (the 0.8.17 "dim/missing"
sightings were the marquee's fade animation mid-frame).
Georgia Bold rationale recorded: serif matches Mincho sheets, designed
for low-res screens, bold survives 4bpp quantization; any user-supplied
TTF can swap in per cell.

Build: "SRWZ v0.8.19 TEST.chd" (local only).

## 0.8.18 TEST (2026-08-20) - marquee rolled back to Japanese

User verdict on the EN ticker: "I don't think you can make it look good" -
p10 ticker sheet (第 話 「」 までクリア！ 出撃 小隊) restored to the JP
originals from analysis/kvm_labels_jp.bin. The p05 STATUS BAR labels stay
English (EP / Funds / SR Points, baseline-aligned - user approved).
patch_intermission_labels.py now ships p05 cells only; the p10 cell specs
remain commented in intermission_hotpatch.py for future custom-font tries
(user offered to supply a TTF - renderer accepts any font file).
Title cards unchanged from 0.8.17 (32px, JP band). Verified live via PINE.

Build: "SRWZ v0.8.18 TEST.chd" (local only).

## 0.8.17 TEST (2026-08-20) - baseline alignment + JP-band title cards

Live PINE iteration round 2 (user save state):
- render v3: BASELINE-anchored cells (JP glyphs sit on the cell floor, not
  centered). Funds/EP/SR Points now share the adjacent numbers' baseline;
  SORTIE/SQUAD switched to CAPS (descenders would clip the 16px cells),
  explicit pt + baseline 14 matching the NEXT. glyphs (measured rows 30-43).
- Title cards: JP card ink occupies rows 4..27 of the 512x64 texture (top
  band, NOT centered); the ticker samples exactly that band. All 107 cards
  re-rendered at 32px with baseline anchored to row 26.
- KEY finding: hot-writing the PRISTINE JP card showed the ticker title is
  drawn DIM by design (dark modulation) - the earlier "big bright title"
  was the centered 46px render bleeding BELOW the sampled band, drawn
  unmodulated. The anchored render restores authentic JP ticker behavior.

Build: "SRWZ v0.8.17 TEST.chd" (local only).

## 0.8.16 TEST (2026-08-20) - intermission font polish + 40px title cards

User feedback on 0.8.15 (with save state for live testing): Funds/Ep too
small vs BS., Sortie/Squad small, episode title in ticker too big.
Iterated LIVE over PINE against the running game (hot-writing KVM page
cells in EE RAM at p05=0xC5A9E0, p10=0xDC2800/0xDCAAF0, card=0xDBE680,
screenshot loop): render v2 = full cell height + horizontal squeeze with
per-cell floor + stroked outline (tools/intermission_hotpatch.py; the
shipping patch_intermission_labels.py delegates to it).
Ticker title identified as a blit of the VT1 card texture -> cards
re-rendered at 40px (was 46) matching the JP kanji height; card screen
keeps proportions, ticker/preview shrinks ~13%.

Build: "SRWZ v0.8.16 TEST.chd" (local only - no MEGA per user).

## 0.8.15 TEST (2026-08-20) - intermission bar / episode ticker kanji

User intermission screenshot: 第16話／139Turns bar, 資金．/SRポイント．
labels, 第16話「 ticker still JP. Root cause found: these are TEXTURE ART
in KVMDATA.BIN word-sheets (4bpp TIM2 pages, CLUT-index glyphs) - the same
sheet family as the bazaar buttons. No string exists anywhere on disc for
第N話 (exhaustive raw/packed/immediate scans all empty) because the game
composites it from these glyph cells + the serif digit strip on the
intermission page. tools/patch_intermission_labels.py paints:
  p05 (0x28B40): 第->Ep, 資金．->Funds, ＳＲポイント．->SR Points
  p10 (0x52070): 第->Ep, 話->blank, までクリア！->cleared!,
                 出撃->Sortie, 小隊->Squad
JP originals saved for --revert (analysis/kvm_labels_jp.bin).
THEORY under test: the chapter title card's 第５話 line composits from the
same cells (RAM strip "0123456789第話"), so it should now read "Ep 5".
stamp_build.py now fingerprints KVMDATA. ELF unchanged.

Build: "SRWZ v0.8.15 TEST.chd" (full CHD to MEGA).

## 0.8.14 TEST (2026-08-20) - 4-line dialogue relayout (new 3-part version scheme)

User request: dialogue boxes showing 4 rows of text (box caps at 3). 478
speakered T rows had 4-5 line bodies; all now fit 3 lines: 346 re-flowed at
box width (greedy wrap, first width in 37..40 that fits), 132 tightened by
hand (meaning-preserving trims, analysis/relayout_short_en.json) then
wrapped. Ships as analysis/relayout_en.json, merged LAST into KEEP_OVR /
TIGHTEN_ALL in restore_full.py so it wins over passthrough. Full STAGE
rebuild (110 min - compress cache invalidated for ~130 records).
Also: version scheme change per user - 3 parts from now on (0.8.14 follows
0.8.1.13).

ELF unchanged from 0.8.1.13. Build: "SRWZ v0.8.14 TEST.chd" (full CHD to
MEGA - user is home; no delta needed).

## 0.8.1.13 TEST (2026-08-20) - episode-marker kanji (title card 15)

User: title cards confirmed WORKING on 0.8.1.12; asked for the remaining
stage kanji. The 第15話 line is runtime-COMPOSED from lone label strings in
the ELF (the RAM strip "0123456789第話" is a glyph cache of digits + those
labels; no such strip texture exists in VT1 - scanned, only the 107 cards).
tools/patch_ep_labels.py:
  0x445DA8 第 -> "Stage "   0x445CD8 話 -> ""   0x4453F8 話／ -> ／
  0x441F50/60 第%s話『%s』に/を -> "Ep.%s: '%s'"
All sit in already-English label tables (Funds/Info/SR Point/Turns), so
ASCII is proven safe there. verify_elf_patches.py extended with 3 checks.
Risk noted: if the strip compositor uses fixed-width glyph cells, "Stage "
may clip - needs user eyeball on the next chapter card.

Build: "SRWZ v0.8.1.13 TEST.chd"; delta v0.8.1.2 -> v0.8.1.13.

## 0.8.1.12 TEST (2026-08-20) - title cards fixed FOR REAL (offset bug)

0.8.1.11's "back-to-back streaming" theory was WRONG. Root cause found by
diffing the game-decompressed ch1 card in RAM against the bank record: only
16/16384 pixel bytes differed (RAM scribble in two blank rows) - so the bank
IS the source and the exact-size repack should have worked... unless the game
never read my stream from its start. It didn't: records begin 16-BYTE ALIGNED,
and the original bank scan had recorded each record's start at the end of the
previous stream, i.e. INCLUDING 0-12 bytes of zero padding (zeros parse as
harmless varint chunks in the Python decoder). Both painted builds wrote
streams up to 12 bytes early; the game seeks to the aligned offset and landed
mid-stream -> noise, identical garbage regardless of pixel content.

Fix: analysis/vt1_bank_true.json (16-aligned true offsets, all verified);
patch_titlecards.py now restores the PRISTINE bank region from
iso/srwz_alldlg.bin then splices each stream at its true offset, zero-padding
tails. compress_exact retired - slots are indexed, not streamed - and only
plain compress_record constructs are used (0.8.1.11's zero-ref filler groups
appear nowhere in the original corpus; hardware behavior unproven).
stamp_build.py now fingerprints VT1 (title bank was previously invisible
to --diff). ELF unchanged.

Build: "SRWZ v0.8.1.12 TEST.chd"; delta v0.8.1.2 -> v0.8.1.12.

## 0.8.1.11 TEST (2026-08-20) - title cards actually fixed

The painted title cards showed as GARBAGE in-game (user ch1 screenshot):
the card loader streams the VT1 records BACK-TO-BACK - the next record is
found wherever the previous compressed stream ends, so my shorter streams
derailed every following texture. All 107 records repacked to their EXACT
original stream lengths via compress_exact (greedy prefix + split literal
tail that consumes precisely the remaining bytes; the greedy encoder's
final group omits its nref varint when relying on the early total-break,
so each split is roundtrip-validated). rec98 ('Memories'-slot) re-rendered
one AA step simpler to fit its 1433-byte target. Full sequential-walk
check reproduces the original record boundaries byte-for-byte.

Terrain header: Ai/Gr/Wt/Sp experiment REVERTED to 空陸海宇 (user verdict:
abbreviations read poorly at PS2 resolution). Proper fix queued: micro
"AIR/GND/SEA/SPC" glyphs drawn into the font itself, pending the font-
location hunt (new attack vector via the dynamic font cache).

Build: "SRWZ v0.8.1.11 TEST.chd"; delta v0.8.1.2 -> v0.8.1.11.

## 0.8.1.10 TEST (2026-08-20) - caption kagi + idiom audit

- Battle voice captions: ASCII "quotes" -> 「」 (56,023 fields; matches the
  dialogue box style; JP data used 0x8175/76 natively so renderer-safe).
  5,179 zero-padding fields keep ASCII quotes (render fine; wording-trim
  candidates later). tools/patch_srvc_kagi.py.
- Idiom proofread: scanned all stage dialogue against a 50-idiom JP list -
  60 hits, 51 already idiomatic (DeepSeek did well), 9 fixed via
  passthrough_en.json: Bradman 棚に上げて nuance ("And you dare lecture
  us!"), 尻に火 de-literalized ("feeling the heat"), 頭が上がらない x2
  ("under his/your sister's thumb"), Amuro's trimmed "hypocrite" line,
  Teraru->Terral + ".." punctuation, 背水の陣 restored ("backs to the
  wall"), 頭に血 ("Cool your head!").

Build: "SRWZ v0.8.1.10 TEST.chd"; delta v0.8.1.2 -> v0.8.1.10.

## 0.8.1.9 TEST (2026-08-20) - GINN objective + spirits nudge + build gate

- Stage-8 objectives: "Jin Hi-Maneuver Type 2" -> "GINN High Maneuver 2"
  (matches the unit list; user memory-report; both objective + failure
  lines, rec10, fits budgets 40/48 and 49/64).
- Level-up spirits column: fixed offset -30 instead of 0 (0.8.1.8 sat a
  bit right of the column; -30 = the original correct Strike position).
- tools/verify_elf_patches.py: asserts every ELF hook/cave/label word
  before builds - added after the 0x343630 word silently reverted between
  0.8.1.8 and the next session (cause unidentified; suspected lost write
  during a concurrent background build chain). RUN IT BEFORE EVERY CHD.

Build: "SRWZ v0.8.1.9 TEST.chd"; delta v0.8.1.2 -> v0.8.1.9.

## 0.8.1.8 TEST (2026-08-20) - level-up popup spirits column

Spirits ('Trust'/'Resolve') drew over the Skills column: the popup builder
(~0x343298, draw-list filler 0x34C590, draw list decoded at 0x6D4Axx in
state D41A1F10) gives skills a FIXED column X but computes spirit X as
base+0x136 + a per-spirit s16 (entry+36) - JP-era centering offsets that
are garbage with English names. One-word fix (patch_lvlup_spirits.py):
addu a3,v0,v1 @0x343630 -> daddu a3,v0,zero; spirits now left-align at
their column base like skills. (May also inform the Gekkostate EXP popup
bug - same UI family, still awaiting a state.)

Build: "SRWZ v0.8.1.8 TEST.chd"; delta v0.8.1.2 -> v0.8.1.8.

## 0.8.1.7 TEST (2026-08-20) - caption punctuation is control codes

User proof (static-page display, no typewriter): captions CUT at the first
ASCII ',' or '.' - the caption renderer treats them as control codes, the
same engine convention as the menu reader. That is why the original data
used fullwidth periods; 0.8.1.6's ASCII conversion caused '"Well' /
'"Tch! To lose my pace' / bare-quote cuts, and the ~11.8k pre-existing
ASCII commas had been silently cutting lines in every build.

patch_srvc_polish v2: EN caption punctuation refolded engine-safe -
runs of dots -> single-cell ellipsis 0x8163 (also kills the wide ". . ."
look), lone '.' -> 0x8144, ',' -> 0x8143, with byte-neutral ", "/". "
collapse so tight fields convert too. 24,634 + 11,819 fields over two
passes; 70 tight multi-comma lines remain ASCII (future manual trim).

Build: "SRWZ v0.8.1.7 TEST.chd"; delta v0.8.1.2 -> v0.8.1.7.

## 0.8.1.6 TEST (2026-08-20) - caption offsets understood, SRVC polish

**Hit reactions fixed** (0.8.1.4/5 regression): the voice-sync offsets have
TWO meanings - FIELD SELECTORS picking a whole line out of the pilot's
quote block (VALID for English: srvc.build space-pads fields so field
starts are byte-identical to JP), and MID-FIELD PAGE positions (JP-only,
the original truncation bug). 0.8.1.4/5 discarded ALL offsets, so hit
reactions showed the attacker's first line. v3 cave: keep base+offset;
back-scan to the field's NUL boundary; offset AT a field start is trusted,
mid-field offsets trigger the 
 page scan (with last-page fallback).
addu sites restored to original; caves rebuilt (34 words each,
0x78BBA0/0x78BC40, fsz 0x1CE0).

**SRVC caption polish** (tools/patch_srvc_polish.py): 13,823 English
fields - fullwidth ．/… -> ASCII ./..., and 2,181 trailing literal 

stripped (each made an orphan blank/quote page). In-place, space re-padded,
SEG offsets untouched.

**斗牙 -> "Touga"** added to PILOTS (kanji name absent from every list;
his 5 plate records were the last Japanese name plates reported).

Build: "SRWZ v0.8.1.6 TEST.chd"; delta v0.8.1.2 -> v0.8.1.6.

## 0.8.1.5 TEST (2026-08-20) - caption blank-page fallback

0.8.1.4 showed BLANK captions when the EN line has fewer 
's than the JP
had voice-synced pages (Denzel Ray Pistol). Both caves now track the
current segment start (t8) and, when the scan runs out of text, re-show
the LAST page for the remaining pages instead of blanking. Caves grew to
26 words; cave2 moved 0x78BC00 -> 0x78BC20; fsz -> 0x1C80.

Build: "SRWZ v0.8.1.5 TEST.chd"; remote delta v0.8.1.2 -> v0.8.1.5.

## 0.8.1.4 TEST (2026-08-20) - caption paging, path 2

Captions still truncated on 0.8.1.2/3: there are TWO near-identical page
display paths - 0.8.1.2 hooked only the page-advance fn (0x2EA320). The
caption-START fn (0x2EA4B0, channel in s3, manager s6) computes
s0=base+JP_offset at 0x2EA644 and calls the converter at 0x2EA684; now
also neutralized + routed through cave2 0x78BC00 (s3 variant). PT_LOAD
fsz -> 0x1C00. Testing note: loading an old SAVE STATE restores the old
code - test via memory-card load / live play only.

Build: "SRWZ v0.8.1.4 TEST.chd"; remote delta v0.8.1.2->v0.8.1.4 (130KB).

## 0.8.1.3 TEST (2026-08-20) - status-plate pilot names

172 [u16 id][name] pilot records translated (the in-battle status plate
showed ロラン/ガロード/アスラン while the bare copies were English).
New pass field_replace_prefixed_whole in patch_compdata.py: WHOLE-FIELD
match plus id-high-byte<=7 guard - no SJIS trail or ASCII byte is that
small, so a kana pair can never masquerade as an id (the v1.49 スRey/
ミChiru substring failure is structurally impossible here).

Build: "SRWZ v0.8.1.3 TEST.chd"; shipped remotely as 0.8.1.2 (MEGA) +
124KB xdelta.

## 0.8.1.2 TEST (2026-08-20) - battle caption paging fixed (option B)

New version scheme: major.minor.build; 0.8.1.1 == v2.01 (same ISO, both
stamped).

**Voice captions no longer head-truncated.** Root cause: captions are PAGED
(page-advance fn 0x2EA320, channel page counter +0x54, converter 0x2EA280
turns literal 
 into 0x0A and fills the display buffer 0x5FDDB8). Each
page's start = quote_base + a per-page BYTE OFFSET computed for the
JAPANESE text - on English quotes page 2 landed mid-word ('"Target
approach!
Follow me now!"' showed 'ach!
Follow me now!"').
Fix (tools/patch_caption_paging.py): 0x2EA438 addu s0,a0,v1 ->
daddu s0,a0,zero (ignore JP offset); 0x2EA47C jal converter -> jal cave
0x78BBA0, which skips (page-1) literal "
"s in the English text and
tail-jumps to the converter. Impossible pages (JP had more pages than EN
has 
's) show the remainder/blank instead of garbage. JP quotes use the
same literal 
 convention, so untranslated lines page as before.
Found via user's remote save states + PCSX2 write breakpoints at 0x5FDDB8
(freezes: memset clear 0x19DF28 <- 0x2EBDD0; MMI strlen; fill strcpy with
pre-advanced src; renderer 0x13A390 branching on 0x0A).

Build: "SRWZ v0.8.1.2 TEST.chd". ELF changed -> new PCSX2 CRC (old save
STATES warn on load; memory-card saves unaffected).

## v2.01 TEST (2026-08-20) - English title cards + ellipsis style

**All 107 chapter title cards painted English** (tools/patch_titlecards.py):
the 第N話 cards are pre-rendered 512x64 4bpp grayscale-mask textures in a
banlz bank inside VT1.BIN (offsets: analysis/vt1_bank.json, 1:1 with the
episode-title table at COMPDATA+0x72DA0). Found by freezing a PCSX2 write
breakpoint inside the banlz decompressor (0x1C6D70; worker thread reads
src/dst from 0x46F650/0x46F658). Rendered in Georgia Bold; AA quantized to
5->4->3 gray levels until greedy compression fits each slot (full 16-level
AA compresses WORSE than kanji art - never fall into the optimal DP).
第/話 + digits line still JP (shared strip, separate source, on request).

**Ellipsis style normalized**: every dialogue fullwidth … -> ASCII "..."
(user choice); trim_fit's "..."->… byte-saver removed. 479 additional rows
now kagi-quote (their trailing … had blocked the endswith('"') check).
9 fullwidth-ellipsis bytes remain, inside the 5 perennially slot-bound
records (59/74/96/115 conservative, 137 shipped-blob - SAME as v2.00; a
false regression alarm traced to reading fallback stats mid-run).

restore_full.py now rebuilds IN-PLACE on iso/srwz_restore.bin (STAGE region
only), preserving the VT1/COMPDATA/ELF patches across rebuilds.

Build: "SRWZ v2.01 TEST.chd" (local only). Stamped v2.01.

## v2.00 TEST (2026-08-20) - full text restoration + UI fixes

**STAGE rebuilt from Japanese with FULL translations** (tools/restore_full.py):
- 7,464 budget-truncated rows healed by option-3 relocation (append + repoint
  + zero); 72,347 rows in place; 91 trimmed (no pointer ref); 0 skipped.
- tighten_en.json truncations DROPPED (relocation obsoletes them);
  namefix/passthrough quality overrides kept. M1/M2/M3/objectives/EXTRA and
  every apply_stage guard preserved.
- Game-wide kagi quotes (69,446 rows) + glossary links (107) applied in the
  same pass - including the rows the ALLDLG pass skipped because their
  closing quote had been truncated off.
- All 167 records compressed in "full" mode - no conservative fallbacks.
  strict verify: 0 problems.

**COMPDATA menu-encoding** (patch_compdata.py): raw 0x2E-0x3D in menu-drawn
strings are control codes - "Type100" rendered as "TypeDijeh" on the upgrade
screen. All name/db/ability/ambig passes now menu-encode. SHORT[百式]="Hyaku"
(8-byte slot, name cell = 0x6D0C0+unit_id*8, can never grow). 21 unit names,
3 pilot names, ability periods fixed. 6 ability texts shortened to fit their
slots menu-encoded (abilities_en.py). Captain/leader bonus strings rewritten
<= 18 cols/line (the pilot-screen panel CLIPS, not wraps - "Adjacent allies
vs Gaizok" lost its "Gaizok"); Datenshi -> Shadow Angels; series/glossary
pass range extended to 0x72270 (7 terms had stayed Japanese).

**Texture/label fixes**: bazaar 購入/売却 repainted Buy/Sell in KVMDATA.BIN
word sheet (patch_bazaar_buttons.py); vertical 特殊スキル/特殊能力/強化パーツ
labels are newline-separated ELF strings - now ＳＫＩＬＬ/ＡＢＩＬ/ＰＡＲＴＳ
(patch_vlabels.py).

Build: iso/srwz_restore.bin -> "SRWZ v2.00 TEST.chd" (local only, test).
Stamped as v2.00.

## SRWZ ALLDLG TEST (2026-08-19) — game-wide 「」 quotes + glossary links
- tools/apply_quotes_links_all.py over all records with extractor data
  (base: corridor2 = corridor scene + linkpos/underline/backlog ELF patches):
  163 records converted, 52,635 dialogue rows "→「」 (blue speaker names),
  89 《》 glossary links restored per JP original (55-term dictionary),
  glossary terms de-quoted where JP unmarked; 44,936 rows in place, 7,534
  relocated (option-3, old bytes zeroed); optimal-DP compressor used for
  tight slots. Records 59/93/137 unconverted (slot-bound even in-place);
  11 records in-place-only fallback. Strict-verified all 205 records.
- Reports: analysis/alldlg_report.json (10 link misses, 73 wide-line warnings
  for later review).


## SRWZ CORRIDOR FINAL v3 (2026-08-19) — backlog fixed
- **patch_backlog.py** (live-RE'd via PINE, verified in-game): the backlog drew
  RAW record strings, and the blit consumes bytes 0x2E-0x3D as control codes
  BEFORE ASCII translation — every '.' (0x2E) acted as a newline, breaking each
  backlog row at its first period and overprinting the next row (digits would
  corrupt too). Fix: a converting-copy stub (0x78BAF0, uses the cave ASCII map)
  hooked over the backlog row-buffer copies (0x221430/44); caller's truncating
  NULs NOPed; already-converted text passes through (dialogue path unaffected).
- Also mirrors the VWF dest-width fix onto flush path A (0x13AE5C -> stub
  0x78BAC0) which patch_vwf1 had left unpatched (path B only).
- ELF patch chain is now: patch_linkpos + patch_underline + patch_backlog —
  ALL THREE required in every future build (see corridor_polish.py).


## SRWZ CORRIDOR FINAL v2 (2026-08-19) — production corridor scene + underline v2
- rec001 rows 142-211 production pass (tools/corridor_polish.py): 「」 quotes
  (blue speaker names), 《》 glossary links restored per the JP original
  (19 instances: Glory Star / Titans / AEUG incl. possessives), unmarked terms
  de-quoted, ≤37 cols × 3 lines verified; 60 rows in place, 9 relocated
  (option-3 repoint, old bytes zeroed), 16744/17024 slot, strict-clean.
- patch_underline v2 (live-tuned via PINE, user-approved): NEW half-width
  underscore glyph (private idx 69 / code 0x8585, ink = bottom row, 12px);
  decoder normal-range 69→70; advance hook relocated to 0x78BA60 with
  0x8585→advance 12 (seamless line); underline count = round(width/12);
  restore stub keeps post-link text at the TERM's end. Underline now solid,
  1px thick, slightly below the letters, ending at the term.
- patch_linkpos unchanged. Both ELF patches REQUIRED in every future build.


## LINKFIX test build (2026-08-19) — glossary-link renderer fixed
- `SRWZ LINKFIX TEST.chd` — srwz_affect.bin (option-3 corridor/in-game link test
  rows) + two NEW ELF patches, found by live PINE reverse-engineering:
  - **patch_linkpos.py**: the dialogue segment drawer advanced X by
    charcount×21 (fixed pitch) at 0x22163C, ignoring the VWF — every 《link》
    (and all text after it on the line) drifted right ~8px per preceding
    English char. Now loads the true end-X from 0x46E340. 3-instruction patch.
  - **patch_underline.py**: the link underline copied one fullwidth ＿ per term
    CHAR (21px each) — ~8px/char too long over 13px English. Stub at 0x78B920
    (cave PT_LOAD extended into the ELF's unused file tail) recomputes the
    count from the term's true pixel width.
- In-game verified (PINE hot-patch before baking): 《Glory Star》 half- and
  fullwidth render tight, colored + underlined, flush with surrounding text.
- Unlocks the glossary re-link pass: bare 《term》 is now the link format
  (no 『』 wrapper needed).
- APPLY BOTH PATCHES TO EVERY FUTURE ELF BUILD.


## Process

Before `chdman createcd`:

```
python tools/stamp_build.py <iso> <version> "<what changed>"
```

Then add an entry here. To bisect later:

```
python tools/stamp_build.py --diff v1.26 v1.44
python tools/stamp_build.py --list
```

**Never infer build contents from file mtimes.** A CHD's mtime is when the
~8-minute build *finished*; back-dating it to guess which ELF shipped sent me to
an innocent 74-byte ELF diff, while the manifest shows v1.26 and v1.27 in fact
shipped byte-identical ELFs (`93b1ce23fd01`).

## Confidence

`v1.44` onward is recorded at build time and is authoritative. `v1.25`–`v1.43`
is **reconstructed after the fact** from session history, tool state and the two
extracted images — the *direction* of each entry is reliable, exact tool
invocations are not. Only v1.26, v1.27 and v1.44 have region hashes in
`analysis/build_manifest.json`; everything else is prose.

---

## v1.52 - 2026-08-19 - narration reflowed evenly

The v1.51 rewrite reached the required line COUNT by splitting the widest line
in half, which met the viewer's constraint but read badly: rec0 bounced between
15 and 44 columns where the Japanese held a steady 40-42.

Replaced with minimum-raggedness wrapping by dynamic programming - dp[k][j] =
best cost for the first j words on k lines, a line's cost being the square of
its unused columns, last line free as in ordinary typesetting. Worst spread
across all 28 chunks fell from 37 columns to 10; lines now sit at a consistent
30-35.

Structural guarantees from v1.51 all still hold and are re-checked on every run:
exact newline count per payload (refuses to write on mismatch), no truncation,
no partial cp932 characters, width capped at the original's 44 columns.
28 of 28 chunks translated, 0 skipped. File 8,767 bytes in its 9,056-byte slot.

## v1.51 — 2026-08-18 — narration restored (`patch_mtvpros` rewritten)

All 28 prologue/interlude narration chunks are English again, with the structure
the viewer depends on preserved. **NEEDS AN IN-GAME TEST at chapter 9 -> Next
Map**, since that is the transition v1.50 fixed by reverting this file.

What the rewrite guarantees, and how each is checked before writing:
 - **Exact newline count per payload.** Every chunk is reflowed to the ORIGINAL
   line count (rec0 45, rec1 23, rec5 24, rec7 28...). The tool re-parses its own
   output and REFUSES TO WRITE on any mismatch. Verified independently: 45->45,
   23->23, 24->24, 28->28 across all 28 chunks.
 - **No truncation.** Anything that cannot fit is reported and SKIPPED, leaving
   that chunk Japanese - always safe. This run skipped 0.
 - **No partial characters.** Every payload strict-decodes as cp932, so menu
   encoding cannot leave a lead byte without its trail.
 - Line width capped at the original's 44 half-width columns.

Implementation note: narrowing the wrap width does NOT step one line at a time -
it can jump 45 -> 47 and never hit the target, which made the first attempt skip
2 chunks. The count is now reached deterministically by splitting the widest
remaining line at a word boundary.

File is 8,734 bytes and fits its original 9,056-byte slot, so no relocation.

## v1.50 — 2026-08-17 — **chapter-9 hang FIXED** (user-confirmed)

**Cause: `MTV_PROS.BIN`, the narration viewer.** Pressing Next Map after chapter
9 black-screened forever. Proven by bisection: an image differing from the
working Japanese disc by ONLY this file's 5 sectors reproduces the hang, and
restoring it clears it.

Two defects in `patch_mtvpros`, both inside the `rawt` prose payload — the chunk
STRUCTURE was byte-identical (14 records, 72 chunks, same tags and sizes), which
is why a structural check "cleared" it earlier and cost several test cycles:
 - **The viewer paginates on NEWLINES and we changed the count.** rec0's
   Japanese prose has 45 newlines, ours 40 (rec1 23->22, rec3 15->13,
   rec5 24->23, rec7 28->27). The viewer waits for a page that never comes.
 - **Long English truncates with no terminator.** Japanese payloads end with 。
   (0x81 0x42) exactly at the declared size; where English ran longer it was
   cut mid-character - rec9 @0x0406 ends 'e', rec2 @0x01C8 ends 'D'.

`patch_mtvpros.py` is marked DISABLED with the diagnosis. **Cost: the prologue
and interlude narration (28 chunks) ships Japanese again.** A correct version
must reproduce the original newline count per payload and REJECT any line that
cannot fit rather than truncating it.

Also reverted here: the v1.49 prefixed pilot-name pass. `field_replace_prefixed`
only checks that a match sits 2 bytes after a NUL - it does not anchor to the
field start, so it matched SUBSTRINGS and mangled names mid-word (ミチル ->
ミChiru, スレイ -> スRey, ビダン -> ビDan). Safe only for the narrow
enemy-designation range it was written for, never as a bulk pass over the
418 KB pilot database.

### Method note - two mistakes that cost real time

**"Same structure" is not "same content."** MTV_PROS was cleared on matching
record/chunk counts and sizes. The damage was entirely inside payloads.

**Bisect FORWARD from the working build, one variable at a time.** The first
three diagnostics each restored ONE group and left everything else ours, so a
cause in any untested group survived every run - three "still black" results
that carried almost no information. Worse, the `no-reloc` disc restored the
original file table while leaving OUR larger encyclopedia files in place, so it
read truncated data: its failure may have been the diagnostic's own fault.
Building up from the Japanese disc (jp + our STAGE; jp + our ELF/STAGE/MAPNAME)
gave clean single-variable answers immediately and found the file in two steps.
New helper: `tools/restore_region.py` backs one file out of a built ISO.

## v1.48 — 2026-08-17 — battle voice to 100%

**+108 head-truncated quotes.** These end with 」 but have NO opening 「
(`に向け集中砲火だ！」`, `ﾌカタキだっ！」`), and `srvc_work.is_quote()` requires a
leading 「 — so the entire pipeline had skipped them since it was written and
they still shipped Japanese.

Verified they are **pre-existing damage in the original file**, not caused by our
rebuild: parsing the untouched extract finds the same 142 head-truncated strings.
Most carry a stray byte where a multi-byte character was cut, so the readable
remainder was translated and the debris dropped. 92 via DeepSeek; 16 by hand
(all 16 contain the literal `\n` marker, which the model echoed back in a
different form so the reply never matched its key).

Applied through a SUPPLEMENTARY map (`build_head_map`) checked only after
`is_quote` fails, leaving the proven replacement path untouched.

SRVC now **67,334 / 67,339 (100.0%)**. The residual 5 are pure binary that merely
decodes as kanji (`諠G 如`, `蚓J!朶`, one holding a private-use character).

`ftable_audit.py`: 0 collisions, nothing past end of image, after SRVC relocated
to LBA 1826000.

**`status.py` was reading SRVC at its pre-relocation LBA** and reported a
finished file as 98.2% translated. It now resolves the LBA from the game's file
table; `stamp_build.py` does the same for every relocatable file.

## v1.47 — 2026-08-17 — **100% translation** (everything except the BGM block)

| | English | total | |
|---|---|---|---|
| Scenario dialogue | 68,911 | 68,911 | **100%** |
| Scene headers | 309 | 309 | **100%** |
| Pilot / character DB | 8,021 | 8,021 | **100%** |
| Unit names | 326 | 326 | **100%** |
| Ability descriptions | 55 | 55 | **100%** |
| Weapon names | 768 | 768 | **100%** |
| Episode titles | 118 | 118 | **100%** |
| Battle voice (SRVC) | 67,274 | 67,339 | **99.9%** |
| BGM block | 164 | 804 | 20.4% — *excluded by design* |

**Dialogue reached 100% by fixing four distinct defect classes**, none of which
any existing check could see, because every check validated SIZE and none
validated LANGUAGE:
- **463 fields the extractor never emitted** (`_M3`): `strdump` rejected them via
  `kana >= 1` (all-kanji lines), strict `shift_jis` (NEC `Ⅰ`/`Ⅱ`/`∑`), and
  `jp_score` (headers are mostly U+3000 padding).
- **231 over-budget rows**: `apply_record` SKIPS a row whose English exceeds its
  slot, shipping the Japanese. 111 recovered mechanically ('...'->'…', '..'->'.',
  contractions, rank abbreviations), 120 rewritten by hand.
- **234 passthrough rows**: the stored "translation" WAS the Japanese source. They
  fit budget and applied without error - nothing ever asserted a T value is English.
- **219 partial rows**: English prose with the Japanese speaker name left in
  (`ジ・エーデル` x66). Substituted from the glossary + 16 additions.
- 7 stragglers with no translation at all, incl. rec203's developer scene, which
  uses `アムロ「…」` (speaker joined to the quote) so no `speaker\n「…」` pass matched it.
- New standing check: `tools/find_passthrough.py`.

**Also:** 117 unit names (hand-authored canon, not Hepburn - `MajingaZ` vs
Mazinger Z), 55 ability descriptions, 664 pilot-DB fields and the last 19 battle
lines. SRVC relocated to LBA 1826000 as it grew; `tools/ftable_audit.py` confirms
0 collisions in the game's own file table (fields are at name+0x28, NOT +0x20).

**Measurement bugs fixed in `status.py` — earlier percentages were wrong both
ways.** It counted the fullwidth block as Japanese (flagging 11,170 lines of our
OWN English), counted binary that decodes as Shift-JIS (1,794 records like
'烝s', '@ピ'), read SRVC from its pre-relocation LBA (reporting a finished file
as 98% untranslated), and drew region boundaries that mixed unit names, ability
prose and BGM cues together. Figures quoted before this build (80.8% DB, 95.3%
SRVC, 33.8% unit names) should be disregarded.

## v1.45 — 2026-08-17 — dialogue the extractor never saw, + episode titles

- **New `_M3` pass** (`tools/gen_missing3.py`, `gen_missing3_en.py`): **463
  fields** across 116 records that had **no row in any `recNNN_script.json`**, so
  no earlier pass could reach them. `strdump.dump()` had rejected them:
  - `kana >= 1` — all-kanji lines. `花江\n「勝平！！」` is 15 bytes and 9 chars, so
    it passes every length test; it fails because 花江/勝平 are kanji and 「」！！
    punctuation, leaving zero kana. The rule exists to reject MIPS code that
    decodes as Japanese by chance, and takes real dialogue with it. **350 fields.**
  - strict `shift_jis` on line 49 — NEC extensions throw `UnicodeDecodeError`
    and the field is dropped before any filter runs: `ビアルⅠ世` (Bial I),
    `ガンダムＭｋ－Ⅱ`, `グラン∑`. **66 fields.**
  - `jp_score >= 0.60` — scene headers are mostly U+3000 centering padding,
    which the score does not count as Japanese. **47 headers**, e.g.
    `～駿河湾　漁港～`, `～ビアルⅠ世　ブリッジ～`.
- **Keyed by OFFSET, not row index.** Re-extracting into `script.json` would
  insert rows and renumber everything after them, silently invalidating the
  index-keyed `T` dicts across 167 files — the v1.32 mass-revert shape. `_M3`
  is offset-keyed and immune.
- 228 of 230 unique strings fit. The 2 that do not are genuinely impossible
  (`Hamamoto` + `Kappei...` cannot fit a 15-byte usable slot) and stay Japanese.
- Names resolved by counting existing usage so spellings match what already
  ships: Touga (55 vs Toga 15), Kei (62 vs Katsura 11), Tekkoki (182 vs
  Tekkouki 7), Gyukenki, Goushi (matching Zushi/Shishi/Ryoshi/Onshi).
- **Episode titles:** `TITLES` already had `目覚めの日 → "Day of Awakening"`, but
  `field_replace` computes `budget = slot - 1` to preserve the NUL, so 16 bytes
  into a 16-byte slot was **rejected by one byte** and the card stayed Japanese.
  Now `"The Awakening"` (13). Same for `世界の終わる時` (19 → `"World's End"`).
  **UNVERIFIED:** the title card uses a serif face, not the dialogue gothic — if
  it draws through a different renderer, English may come out blank. This build
  is the test; if it renders, the other 106 titles are mechanical.
- New tool `tools/why_jp.py <japanese>` — given text seen in-game, reports the
  record, offset, and which stage let it through (extraction / translation /
  budget / bytecode guard).
- **Guard bug fixed (introduced v1.44):** `translatable()` did not count U+2026.
  cp932 decodes the game's ellipsis (0x8163) to U+2026, which sits outside every
  CJK range, so `$n\n「………」` scored 2 (its two brackets) and was refused as
  bytecode — **33 genuine lines in 33 records**. Caught by auditing why `_M3`
  applied 427 of 463 rather than trusting the total. Bytecode is unaffected:
  `Pブ` still scores 1 and is still refused, and the `_M2` refusal count is
  unchanged at 464, so v1.44 shipped no false positives.
- **`stamp_build.py` bug fixed:** unsized regions defaulted to 64 sectors, but
  COMPDATA is 74 — so the episode-title region was never hashed and v1.44 vs
  v1.45 reported COMPDATA "identical" when it had changed. Extents now come from
  the ISO9660 directory, with a printed WARNING when anything falls back.
  This also revealed SRVC was being hashed at 128 KB instead of 3.3 MB.
  **Caveat: the v1.26 / v1.27 / v1.44 stamps predate this fix**, so their SRVC,
  MAPNAME, COMPDATA, ZKN_KW and ZKN_RT hashes are partial. They can only miss a
  change, never invent one — and the v1.26→v1.27 conclusion was independently
  confirmed by a full sector-diff of both images.

## v1.44 — 2026-08-17 — **chapter-2 AND chapter-5 blank-dialogue stalls FIXED** (both user-confirmed in game)

- **`apply_stage.translatable(orig, off)`** — new guard, checked by *every* pass
  against the ORIGINAL bytes. Scenario bytecode contains byte pairs that decode
  as valid Shift-JIS (`0x8375`=`ブ`, `0x8376`=`プ`, `0x8340`=`ァ`), so the
  extractor offered them as strings; `rec002_script.json` row 0 is literally
  `{'text': 'Pブ', 'budget': 3}`. Refuses **464 bytecode rows** (5.4% of `_M2`),
  **0 rows from the curated `T` dicts**.
- **Trim-loop fix** in the dialogue pass: it rebuilt rows as a plain
  `en.encode("cp932")`, dropping the leading `0x0C` glossary marker and silently
  reverting menu rows to ASCII. `_M2`'s own trim loop was already correct.
- **Enemy pilot designations restored** (267 fields) — cleared by v1.43.
- Verified on the built image: rec002 rows 0–4 byte-identical to stock, rows 5–9
  still `ZAFT`/`Phantom Pain`, row 100 English. 0 records oversize.
- **Scope was never one scene: 116 of 167 records had bytecode overwritten**
  (rec002 was only 5 of the 464 rows; worst were rec000 26, rec142 25, rec101 19).
  The chapter-5 blank dialogue the user hit separately was the same bug and was
  fixed by the same guard, without being diagnosed on its own. Any remaining
  blank-box or dead-scene report from ≤v1.43 should be re-tested on v1.44 before
  being investigated — it may already be gone.
- Known, pre-existing and unrelated: **232 rows still exceed budget and remain
  Japanese**; ~519 dialogue rows untranslated; 1,147 SRVC slots Japanese by design.

## v1.43-stage126 — 2026-08-17 — **DIAGNOSTIC** (not a release)

Question it answered: *STAGE.BIN or COMPDATA?* Built by sector-copying v1.26's
STAGE.BIN into the v1.27 image (both regions are same-size and in place, so no
rebuild was needed). **Ran clean** → STAGE guilty, COMPDATA innocent.

## v1.42 — 2026-08-17 — **DIAGNOSTIC**, did not fix

Disabled the epilot COMPDATA pass, on the theory that a blank box with no
portrait *and no name* meant a speaker-lookup failure. **Still stalled** → the
theory was wrong; the pass was restored in v1.44.

## v1.41 — 2026-08-17 — did not fix

`HEAP_BASE` 0x790000 → **0x78CD00** (shift 0x3000, a whole 3 pages). Correct in
itself, unrelated to the stall.

## v1.40 — did not fix; **ruled out the text**

Shipped rec002 row 100 as Japanese. Still stalled → proved the stalling line's
own text was not the cause. (Correct conclusion, wrong target: the corruption was
in rows 0–4, not row 100.)

## v1.38 — library page freeze fixed

Restored the encyclopedia offset tables by running `zkn_build --elf`; v1.29 had
rebuilt the ELF without it, leaving stock tables against rebuilt data.

## v1.35 — enemy pilot fields 132 → 267

Added `field_replace_prefixed()` for `[u16 id][name]` records.

## v1.33 — padding moved after the text

Front-padding had indented dialogue and pushed lines out of the box.

## v1.32 — mass revert (regression)

Only "changed" records were passed to `apply_stage`, which rebuilds STAGE from
the original and writes the whole region — every omitted record reverted to
Japanese. **Always pass all 167** (`analysis/recs_all.txt`). Caught from a Zambot
screenshot.

## v1.31 — objectives ran together

`"Annihilate all enemies。Defeat Shinn or Alex。"` on one line: an exact-budget
fill leaves no NUL terminator, so the renderer reads into the next field. Fixed
by requiring strictly `< budget`.

## v1.30 — stall present

## v1.29 — text disappeared (regression)

`patch_hwfont` had a hardcoded heap address `MASTER_LATIN = 0x9AE610`; fixed by
reading the BSS global at `0x0046E3A8`. This build also skipped `zkn_build --elf`
(see v1.38).

## v1.28 — stall present

## v1.27 — **FIRST BROKEN BUILD** (stamped)

Data-only; ELF **identical** to v1.26. Added the `_M2` second pass (STAGE.BIN),
the expanded `name_source.json` and the epilot pass (COMPDATA). The `_M2` pass
wrote translations over live scenario bytecode in rec002 rows 0–4 — see v1.44.

## v1.26 — last confirmed-clean build (stamped)

## v1.25 — clean (user-confirmed)
