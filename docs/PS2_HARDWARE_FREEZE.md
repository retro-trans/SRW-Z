# The PS2 hardware freeze — investigation notes

**Status: unsolved. Cause narrowed, two diagnostics out with the tester.**
Last updated 2026-09-08.

---

## The symptom

On real PlayStation 2 hardware, in a battle:

> "Animation starts but the moment they're supposed to start talking the whole
> game freezes up with only music playing."

Earlier report from the same tester group named the stage as "Family 2" and the
trigger as starting a combat animation.

**Music continuing while everything else stops is the single most useful clue.**
The IOP drives audio independently of the EE. Music playing means the IOP is
alive and the EE is stuck — an infinite loop or a wait that never completes, not
a crash to a dead machine.

## What is established

| Fact | How we know |
|---|---|
| The tester's setup is fine | The unmodified japanese ISO plays correctly through the exact same loading method |
| Our patch is at fault | Same setup, our image, reproducible freeze |
| Our caption CODE is not the cause | Diagnostic A (below) removed it; "same issue, no change" |
| It is not emulator-visible | Plays fine in PCSX2, including the same battles |

The last point matters more than it looks. **PCSX2 zeroes EE RAM at boot; a real
PS2 does not.** Any code that scans for a zero terminator, or reads a length
from memory it never initialised, behaves on the emulator and misbehaves on
hardware. This project has been bitten by that class before (see
`hardware-vs-pcsx2-zeroed-ram` in the session memory).

## Ruled out, with evidence

Everything here was checked directly against the disc, not reasoned about.

**The caption text pipeline.**
- Longest caption we ship, after the converter turns each literal `\n` into one
  newline byte: **94 bytes, 95 with the terminator**. The destination field is
  **96 bytes** (object offset 456, next field written at 552). Zero captions
  overflow it. The japanese maximum is 86.
- `BTL/SRVC.BIN` contains **no audio** — it is caption text only, so nothing was
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
- *Still freezes* → the cause is in our DATA. Next suspects: the three relocated
  files and their file-table entries, then STAGE.
- *Runs* → the cause is in our ELF patches. Next step is a three-word revert of
  the glyph-cache hooks (`0x13AA68`, `0x13AAE0`, `0x13A260`).

## Leading hypothesis if B runs

The **glyph-cache reuse patch (0.9.62)**. It was written to stop menu text
running out of texture cells, and it manipulates the glyph cache's texture
cursor and a per-frame code→cell table in the cave. Diagnostic A did **not**
remove it — that build still draws battle text through our modified blit.

Why it fits: it is the one patch that computes graphics coordinates. A cell
coordinate that lands outside the texture produces a malformed GS transfer,
which PCSX2 tolerates and real hardware can hang on. The per-frame tag is
advanced by the reset function `0x13A260`, called from the frame function
`0x13C3B0` and 21 screens — if a battle animation never calls it, the table
holds stale entries from an earlier frame.

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
