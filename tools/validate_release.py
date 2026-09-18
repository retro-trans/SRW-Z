"""Validate uploaded standard assets; no original game binaries are required."""
import argparse

from retro_trans.catalog import Catalog
from retro_trans.catalog_builder import release_record
from retro_trans.core import GitHubClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    args = parser.parse_args()
    repo = "retro-trans/SRW-Z"
    client = GitHubClient()
    release = client.json("https://api.github.com/repos/" + repo + "/releases/tags/" + args.tag)
    record = release_record(repo, release, client)
    if record is None:
        raise SystemExit("Release has no standard BUILD-MANIFEST.json.")
    Catalog({"schema_version": 1, "releases": [record]})
    print("Published manifest, checksums, report and patch bytes verified.")


if __name__ == "__main__":
    main()
