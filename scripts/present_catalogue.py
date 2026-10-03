"""The present-day Earth catalogue shared by fetch_bluemarble, fetch_present_weather and
build_ecco2_mean (jikhanjung P10).

All three write into data/derived/present-earth/: files named `<key>-<sha12>.<ext>` so a
changed file gets a new URL under the year-long immutable cache, and one catalogue.json
with a section per script. Writing a section replaces that section's files only.

The daily refresh on the server (jikhanjung P11) writes the `weather` section into its own
directory, `present-live/`, with `keep_previous`: the moment before stays listed as
`previous` and on disk for one more day, so a page opened just before the swap still finds
its files. Only this module and the scripts that call it are copied to the host for that.
"""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/derived/present-earth"
CATALOGUE = OUT / "catalogue.json"
SECTIONS = ("base", "weather", "ocean")


def read(out=OUT):
    try:
        return json.loads((Path(out) / "catalogue.json").read_text())
    except FileNotFoundError:
        return {"schema_version": 1}


def write_section(section, blobs, meta, out=OUT, keep_previous=False):
    """`blobs` {key: (bytes, extension)} -> files; `meta` is stored beside their `assets`.
    With `keep_previous` the section's former assets stay as `previous` (and on disk);
    anything older goes."""
    if section not in SECTIONS:
        raise ValueError(section)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    document = read(out)
    former = document.get(section, {}).get("assets", {})
    old = {a["file"] for a in former.values()} | {
        a["file"] for a in document.get(section, {}).get("previous", {}).get("assets", {}).values()}
    assets = {}
    for key, (blob, extension) in blobs.items():
        sha = hashlib.sha256(blob).hexdigest()
        name = f"{key}-{sha[:12]}.{extension}"
        part = out / f".{name}.part"
        part.write_bytes(blob)
        os.chmod(part, 0o644)
        os.replace(part, out / name)
        assets[key] = {"file": name, "bytes": len(blob), "sha256": sha}
    document[section] = {**meta, "assets": assets}
    keep = {a["file"] for a in assets.values()}
    if keep_previous and former:
        document[section]["previous"] = {"assets": former}
        keep |= {a["file"] for a in former.values()}
    part = out / "catalogue.json.part"
    part.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n")
    os.chmod(part, 0o644)
    os.replace(part, out / "catalogue.json")
    for name in old - keep:
        (out / name).unlink(missing_ok=True)
    return document[section]
