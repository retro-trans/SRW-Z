
## BEFORE proofreading a record, check EXPORT_TRUST.md

`analysis/review/EXPORT_TRUST.md` scores how often a record's export pairs the
right Japanese with the right English. 55 of 167 records score under 60% and 7
score 0%. If your record is in the low band, the `jp` beside a row is probably
NOT that row's source text - do not "correct" English to match it. Verify
against the image or say you could not.

# Proofreading brief — SRW Z English patch

You are proofreading machine-translated (DeepSeek) dialogue against the Japanese
source. Fix what is WRONG; leave what is already fine alone.

## Input
A JSON list. Each entry: {"row", "off", "slot", "jp", "en"}
- `jp` — the Japanese source
- `en` — what currently ships (already wrapped, already quoted)
- `slot` — bytes available in place. Longer text can be relocated, so this is a
  hint, not a wall.

## COVERAGE IS MANDATORY
Review EVERY row in the slice, in order. Do not sample, skip ahead, or stop
early. Your final reply must state how many rows the slice contained and
confirm you examined all of them. A previous run silently reviewed 96 of 120
rows; that is a failure.

## Error classes to hunt (these are REAL misses from this corpus)
1. **Dropped proper nouns.** 「すまぬ、ランスロー大佐」 shipped as "Forgive me,
   Colonel." — the name Lancerow vanished. 「追うな、レントン！」 shipped as
   "Don't chase him,!" — the addressee vanished and left a stray comma.
2. **Dropped particles and nuance.** も = "too/as well", だけ = "only",
   まだ = "still / not yet". 「だが、まだだ！」 is "But it's not over yet!",
   not "But not yet!". 「宇宙革命軍も来るぞ」 = "coming TOO".
3. **Wrong gameplay verbs.** 隣接すれば = "when they are ADJACENT", NOT "dock
   with". Getting this wrong misinforms the player about how to win.
