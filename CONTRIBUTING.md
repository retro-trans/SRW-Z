# Contributing

Start with [TRANSLATING.md](TRANSLATING.md) — it covers the extract/edit/apply
loop and the rules the engine enforces.

## What is most useful

1. **Proofreading.** 141 of the 205 scenario records have never been read by a
   human. They are mechanically clean — names, links, punctuation and escapes
   are all correct — but nobody has checked whether the prose makes sense.
   Wrong-but-well-formed translations are what is left.
2. **The export-pairing problem.** See `analysis/review/EXPORT_TRUST.md`. Around
   30% of exported rows pair the wrong Japanese with the right English, which
   blocks proofreading on 55 records. Fixing it needs the per-record string
   referencing scheme worked out.
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
