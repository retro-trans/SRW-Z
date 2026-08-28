# Starting your own translation

This project is built so you can fork it and either fix the English or take the
game into another language entirely. Everything below works from a disc image
you dump from your own copy.

## What you need

- A PS2 copy of **Super Robot Taisen Z** (SLPS-25887) and a way to dump it
- Python 3
- [`chdman`](https://www.mamedev.org/) if you want to build a `.chd` for emulators
- [`xdelta3`](https://github.com/jmacd/xdelta) if you want to distribute a patch

None of those binaries are in this repo — get them from their own projects.

## The loop

```sh
# 1. pull every string out of YOUR image
python tools/extract_script.py mygame.bin script.json

# 2. edit the "text" fields in script.json - that is the whole job

# 3. write it back (refuses to write anything if a row is invalid)
python tools/apply_script.py mygame.bin script.json --write

# 4. check you did not break the image
python tools/verify_pointers.py mygame.bin --min 85
python tools/scan_visible_defects.py mygame.bin
```

`extract_script.py` tells you which situation you are in. A Japanese image gives
you the original script to translate from; an image patched with our English
gives you the current translation to revise.

Round-trip is exact: extract, change nothing, apply, and the image is
byte-identical. If you see rows being written when you changed nothing, that is
a bug — please report it.

## Comparing the Japanese against a translation

To proofread, or to see how somebody else rendered a line, build a side-by-side
table from your own two images:

```sh
python tools/build_compare.py japanese.chd translated.chd compare.html
```

It takes `.chd`, `.bin`, `.iso` or `.cue` (a `.chd` is extracted with chdman),
and writes ONE self-contained HTML file - open it in any browser, no server and
no internet. Search either language, filter by record, dialogue only, or rows
that overflow the box.

Nothing is distributed with this: the comparison is generated locally from discs
you own.

Every row is labelled with HOW it was paired:

| label | meaning |
|---|---|
| `pointer` | matched through the pointer table — reliable |
| `same-offset` | no pointer referenced it, so the English is assumed to sit where the Japanese did |
| `suspect` | paired, but the English is empty or does not look like text |

On this translation it reports **100% `pointer`** across all 68,628 dialogue
rows. If a fork sees `same-offset` or `suspect` rows, those are the ones not to
trust.

## Checking it with only a japanese disc

Judge it for yourself - one command, and only your own japanese disc:

```sh
python tools/compare_translation.py "Super Robot Taisen Z (Japan).chd"
python tools/compare_translation.py game.iso --rec 127   # one scenario
python tools/compare_translation.py game.iso --only untranslated
```

Writes an HTML page with the Japanese beside our English, filterable by record
and searchable in either language. Accepts `.chd`, `.iso`, `.bin` or `.cue`.

No patched image is needed: the pairing was done once and stored in
`analysis/translation_pairs.json`, keyed by Japanese offset. That file holds no
Japanese text - only offsets into the disc you already own.

Rows come in three kinds, kept apart on purpose. **not translated** means we
have no English for that line; **no confident match** means we cannot prove
which English goes with it - those lines are almost certainly translated, and
counting them as missing work would be wrong.

## Changing one line

Most bugs arrive as a screenshot of a single wrong line. Find it, then fix it
in place - no need to touch the rest of the script.

**Work on a patched image, not your virgin dump.** These offsets describe the
English layout, so `fix_row.py` refuses a clean Japanese disc - it finds
Japanese where it expected the line you are correcting, and says so rather
than writing anything. Apply the release patch first - see [Play it](README.md#play-it).

Starting a translation from scratch is the opposite: point
`extract_script.py` at your virgin dump and there is nothing to patch.


```sh
# 1. find it. the check page above is searchable in both languages,
#    or pull the script out and grep it
python tools/extract_script.py mygame.bin script.json

# 2. describe the fix in analysis/row_fixes.json, then
python tools/fix_row.py mygame.bin            # dry run, checks everything
python tools/fix_row.py mygame.bin --write
```

Each entry names the record, the offset, the row as it is now (`was`) and the
replacement. The `was` field is the safety catch: if the row on disc does not
match, the fix is refused rather than overwriting someone else's work.

```json
[{"rec": 132, "off": "0x015620",
  "was": "Kazuki
people of Io, ...",
  "text": "Kazuki
「I'm counting on you, ...",
  "why": "lost its first line and named the wrong target"}]
```

It refuses anything the engine would reject - more than 3 body lines, a line
over 34 columns, text that will not encode as cp932, or a replacement too long
for its slot. The first line of a row is the speaker and is structural; do not
turn it into a sentence.

## Rules the engine enforces

`apply_script.py` refuses to write a row that breaks any of these, because every
one of them has broken this game at least once.

**The box is 3 lines by 34 columns.** Fullwidth characters count 2. Line 1 of a
row is the speaker name and is structural — do not translate it into a sentence.

**Placeholders expand at runtime.** `$n` and `$f` are 7 columns, `$F` is 14,
`$l` is 6, `$c` is a player-entered squad name and is unbounded. Count the
expanded width, not the 2 characters you see.

**`《term》` links must resolve.** The term has to exist in the keyword bank or
the scene *crashes*. A term and its links are ONE edit; if you rename one,
rename the other. Rename the bank first — an entry with nothing pointing at it
is harmless, a link pointing at nothing is not. Check with
`python tools/fix_dead_links.py <iso> --dry-run`.

**Text must encode as cp932.** Em-dashes, curly quotes and most accented
characters do not. `ö/ä/ü` are unavailable, which is why the German-named
characters here ship without umlauts. `β` does exist (`0x83C0`).

**Replacements must fit their slot.** A longer string needs relocating to the
end of the record with its pointer rewritten — see "option 3" in
[`docs/TECHNICAL.md`](docs/TECHNICAL.md). `apply_script.py` does not do this for
you; it will tell you the row does not fit.

**Menus are drawn by a different renderer** where ASCII `0x2E–0x3D` (`.` and the
digits) are *control codes*. Menu and library text uses fullwidth `．` and `０`
on purpose. Do not "fix" those to ASCII — the renderer will break the line at
every period.

## Before you build

```sh
python tools/verify_pointers.py <iso> --min 85    # catches the save-load freeze
python tools/verify_elf_patches.py <iso>          # catches reverted ELF patches
python tools/fix_dead_links.py <iso> --dry-run    # must report 0
python tools/scan_visible_defects.py <iso>        # must report 0
```

The first one matters most. An edit that moves bytes inside a record while
leaving its pointer table alone produces an image that boots, plays fine, and
freezes when you load a save — and every length-based check passes. That
shipped here once.

## Naming

`analysis/glossary.json` maps Japanese terms to the English this translation
uses, and `analysis/glossary_sources.json` records where each came from and how
far to trust it:

| status | meaning |
|---|---|
| `cited` | verified against a named source |
| `corrected` | fixed, with the reasoning recorded |
| `chosen` | no official English exists; a decision was made |
| `corroborated` | matches our own script — circular, **not** evidence |
| `legacy-unverified` | inherited, source never recorded |
| `ambiguous` | the same katakana is two different characters — **never** rename globally |

If you are translating to another language, the glossary is still useful as a
list of *which* terms are proper nouns and which are ordinary words, even though
the English side will not be.

The `ambiguous` entries are the trap. サラ is three different characters
depending on the series; メサ is a God Sigma character and not Jerid's surname.
A global find-and-replace on those renames the wrong person.

## Contributing back

Pull requests welcome, especially:

- proofreading — 141 of the 205 scenario records have never been read by a human
- the export-pairing problem in `analysis/review/EXPORT_TRUST.md`
- other languages, as separate branches or forks

Please do not add the original Japanese script, disc images, or third-party
binaries to the repository.
