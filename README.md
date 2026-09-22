# Super Robot Taisen Z — translation project

An open toolchain for translating **Super Robot Taisen Z** (PlayStation 2,
SLPS-25887 and The Best SLPS-73270), plus the English translation built with it.

## Contribute

The project is mostly done but we haven't tested every route yet, and human
proofreading has covered 2,389 lines so far out of 87,835. If you want to
contribute to this project or the next in any way — be it bug reports,
proofreading or playtesting — please join my Discord:

**[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)**

## Play it

The latest release is **[v0.9.85](https://github.com/retro-trans/SRW-Z/releases/tag/v0.9.85)**,
with separate patches for the original Japanese edition (**SLPS-25887**) and
**The Best edition (SLPS-73270)**. You need your own copy of the matching game.

This release includes translation updates, King Vega terminology,
corrected chapter title cards, and the previous interface and dialogue fixes.
See the release notes for the full changelog and remaining playtesting checks.
The Best patch remains experimental.

### Apply

**The easiest way:** Using our tools [Retro Trans](https://github.com/retro-trans/retro-trans-tools) provides a desktop interface for applying translation patches. Download the app from its Releases page, choose **Automatic** tab, select your source game image (.iso or .chd), wait for the app to analyze it then click Patch.

**Other ways**: [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) accepts the same `.xdelta` files. Select your unpacked `.bin`/`.iso` as the original file and the appropriate patch.

**Command line**: Get [xdelta3 here](https://github.com/jmacd/xdelta). `chdman.exe` is included with [MAME](https://www.mamedev.org/release.html); you do not need to install or run MAME.

You need your own Japanese disc image, or the matching published English v0.9.83 image for an upgrade. Choose the patch that matches your edition; the two editions are not interchangeable.

| Your source image | Patch |
|---|---|
| Original Japanese release, SLPS-25887 | `SRWZ-English-v0.9.85.xdelta` |
| Japanese The Best release, SLPS-73270 | `SRWZ-English-Best-v0.9.85.xdelta` |
| Original-edition English v0.9.83 | `SRWZ-English-v0.9.83-to-v0.9.85.xdelta` |
| The Best edition English v0.9.83 | `SRWZ-English-Best-v0.9.83-to-v0.9.85.xdelta` |

**Original Japanese edition:**

```
xdelta3 -d -s "Super Robot Taisen Z (Japan).iso" SRWZ-English-v0.9.85.xdelta "SRWZ English v0.9.85.iso"
```

**Japanese The Best edition:**

```
xdelta3 -d -s "Super Robot Taisen Z [The Best] [J].iso" SRWZ-English-Best-v0.9.85.xdelta "SRWZ English Best v0.9.85.iso"
```

**Already on original-edition v0.9.83?** Use the smaller upgrade patch:

```
xdelta3 -d -s "SRWZ English v0.9.83.iso" SRWZ-English-v0.9.83-to-v0.9.85.xdelta "SRWZ English v0.9.85.iso"
```

**Already on The Best edition v0.9.83?** Use its upgrade patch:

```
xdelta3 -d -s "SRWZ English Best v0.9.83.iso" SRWZ-English-Best-v0.9.83-to-v0.9.85.xdelta "SRWZ English Best v0.9.85.iso"
```

**If you have a `.chd`**, unpack it first, then apply the matching patch to `game.bin`:

```
chdman extractcd -i "your-game.chd" -o tmp.cue -ob game.bin
```

A `.chd` cannot be patched directly. If the patcher reports a checksum mismatch, check your source edition and version against the hashes in `README-v0.9.85.txt`. Do not disable source verification. Upgrade patches require the exact published v0.9.83 outputs; local test builds with the same version label may differ. Full and upgrade patches produce identical v0.9.85 output within each edition.

### Sharper UI art (optional)

English interface artwork and the SRW title logo are included in the patches.
The optional `SRWZ-texture-pack.zip` provides sharper PCSX2 intermission artwork
for the original edition. It is unchanged from v0.9.83 and has not been
revalidated against v0.9.85's native artwork; Best support remains unverified.

For the original edition, copy its `textures` folder into your PCSX2 user
directory, giving `textures/SLPS-25887/replacements/*.png`, then enable
**Settings -> Graphics -> Texture Replacement -> Load Textures**.

## Check the translation

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

Changing a line you disagree with is in
**[TRANSLATING.md](TRANSLATING.md)**.

## Translate it

Fork it to fix the English, or to take the game into another language. Start
with **[TRANSLATING.md](TRANSLATING.md)**.

```sh
python tools/extract_script.py mygame.bin script.json   # pull the text out
#   ... edit the "text" fields ...
python tools/apply_script.py mygame.bin script.json --write
python tools/verify_pointers.py mygame.bin --min 85     # never skip this
```

Round-trip is exact by construction: extract, change nothing, apply, and the
image is byte-identical.

You need your own copy of the game. This repository contains no disc image, no
game data and no dump of the original Japanese script — `extract_script.py`
reads those from the disc you dump yourself.

## What is here

| Path | Contents |
|---|---|
| `TRANSLATING.md` | **start here** — the edit loop and the rules the engine enforces |
| `TOOLS.md` | every tool, what it is for, and when you need it |
| `tools/` | 197 tools: the LZ codec, the pipeline, patchers, verifiers, gates |
| `analysis/english_script.json` | the English translation — 167,613 strings |
| `analysis/translation_pairs.json` | our English keyed by Japanese offset, for the check above |
| `analysis/glossary.json` | 1000 terms, with provenance in `glossary_sources.json` |
| `docs/TECHNICAL.md` | how the data, the engine and the pipeline actually work |
| `docs/BASE_RULES.md` | portable rules for running a project like this |
| `docs/RENDERER.md` `VWF.md` `CUSTOM_FONT.md` | how the text engine draws, and the font work |
| `docs/LZ_FORMAT.md` `DEBUGGER_TRACE.md` `FINDINGS.md` | the container format and the live-tracing method |
| `CHANGELOG.md` | every build, what changed, and what broke |

## Using these tools

They expect a decrypted PS2 disc image you dump yourself from your own copy.
Most take the image as their first argument and are read-only unless passed
`--write`:

```sh
python tools/scan_visible_defects.py <iso>          # report
python tools/verify_pointers.py <iso> --min 85      # gate before building
python tools/fix_terms_global.py <iso> --write      # apply
```

Windows note: anything using `multiprocessing` must be a real file on disk, never
a heredoc — spawned workers re-import the module and cannot import `<stdin>`.

## Do not sell this

This patch is free. Do not sell it, and do not sell anything made with it -
no pre-patched discs or images, no loaded memory cards or consoles, no
paywalled or ad-gated downloads.

It is an unofficial fan translation of a game Bandai Namco owns. Selling it
takes money for work that was given away, and it is the surest way to get a
project like this shut down.

## Credits

We use the [Bizin Gothic font by yuru7](https://github.com/yuru7/bizin-gothic)
in this translation. Thank you to its creators and contributors.

The Best edition build draws on the technical knowledge shared by
[dyzz/srwz-zh](https://github.com/dyzz/srwz-zh/). Their research helped us
adapt our English translation to the Japanese The Best release.

| Role | |
|---|---|
| Project lead | pow |
| Proofreading | Valz, Hakhan Dakharan |
| | *2,389 lines read against the Japanese so far - see [Human proofreading](#human-proofreading)* |
| Playtesting | pow, KagamineRin, Melfice, Melfice's friend |

Translation passes, tooling and reverse engineering were done with Claude
(Anthropic), directed by pow. The translation is machine-produced and then
edited - see the release notes for what that means in practice.

Names and terminology follow the Super Robot Wars community wiki.

## Status

The translation is in progress. `CHANGELOG.md` is the honest record, including
the builds that shipped broken and why.

### Human proofreading

Every line is machine-translated first. So far a human has read **2,389 lines**
against the Japanese - 1,139 of 68,622 dialogue lines (1.66%) and 1,250 of
19,213 battle lines (6.51%) - and supplied replacement English on 1,886 of
them. The rest they read and passed, which is work too.

Of those rewrites, **1,154 are live in the build** so far: 555 dialogue lines
and 599 battle captions. The gap is not backlog. Most of the remainder are
rows where the proofreader typed out the line and concluded it was already
right, so there was nothing to change. A smaller number could not be applied
and say so in the workbook: 7 battle captions need more bytes than the field
holds, and 44 target text that an earlier pass had already corrected, which
is a fault in our caption index rather than in their work.

That does not count the machine passes, which have been over the whole script
several times. This number is only about human eyes, and mixing the two would
make it look larger than it is.

Counted, not estimated: `python tools/proofread_status.py` reads the
proofreading workbooks, so the figure cannot drift from what was really done.
Tracking it per stage was tried and abandoned - a proofreader stops mid record
and "no change needed" looks identical to "never read", so only a line count
can be honest.
