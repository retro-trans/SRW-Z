# The PS2 hardware freeze — investigation notes

**Status: fixed on the reported PS2 setup. The user confirmed Diagnostic C
works on 2026-09-08. The same image is packaged as v0.9.72.**
Last updated 2026-09-08.

---

## Follow-up: the missing alignment invariant

The earlier investigation checked caption lengths, voice IDs, and offsets
against file bounds, but did not check **address alignment**. `SRVC.BIN`
contains binary headers and voice/caption records as well as text. The engine
uses ordinary `lhu` and `lw` to read those records; these require aligned
addresses on the EE.

The original `tools/srvc.py:build()` appended the OLD block padding after
variable-length translated strings. That does not preserve alignment: once a
block changes length, the next block starts at an arbitrary byte offset.
Recomputing `SRVC.SEG` makes the offsets numerically correct but still unsafe
for the CPU's aligned loads.

Direct audit of the ISO files, using their ISO9660 directory entries:

| Image | Blocks | Starts not aligned to 16 bytes | Not aligned to 4 | Odd starts |
|---|---:|---:|---:|---:|
| Japanese `srwz.bin` | 353 | 0 | 0 | 0 |
| Pre-fix `srwz_cap.bin` | 353 | 323 | 254 | 162 |
| 0.9.66 / 0.9.71 | 353 each | 323 | 254 | 162 |
| Diagnostics A / B | 353 each | 323 | 254 | 162 |

For example, Japanese block 4 starts at `0x9B0`; ours starts at `0x986`.
Its final cell is at block-relative `0xC84`, giving archive address `0x160A`,
which is two bytes off a word boundary. Block 16 starts at `0x1BFC5` and
puts its final cell at `0x1D281`, an odd address.

The relevant original instructions are unchanged by our patch:

```
0x2EA5BC  lhu a0,0(s0)       read clip ID on caption start
0x2EA5C8  jal 0x181830       request voice playback
0x2EA604  lw  v1,4(s0)       read caption offset from the same record
0x2EA3C4  lhu a0,0(s1)       read clip ID on page advance
0x2EA3F0  lw  v1,4(s1)       read caption offset on page advance
```

Odd record addresses can fault at the clip-ID read; addresses congruent to 2
modulo 4 can get past that read and fault at the caption-offset read. This
fits the reported boundary where speech/captions should start. Removing the
caption caves cannot fix it: these reads happen before either cave is called.

There is also evidence that misalignment survives loading. The existing
`_work/analysis/_btl_ram.bin` emulator RAM dump contains an SRVC block 285
header at `0x0160D312`, referenced by aligned pointer fields at `0x005FB5D4`,
`0x005FB5E4`, and `0x005FDE20`. Fields at `0x005FDC5C` and `0x005FDC60`
point into its record region at `0x0160E57E` and `0x0160E586`, also misaligned
for `lw`. This is an archived emulator dump, **not a capture of the tester's
freeze**; its caption and glyph-dedup hook sites are original, so it is not
evidence about the current glyph-cache patch.

PCSX2's interpreter source explicitly checks alignment for `LH`/`LHU`/`LW`,
but its `RaiseAddressError` helper says the exception is not actually raised
in the guest CPU yet. Emulator success therefore does not rule out an EE
Address Error. See the [PCSX2 implementation](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/R5900OpcodeImpl.cpp).
This supports the hardware/emulator distinction; it is not a hardware trace.

### Repair and verification

`tools/srvc.py` now pads every emitted block to 16 bytes, including opaque
blocks, before recording the next SEG offset. The working copy under
`_work/tools` has the same fix.

`tools/audit_srvc_alignment.py` is a read-only ISO gate, with an optional
`--emit-aligned DIR` mode that writes repaired standalone `SRVC.BIN` and
`SRVC.SEG` files. It treats existing blocks as opaque bytes: no strings,
headers, voice IDs, or within-block offsets are rewritten.

The verified current-image repair is in
`_work/analysis/ps2_aligned_srvc/`:

- Adds exactly **2,173 zero bytes**, yielding **2,917,408 bytes / 1,425 sectors**.
- Preserves all 353 existing block payloads byte for byte, with zero padding
  added only after each block.
- All block starts and the EOF sentinel are now 16-byte aligned.
- Running the repair again is byte-identical.
- The repaired builder round-trips the entire Japanese archive byte-identically
  and produces exactly the same repair as the opaque-block method on ours.
- Malformed SEG boundaries are rejected. This initial repair left the
  production image untouched. After the successful PS2 test, the v0.9.72
  build promoted the aligned image to `srwz_cap.bin`, preserving its previous
  contents as `_work/iso/_pre0972.bin`.

