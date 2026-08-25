# Technical reference

How the data, the files and the pipeline actually work. `RULES.md` is the
judgement; this is the machinery.

## Data model

```
DATA_STAGE.BIN            banlz-compressed, at LBA 1651029
  └─ record  rec109…rec150     one scenario, 400–1450 rows
       └─ row                   one dialogue box the player advances through
            line 1  speaker     locked - see below
            line 2..4  body     max 3 lines, max 34 columns
```

A **slice** is 80 consecutive rows of spoken dialogue, cut to fit an agent's
budget. It is **not** a scene — nothing in the data marks scene boundaries, so
one slice can hold the tail of one scene and the start of another. One held
three. Row numbers have gaps because slices are filtered to spoken dialogue
only (rows whose Japanese contains 「 and a line break).

## Files

| Path | What |
|---|---|
| `analysis/review/recNNN.json` | full record export — JP/EN pairs, `off`, `slot` |
| `analysis/review/slices/recNNN_000.json` | the 80-row cuts agents are given |
| `analysis/review/fixes/recNNN_000.json` | agent output: only changed rows |
| `analysis/review/BRIEF.md` | what every agent reads first |
| `analysis/review/QUEUE.md` | resume state: done / in flight / applied |
| `analysis/db_en.json` | 407 legacy name mappings — conflicts with the wiki, do not trust |

**Exports are STALE.** They are a snapshot; the image moves on as sweeps run.
Good for context — who is speaking, what a term means, how a repeated line
reads elsewhere. Never evidence about current spelling.

## Constraints the engine imposes

- **Box: 3 lines × 34 columns.** Fullwidth counts 2. This is a *display* limit,
  not a byte limit — relocation buys bytes, not space. Some dropped clauses
  simply cannot be restored.
- **Placeholders expand at runtime**: `$n` 7 cols, `$f` 7, `$F` 14, `$l` 6,
  `$c` = player-entered squad name, unbounded. Wrapping must count the
  EXPANDED width.
- **`《term》` glossary links** must resolve to a keyword-bank entry or the scene
  crashes. Never invent one.
- **Speaker lines are locked.** `apply_fixes.py` refuses any edit that changes
  line 1 — that guard is what stops an agent corrupting row structure. Speaker
  renames go through `apply_names.py` instead. Colour comes from `speaker_id`,
  not the name text, so relabelling is cosmetic.
- **Menu text ≠ dialogue.** In menu-drawn rows, ASCII 0x2E–0x3D are control
  codes, so fullwidth `．` and `４` are CORRECT there and wrong in dialogue.
  Dialogue is identified by the presence of 「.

## Relocation ("option 3")

A row that grows past its slot is appended at the record end and every
4-aligned pointer to it is rewritten; the old slot is zeroed. Consequences:

- A high, out-of-sequence `off` means the row was relocated. That is **normal**,
  not a mis-pair. Judge pairing by content only.
- Byte budget is effectively gone for dialogue. The 34-column box is the real
  constraint.

## Pipeline order — this matters

```
1. agents write fix files        read-only, safe to run in parallel
2. apply_fixes.py  -> image      agent fixes land
3. fix_terms_pass.py -> image    scripts get the last word
```

Reversing 2 and 3 silently undoes scripted fixes, because slices come from the
stale export and an agent fix can carry an old spelling back in.

**Never run two writers against the image at once.** Recompression takes
20–40 minutes and it is tempting to start the next pass early. Don't.

## Tools

| Script | Job |
|---|---|
| `make_slices.py N rec…` | cut records into N-row slices |
| `apply_fixes.py <iso>` | apply all `fixes/rec*.json`; validates and refuses bad edits |
| `fix_terms_pass.py <iso>` | 52-rule name/term table, in place (same length or shorter) |
| `fix_terms_grow.py <iso>` | same, for replacements that get longer — re-wraps, relocates |
| `fix_rank.py <iso>` | 准将 → "General X" (address) / "Brigadier General" (statement) |
| `audit_names.py [--rules]` | fuzzy-match every dictionary name against every row |
| `check_alignment.py <iso>` | measure export/source mis-pairing |
| `verify_elf_patches.py` | run before every image build |

Rule shape — conditioned on the Japanese so nothing unrelated is renamed:

```python
(u"ノルブ",     "Norbu",   "Norb"),
(u"ヴォダラク", "Vodalak", "Vodarac"),   # the order
(u"ヴォダラ宮", "Vodarac", "Vodara"),    # the palace
```

## Glossary DB schema

What ours lacked. `series`/`source` (provenance) and `status` are the fields
that matter:

