# Standard Retro Trans releases

Future releases use the shared [Retro Trans release builder](https://github.com/retro-trans/retro-trans-tools/blob/main/docs/RELEASE_STANDARD.md).
Existing releases remain compatible through reviewed historical catalog metadata.
Do not replace historical patch assets.

Install the builder in the Python environment used for release work:

```powershell
python -m pip install git+https://github.com/retro-trans/retro-trans-tools.git@v0.2.0
```

Copy the [example configuration](https://github.com/retro-trans/retro-trans-tools/blob/main/examples/release-config.json)
to a private local `release-local.json`. Set `game_id` to `srw-z`, `game_name` to
`Super Robot Wars Z`, `platform` to `PS2`, `language` to `en`, and use `original`
or `best` for the edition to match the imported catalog. Use the actual stable
version and local source/target ISO paths. Paths are relative to the configuration
file. Include one entry for each supported original or previous translated input.
For the untranslated source, `source_version` is `original`.

Omit `source_commit` in this private configuration when using the helper; it pins
the current clean HEAD. If supplied, it must equal that commit. The helper needs
GitHub CLI authentication with permission to publish releases.

```powershell
python tools/release.py 0.9.84 --config "../SRW Z/release-local.json" --dry
python tools/release.py 0.9.84 --config "../SRW Z/release-local.json"
```

The helper generates all full and incremental patches, applies each to its exact
source, checks the entire resulting SHA-256, and prepares `BUILD-MANIFEST.json`,
`SHA256SUMS.txt`, and `VALIDATION.json`. It retains the pinned source archive,
release branch, and optional texture pack. Game binaries and the local
configuration are excluded from the publish directory.

Publication creates a draft, uploads verified assets, checks their published
metadata, then makes the release public. A failure leaves the release unpublished
or in draft for inspection. Existing releases are refused, and assets are never
overwritten. Corrected bytes require a new version.

The release validation workflow checks uploaded protocol assets on GitHub.
Actual game-file round trips run locally. The central catalog discovers valid
releases hourly or when its workflow is manually triggered.
