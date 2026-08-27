# Finding the dialogue glyph renderer — PCSX2 debugger trace

> **STATUS: DONE.** This trace was completed on the SLPS-25887 build
> (CRC `6081EA7F`). The renderer chain and the exact byte-read / glyph-lookup
> instructions are documented in **[`RENDERER.md`](RENDERER.md)**. The reader is
> `0x13A390` (`lbu v0,(s4)`) inside the glyph blit `0x13A290`; the half/full
> width decision is at `0x22137C` in the layout routine `0x2212B0`. The steps
> below are kept as a record of the method.

**Goal:** find the one MIPS instruction in the boot ELF (`SLPS_258.87`) that
reads a dialogue text byte for rendering. Once we have that address, the
ASCII→fullwidth patch is straightforward. Static signature search did not
converge (see `FINDINGS.md`), so we catch the reader at runtime with a memory
breakpoint. A human doing this interactively takes ~5 minutes; it's only hard
to automate.

You do **one** thing: make the breakpoint fire and send back a screenshot of
where it stops. I do the rest.

---

## What you need on the machine (already set up on the server)

- **PCSX2 2.6.3** — installed (`C:\Program Files\PCSX2\pcsx2-qt.exe`).
- **The patched build** — `E:\Projects\SRW Z\_work\iso\srwz_en.bin`
  (chapter 1 is translated; the English text is in RAM once a stage loads).
- BIOS is already configured.

Boot it from a terminal:

```
& "C:\Program Files\PCSX2\pcsx2-qt.exe" -fastboot -batch -- "E:\Projects\SRW Z\_work\iso\srwz_en.bin"
```

---

## Step 1 — turn on the debugger

1. `Settings → Interface` → enable **“Show Advanced Settings”** (or in the
   `Tools` menu, tick **Show Advanced Settings**).
2. A **`Debug`** menu now appears in the menu bar (next to Help). Open it →
   **`Open Debugger`** (or `Debug → Debugger`). A debugger window opens with a
   disassembly pane, a register pane, a memory pane, and a breakpoint list.

*(If there is no Debug menu: `Settings → Emulation` → enable **“Enable
Debugger”**, then reopen from the Debug menu.)*

---

## Step 2 — reach a chapter-1 dialogue line

New game → **main scenario** → character select: press **Right** to the female
side → choose **Setsuko** → on her profile press **Down** to the **決定**
(Confirm) button → confirm → skip the opening narration (mash Circle/Enter) →
you’ll reach the **corridor scene** (a spaceship hallway, characters talking).

Advance until a **line of English text is on screen** (empty grey boxes are the
English — the font can’t draw ASCII yet; that’s the whole point). Now the whole
chapter-1 script is decompressed in RAM.

Default keys in this build: arrows = d-pad, **L = Circle (confirm/advance)**,
K = Cross (cancel), Enter = Start.

---

## Step 3 — find the dialogue buffer in RAM

In the debugger’s **Memory** pane there is a search box (or `Ctrl+F` /
right-click → *Search*). Search the **EE memory** for this exact ASCII text:

```
Glory Star
```

(That phrase appears ~15× in chapter 1, so it’s easy to find. Alternatives:
`scramble to launch`, `Virgola`, `Denzel`.)

Note the **address** of the first hit — e.g. something like `0x01C4xxxx` or
`0x00Bxxxxx`. This is (a copy of) the decompressed script. There may be several
copies; any that the renderer actually reads will work — see next step.

---

## Step 4 — set a READ breakpoint on it

1. In the debugger, open the **Breakpoints** pane → **New** (or right-click the
   found address in the Memory pane → **Add breakpoint**).
2. Set it as a **Memory** breakpoint, condition **Read** (not execute, not
   write), on the address from Step 3. A size of 4–16 bytes is fine; or set it
   on the address of the first character of a line that hasn’t displayed yet.
3. Make sure the breakpoint is **enabled**.

---

## Step 5 — trigger the read

Back in the game, **advance one more dialogue line** (press L/Circle). When the
renderer reads that text, **execution halts** and the debugger jumps to the
instruction that did the read (an `lbu`/`lb`/`lhu` load, program counter shown
in the disassembly).

---

## Step 6 — send me this

Take a **screenshot of the debugger** showing:

- the **disassembly pane** around the stopped PC (the highlighted current
  instruction, plus ~20 lines above and below), **and**
- the **register pane** (so I can see which register holds the text pointer).

Also copy the **PC value** (the address of the current instruction) as text if
you can.

That’s everything. From the PC I can:
1. disassemble the full routine in the ELF,
2. see how it turns a byte into a glyph, and
3. inject the ASCII→fullwidth remap so English renders.

---

## Notes / troubleshooting

- **Nothing breaks when you advance a line:** the copy you found isn’t the one
  the renderer reads. Repeat Step 3, pick a different hit, or set the read
  breakpoint on the first byte of the *next* line to be shown. You can also
  search for the text of the *specific line about to appear*.
- **It breaks constantly / too early:** you may have caught a memcpy that
  copies the buffer. Note that PC too (send it), then **continue** (F5/Run) a
  few times — the *rendering* read usually happens right as the glyph appears,
  and the routine will reference a font/texture address. Any of these PCs help;
  the render one is ideal.
- **Prefer not to fiddle:** if you can instead dump EE RAM around the buffer
  and give me the buffer’s address, I can narrow the search statically — but
  the breakpoint PC is what really unblocks it.

Once you paste the screenshot back to me, I’ll build and test the patch.