```json
{ "jp": "ノルブ",
  "en": "Norb",
  "series": "Eureka Seven",
  "status": "cited",
  "source": "eurekaseven.fandom.com/wiki/Norb" },

{ "jp": "ガガーン",
  "en": "Gagarn",
  "series": "Space Emperor God Sigma",
  "status": "chosen",
  "note": "no english source; corpus-dominant 99 vs 30" }
```

Build-time validation: no duplicate `en` for different `jp`; flag any `jp` that
is a prefix of another `jp`; every `cited` entry has a `source`.

## Known artifacts (do not "fix" these)

- **Export mis-pairing is FAR worse than 1%.** This entry used to say "~1% of
  rows (221 measured)". Re-measured 2026-08-24 across all 167 script files:
  8,415 rows resolve to an EMPTY string and 15,972 have a JP/EN structure
  mismatch — roughly 30% of pairs. 55 of 167 records score under 60% sane
  pairs; 7 score **0%**. See `analysis/review/EXPORT_TRUST.md`.

  Cause: `export_review.py` resolves English by JP offset, and when no 4-aligned
  pointer targets that offset it **silently assumes English lives at the same
  offset**. For a relocated row the old slot has been zeroed, so the export
  shows `""`; for others it grabs an unrelated string.

  **The image is NOT damaged** — verified 68,340 dialogue strings, 1 anomaly,
  and that one is untranslated Japanese in inline `name「text」` form. The game
  resolves text through its own pointers; only the export mislabels pairs.

  Do not assume a fix: pointer-POSITION pairing (match `jb[p]` to `eb[p]`) is
  exact on rec144 (847/847) but yields mid-string garbage on rec127/139/119/98/
  107/104, so records use more than one referencing scheme. Anyone fixing this
  must establish the scheme per record first.
- **Literal backslash-n** WAS real and player-visible. This entry previously
  claimed "zero rows of the real image, `fix_literal_nl.py` confirms 0" - that
  was WRONG. 163 occurrences sat in 7 records and rendered the characters 

  inside the dialogue box; a user screenshot caught them. The tool's detection
  was correct, but it iterates `analysis/review/rec*.json`, so it never saw
  rec104/107/136 - 134 of the 163. Fixed 2026-08-24 by
  `fix_literal_nl_global.py`, which scans the image.

  **The lesson is general:** any tool driven by the export set is blind to 141
  of the 205 records. A "0" from one of them means "0 in the 26 records I can
  see" - never "0 in the game".

## When a slice does not give enough context

An agent is not limited to its slice — it has full read access.

1. Read the whole record at `analysis/review/recNNN.json`. Better than reading
   neighbouring slices, since the slice is a filtered subset of it.
2. Grep the corpus for the same Japanese line. These games reuse dialogue
   heavily, so a correct rendering elsewhere is ground truth and a disagreement
   proves one of them wrong.
3. Check the name dictionary — but see the warning above about `db_en.json`.
4. Budget it. Every extra read costs context that belongs to the 80 rows you
   were given.
5. Still not enough? Leave the row and say so. A coherent line you could not
   verify beats a confident guess.

## Name sources: akurasu contradicts itself

akurasu is the baseline, but it is NOT one voice. Different pages romanise the
same character differently:

| JP | Pilot_Database | Banpresto_Originals_List | superrobotwars.fandom |
|---|---|---|---|
| ツィーネ | Ziene | Tsuine | Xine |
| メール | Mel Beater | Mail Beater | - |
| バルゴラ | Virgola | Virgora | - |

**Precedence, in order:**

1. `Super_Robot_Wars/Z/Pilot_Database` - the page BASE_RULES names, for pilots
2. `Super_Robot_Wars/Z/Unit_Database` - for mecha
3. any other akurasu page
4. series wikis (Wikipedia, Getter/Gundam/Eureka wikis)

Rule 4 is LAST, not first. On 2026-08-24 eight names were "corrected" from
Wikipedia against the baseline - Ryoma/Ryouma, Benkei Kuruma/Kurama, Quattro
Bajeena/Bageena, Sarah Zabiarov/Sara Zabirov, Elchi/Elche, Rag Ulalo/Uralo,
Chill/Chiru, Bilin/Birin - and all had to be reverted. A better-sourced
spelling is still the wrong one if it is not the baseline's.

cp932 cannot encode ö/ä/ü, so akurasu's "Löwen General" ships as "Lowen
General". β IS encodable (0x83C0), so "Galbaldy β" is fine.

Provenance lives in `analysis/glossary_sources.json`: every entry carries
status (cited / corrected / chosen / corroborated / legacy-unverified /
ambiguous / CONFLICT), a source, and a note.
