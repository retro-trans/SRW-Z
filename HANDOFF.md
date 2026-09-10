# SRW Z handoff — 2026-09-10

Supersedes the 2026-09-08 handoff (v0.9.72 release work, PS2 freeze
resolution). That history now lives in `_work/CHANGELOG.md`; nothing in it is
an open blocker.

## Current status

**0.9.78 is built, verified, and on the user's PC. It is NOT released.**

    E:\Projects\SRW Z\SRW Z English v0.9.78.chd
    2,537,441,997 bytes   SHA1 cf4a49299caffe9ebe5115cc85ecb8577221b881
    chdman verify: raw SHA1 OK, overall SHA1 OK
    target image  8c626fa230fd7c2105833594e336c16d8e913ba6

The user reads builds off the PC directly, so no MEGA upload and no xdelta
unless they ask ([[test-build-delta]]). MEGA is waived anyway — account full.

**The master disc has moved well past 0.9.78.** Everything under "unbuilt"
below is written to `_work/iso/srwz_cap.bin` and gated, but is in no CHD. The
user was last testing 0.9.73.

## Workspace and source state

- Working images, tools, artifacts: `E:\Projects\SRW Z` (NOT the git repo)
- Master disc: `E:\Projects\SRW Z\_work\iso\srwz_cap.bin`
- JP reference: `E:\Projects\SRW Z\_work\iso\srwz.bin` (sha1 e8dbe37e…)
- Canonical repo: `E:\Projects\SRW-Z` — GitHub retro-trans/SRW-Z
- Branch `fix/caption-bleed`, HEAD `1118152`, pushed. Tree clean except a
  pre-existing untracked `tools/best_adapter/`.
- `origin/main` is still `8a5a0e8`. **Do not merge without being told**
  ([[branch-per-task]]).
- Latest published release is still v0.9.72. 0.9.73–0.9.78 are local builds.

Read first: `_work/CHANGELOG.md` (top section), `TRANSLATING.md`,
`docs/BASE_RULES.md`.

## Unbuilt since 0.9.78 — the case for 0.9.79

| change | scale |
|---|---|
| name-token overflow re-wrap | 109 rows |
| 総統 → Supreme Commander | 27 rows |
| Xabungle → akurasu | 766 changes, 3 pools |
| 無限獄 / Asakim cluster | 6 rows |
| Kazami's dropped noun | 1 row |
| Brai → Burai (SRVC) | 20 captions |
| 月光蝶 weapon name | 1 COMPDATA entry |

All gated green at handoff:

    struct intrusions 0 · integrity 0 problems · dead links 0 · brackets 0
    control bytes OK · SRVC index OK (353 blocks) · ELF patches present
    pointers 80,986 / 9  (BASELINE — memorise this pair)
    rows over the box 4  (pre-existing rec1/rec25 library entries)

Build recipe: run the gates, then

    tools/chdman.exe createcd -np 3 -i iso/srwz_cap.cue -o "E:\Projects\SRW Z\SRW Z English v0.9.79.chd"

alone — it gets OOM-killed if anything else heavy runs — then `chdman verify`,
then `tools/stamp_build.py <iso> 0.9.79 "<note>"`, then the CHANGELOG entry.

## Open decisions — the user's, not yours

1. **M-Fly captions.** 13 SRVC captions say "M-Fly" for 月光蝶. The dialogue
   (26 rows) and the weapon list are both correct now. A raw SRVC edit may not
   change a caption's byte length, and "Moonlight Butterfly" is 14 bytes longer
   than "M-Fly", so 12 of the 13 can carry the full name only if surrounding
   words give way (`"Use White Doll's M-Fly, no choice!"` →
   `"White Doll's Moonlight Butterfly!"`). One, at 19 bytes, cannot hold it at
   all. **The trade is the user's call and was explicitly left open.**
2. **Rey's line**, rec110 0x018cd0. 「おそらく皆、そうして真偽を気にする。なかなか穿った作戦だな」
   currently reads *"They'll all fret over what's real like that, no doubt. A
   shrewd tactic."* Not wrong, but clunky — "no doubt" is stranded and 真偽
   flattened. Proposed: *"No doubt they'll all worry about what's true and what
   isn't. A shrewd plan."* Needs relocation (81 B into a 79 B slot), routine.
   Offered; no answer yet.
3. **総統 splitting per character.** Applied uniformly to Gattler AND Seidel.
   The 大尉 precedent would allow splitting it; mentioned, not requested.

## Settled this session — do not re-open

- **`少将`** — no decision needed. My "General 10 / Major 9" was a
  substring-counting artifact ("Major General" contains both words). Real
  counts: Major General ×10, General ×1. One stray, fixed.