**Hardware test performed:** the user tested Diagnostic C and reported
"It works!!!" on 2026-09-08. It contains both aligned files and the same ELF.
`SRVC.BIN`'s ISO9660 byte size
(both endian fields) must reflect the repaired file. The current game's own
file table still reserves the original **1,618 sectors**, so the repaired
**1,425-sector** file fits without changing that table or relocating anything.
A test using only the BIN without the new SEG is invalid. Diagnostic C isolates
alignment; its successful PS2 result confirms this repair resolves the reported
freeze. Diagnostic B still has the misaligned data and remains vulnerable
under this explanation.

### Diagnostic C passed the user's PS2 test

Local patch: `E:\Projects\SRW Z\SRWZ-DIAG-C-aligned-srvc.xdelta`
(5,724,801 bytes). Apply it to the **original Japanese 2048-byte-sector image**,
not an already patched image. Instructions are beside it in
`SRWZ-DIAG-C-aligned-srvc.txt`.

The resulting image is `_work/iso/_diag_aligned_srvc.bin`. Compared with the
current English image, a full-image verification permits differences only in
three regions: SRVC.BIN (including its sector padding), SRVC.SEG, and the
eight ISO9660 size bytes. The ELF and game file table are byte-identical.
Decoding the xdelta was also verified against the entire target image hash.

| Artifact | SHA1 |
|---|---|
| Original Japanese source | `e8dbe37e88afe8f82d48889b0775274ccde3cf99` |
| Current English comparison image | `697fa3e227750962d078934196b47127bacaa6f6` |
| Diagnostic C target | `ffa3afe9c7dc700f6bffc9d863091a0d619972e3` |
| Diagnostic C xdelta | `60938962035e88d8505916baa4cf3b7aad5e3962` |

The source and target are each 3,758,358,528 bytes. Build details and the
before/after audit are in `_work/analysis/ps2_aligned_srvc/diagnostic.json`.
The user has confirmed this image works on PS2. This is confirmation of the
reported failure being fixed, not a claim that every battle has been tested.

The remaining sections retain the earlier investigation and diagnostic history.

---

## The symptom

On real PlayStation 2 hardware, in a battle:

> "Animation starts but the moment they're supposed to start talking the whole
> game freezes up with only music playing."

Earlier report from the same tester group named the stage as "Family 2" and the
trigger as starting a combat animation.

Music continuing while everything else stops is consistent with the audio side
continuing after an EE failure. It does **not** distinguish an infinite loop,
a stalled wait, and an exception such as Address Error.

## What is established

| Fact | How we know |
|---|---|
| The tester's setup is fine | The unmodified japanese ISO plays correctly through the exact same loading method |
| Our patch is at fault | Same setup, our image, reproducible freeze |
| Removing the two caption-conversion hooks does not fix it | Diagnostic A (below) restored both; "same issue, no change" |
| It is not emulator-visible | Plays fine in PCSX2, including the same battles |

The last point matters more than it looks. **PCSX2 zeroes EE RAM at boot; a real
PS2 does not.** Any code that scans for a zero terminator, or reads a length
from memory it never initialised, behaves on the emulator and misbehaves on
hardware. This project has been bitten by that class before (see
`hardware-vs-pcsx2-zeroed-ram` in the session memory).

## Ruled out, with evidence

Everything here was checked directly against the disc, not reasoned about.

**Caption lengths and routing (this did not check alignment).**
- Longest caption we ship, after the converter turns each literal `\n` into one
  newline byte: **94 bytes, 95 with the terminator**. The destination field is
  **96 bytes** (object offset 456, next field written at 552). Zero captions
  overflow it. The japanese maximum is 86.
- `BTL/SRVC.BIN` contains **no audio** — it holds text and binary records, so no audio was
  truncated when English shrank it from 1618 to 1424 sectors.
- `BTL/SRVC.SEG` (the block offset table) ends exactly at our file size in both
  ours and the japanese, so no block points past the file.
- All **353 blocks parse**, and **every voice ID is byte-identical to the
  japanese** (0 differences). Voice selection is intact.

**Our patch code being overwritten in RAM.**
- The japanese executable's highest address is `0x789D00`. The kernel heap is
  created by the `InitHeap` syscall at `0x1001D0` with base **`0x78CD00`**. Our
  cave occupies `0x78A070..0x78C900`, inside the ~12 KB gap between them, and is
  declared by its own PT_LOAD (segment 208 of 210, filesz = memsz = 10384).
- No other segment's memory range overlaps the cave.
- The big pool built at `0x140640` runs from `0x88BD00` to the top of RAM, well
  clear of us.
