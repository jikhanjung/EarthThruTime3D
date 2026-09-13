#!/usr/bin/env python3
"""Fetch or verify a pinned plate model archive and the members this project uses.

One manifest per model under sources/plate-models/, each naming its archive and which
member plays which role. Models are laid out differently by their publishers, so the
role is what the rest of the pipeline reads, never a file name.

Separate from the Scotese maps on purpose. Those are published pictures this project
measures; these are rotation models that reconstruct geometry, with different authors,
licences and limits.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "sources/plate-models"
HOME = ROOT / "data/sources/plates"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def models():
    return sorted(path.stem for path in MANIFESTS.glob("*.json"))


def manifest(model):
    return json.loads((MANIFESTS / f"{model}.json").read_text())


def local_name(member):
    """Members keep their base name locally; archives disagree about directories."""
    return Path(member["name"]).name


def member_path(model, member):
    return HOME / model / local_name(member)


def verify(path, expected_bytes, expected_hash, label):
    data = path.read_bytes()
    if len(data) != expected_bytes or digest(data) != expected_hash:
        raise ValueError(f"Differs from pinned manifest: {label}")


def fetch(model, verify_only):
    document = manifest(model)
    archive = document["archive"]
    target = (ROOT / archive["path"]).resolve()
    if not target.is_relative_to(HOME.resolve()):
        raise ValueError("The archive must stay inside the local source directory")

    if target.exists() or verify_only:
        verify(target, archive["bytes"], archive["sha256"], archive["path"])
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download") as temp:
            subprocess.run([
                "curl", "--fail", "--silent", "--show-error", "--location",
                "--connect-timeout", "10", "--max-time", "600", "--retry", "2",
                "--output", temp.name, archive["url"],
            ], check=True)
            verify(Path(temp.name), archive["bytes"], archive["sha256"], archive["path"])
            # Publish verified bytes only; keep any existing file on mismatch.
            os.link(temp.name, target)
    print(f"OK {archive['path']}")

    with zipfile.ZipFile(target) as bundle:
        for member in document["members"]:
            destination = member_path(model, member)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() and not verify_only:
                # Read from the archive rather than trusting its paths on disk.
                data = bundle.read(archive["member_prefix"] + member["name"])
                if len(data) != member["bytes"] or digest(data) != member["sha256"]:
                    raise ValueError(f"Archive member differs from manifest: {member['name']}")
                destination.write_bytes(data)
            verify(destination, member["bytes"], member["sha256"], member["name"])
            print(f"OK {destination.relative_to(ROOT)}  [{member['role']}]")
    print(f"{document['short_title']}: archive and {len(document['members'])} members verified. "
          f"Licence: {document['license']['name']}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", default=None,
                        help=f"model ids; default all of {', '.join(models())}")
    parser.add_argument("--verify-only", action="store_true",
                        help="Check local files without network access")
    args = parser.parse_args()
    for model in (args.models or models()):
        fetch(model, args.verify_only)


if __name__ == "__main__":
    main()
