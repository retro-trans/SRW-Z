# Title-screen release labels

The title screen uses bank 6 of `DATA/VT1.BIN`, not JTIM or NISVDATA.
The bank occupies offsets `0xA751B0..0xAE7710` in both disc editions and
decodes to 2,349,392 bytes. Its bright background TIM2 starts at `0x1B10D0`:
640 by 448 pixels, linear 8-bit indices and the normal PS2 tiled CLUT.

`tools/patch_title_branding.py` draws two right-aligned labels using existing
palette colors and a one-pixel dark outline. The version begins at y=402;
the author begins at y=420. Both end at x=622, leaving an 18-pixel right margin.
v0.9.79 uses `v0.9.79` and `github.com/retro-trans` exactly as requested.

Only the bright title background is changed. The logo, menus, darker
background, palette, executable, subtitle data, bank offsets and decoded
allocation are preserved. The Best adapter already copies VT1 across editions.

Build the optional fast compressor from its source, outside the repository:

```powershell
g++ -O3 -std=c++17 tools/banlz_pack_fast.cpp -o '<work>/banlz_pack_fast.exe'
python -B tools/patch_title_branding.py '<unbranded-English.iso>' --version v0.9.79 --work '<work>/branding' --compressor '<work>/banlz_pack_fast.exe'
```

Inspect the dry-run report, then repeat with `--write`. Omit `--compressor`
to use the slower Python codec. The font defaults to Windows Arial Bold;
`--font` accepts another explicit font path, and the report fingerprints it.

The patcher intentionally refuses a bank differing from the verified
unbranded source. Keep the prior unbranded build available when changing the
version; do not paint over old labels. Future translation updates can reuse
the verified branded bank, provided the title assets themselves did not change.

For v0.9.79 the repacked bank is 459,513 bytes inside its 468,320-byte slot.
Strict decoding matches every intended byte. Full-disc comparison of both
outputs confirms that no bytes outside this bank changed from their earlier
.79 builds. The user is handling the visual check; no in-game visual pass
is claimed for these labels. The replacement GitHub release must remain a draft.
