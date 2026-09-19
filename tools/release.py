"""Publish a verified SRW-Z release, retaining the pinned source and optional art.

Install the shared tool once: python -m pip install git+https://github.com/retro-trans/retro-trans-tools.git@v0.2.0
Usage: python tools/release.py 0.9.84 --config /path/to/release-local.json
Use --dry to inspect the intended release without building or publishing.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / "SRW Z"
BAD = (".bin", ".chd", ".iso", ".cue", ".img", ".elf", ".exe", ".zip", ".7z", ".rar", ".xdelta", ".pss", ".msb", ".vpk")


def run(command, check=True):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--repo", default="retro-trans/SRW-Z")
    parser.add_argument("--config", type=Path, default=WORK / "release-local.json")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    version, tag = args.version.lstrip("v"), "v" + args.version.lstrip("v")
    if args.dry:
        print("Would build and round-trip every patch in", args.config)
        print("Would publish immutable release", args.repo, tag, "with source archive and optional texture pack.")
        return 0
    from retro_trans.release import build_release, validate_directory
    dirty = run(["git", "status", "--porcelain"]).stdout.strip()
    if dirty:
        raise RuntimeError("Commit your source changes before cutting a release.")
    commit = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["version"].lstrip("v") != version:
        raise RuntimeError("Requested version and release configuration disagree.")
    configured_commit = config.get("source_commit")
    if configured_commit and configured_commit != commit:
        raise RuntimeError("source_commit does not match the checked-out release source.")
    config["source_commit"] = commit
    for entry in config["patches"]:
        for side in ("source", "target"):
            entry[side] = str((args.config.resolve().parent / entry[side]).resolve())
    gh = shutil.which("gh")
    if not gh and os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "GitHub CLI" / "gh.exe"
        if candidate.is_file():
            gh = str(candidate)
    if not gh:
        raise RuntimeError("GitHub CLI is required to publish a release.")
    run([gh, "repo", "view", args.repo, "--json", "name"])
    existing = run([gh, "release", "view", tag, "--repo", args.repo], check=False)
    if existing.returncode == 0:
        raise RuntimeError("Release already exists. Publish a new version; assets are never overwritten.")
    if "not found" not in existing.stderr.lower():
        raise RuntimeError(existing.stderr.strip())
    WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-build-", dir=WORK) as scratch:
        scratch = Path(scratch)
        local_config = scratch / "private-config.json"
        local_config.write_text(json.dumps(config), encoding="utf-8")
        directory = scratch / "publish"
        build_release(local_config, directory)
        source_archive = directory / ("SRWZ-source-" + tag + ".zip")
        run(["git", "archive", "--format=zip", "--prefix=SRWZ-" + tag + "/", "-o", str(source_archive), commit])
        with zipfile.ZipFile(source_archive) as archive:
            if any(name.lower().endswith(BAD) for name in archive.namelist()):
                raise RuntimeError("Source archive contains game data or binary artifacts.")
        generator = ROOT / "tools" / "build_texture_pack.py"
        if generator.exists():
            import sys
            run([sys.executable, str(generator)])
        pack = WORK / "_work" / "dist" / "SRWZ-texture-pack.zip"
        if pack.exists():
            shutil.copyfile(pack, directory / pack.name)
        validate_directory(directory)
        # Verify existing refs or create them without force updates.
        for ref, command in (("release/" + tag, "branch"), (tag, "tag")):
            resolved = run(["git", "rev-parse", "--verify", ref], check=False)
            if resolved.returncode == 0 and resolved.stdout.strip() != commit:
                raise RuntimeError("Existing release ref points at different source: " + ref)
            if resolved.returncode != 0:
                run(["git", command, ref, commit])
            run(["git", "push", "origin", ref])
        assets = [str(p) for p in directory.iterdir() if p.is_file()]
        run([gh, "release", "create", tag, *assets, "--repo", args.repo, "--verify-tag", "--draft",
             "--title", "SRW Z English " + tag, "--notes", "Verified full and upgrade patches. Retro Trans automatically selects a compatible route. See BUILD-MANIFEST.json for exact binary identities."])
        uploaded = json.loads(run([gh, "api", "repos/" + args.repo + "/releases/tags/" + tag]).stdout)
        by_name = {a["name"]: a for a in uploaded["assets"]}
        validate_directory(directory)
        from retro_trans.core import sha256_file
        for path in directory.iterdir():
            asset = by_name.get(path.name)
            if not asset or asset["size"] != path.stat().st_size or (asset.get("digest") and asset["digest"] != "sha256:" + sha256_file(path)):
                raise RuntimeError("Uploaded asset failed verification; release remains a draft: " + path.name)
        run([gh, "release", "edit", tag, "--repo", args.repo, "--draft=false"])
    print("Published", args.repo, tag)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        raise SystemExit(str(exc))
