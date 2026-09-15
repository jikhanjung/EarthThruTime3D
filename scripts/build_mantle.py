"""Pack the pinned OPT1 ParaView surfaces, preserving source frames and topology.

Only the inline-binary VTK XML subset present in this archive is read.
Unsupported encodings/cell types fail rather than silently becoming different geometry.
No temperature, velocity, interpolation or mantle physics is calculated here.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np

from geodynamics import ROOT, source

PREFIX = "OPT1_3D_visualisation_ParaView/"
DTYPES = {"Float32": "<f4", "Float64": "<f8", "Int64": "<i8", "UInt8": "u1"}


def array(node, root):
    if node is None:
        raise ValueError("Missing VTK array")
    if root.get("byte_order") != "LittleEndian" or node.get("format") != "binary":
        raise ValueError("Unsupported VTK encoding")
    dtype = DTYPES.get(node.get("type"))
    if dtype is None:
        raise ValueError("Unsupported VTK scalar type")
    text = "".join((node.text or "").split())
    compressor = root.get("compressor")
    header = root.get("header_type", "UInt32")
    if compressor == "vtkZLibDataCompressor" and header == "UInt32":
        # meshio encodes the compressed header and payload as separate base64 strings.
        blocks = int.from_bytes(base64.b64decode(text[:8], validate=True)[:4], "little")
        if not 1 <= blocks <= 100000:
            raise ValueError("Invalid VTK block count")
        encoded_length = 4 * (((3 + blocks) * 4 + 2) // 3)
        sizes = np.frombuffer(base64.b64decode(text[:encoded_length], validate=True), dtype="<u4")
        if len(sizes) != 3 + blocks:
            raise ValueError("Invalid compressed VTK header")
        compressed = base64.b64decode(text[encoded_length:], validate=True)
        if int(sizes[3:].sum()) != len(compressed):
            raise ValueError("VTK compressed byte count mismatch")
        chunks, start = [], 0
        for i, size in enumerate(sizes[3:]):
            end = start + int(size)
            chunk = zlib.decompress(compressed[start:end])
            expected = int(sizes[2] or sizes[1]) if i == blocks - 1 else int(sizes[1])
            if len(chunk) != expected:
                raise ValueError("VTK decompressed byte count mismatch")
            chunks.append(chunk)
            start = end
        data = b"".join(chunks)
    elif not compressor and header == "UInt64":
        raw = base64.b64decode(text, validate=True)
        if len(raw) < 8 or int.from_bytes(raw[:8], "little") != len(raw) - 8:
            raise ValueError("VTK byte count mismatch")
        data = raw[8:]
    else:
        raise ValueError("Unsupported VTK compression/header")
    result = np.frombuffer(data, dtype=dtype)
    if not np.isfinite(result).all():
        raise ValueError("Non-finite VTK data")
    return result


def read_piece(data, primitive):
    root = ET.fromstring(data)
    pieces = root.findall("UnstructuredGrid/Piece")
    if root.get("type") != "UnstructuredGrid" or len(pieces) != 1:
        raise ValueError("Expected one unstructured piece")
    piece = pieces[0]
    points = array(piece.find("Points/DataArray"), root).reshape(-1, 3)
    cells = {a.get("Name"): array(a, root) for a in piece.findall("Cells/DataArray")}
    offsets, indices, types = (cells[k] for k in ("offsets", "connectivity", "types"))
    if (len(points) != int(piece.get("NumberOfPoints")) or len(types) != int(piece.get("NumberOfCells"))
            or len(offsets) != len(types) or (len(offsets) and offsets[-1] != len(indices))
            or (not len(offsets) and len(indices)) or np.any(np.diff(np.r_[0, offsets]) <= 0)):
        raise ValueError("VTK topology count mismatch")
    if indices.size and (indices.min() < 0 or indices.max() >= len(points)):
        raise ValueError("VTK point index out of bounds")
    sizes = np.diff(np.r_[0, offsets])
    if primitive == "triangles":
        if np.any(types != 5) or np.any(sizes != 3):
            raise ValueError("Expected VTK triangles")
        packed = indices
    elif primitive == "lines":
        if np.any(~np.isin(types, [3, 4])) or np.any(sizes < 2):
            raise ValueError("Expected VTK lines or polylines")
        segments, start = [], 0
        for end in offsets:
            cell = indices[start:end]
            segments.append(np.column_stack((cell[:-1], cell[1:])).ravel())
            start = end
        packed = np.concatenate(segments) if segments else np.array([], dtype="<u4")
    else:
        raise ValueError("Unknown primitive")
    values = {a.get("Name"): array(a, root) for a in piece.findall("PointData/DataArray")}
    if any(len(v) != len(points) for v in values.values()):
        raise ValueError("Point scalar count mismatch")
    time = root.find(".//FieldData/DataArray[@Name='TimeValue']")
    return points, packed, values, float(array(time, root)[0]) if time is not None else None


def time_mapping(bundle):
    root = ET.fromstring(bundle.read(PREFIX + "StateFile/OPT1-model.pvsm"))
    proxy = root.find(".//Proxy[@type='TimeToTextConvertor']")
    if proxy is None:
        raise ValueError("Missing age annotation")
    def value(name):
        return float(proxy.find(f"Property[@name='{name}']/Element").get("value"))
    scale, shift = value("Scale"), value("Shift")
    if (scale, shift) != (-20, 1000):
        raise ValueError("Unexpected source time mapping")
    return scale, shift


def layer(bundle, name, frame):
    primitive = "lines" if name == "boundaries" else "triangles"
    if name == "boundaries":
        members = [PREFIX + f"Reconstruction/Plate-polygons/PlateBoundaries_gcm32__{frame:02d}.vtu"]
    else:
        title = {"slabs": "Slabs", "piles": "Piles"}[name]
        parent = PREFIX + f"{title}/{title}_{frame:02d}.pvtu"
        root = ET.fromstring(bundle.read(parent))
        if float(array(root.find(".//FieldData/DataArray"), root)[0]) != frame:
            raise ValueError("Source frame/time mismatch")
        members = []
        for part in root.findall(".//Piece"):
            relative = PurePosixPath(part.get("Source"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe VTK piece reference")
            members.append(str(PurePosixPath(parent).parent / relative))
    points, indices, count = [], [], 0
    depths = []
    for member in members:
        p, cells, values, time = read_piece(bundle.read(member), primitive)
        if time is not None and time != frame:
            raise ValueError("Piece time mismatch")
        radius = np.linalg.norm(p, axis=1)
        if np.any(radius > 1.01) or np.any(radius < 0.5):
            raise ValueError("Coordinates outside expected unit mantle shell")
        if name != "boundaries":
            depth = values["Depth(km)"] if name == "slabs" else values["NonDimDepth"] * 6371
            # File fields are rounded; validate their units against the actual geometry.
            if not np.allclose(depth, (1 - radius) * 6371, atol=0.1, rtol=0):
                raise ValueError("Source depth and radius disagree")
            depths.append(depth)
        points.append(p)
        indices.append(cells + count)
        count += len(p)
    positions = np.concatenate(points).astype("<f4")
    connectivity = np.concatenate(indices).astype("<u4")
    payload = positions.tobytes() + connectivity.tobytes()
    info = {"primitive": primitive, "points": len(positions), "indices": len(connectivity),
            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            "source_members": members}
    if depths:
        depth = np.concatenate(depths)
        info["depth_range_km"] = [float(depth.min()), float(depth.max())] if len(depth) else None
    return payload, info


def build(output, frames):
    document, path = source("muller2022-opt1")
    output.mkdir(parents=True, exist_ok=True)
    # Build in a staging directory; publish the catalogue only after every frame succeeds.
    with tempfile.TemporaryDirectory(dir=output, prefix=".build-") as staging:
        stage = Path(staging)
        catalogue = {"schema_version": 1, "source": document["id"], "kind": "published_simulation",
                     "source_archive_sha256": next(a["sha256"] for a in document["assets"] if a["role"] == "archive"),
                     "coordinates": document["coordinates"], "reference_frame": document["reference_frame"],
                     "binary_layout": "little-endian float32 xyz[points], then uint32 indices[indices]",
                     "interpolation": "none", "frames": []}
        with zipfile.ZipFile(path) as bundle:
            scale, shift = time_mapping(bundle)
            for frame in frames:
                entry = {"index": frame, "source_time": frame, "age_ma": shift + scale * frame, "layers": {}}
                for name in ("slabs", "piles", "boundaries"):
                    data, info = layer(bundle, name, frame)
                    # Content-addressed files keep a previous catalogue valid during rebuilds.
                    filename = f"{name}-{frame:02d}-{info['sha256'][:16]}.bin"
                    (stage / filename).write_bytes(data)
                    compressed = gzip.compress(data, compresslevel=6, mtime=0)
                    compressed_name = filename + ".gz"
                    (stage / compressed_name).write_bytes(compressed)
                    info["gzip"] = {"file": compressed_name, "bytes": len(compressed),
                                    "sha256": hashlib.sha256(compressed).hexdigest()}
                    entry["layers"][name] = {"file": filename, **info}
                catalogue["frames"].append(entry)
                print(f"OPT1 {entry['age_ma']:g} Ma: packed source frame {frame}")
        (stage / "catalogue.json").write_text(json.dumps(catalogue, indent=2) + "\n")
        for file in stage.iterdir():
            if file.name != "catalogue.json":
                file.replace(output / file.name)
        (stage / "catalogue.json").replace(output / "catalogue.json")
    return catalogue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", nargs="+", type=int, choices=range(51), default=list(range(51)))
    parser.add_argument("--output", type=Path, default=ROOT / "data/derived/mantle/muller2022-opt1")
    args = parser.parse_args()
    build(args.output, sorted(set(args.frames)))


if __name__ == "__main__":
    main()
