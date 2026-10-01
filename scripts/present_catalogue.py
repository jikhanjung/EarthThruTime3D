"""The present-day Earth catalogue shared by fetch_bluemarble, fetch_present_weather and
build_ecco2_mean (jikhanjung P10).

All three write into data/derived/present-earth/: files named `<key>-<sha12>.<ext>` so a
changed file gets a new URL under the year-long immutable cache, and one catalogue.json
with a section per script. Writing a section replaces that section's files only.
"""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/derived/present-earth"
CATALOGUE = OUT / "catalogue.json"
SECTIONS = ("base", "weather", "ocean")


def read():
    try:
        return json.loads(CATALOGUE.read_text())
    except FileNotFoundError:
        return {"schema_version": 1}


def write_section(section, blobs, meta):
    """`blobs` {key: (bytes, extension)} -> files; `meta` is stored beside their `assets`."""
    if section not in SECTIONS:
        raise ValueError(section)
    OUT.mkdir(parents=True, exist_ok=True)
    document = read()
    old = {a["file"] for a in document.get(section, {}).get("assets", {}).values()}
    assets = {}
    for key, (blob, extension) in blobs.items():
        sha = hashlib.sha256(blob).hexdigest()
        name = f"{key}-{sha[:12]}.{extension}"
        part = OUT / f".{name}.part"
        part.write_bytes(blob)
        os.replace(part, OUT / name)
        assets[key] = {"file": name, "bytes": len(blob), "sha256": sha}
    document[section] = {**meta, "assets": assets}
    part = CATALOGUE.with_suffix(".json.part")
    part.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n")
    os.replace(part, CATALOGUE)
    for name in old - {a["file"] for a in assets.values()}:
        (OUT / name).unlink(missing_ok=True)
    return document[section]
