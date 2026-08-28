# The tools

Every script in `tools/`, what it is for, and how to run it. Generated from the tools' own docstrings by `tools/gen_tools_doc.py` - re-run it after adding or removing a tool rather than editing this file.

**If you are starting a translation**, you need five of them: `extract_script.py`, `apply_script.py`, and the three gates `verify_pointers.py`, `verify_elf_patches.py`, `integrity.py`. Everything else is there for when you hit the specific problem it solves. Start with [TRANSLATING.md](TRANSLATING.md).

Two warnings that are not obvious from any docstring:

* **Verify against the image, not against a tool's report.** Several bugs here were "the fix existed and never reached the image". A tool saying it applied 400 changes is not evidence the game changed.

* **Menu text is not cp932.** ASCII `0x2E-0x3D` are control codes to the menu reader, so digits and periods in menu strings must go through `patch.encode(s, "menu")`.

| Section | Tools |
| --- | ---: |
| [The pipeline](#the-pipeline) | 5 |
| [Gates - run these before every build](#gates--run-these-before-every-build) | 8 |
| [Libraries - imported, not run](#libraries--imported-not-run) | 5 |
| [ISO plumbing](#iso-plumbing) | 7 |
| [Build and packaging](#build-and-packaging) | 5 |
| [Translation data](#translation-data) | 11 |
| [Applying text to the image](#applying-text-to-the-image) | 4 |
| [Fixing specific defects](#fixing-specific-defects) | 15 |
| [Patching the executable, art and UI](#patching-the-executable-art-and-ui) | 35 |
| [Generators](#generators) | 4 |
| [Scanning and auditing](#scanning-and-auditing) | 8 |
| [Searching](#searching) | 2 |
| [Font and texture work](#font-and-texture-work) | 8 |
| [Battle voice lines (SRVC)](#battle-voice-lines-srvc) | 9 |
| [Live instrumentation](#live-instrumentation) | 8 |
| [Layout and re-wrapping](#layout-and-re-wrapping) | 1 |
| [Everything else](#everything-else) | 36 |

## The pipeline

The five you need on day one. `extract_script` pulls every string out of an image YOU dumped into editable JSON; you translate the `text` fields; `apply_script` writes them back. Round-trip is exact - extract, change nothing, apply, and the image is byte-identical. The `english_script` pair moves this project's English in and out as standalone source, which is what makes the repo forkable without shipping the publisher's text.

**`apply_english_script.py`**  
Re-apply analysis/english_script.json to a disc image.

**`apply_script.py`**  
Write an edited extract_script.py file back into a disc image.

**`build_compare.py`**  
Build a side-by-side Japanese/English comparison table as a single HTML file.

**`export_english_script.py`**  
Export the ENGLISH script as standalone, publishable source.

**`extract_script.py`**  
Extract every text string from a disc image into an editable JSON file.

## Gates - run these before every build

Each of these exists because something shipped broken. `verify_pointers` is the important one: the failure it catches produces an image that boots, plays, and freezes only when a save is loaded. `check_publishable` is the newest - it reads CONTENT rather than paths, so it can see the original japanese sitting inside an otherwise publishable file, which `.gitignore` cannot.

**`check_publishable.py`**  
Refuse to publish the original japanese script.

**`fix_dead_links.py`**  
Make every glossary link in dialogue resolve to a real keyword entry.

**`integrity.py`**  
Structural integrity check of a built ISO.

**`scan_visible_defects.py`**  
Scan every STAGE record for defects a PLAYER would see on screen.

**`verify_elf_patches.py`**  
Assert every ELF patch is present in an ISO. Run BEFORE building a CHD.

**`verify_iso.py`**  
Read the patched files back out of the ISO and confirm the English is there.

**`verify_pointers.py`**  
Structural gate: every pointer must still land on the START of a string.

**`verify_spirits.py`**  
Assert no two spirit commands share a name.

## Libraries - imported, not run

`banlz` is the Banpresto LZ codec, ported from the boot ELF; almost everything else depends on it. `patch` holds the text encoder - note that ASCII 0x2E-0x3D are CONTROL CODES to the menu reader, so menu text must be encoded with `patch.encode(s, "menu")` rather than plain cp932. `pool` handles the COMPDATA string pool.

**`banlz.py`**  
Banpresto LZ codec for SRW Z (PS2), ported from the boot ELF.

**`banlz_strict.py`**  
Decode banlz streams the way the GAME does, and flag what our decoder hides.

**`patch.py`**  
Byte-budget-safe in-place patcher.

**`pool.py`**  
COMPDATA string pool: enumerate, repack, and repoint.

**`rewrap_dialogue.py`**  
Re-wrap every over-wide dialogue string in STAGE.

## ISO plumbing

Reading and writing the disc itself: list the ISO9660 tree, pull a file out, splice one back in, fix the directory record when a file changes size, and diff two 3.5GB images at sector granularity.

**`bin2iso.py`**  
Convert a MODE1/2352 .bin track into a plain 2048-byte/sector .iso.

**`diff_images.py`**  
Diff two 3.5GB PS2 disc images at sector granularity, report changed LBA ranges, and label each with the file it belongs to via the game's internal file table (\\DATA\\NAME... [u32 LBA][u32 sectors] at name+0x20).

**`isoextract.py`**  
Extract files out of the PS2 ISO by LBA + size, using the TSV from isolist.py.

**`isolist.py`**  
Dump the full ISO9660 file tree of a PS2 disc image.

**`pullelf.py`**  
Find and extract the boot ELF (SLPS_xxxxx / the SYSTEM.CNF BOOT2 target) from a PS2 ISO. Reuses the ISO9660 walker approach from isolist.py.

**`splice_file.py`**  
Write a same-size file back into the ISO at a known LBA (no relocation, no pointer edits). Verifies the size matches the original before writing.

**`update_dirsize.py`**  
Patch the ISO9660 directory-record data-length for a file so the emulator loads the full (grown) ELF. Usage: update_dirsize.py <iso> <NAME> <newsize> Scans the root directory extent (from the PVD at LBA 16) for the 8.3 name and rewrites the 8-byte size field (LE u32 at rec+10, BE u32 at rec+14).

## Build and packaging

`stamp_build` fingerprints every region the game loads, so "what changed between these two builds?" is answerable without extracting both CHDs - a question that once cost a day. `project_stats` measures translation coverage from the image rather than from any tool's report.

**`build_texture_pack.py`**  
Package the PCSX2 texture-replacement pack that ships with a build.

**`project_stats.py`**  
Whole-project statistics for the SRW Z English patch.

**`stamp_build.py`**  
Fingerprint every region the game loads, so "what changed between two builds?" is answerable instantly.

**`stamp_terrain_glyphs.py`**  
Draw micro AIR/GND/SEA/SPC art into the terrain kanji font cells.

**`zkn_build.py`**  
Rebuild the encyclopedia archives with translated text.

## Translation data

Not tools - dictionaries. Mostly japanese term to english name, which is reference material rather than script: the japanese side is the LOOKUP KEY the patch tools match on, so it cannot be removed without breaking them.

**`abilities_en.py`**  
English for the 55 ability/skill descriptions in COMPDATA 0x6B8F0..0x6D0C0.

**`battle_quotes_en.py`**  
English for the pilot battle quotes in COMPDATA (defeat / retreat lines).

**`compdata_en.py`**  
English tables for DATA/COMPDATA.BN rec0 (names, titles, bios).

**`compdata_ui_en.py`**  
English for COMPDATA record 0 UI strings: leader-bonus effects and names, stat descriptions, search-screen labels, and squad-bonus text. Keyed by the decompressed-record offset. Menu-rendered -> patch_compdata encodes these with mode "menu" (digits and . / : ; < = become fullwidth, 2 bytes each), so keep digits sparse and avoid ':' and '/'.

**`elf_ui_en.py`**  
English UI strings for the boot ELF (SLPS_258.87), keyed by file offset.

**`epilot_en.py`**  
Enemy pilot / generic crew designations (COMPDATA ~0x24000-0x2C000).

**`gen_missing3_en.py`**  
Translate the 463 dialogue fields the extractor never saw (see gen_missing3).

**`mtvpros_en.py`**  
English prologue narration for DATA/MTV_PROS.BIN rawt chunks.

**`soundsel_names.py`**  
Base-name romanizations + song titles for the Sound Select tables.

**`units_en.py`**  
Canon English names for the 117 unit slots still Japanese in COMPDATA.

**`zkn_names_en.py`**  
Curated encyclopedia (図鑑) name translations: series titles and glossary terms.

## Applying text to the image

**`apply_fixes.py`**  
Splice proofreading fixes into the shipped image.

**`apply_names.py`**  
Normalise speaker names game-wide to the wiki-canonical spelling.

**`apply_pool.py`**  
Repack the COMPDATA string pool and splice it back into an image.

**`apply_quotes_links_all.py`**  
Game-wide dialogue polish: kagi quotes + glossary links (all records).

## Fixing specific defects

Each of these was written for one bug found by someone playing the game and noticing something wrong on screen. They are kept because the TECHNIQUE generalises even when the specific fix does not.

**`fix_body_terms.py`**  
Normalise names and terms INSIDE dialogue, not just on the speaker line.

**`fix_fullwidth.py`**  
Fullwidth punctuation -> ASCII, in ENGLISH DIALOGUE only.

**`fix_ghingnham.py`**  
ゲンガナム is "Ghingnham", not "Gendarme".

**`fix_hard_lines.py`**  
Shorten the 8 dialogue lines that cannot fit the box once $ expands.

**`fix_literal_nl.py`**  
224 rows carry a LITERAL backslash-n instead of a real line break, so the dialogue box shows the characters \n to the player:

**`fix_literal_nl_global.py`**  
Unescape LITERAL backslash-n across ALL 205 STAGE records.

**`fix_lowen_captions.py`**  
Normalise every spelling of レーベン to Lowen in the battle captions.

**`fix_placeholder_wrap.py`**  
Re-wrap dialogue whose $ placeholders overflow the box once expanded.

**`fix_pool_strays.py`**  
Repair the pool pointers that 0.8.81's repack left behind.

**`fix_popup_wrap.py`**  
Restore the line breaks that translation dropped from long STAGE strings.

**`fix_rank.py`**  
\u51c6\u5c06 (Brigadier General) ships six different ways across 131 rows: General 79, Colonel 20, Vice Admiral 12, Brigadier General 10, Major General 6, Commodore 4. Agents keep fixing it one row at a time; this settles it.

**`fix_row.py`**  
Replace individual dialogue rows, from a list of hand-written corrections.

**`fix_terms_global.py`**  
Term fixes across ALL 205 STAGE records, not just the 26 that were exported.

**`fix_terms_grow.py`**  
Term fixes whose replacement is LONGER than the text it replaces.

**`fix_terms_pass.py`**  
Term fixes resolved through the pointer, so RELOCATED rows are covered.

## Patching the executable, art and UI

The largest family, because most of the UI is not text at all. Anything that cannot be found as cp932 anywhere on the disc is ART, and has to be repainted with the artwork's own palette indices.

**`patch_backlog.py`**  
Backlog (Triangle) rendering fixes for VWF English text.

**`patch_bazaar_buttons.py`**  
Paint "Buy"/"Sell" over the bazaar 購入/売却 button glyphs.

**`patch_caption_paging.py`**  
Battle voice-caption paging fix, v3 (option B done right).

**`patch_compdata.py`**  
Translate DATA/COMPDATA.BN (names, episode titles, bios) and splice it.

**`patch_effect_strings.py`**  
Translate the CODE-BUILT weapon-effect names on the weapon screen.

**`patch_elf_labels.py`**  
Shorten fixed ELF UI labels that collide with the value next to them.

**`patch_ep_labels.py`**  
Translate the 第/話 episode-marker kanji in the ELF label tables.

**`patch_flushlog.py`**  
Investigation logger: capture the FULL per-glyph struct at blit time to free EE RAM (0x1400000), so PINE can read the real texture-base + UV values that the flush consumes. NO width change -> logs clean FULLWIDTH values. Apply on top of patch_renderer only.

**`patch_font.py`**  
VWF step 1: swap fullwidth Latin/digit glyphs for half-width ones (multi-cave).

**`patch_font_advance.py`**  
VWF step 2: half pen-advance for the (squished) Latin/digit glyphs.

**`patch_font_destwidth.py`**  
VWF step 3: half the sprite DEST-WIDTH for Latin/digit glyphs.

**`patch_font_shadowadv.py`**  
VWF step 4: half the SHADOW pen advance for Latin codes.

**`patch_font_squish.py`**  
VWF (reliable, code-only): condense fullwidth Latin glyphs to half-width.

**`patch_hsfc_recaps.py`**  
Translate the episode-recap bank shown on the save/load screen.

**`patch_hwfont.py`**  
HALF-WIDTH FONT v2 - MASTER-FONT ARCHITECTURE (the validated design).

**`patch_intermission_labels.py`**  
Paint the intermission/ticker JP kanji textures in English.

**`patch_library_nisv.py`**  
Translate the LIBRARY menu in the ISO - the texture the game ACTUALLY draws.

**`patch_linkpos.py`**  
Fix glossary-link (and any segment) X drift with the VWF font.

**`patch_log.py`**  
Instrument the glyph blit to log per-glyph dest+source coords to a RAM ring buffer, so PINE can read the exact numbers.

**`patch_lvlup_spirits.py`**  
Level-up popup: pin the Spirits column in place.

**`patch_mapmodel_terrain.py`**  
Terrain-zone names inside MAPMODEL.BIN (LBA 1652964, 55 MB).

**`patch_micro_glyphs.py`**  
MICRO-GLYPHS: kanji cells re-drawn as Latin art, at the kanji's own width.

**`patch_mtvpros.py`**  
Translate DATA/MTV_PROS.BIN (prologue + interlude narration) and splice it.

**`patch_op_titles.py`**  
Translate the OPENING's series-title cards (OP0/OP1/OP2.BIN).

**`patch_outline_half.py`**  
Experiment: halve the glyph OUTLINE offsets globally.

**`patch_renderer.py`**  
ASCII -> fullwidth glyph renderer patch for SRW Z (SLPS-25887).

**`patch_spirit_abbrev.py`**  
Point the spirit-command UI at the private micro-glyph codes.

**`patch_srvc_kagi.py`**  
Battle voice captions: ASCII "quotes" -> kagi brackets 「」.

**`patch_srvc_polish.py`**  
SRVC caption text polish v2 (in-place, same-length).

**`patch_terrain_glyphs.py`**  
PERMANENT terrain micro-glyphs: AIR / GND / SEA / SPC / WTR.

**`patch_titlecards.py`**  
Repaint the chapter TITLE CARD textures in English.

**`patch_underline.py`**  
Pixel-accurate glossary-link underline (v2 FINAL, companion to patch_linkpos).

**`patch_vlabels.py`**  
Translate the VERTICAL labels on the in-battle unit/pilot status screens.

**`patch_vwf1.py`**  
True-VWF step 1: per-Latin-glyph flag + REAL dest-width (flush-based).

**`patch_vwf_widths.py`**  
Make the half-width Latin font PROPORTIONAL - advance-only (v2).

## Generators

**`gen_hwatlas.py`**  
Half-width glyph atlas v5 - GRAYSCALE (2bpp, 4 alpha levels).

**`gen_intro_cards.py`**  
PCSX2 texture replacements for the prologue title cards.

**`gen_missing3.py`**  
Build an OFFSET-KEYED worklist of dialogue the extractor never saw.

**`gen_tools_doc.py`**  
Generate TOOLS.md - one line per tool, grouped by what it is for.

## Scanning and auditing

**`audit_names.py`**  
Audit every name in analysis/db_en.json against the corpus.

**`caption_audit.py`**  
Rank battle captions by how likely the english is WRONG, not just short.

**`ftable_audit.py`**  
Audit the game's own filename->LBA table for overlapping extents.

**`scan_broken_quotes.py`**  
Find dialogue rows whose quoting is broken - the class the Zushi row is in.

**`scan_empty_speaker.py`**  
Rows whose SPEAKER LINE was emptied - the box renders completely blank.

**`scan_speaker_mismatch.py`**  
Find rows whose SPEAKER name disagrees with the japanese speaker field.

**`status.py`**  
Translation state, measured from the BUILT ISO rather than from tool logs.

**`zkn_audit.py`**  
Audit the in-game LIBRARY (encyclopedia) text as it exists in the image.

## Searching

**`find_passthrough.py`**  
Find T entries whose 'English' is actually the Japanese source copied through.

**`link_overlap.py`**  
Restore the 《Overlap》 links the Japanese script had, and one missed line.

## Font and texture work

The font is HALF-WIDTH, not variable-width: the stamper writes a constant 12 and the advance hook adds 1, giving a flat 13px pitch. See docs/VWF.md and docs/CUSTOM_FONT.md before touching any of this.

**`compare_atlases.py`**  
Render the same sample text with the shipped atlas and candidate atlases.

**`export_font_sheet.py`**  
Export the half-width Latin font actually stamped into the game.

**`font_texture.py`**  
Export the glyph atlas as an editable texture, and import an edited one back.

**`make_ascii_font.py`**  
Generate a half-width ASCII glyph atlas + width table for the SRW Z VWF patch.

**`make_font_data.py`**  
Generate half-width ASCII glyph data + index table for the VWF boot-hook.

**`rasterise_font.py`**  
Rasterise a TrueType face into the game's 12x24 half-width atlas format.

**`set_atlas.py`**  
Write a 69x72-byte glyph atlas into the image's font cave.

**`sim_vwf_tramp.py`**  
Simulate the v2 advance trampoline before writing it.

## Battle voice lines (SRVC)

Captions are free-length once the sequence records are repointed with `--free`, so there is no byte budget to fight.

**`srvc_apply.py`**  
Apply the English battle voice lines to BTL/SRVC.BIN and splice into an ISO.

**`srvc_bytefit.py`**  
Shorten battle quotes so none EXCEEDS its original byte length.

**`srvc_deepseek.py`**  
Translate the battle voice lines (BTL/SRVC.BIN) via DeepSeek.

**`srvc_fit.py`**  
Fit a battle-caption translation into its ORIGINAL byte budget.

**`srvc_line_fixes.py`**  
Targeted battle-caption line corrections (post-review).

**`srvc_pairs.py`**  
Pair every battle caption to its japanese, through the sequence records.

**`srvc_records.py`**  
Resolve the voice/sequence records inside SRVC blocks.

**`srvc_refit.py`**  
Re-translate the battle lines that overflow the box, with per-line budgets.

**`srvc_work.py`**  
Build the battle-voice worklist from BTL/SRVC.BIN.

## Live instrumentation

PCSX2 is driven over its PINE socket to watch the running game - where a string is drawn, which code path renders it. See docs/DEBUGGER_TRACE.md.

**`capture.ps1`**  
Screenshot capture helper for PCSX2.

**`click.ps1`**  
Send a mouse click to the emulator window.

**`drive.ps1`**  
Drive the emulator through a scripted input sequence.

**`nav_charsel.ps1`**  
Navigate to the character-select screen.

**`nav_corridor.ps1`**  
Navigate to the corridor scene.

**`nav_tocorr.ps1`**  
Navigate toward the corridor scene.

**`pine_dump.py`**  
Dump a range of PCSX2 EE RAM via PINE to a file. Usage: python pine_dump.py <hex_addr> <nbytes> <out.bin> Reads in 32-bit words (op=2), batched, so any range works.

**`pine_read.py`**  
Minimal PINE client to read PCSX2 EE memory, and dump the glyph log buffer.

## Layout and re-wrapping

Dialogue is 3 lines of 34 columns; scenario-chart recaps get 56.

**`make_slices.py`**  
Cut the exported review files into agent-sized slices.

## Everything else

**`battle_quotes_en_b.py`**  
Battle quotes, second half. Merged with battle_quotes_en.BATTLE_QUOTES.

**`caption_review.py`**  
Print paired captions for a human to read, one detector class at a time.

**`check_alignment.py`**  
Find rows where our English does not correspond to its Japanese source.

**`compare_captions.py`**  
Check the BATTLE VOICE LINES against the japanese, from your own disc.

**`compare_translation.py`**  
Check this translation against the original, using only your own disc.

**`compdata_ui_en_b.py`**  
Episode/scenario titles (the "Ep. N <title>" line and the scenario chart), route-select labels, and the character-select taglines/bio. Offset-keyed in COMPDATA record 0; menu-encoded, so digits and . / : ; < = cost 2 bytes each.

**`corridor_polish.py`**  
Production pass for the corridor scene (rec001 rows 142-211).

**`disasm.py`**  
Small MIPS disassembler used by the RE tools.

**`export_pairs.py`**  
Export our English keyed by JAPANESE offset, so one disc is enough to compare.

**`export_review.py`**  
Export JP/EN pairs for proofreading, straight from the SHIPPED image.

**`export_synopses.py`**  
Export the stage synopses as ENGLISH, keyed by scenario record.

**`harvest_labels.py`**  
Compose the intermission bar labels from HARVESTED original glyphs.

**`intermission_hotpatch.py`**  
Live-iterate the intermission label fonts via PINE.

**`mdis.py`**  
Word-by-word MIPS disassembler for PS2 EE code.

**`name_map.py`**  
Ship the name maps as FINGERPRINTS, and rebuild them from your own disc.

**`preview_16level.py`**  
Show 4-level vs 16-level alpha for the SAME face, at real size.

**`release.py`**  
Cut a release: branch it, archive the source, attach everything.

**`relink_missing.py`**  
Restore glossary links the English script dropped.

**`rename_term.py`**  
Rename a term everywhere in STAGE.BIN, conditioned on the japanese.

**`rendercmp.py`**  
Compare structural markers of the text renderer between two PS2 ELFs, to see whether both use SRW Z's two-pen + 8-sprite-outline scheme.

**`restore_region.py`**  
Restore one file's sectors in an ISO from the original Japanese image.

**`review_status.py`**  
Track which scenario records a human has actually read.

**`srvc.py`**  
Parse and rebuild BTL/SRVC.BIN using its companion BTL/SRVC.SEG.

**`ui_batch10.py`**  
Fix pass: forecast/char-select overlaps + control-code mode-select strings.

**`ui_batch2.py`**  
Skill & spirit names + descriptions (ELF 0x335E50-0x337740).

**`ui_batch3.py`**  
Intermission UI: shop, formation, upgrade, training, parts, name entry.

**`ui_batch4.py`**  
Save/memory-card system messages + series titles (0x33Axxx).

**`ui_batch5.py`**  
Battle prep / squad list / results UI (0x341300-0x343400).

**`ui_batch6.py`**  
Map/sortie/battle-flow UI (0x343400-0x3455B0).

**`ui_batch7.py`**  
Options, search, library, transfer, Q&A (0x345600-0x347CC0).

**`ui_batch8.py`**  
Bazaar item flavor descriptions (0x33C400-0x33D780).

**`ui_batch9.py`**  
Library, dialogue viewer, formation confirms, upgrade extras (0x33DA-0x33F6).

**`unify_overlap.py`**  
One English name for 相克界: "Overlap".

**`zkn.py`**  
Reader/writer for the encyclopedia files (MTVZKNRT/PT/KW = 図鑑 robot / character / keyword).

**`zkn_deepseek.py`**  
Translate encyclopedia descriptions via DeepSeek, in the batch-file format.

**`zkn_name_check.py`**  
Cross-check every LIBRARY name against the glossary DB, by Japanese key.
