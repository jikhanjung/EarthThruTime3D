"""Verified geodynamic sources and a structural inventory (not a reconstruction)."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from fetch_paleodem import ROOT, SOURCES, verify

NS = {"gpml": "http://www.gplates.org/gplates", "gml": "http://www.opengis.net/gml"}


def source(model):
    document = json.loads((ROOT / "sources/geodynamics" / f"{model}.json").read_text())
    for asset in document["assets"]:
        path = (ROOT / asset["path"]).resolve()
        if not path.is_relative_to(SOURCES):
            raise ValueError("Source must stay in data/sources")
        verify(path, asset)
    archive = next(a for a in document["assets"] if a["role"] == "archive")
    return document, ROOT / archive["path"]


def gpml_summary(data):
    root = ET.fromstring(data)
    types, networks = Counter(), []
    for member in root.findall("gml:featureMember", NS):
        for feature in member:
            kind = feature.tag.rsplit("}", 1)[-1]
            types[kind] += 1
            if kind != "TopologicalNetwork":
                continue
            networks.append({
                "id": feature.findtext("gpml:identity", namespaces=NS),
                "name": feature.findtext("gml:name", namespaces=NS),
                # Preserve raw time strings, including distantPast/distantFuture.
                "valid_time": [x.text for x in feature.findall("gml:validTime//gml:timePosition", NS)],
                "plate_id": feature.findtext("gpml:reconstructionPlateId//gpml:value", namespaces=NS),
            })
    return {"feature_types": dict(sorted(types.items())), "networks": networks}


def inventory():
    document, path = source("muller2019")
    members = []
    with zipfile.ZipFile(path) as bundle:
        for name in sorted(bundle.namelist()):
            if name.endswith("/") or name.startswith("__MACOSX/"):
                continue
            data = bundle.read(name)
            item = {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            suffix = Path(name).suffix.lower()
            item["role"] = {".rot": "rotation", ".gproj": "project", ".gpml": "features",
                            ".gpmlz": "features"}.get(suffix, "supporting")
            if suffix in (".gpml", ".gpmlz"):
                item.update(gpml_summary(gzip.decompress(data) if suffix == ".gpmlz" else data))
            members.append(item)
    return {"schema_version": 1, "source": document["id"], "kind": "structural_inventory",
            "note": "Feature validity is not resolved network coverage; no geometry or strain reconstructed.",
            "members": members}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/derived/geodynamics/muller2019-inventory.json")
    args = parser.parse_args()
    result = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    count = sum(len(m.get("networks", [])) for m in result["members"])
    print(f"{len(result['members'])} members, {count} network features -> {args.output}")


if __name__ == "__main__":
    main()
