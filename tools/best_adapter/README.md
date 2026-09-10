# English adapter for SRW Z The Best

Build a **test candidate** for the Japanese Best edition (SLPS-73270) from the
project's current Original-edition English ISO. Keep translating and building
the English Original edition as usual; this adapter imports that build on each
update. It does not require maintaining a second translation corpus.

The adapter uses the published edition layout information from
[dyzz/srwz-zh, commit 8c741db](https://github.com/dyzz/srwz-zh/commit/8c741db5ff88ff91bdf97561cd56d07a935bafd7).
`layout.json` preserves that factual mapping and its provenance. The Python
adapter uses this English project's codecs and runtime; it does not invoke or
copy the Chinese compiler's implementation or translations.

## Build

Python 3.8 or newer, the SRW-Z repository's `tools` directory, and xdelta3 are
required. All three input ISOs remain read-only. Generated files contain game
data and belong outside the repository.

```powershell
$env:PYTHONUTF8 = '1'
python -B tools/best_adapter/build.py `
  --original 'E:\Projects\SRW Z\game.bin' `
  --best 'E:\Projects\SRW Z\Super Robot Taisen Z [The Best] [J].iso' `
  --english 'E:\Projects\SRW Z\_work\iso\srwz_cap.bin' `
  --work 'E:\Projects\SRW Z\_work\best-next-build' `
  --output 'E:\Projects\SRW Z\SRW Z English Best - next test.iso' `
  --patch 'E:\Projects\SRW Z\SRWZ-English-Best-next-test.xdelta' `
  --xdelta 'E:\Projects\SRW Z\xdelta3.exe'
```

Run from the repository root. If the adapter is installed elsewhere, pass
`--tools <repository>/tools`. Use **a new work directory and output names for
each English update**. `--resume --work <directory>` deliberately reuses that
directory's frozen English snapshot; it does not import newer translations.
Omit `--output` and patch arguments to build and verify components only.

The patch applies to the **unmodified Japanese Best ISO**, not an English
Original ISO. Source identities are checked before import:

| Input | Bytes | SHA-256 |
|---|---:|---|
| Japanese Original | 3758358528 | `ddbedefc0061213c50928fb213a7fb277c0345f01dab7386adc0383638a78cd2` |
| Japanese Best | 3755081728 | `950e2759d0d7482387d97d6df31325d9e352097a23e0bb4724073d1538d8cf77` |

## What it carries across

- Current English text and translated graphics, including encyclopedia files
  relocated through VMAP rather than the ISO directory alone.
- English font, caption and glyph-cache runtime hooks, rebased into Best's ELF.
- Best's native gameplay code, four database corrections, ending data and voice
  IDs. English descriptions and the swapped voice-actor credits reflect Best.
- Best's protagonist-name macro in the corrected Jiron dialogue.
- The PS2 fix: all 353 subtitle blocks and the EOF remain 16-byte aligned.

The English runtime begins at `0x78A870`; the heap starts at `0x78D500`.
Native Best subtitle block boundaries and opaque tails remain byte-identical.
Repeated captions share storage only where needed to fit a native subtitle
pool. Text references read back to the imported captions.

The current English input contains stale subtitle indexes and several scenario
strings beyond native decoded allocations. The adapter recovers complete
captions by their preserved order, retains Best metadata, and packs scenario
text into proven native text space. This changes placement, not wording.
These repairs affect the separate Best output only. Reports identify every
affected input block.

## Verification and limits

The build checks compressed records with the game's strict decoder behavior,
reads scenario text through output pointers, checks ELF archive tables,
preserves Best voice metadata and opaque subtitle tails, verifies ISO/VMAP
agreement and every untouched ISO byte range, and decodes the generated xdelta
back to the candidate's exact SHA-256.

Run regression tests with the private snapshot:

```powershell
$env:SRWZ_BEST_TEST_WORK = 'E:\Projects\SRW Z\_work\best_english_build'
$env:SRWZ_TOOLS = 'E:\Projects\SRW-Z\tools'
python -B tools/best_adapter/test_adapter.py
```

This is an experimental adapter. Static checks and an xdelta round trip do
not establish that the game boots or runs correctly on PCSX2 or PS2 hardware.
Test the opening, both protagonists, menu fonts, a voiced battle, the help book
and encyclopedia before promoting a candidate to a release. Existing English
Original save states are unsuitable for testing a different executable.

New runtime hooks, a larger runtime segment, or changes to corrected English
descriptions may require adapter work. Scenario record 161 now imports its
six name fields through verified native owners; edits outside those audited
slots stop the build. The adapter
fails on unknown conflicts or capacity overflow instead of truncating text.

`inputs.json`, `stage-port.json`, `subtitle-port.json`, `data-port.json`,
`elf-port.json`, `archive-port.json`, `verification.json`,
`iso-verification.json`, and `patch-verification.json` document each build.
Do not commit snapshots, decoded assets, candidate ISOs or xdelta scratch ISOs.