4. **Singular flattened to plural.** 屍 (one man's corpse) became "their
   corpses".
5. **Terminology drift.** 革命軍 = "Revolutionary Army", not "revolutionaries".
   Check the glossary below.
6. **Conditional/aspect errors.** こうなったら = "it HAS come to this", not "if
   it comes to this". 仕掛けるなら = "if you meant to attack".
7. **Unnatural English.** Literal word order, missing articles, robotic
   phrasing. Make it sound like a person speaking. Keep register: soldiers
   sound like soldiers, teenagers like teenagers.

Do NOT rewrite a line merely because you would have phrased it differently. If
it is accurate and reads naturally, leave it.

Ellipses are ALREADY normalised to ASCII "..." — do not spend effort on them.

## Hard constraints — a violation breaks the game
- Keep the SPEAKER line (first line) exactly as-is, including `$n`, `$F`, `$f`.
- Keep every `$` placeholder. `$n` = pilot short name, `$F` = full name,
  `$c` = squad name. They expand at runtime.
- Keep the kagi quotes 「 」 around speech and （ ） around thoughts.
- Keep any 《term》 glossary link exactly as spelled — it must match a keyword
  entry or the game CRASHES. Never add new ones.
- Body: at most **3 lines**, each at most **34 columns**. Fullwidth counts 2.
  `$F` counts 14; `$n` and `$f` count 7. 「」 cost 2 each.
- ASCII `...` only, never `…`. American spelling. No ASCII digits inside 《》.

## Glossary — exact spellings
Names and terms come from akurasu.net / the SRW wiki. Never invent a
transliteration and never "unify" a term to one you saw elsewhere in the corpus.

Glory Star, Rivalry Zone (相克界 — NOT "Overlap"), Trapar, Ref (リフ, the sport),
Scub Coral / Scub (スカブ), ZAFT, PLANT, Orb, AEUG, Titans, Karaba, Coordinator,
Natural, Blue Cosmos, Logos, FAITH, Gym Ghingnham, Exodus, Overman, Gundam,
Revolutionary Army, Aprilius Alliance, Setsuko・Ohara, Rand・Travis,
Kei Katsuragi (桂 — NOT Katsura), Lowen, Ziene Espio, Touga Tenkuuji,
Lancerow Darrow, Asakim Dowin, Joseph Yaht, Sting Oakley,
Edel Bernal — **Brigadier General** of the Chimera Special Forces.

Terms this corpus keeps getting WRONG — check every occurrence:
- **Taikyoku** (太極). Never "Taiji". 43 rows shipped wrong.
- **Hyakki Empire** (百鬼帝国). NOT Mycenae — that is ミケーネ from Great
  Mazinger, a different franchise and a different empire.
- **Mycenae** (ミケーネ) only when the Japanese really says ミケーネ.
- **Vodara Palace** (ヴォダラ宮) is the place; **Vodarac** (ヴォダラク) is the
  religious order. They are not interchangeable.
- **Tekkouki** (鉄甲鬼) is a name — do not translate it as "Iron Demon".
- 大特異点 = "the Great Singularity".

## Output
Write ONLY the rows you changed to the output path you are given, as JSON:
`[{"row": 123, "en": "Speaker\n「fixed line one\nline two」"}, ...]`
Real newlines inside the string (JSON \n). If you changed nothing, write `[]`.

Then reply with ONE line: rows in slice, rows examined, rows changed, and the
2-3 most serious problems found.

## Rows whose Japanese does not match the English

About 1% of rows (221 measured) are paired with the WRONG Japanese in the
export. Our shipped ENGLISH is fine; only the `jp` field is wrong. They arrive
in BLOCKS, not singly - one run was 42 consecutive rows.

Worst records, so expect blocks if you are reviewing these:
    rec144  65 rows      rec147  56 rows
    rec131  30 rows      rec119  22 rows

The giveaway: the English reads as one coherent scene while the `jp` field jumps
to different characters, or a different series entirely (Big O text against a
Getter Robo scene).

When you see it: LEAVE THE ROWS ALONE and list the row numbers. Do NOT rewrite
coherent English to match unrelated Japanese - you would be replacing a correct
line with a wrong one.

NOT a mispair: an out-of-sequence byte offset on its own. Relocated rows get
high offsets and are perfectly fine. Judge by CONTENT, never by offset.

## Do NOT "fix" a literal backslash-n

The slice files are cut from an export that is STALE relative to the shipped
image. The export still shows a literal two-character backslash-n in ~224 rows;
the real image was repaired long ago and has none. tools/fix_literal_nl.py
confirms 0 rows against the ISO.

So: if you see a stray backslash-n, IGNORE IT. It is an artifact of the export,
not something a player will ever see. One agent spent a whole slice budget
"fixing" 19 of these.

The same staleness explains term spellings that look wrong in your slice but are
already corrected in the build. That is why the name list is off-limits.

### Mispair vs shipped damage - how to tell them apart

Both look like "the English does not match the Japanese". They need OPPOSITE
handling, and the SPEAKER LINE tells you which one you have:

- **Speaker names DISAGREE** (jp says one character, en says another) -> export
  MISPAIR. Our English is fine. LEAVE IT ALONE.
- **Speaker names AGREE but the content is unrelated** -> shipped DAMAGE. An
  earlier bad pass wrote the wrong text into that row. FIX IT - translate the
  Japanese properly.

Confirm damage with two more signals: the Japanese flows coherently from the
row before into the row after (so the pairing is right), and the row often has
an out-of-sequence offset, meaning it was rewritten at some point.

Real case: rec143 row 350. Speaker "Asuham" on both sides; JP runs 349 "Asuham
Boone! You came too!" -> 350 "Of course, Gain! My friend and the world are at
stake" -> 351 "And above all, I fight for my sister Karin's child!!". The
shipped English said "I'm not here to help you. I just can't stand that guy."
Wrong line, correctly paired - a repair, not a mispair.

### CORRECTION: rec144 / rec132 / rec149 - missing speaker lines are DAMAGE

Earlier guidance called rec144 the worst "mispair" record. That was WRONG.
Measured: 77 rows across rec144 (63), rec132 (9), rec149 (4), rec131 (1) have a
different defect entirely - the English row LOST ITS SPEAKER LINE.

    JP   \u30b8\u30fb\u30a8\u30fc\u30c7\u30eb || \u300c\u3044\u3044\u3088\u3001\u305d\u3046\u3044\u3046\u306e\uff01 || ...        (4 lines: speaker + 3 body)
    EN   "Fine, I like that! The more || ...              (3 lines: NO speaker)

Two things are wrong and BOTH are player-visible:
  1. the speaker nameplate is gone
  2. the body uses ASCII " instead of the kagi \u300c \u300d

DO NOT skip these. They are shipped damage, not an export artifact. A script
now repairs them (restores the speaker from the Japanese tag and converts the
quotes), so you do not need to fix them by hand - but do NOT treat a row as
"mispaired" just because its first line is dialogue instead of a name.

A real mispair still means: speaker names present on BOTH sides and DISAGREEING.

### FINAL word on the "anomalous rows" - three different causes

221 rows were flagged by a heuristic. They are NOT one phenomenon:

1. MISSING SPEAKER LINE (77 rows: rec144 63, rec132 9, rec149 4, rec131 1)
   English lost its speaker line and uses ASCII " instead of the kagi.
   -> SHIPPED DAMAGE. A script repairs it. Do not call it a mispair.

2. NAME SPELLING DRIFT (24 rows, scattered)
   Same character, minority spelling - "Zee" where the corpus says "Jie",
   "Hugi" for "Hugy". -> COSMETIC. Term rules fix it. Ignore.

3. GENUINE SPEAKER MISMATCH (~120 rows, in BLOCKS)
   The jp tag names a completely DIFFERENT character than the English, in
   several consecutive rows - e.g. rec147 rows 224-227: jp \u9244\u4e5f -> en "Loran",
   jp \u30b8\u30a8\u30fc -> en "Kamille", then "Rand". -> EXPORT MISPAIR. Our English is
   fine. LEAVE THESE ALONE and list the row numbers.

Known block: rec147 from about row 224 onward. rec119 has one too.

The test is still the speaker line, but read it carefully: a DIFFERENT NAME
means mispair; a MISSPELLED name means cosmetic; NO name at all means damage.
