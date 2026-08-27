# Contributing

Start with [TRANSLATING.md](TRANSLATING.md) — it covers the extract/edit/apply
loop and the rules the engine enforces.

## What is most useful

1. **Proofreading.** 141 of the 205 scenario records have never been read by a
   human. They are mechanically clean — names, links, punctuation and escapes
   are all correct — but nobody has checked whether the prose makes sense.
   Wrong-but-well-formed translations are what is left.
2. **Reading a record against its Japanese.** `tools/build_compare.py`
   builds a side-by-side table from your own two images and pairs every row
   through the pointer table - 100% on all 68,628 dialogue rows. It labels
   each row `pointer`, `same-offset` or `suspect` rather than presenting a
   guess as fact, so you can see which rows to trust. (The older
   `export_review.py` guesses when no pointer references an offset, and is
   wrong on every relocated row - that is where the “30% mispaired” figure
   in `analysis/review/EXPORT_TRUST.md` came from. Use build_compare.)
3. **Other languages.** The toolchain is language-agnostic. cp932 is the
   constraint: the font has no accented Latin characters, so languages needing
   them also need font work.

## House rules

**Verify against the image, not against a tool's report.** Several bugs here
were "the fix existed and never reached the image". A tool saying it applied 400
changes is not evidence that the game changed.

**Run the gates before every build.** They are in TRANSLATING.md. The pointer
gate especially — the failure it catches produces an image that boots, plays,
and freezes only when a save is loaded.

**Do not commit** disc images, extracted game files, the original Japanese
script, or third-party binaries. `.gitignore` covers the obvious cases.

**On Windows**, anything using `multiprocessing` must be a real file on disk,
never a heredoc — spawned workers re-import the module and cannot import
`<stdin>`. This has bitten the project three times.

## Reporting a bug in the translation

A screenshot is worth more than a description. Most of the real bugs found in
this project were spotted by someone playing it and noticing something odd on
screen, not by any automated check.
