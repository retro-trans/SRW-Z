# -*- coding: utf-8 -*-
"""Package the PCSX2 texture-replacement pack that ships with a build.

Texture replacements live in `textures/<SERIAL>/replacements/`, keyed by
the game's SERIAL only - not by CRC - so one pack works for every build
of SLPS-25887.  (Per-GAME SETTINGS are the opposite: `gamesettings/
SLPS-25887_<CRC>.ini` is CRC-keyed, so it is orphaned by every ELF patch
we ship.  That is why the pack includes a settings ini the player can
rename, and why upscale is better set globally.)

The ONE thing that can break a replacement across builds: a replacement
is matched on the hash of the ORIGINAL texture, so if a patch repaints
that texture inside the ISO, its hash moves and the replacement stops
matching.  Today that applies to nothing in this pack - the intermission
labels/menu are KVMDATA art we leave alone, and the prologue cards are
not on the disc at all - but re-check after touching any texture bank.

Usage: build_texture_pack.py [outdir]     (default: _work/dist)
"""
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(WORK, "tools")
LIVE = r"C:\Users\Binh\Documents\PCSX2\textures\SLPS-25887\replacements"
GENERATORS = ["gen_hd_labels.py", "gen_hd_menu.py", "gen_intro_cards.py"]

README = """SRW Z English - PCSX2 texture pack
==================================

WHAT THIS IS
  Crisp 4x replacements for the UI art the game draws as TEXTURES rather
  than text: the intermission status-bar labels and menu buttons, and the
  two prologue title cards ("On that day, the world collapsed...").

INSTALL
  Copy the `textures` folder into your PCSX2 user directory, so you end
  up with:

    <PCSX2 user dir>/textures/SLPS-25887/replacements/*.png

  Find the user directory via Settings -> Folders, or Help -> Open Data
  Directory. On a default Windows install it is Documents\\PCSX2.

  Then turn ON:  Settings -> Graphics -> Texture Replacement ->
                 "Load Textures"
  and restart the game. PCSX2 scans this folder when the game BOOTS, so
  files added while it is running are not picked up until a restart.

WORKS WITH ANY BUILD
  Replacements are matched per game SERIAL (SLPS-25887), so this pack
  works with any version of the patch - no need to re-copy it when a new
  build lands.

THE TWO PROLOGUE CARDS ARE OPTIONAL AND MACHINE-SPECIFIC
  ("On that day, the world collapsed..." / "And so, a new world begins...")

  These two are NOT in the replacements folder, because they cannot be
  made portable - tested on a Steam Deck, where the UI replacements
  applied and these did not.
  PCSX2 matches a replacement on a hash of the texture's raw data, and the
  page these cards live on carries leftover garbage in its unused area -
  so the SAME card hashes differently on different machines and even
  between runs. (Proof: two dumps of one card were pixel-identical yet
  hashed differently.) Everything else in this pack is unaffected.

  To enable them on YOUR machine, once:
    1. Settings -> Graphics -> Texture Replacement -> tick "Dump Textures"
    2. Play the prologue until each Japanese line appears
    3. In textures/SLPS-25887/dumps/, find the two 1024x512 PNGs showing
       the Japanese line (sorting by size helps - they are ~10-30 KB)
    4. Copy the matching file out of intro-cards/ in this pack into
       textures/SLPS-25887/replacements/, RENAMED to the dumped filename
    5. Untick "Dump Textures", restart the game

RECOMMENDED, AND EASY TO MISS
  Set the internal resolution to 4x GLOBALLY (Settings -> Graphics ->
  Upscale Multiplier). PCSX2's PER-GAME settings are keyed to the game's
  CRC, and every new build of the patch changes the CRC - so a per-game
  4x setting silently reverts to 1x each time you update. `gamesettings/`
  in this pack holds a ready-made ini if you prefer per-game: rename it
  to match your build's CRC (the CRC appears in the window title and in
  savestate filenames).
"""


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "dist")
    os.makedirs(outdir, exist_ok=True)
    stage = os.path.join(outdir, "_stage")
    repl = os.path.join(stage, "textures", "SLPS-25887", "replacements")
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(repl)

    # 1) regenerate every replacement from its source tool
    for g in GENERATORS:
        script = os.path.join(TOOLS, g)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, script, repl],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=env)
        made = len([n for n in os.listdir(repl)])
        print("%-22s -> %d files total%s"
              % (g, made, "" if r.returncode == 0 else "  (FAILED)"))
        if r.returncode != 0:
            print(r.stdout[-400:].decode("utf-8", "replace"),
                  r.stderr[-400:].decode("utf-8", "replace"))

    # 2) anything in the live folder the generators do not produce is
    #    carried over, so a hand-made replacement is never lost
    carried = 0
    if os.path.isdir(LIVE):
        for n in os.listdir(LIVE):
            if n.lower().endswith(".png") and not os.path.exists(
                    os.path.join(repl, n)):
                shutil.copy2(os.path.join(LIVE, n), os.path.join(repl, n))
                carried += 1
    print("carried over from the live folder: %d" % carried)

    # 3) drop anything NOT portable: a replacement whose name has no
    #    region field hashes the whole page, including unused areas that
    #    hold per-machine garbage, so it will not match elsewhere
    #    (confirmed on a Steam Deck: the region-bounded ones applied, the
    #    full-page prologue cards did not).
    dropped = []
    for n in sorted(os.listdir(repl)):
        parts = n.split("-")
        if len(parts) < 4 or not re.fullmatch(r"r\d+x\d+", parts[2]):
            dropped.append(n)
            os.remove(os.path.join(repl, n))
    print("dropped %d non-portable replacement(s): %s"
          % (len(dropped), ", ".join(d[:16] + "..." for d in dropped)))

    # 4) the two prologue cards, under descriptive names - they must be
    #    renamed per machine (see the README), so they ship separately
    cards = os.path.join(stage, "intro-cards")
    os.makedirs(cards)
    import glob
    known = {"84d6382e3ee8a0af": "card1-on-that-day-the-world-collapsed.png",
             "3a0907da78212f09": "card2-and-so-a-new-world-begins.png",
             "7d47ebcc988fa57e": "card2-and-so-a-new-world-begins.png"}
    for src in glob.glob(os.path.join(LIVE, "*.png")):
        key = os.path.basename(src).split("-")[0]
        if key in known:
            shutil.copy2(src, os.path.join(cards, known[key]))
    print("intro cards staged: %d" % len(os.listdir(cards)))

    # 5) the per-game settings ini, as a convenience
    gs = os.path.join(stage, "gamesettings")
    os.makedirs(gs)
    with io.open(os.path.join(gs, "SLPS-25887_PUT-YOUR-CRC-HERE.ini"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write("[EmuCore/GS]\nupscale_multiplier = 4\nMaxAnisotropy = 0\n"
                "LoadTextureReplacements = true\n")
    with io.open(os.path.join(stage, "README.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(README)

    # 6) zip it
    zpath = os.path.join(outdir, "SRWZ-texture-pack.zip")
    n = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(stage):
            for name in files:
                p = os.path.join(root, name)
                z.write(p, os.path.relpath(p, stage))
                n += 1
    shutil.rmtree(stage)
    print("\n%s\n  %d files, %.1f KB, sha1 %s"
          % (zpath, n, os.path.getsize(zpath) / 1024.0, sha1(zpath)[:12]))


if __name__ == "__main__":
    main()
