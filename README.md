# Super Robot Taisen Z — English translation toolchain

Tooling, documentation and terminology research for the English fan translation
of **Super Robot Taisen Z** (PlayStation 2, SLPS-25887).

This repository contains the **tools and research only**. It does not contain
the game, any part of the game's data, or the translated disc image — see
[What is deliberately not here](#what-is-deliberately-not-here).

## What is here

| Path | Contents |
|---|---|
| `tools/` | ~490 Python tools: the LZ codec, patchers, verifiers, scanners |
| `docs/BASE_RULES.md` | Portable rules for running a translation project like this |
| `docs/TECHNICAL.md` | How the data, the engine and the pipeline actually work |
| `analysis/glossary.json` | 1000 Japanese→English terms used by the translation |
| `analysis/glossary_sources.json` | Provenance for every glossary entry |
| `analysis/review/` | Proofreading brief and export-reliability report |
| `CHANGELOG.md` | Every build, what changed, and what broke |

## The interesting parts

**`tools/banlz.py`** — a clean-room implementation of the game's LZ variant
(compressor and decompressor), which is what makes everything else possible.

**The verifiers.** Each exists because something shipped broken:

| Tool | Catches |
|---|---|
| `verify_pointers.py` | edits that move bytes inside a record and orphan its pointer table |
| `verify_elf_patches.py` | ELF patches that silently reverted |
| `verify_spirits.py` | two spirit commands sharing one name |
| `scan_visible_defects.py` | anything a player would see: overflow, untranslated lines, escapes, garbage tails |
| `zkn_name_check.py` | library names that disagree with the glossary |
| `fix_dead_links.py` | `《term》` links with no keyword-bank entry — these CRASH the scene |

**`analysis/glossary_sources.json`** — every name records where it came from and
how far to trust it: `cited` (a named source), `corrected`, `chosen` (no official
English exists), `corroborated` (matches our own script — which is circular, not
evidence), `legacy-unverified` (inherited, source unrecorded), `ambiguous` (the
same katakana is two different characters — never rename globally).

## Lessons that cost the most

Written up properly in `docs/TECHNICAL.md`; the short version:

- **A glossary term and its `《》` links are ONE edit.** Renaming either half
  alone leaves a dead link, and a dead link crashes the scene. Rename the bank
  first: an entry with no incoming links is harmless, a link with no entry is not.
- **In-place edits must preserve every offset in the record.** Rewriting a
  record as `"\x00".join(parts)` after shortening a string slides everything
  after it left while the pointer table stays put. Record *length* is unchanged,
  so every length-based check still passes. The game boots, plays, and freezes
  when you load a save.
- **Name sources contradict each other**, including akurasu with itself. Fix a
  precedence order and follow it; a better-sourced spelling is still the wrong
  one if it is not the project's baseline.
- **A tool being correct is not evidence that its output shipped.** Two bugs here
  were "the fix existed and never reached the image". Verify against the image.

## What is deliberately not here

Nothing that is Banpresto's or Bandai's:

- no disc images, `.bin`, `.cue` or `.chd`
- no extracted game files, no `DATA_*.BIN`, no boot ELF
- no dumps of the original Japanese script
- seven working files were removed from `tools/` because they embedded blocks of
  the original dialogue verbatim

Also excluded: third-party binaries (`chdman`, `xdelta3`, MAME) — get those from
their own projects.

Short Japanese snippets do appear in docstrings and the changelog where they are
needed to explain a bug or a rule.

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

## Status

The translation is in progress. `CHANGELOG.md` is the honest record, including
the builds that shipped broken and why.
