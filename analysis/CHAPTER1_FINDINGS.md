# Chapter 1 — status and findings

## Conclusion

The chapter 1 **scenario text is compressed** and cannot be safely translated
or reinserted until the decompressor is reverse engineered.

The chapter 1 **battle dialogue is not compressed** and is translatable today
using the same in-place technique already proven on the ELF and MAPNAME.BIN.

## Evidence for compression

Two independent files contain the same stage-1 synopsis, and both encode the
same phrase with the *same* byte sequences:

    DATA/STAGE.BIN @ 0x2723   ...グローリ <17><16> ・スタ <1F><10> ? に...
    DATA/HSFC.BIN  @ 0x001C   ...グロ G<11><8A><17><16> ・スタ <1F><10> I...

Identical markers (`17 16`, `1F 10`) in identical positions across two files
means a shared compressor, not per-file control codes.

The gaps land exactly where **repeated** characters belong. Expanded, the
first line reads as grammatical Japanese:

    戦技研究班グローリ[ー]・スタ[ー]により、
    "...by the combat research team Glory Star,"

`ー` had already occurred 4 bytes earlier in `グロー`. Literal text is stored
raw; repeated substrings become short back-references. Bytes below 0x20 are
impossible in valid Shift-JIS, which makes them free to use as markers.

## What was ruled out

- **Not a control-code language.** Frequency analysis over the dialogue
  regions found 3,228 distinct codes in only 4,277 occurrences — roughly one
  use each. A real control-code set repeats a small vocabulary. The only
  confirmed code is `0A` = newline (304 uses).
- **Not classic LZSS with inline flag bytes.** 21 consecutive characters
  decode cleanly with no flag byte interleaved, so the flag mechanism is not
  the standard one-flag-byte-per-eight-tokens layout.
- **Not a container/framing problem.** There is no compression header before
  the text; it sits inside a bytecode stream.

## Why the back-reference encoding did not fall to inspection

For the first reference the answer is known: at STAGE.BIN 0x274F the marker
`17 16` must expand to `ー` (81 5B), which sits 4 bytes earlier at 0x274B —
so length 2, distance 4. No straightforward reading of the bytes 0x17/0x16
yields (2, 4):

    0x17 low nibble = 7      0x16 = 22      0x16 & 0x0F = 6

None map to distance 4. The scheme likely uses a sliding-window base or a
bit-packed field rather than plain byte fields, so it needs the actual
routine rather than guesswork.

## Recommended next step

Locate the decompressor in the boot ELF (SLPS_258.87) and read the MIPS.
Practical approach: the routine will be called with a pointer into
STAGE.BIN/HSFC.BIN, so trace from the stage-load path, or set a PCSX2
breakpoint on a read of 0x2723 in the loaded STAGE.BIN buffer and step out.
Once the window size and field layout are known, both decompression and
recompression are mechanical.

## What is translatable right now

`BTL/SRVC.BIN` holds ~1.08M characters of **uncompressed** dialogue — the
phrase `グローリー・スター` appears literally 70 times with its `ー` intact.
The container is still unsolved, but in-place byte-budget replacement does
not need it: replace each null-terminated string with English no longer than
the original and pad with nulls. Nothing shifts, no pointer is touched.

Japanese costs 2 bytes/char in Shift-JIS and English ~1, so a translated line
generally has roughly double the character budget of the original.

## Legible fragments of the stage 1 synopsis

Readable portions of HSFC.BIN @ 0x1C, gaps marked `[...]`:

    月面ルテチウム基地を襲撃するエゥーゴ。
    それをバ[...]ラで迎え[...]グロ[ーリー]・スタ[ー]であったが、
    戦[...]いの最中、空間のねじ[れ...]巻き込ま[...]
    漂着したコロニー内[...]繰り広[...]モビ[ルスーツ...]争奪戦。
    シンはイ[ン]パ[ルス...]を駆[...]侵入者を[...]
    新[...]転移[...]の戦い[...]ミネ[ルバ...]再び[...]世界

Reading (gaps inferred from grammar and context — NOT a verified translation):

    The AEUG assaults the Lunar Lutetium Base. Glory Star moves to intercept
    them, but in the midst of the battle they are caught up in a distortion
    of space. A struggle over mobile suits breaks out inside the colony they
    drift into. Shin, piloting the Impulse, goes after the intruder. A new
    dimensional shift occurs... the Minerva... once again... world.

This is a reading aid only. The inferred spans are guesses constrained by
grammar; they must not be treated as source text for a patch.