- **`少尉` = Ensign game-wide.** `中尉` is already Lt.; letting `少尉` also be
  Lt. would put two different ranks on screen identically.
- **`総統` = Supreme Commander**, all 27 rows.
- **Xabungle = akurasu**: エルチ Elchi, ホーラ Hola, コトセット **Cotset**,
  ダイク Dike. Re-confirmed against the wiki before sweeping — my recorded note
  said "Kotset" and was wrong. ブルーメ/Burume appears nowhere in this game.
  アデット is not on akurasu, so Adette stands on the disc majority.
- **Name-token width budget = the DEFAULT protagonist name**, wider of the two
  routes. A renamed protagonist can still clip: an accepted limit, not an open
  question. See [[name-token-width-budget]].

## The thing to understand before touching anything

**A STAGE-dialogue sweep cannot see most of this game's text.** The proofread
export defines a row by the japanese 「, so four pools sit outside every tool,
every sheet and every gate:

| pool | state |
|---|---|
| `rec0` — 110 stage summaries | swept 2026-09-10; was stale on every name decision |
| SRVC battle captions | Brai + Xabungle done; **the rest has never been audited** |
| COMPDATA weapon/unit pool | spot fixes only; **never audited** |
| parenthesised thoughts （…） | 2 fixed; **the rest has never been audited** |

Thoughts are the worst: they sit *inside* STAGE and look addressable, but no 「
means no key, so `apply_lines_relocating.py` cannot take them **and
`export_proofread`'s box gate never counts them**. Use
`tools/fix_offset_rows.py` (addresses a row by offset, appends past the record
end with a pointer rewrite) and measure their px by hand.

Both defects a player reported this session were in these pools. Nothing in the
toolchain would ever have found them.

## Hard-won facts about the tools

- **`reflow_dialogue.width()` is the single measurement.** It now substitutes
  the `$` name tokens (`NAME_TOKENS`) before measuring, so `wrap_field`,
  `reflow`, `apply_lines_relocating` and the box gate all inherit it. Do not
  add a private copy of that table to another tool.
- **`apply_lines_relocating.py` does NOT write text verbatim.** It calls
  `wrap_field`, which flattens the body and re-wraps it. Feeding it
  hand-wrapped text is pointless — fix the measurement instead. It reported
  "231 written in place" when 7 landed.
- **`export_proofread` strips 「」 before measuring px**, because the 400/505
  limits were calibrated that way. An audit that counts the brackets
  over-reports by up to 42 px per line — that turned a real 109 into a claimed
  231.
- **The byte slot is not a real constraint for STAGE rows.** They carry
  absolute pointers (BASE 0x7566F0), so a row that outgrows its slot relocates
  into a free gap or is appended past the record end. Only box width and the
  3-line cap actually bind.
- **SRVC captions may NOT change byte length** — scripted attack sequences
  fetch their lines by byte offset from tables we do not rebuild. Shorter is
  fine if padded with trailing spaces; longer is refused.
- **COMPDATA is already repacked.** `apply_pool.py` keys off the SHIPPED
  offsets, so running it now would move every string in the pool. For a small
  change, edit in place inside the existing slot — see
  `tools/fix_moonlight_butterfly.py`.

## Known soft spot, not yet fixed

`fix_srvc_words.py`, `fix_srvc_names.py` and `fix_srvc_burai.py` sweep the
entire 3.7 GB image and decide what is a caption by whether the bytes look
printable. They **write**. Nothing has broken and the guard has held, but they
should be bounded to SRVC's two extents (LBA 1313214 plus the relocated copy)
rather than trusting a heuristic. Cheap — do it before the next SRVC pass.

## Working discipline that earned its keep

**Six times this session a tool reported success while leaving the defect in
place**: a term split across a line break, rank words a sweep did not match,
names one byte over budget, a wrapper undoing its own input, a sweep keyed on
the wrong japanese term. Every one was caught by **re-running the audit
afterward**, never by the tool's own count.

Do not report a pass as done because the tool said so. Re-measure.

Other standing rules: never post GitHub comments as the user (drafts only —
code pushes are fine); names come from akurasu, verified at the time, not from
memory; update the Google Sheets after any dialogue fix (`sheets_preserve.py`
immediately before `sheets_push.py --only <BOOK>`, and `--only` takes a
WORKBOOK number, not a record number); the glossary must carry every library
term.

## Reading progress

rec111–rec121 read line by line, ~5,650 rows (stages 48–60). Earlier stages
were covered by prior passes; stages 40–47 are the known-bad "sonnet range"
(~26% defect rate) and were re-read in an earlier session.