- Independent confirmation: menus render correctly on hardware, and the menu
  text path runs through the same cave region (`0x78A528` remap, `0x78BA60`
  advance table). If the region were being clobbered, menus would break first.

**Relocated files.**
- `COMPDATA.BN` (1568198 → 1823000), `MTVZKNKW.BIN` (→ 1823200) and
  `MTVZKNRT.BIN` (→ 1824000) are all inside the image (which is 1835136
  sectors) and the game's own file table points at the new locations.
- `MTVZKNPT.BIN` stayed at 1573457; its table size dropped 144 → 136 sectors
  and its data really is 136 sectors long. Consistent, not a bug.
- The old locations still hold their original data, so a stale reference would
  read japanese content, not garbage.

## The one real hazard found in our code

The battle-caption path is hooked at **`0x2EA47C`** and **`0x2EA684`**, where the
japanese calls its converter `0x2EA280` directly. Ours calls our caves
`0x78BBA0` / `0x78BC40`, which tail-jump into that same converter.

- The converter is `strstr`/`memcpy`/`strcpy` (`0x1A1350`, `0x1A1190`,
  `0x1A0D88`) with **no destination bound**.
- Our cave's backward scan is bounded (256 bytes). Its **forward scan is bounded
  only by finding a zero byte** — the counter loaded from `+84` is decremented
  only on the `\n` branch, not per character.

So a caption source that is mis-addressed or unterminated would scan and copy
without limit. On PCSX2 the scan stops at the first zero of cleared RAM; on
hardware it does not. **This remains a genuine robustness defect worth fixing
regardless of whether it is this bug** — but Diagnostic A shows it is not the
freeze, because removing it changed nothing.

## Diagnostics issued

Both are full patches: **apply to the japanese image**, not to a patched one.

| Build | What it changes | Result sha1 | Outcome |
|---|---|---|---|
| **A** `SRWZ-DIAG-nocaptioncave.xdelta` | Restores the two caption hooks to the original call, removing our caption code from the path. Everything else ours. | `c2449145` | **Tested: no change** |
| **B** `SRWZ-DIAG-B-japanese-exe.xdelta` | Puts the japanese executable back, keeps ALL our data. Menus revert to japanese and custom-font text renders wrong — expected. | `e383dd0d` | awaiting test |

**How to read Diagnostic B.**
- *Still freezes* → a data cause remains. Test SRVC alignment first, as described
  above; then investigate the relocated files and STAGE if needed.
- *Runs* → reverting the ELF changes the outcome; investigate those patches
  and their interaction with the data. This would not erase the independently
  demonstrated alignment defect. A three-word revert of the glyph-cache hooks
  (`0x13AA68`, `0x13AAE0`, `0x13A260`) can narrow the code-side difference.

## Earlier hypothesis if B runs (not established)

The **glyph-cache reuse patch (0.9.62)**. It was written to stop menu text
running out of texture cells, and it manipulates the glyph cache's texture
cursor and a per-frame code→cell table in the cave. Diagnostic A did **not**
remove it — that build still draws battle text through our modified blit.

The earlier suspicion was that stale glyph coordinates might cause a bad GS
transfer. Inspection of the actual current ELF does not establish this:
the coordinate paths are bounded, the 112-entry table at
`0x78C520..0x78C8A0` is explicitly zero-initialized, and its tag at `0x78C3FA`
starts at 1. Stale entries might still warrant a separate correctness check,
but they are not evidence of an out-of-range transfer or uninitialized boot
RAM. The SRVC alignment defect now has substantially stronger direct evidence.

## Open questions for the tester

1. Which build was tested (0.9.50, 0.9.66, or a diagnostic)?
2. Does the freeze happen on **every** battle with voice, or only some units?
3. Is it the same on a burned disc as through their usual loader?

## Working notes: addresses

```
0x2EA320   caption setup function (name -> obj+432, caption -> obj+456)
0x2EA47C   hook 1 -> our cave 0x78BBA0     (japanese: jal 0x2EA280)
0x2EA684   hook 2 -> our cave 0x78BC40     (japanese: jal 0x2EA280)
0x2EA280   converter: splits on literal "\n", unbounded strcpy
0x2E9A00   cell descriptor lookup
0x6D2CB8   speaker name pointer table
obj+432    speaker name field, 24 bytes
obj+456    caption field, 96 bytes (next field written at obj+552)
0x78A070   our cave start (PT_LOAD 208), ends 0x78C900
0x78CD00   kernel heap base (InitHeap at 0x1001D0)
0x789D00   end of the japanese image
```
