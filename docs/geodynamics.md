# Geodynamic sources and the mantle experiment

This is the first implementation from [jikhanjung P03](../devlog/20260915_jikhanjung_P03_crustal_deformation_mantle_coupling.md).
The [India–Asia A–A′ popup](india-asia-section.md) now adds an 80 Ma–present regional
section, a PaleoDEM 3D comparison surface and a separately labelled local crust scenario.
The `/mantle/` page displays published OPT1 surfaces, separately from the PALEOMAP globe.
It does not calculate mantle convection, temperature, velocity, crustal deformation or uplift.

## Sources actually inspected

Both source archives and the Zenodo API metadata were downloaded on 2026-09-15. Publisher
MD5 checksums were matched before recording sizes and SHA-256 hashes in
[`sources/geodynamics/`](../sources/geodynamics/). Both API records state CC BY 4.0;
Müller 2019 also provides an agreeing License.txt inside and outside the archive.

- [Müller et al. 2019, model v1.2](https://zenodo.org/records/10525287),
  [paper](https://doi.org/10.1029/2018TC005462): 117 archive members, including 12 rotation
  files and 350 top-level GPML network features. `scripts/geodynamics.py` records member
  hashes, feature types and each network's name, ID, plate ID and raw validity strings.
  It counts feature objects rather than nested GPML value objects. It does not resolve
  topology, choose a GPlates project or calculate velocities. Greater India's stretched
  mesh file contains 16 network features, with validity intervals from 160 Ma down to
  21.1 Ma; this alone is not a complete India–Himalaya deformation history to the present.
- [Müller et al. 2022, supplementary data v3.0](https://zenodo.org/records/6622194),
  [paper](https://doi.org/10.5194/se-13-1127-2022): the 205,811,467-byte OPT1 ParaView ZIP
  contains **extracted surfaces**, not the full temperature volume. Slabs and Piles each
  have 51 PVTU frames, each with 12 VTU pieces. Their point fields are `Depth(km)` and
  `NonDimDepth`, respectively; neither is velocity or temperature. The companion plate
  boundaries are included in this preview. The large temperature NetCDF archives have
  not been downloaded.

Source archives stay gitignored. The existing `sources/plate-models/muller2022.json`
describes a different archive containing plate rotations; it is not this mantle output.
The new sources do not enter the existing plate-model menu or its packing pipeline.

## Reproduce locally

Install the existing `requirements-processing.txt` in `.venv` first. No new dependency
is needed. The Django process does not import NumPy or the processing scripts.

```bash
.venv/bin/python scripts/fetch_paleodem.py --manifest sources/geodynamics/muller2019.json
.venv/bin/python scripts/fetch_paleodem.py --manifest sources/geodynamics/muller2022-opt1.json
.venv/bin/python scripts/geodynamics.py
.venv/bin/python scripts/build_mantle.py
make run
```

Open `/mantle/` or the footer's “맨틀 모형 실험” link. The existing pinned-asset fetcher is
reused despite its historical name. Add `--verify-only` to either fetch command to
verify existing source files without a network request. Metadata snapshots are pinned
too: if upstream metadata changes, inspect it before updating its hash.

`build_mantle.py --frames 0 46 50` builds only the 1000, 80 and 0 Ma source frames for a
small local sample. This replaces the output catalogue with that selection. The default
build contains all 51 frames. An optional `--output` selects another derived directory.

## Time, geometry and binary format

The source ParaView state's `TimeToTextConvertor` specifies `Scale=-20` and `Shift=1000`:
`age_ma = 1000 - 20 * source_time`. Thus source frame 0 is 1000 Ma, and frame 50 is the
present. These are 20 Myr output intervals, not the solver timestep. The page snaps to
available frames and never interpolates different surface topologies.

The packer reads the pinned archive directly without extracting paths from it. Its
[VTK XML](https://docs.vtk.org/en/latest/vtk_file_formats/vtkxml_file_format.html) reader
supports the two encodings actually found: little-endian UInt64 uncompressed inline
binary arrays, and meshio's UInt32 zlib block encoding for plate boundaries. Other
encodings and unsupported cell types fail. It validates byte counts, indices, point
and cell counts, finite values and source times before packing.

Source Cartesian coordinates are retained with surface radius 1. For all mantle pieces,
depth fields are checked against `(1 - radius) * 6371 km` to within 0.1 km (the source
fields have rounded values). Piles' dimensionless depth is multiplied by 6371. The
viewer rotates the entire source scene by −90° about x, placing source +z north upward;
it does not rotate individual layers into a PALEOMAP frame. The wire sphere and grey
inner sphere (radius 0.546) are visual references, not computed temperature or core fields.

Each layer's binary payload contains float32 xyz positions followed by uint32 indices,
both little-endian. Slab and pile triangles retain source connectivity; plate polylines
become individual line segments. Partition boundary points are retained rather than
welded. Colour denotes the layer, not temperature, depth or velocity.

`data/derived/mantle/muller2022-opt1/catalogue.json` stores source archive hash, ages,
coordinate conventions, source members, counts, depth ranges, file names and hashes.
Files use content hashes in their names. A staging build publishes the catalogue last,
so a failed conversion does not replace the previous catalogue. Old unreferenced files
are not automatically deleted. The server serves only files named by the current
catalogue, with matching size/hash; arbitrary source files and ZIPs are not exposed.

## Transfer size and runtime

For the 51-frame build measured on 2026-09-15:

| Payload | Raw bytes | Gzip transfer bytes |
|---|---:|---:|
| All 51 frames, three layers | 174,819,852 | 92,515,323 |
| Present frame, three layers | 3,848,452 | 2,035,186 |
| Smallest frame | 1,477,240 | 769,844 |
| Largest frame | 3,916,992 | 2,075,642 |

The packer writes deterministic gzip representations. Django negotiates gzip, verifies
the selected representation, and supplies `Content-Encoding`, representation-specific
ETags, `Vary: Accept-Encoding` and one-year immutable caching for content-addressed
assets. Browsers decompress before the JavaScript binary reader sees the payload.

Only the selected frame is fetched; there is no timeline prefetch or autoplay. Input is
debounced 180 ms, and superseded requests are aborted. All three layers of the selected
frame are fetched even if one is hidden, so checkbox changes need no new transfer. Old
GPU geometry is disposed when a new frame succeeds. The preceding frame is hidden while
the new age loads, preventing an old structure from being shown with a new date.

1,000 complete uncached traversals would transfer about 92.5 GB of mesh payload after
gzip; 1,000 present-only loads about 2.04 GB. HTML, Three.js, other static assets, protocol
overhead and any interrupted transfers are additional. Browser cache savings are not
guaranteed; provider pricing and included traffic determine cost. CDN cache hits reduce
origin traffic but do not necessarily remove delivery charges. Measure before public rollout.

`MANTLE_DERIVED_DIR` overrides the runtime path. If data is absent or
`SCOTESE_VIEWER_ENABLED` is false, the page has an explanatory empty state and asset
routes return 404. The v0.11.0 packer requires all 51 mantle frames and the five-frame collision dataset,
including gzip representations, and verifies every catalogued asset before packaging.
The image sets `/runtime/mantle/muller2022-opt1` and `/runtime/india-asia` as their
runtime paths. No external storage or CDN configuration is required.

## Validation and next work

```bash
make check
make test
.venv/bin/python tests/geodynamics_check.py
# Development server on 8137, with the default 51-frame data built:
VIEWER_URL=http://127.0.0.1:8137/ node tests/mantle-browser.mjs
```

Synthetic tests cover VTK byte errors, compressed blocks, invalid topology, nonfinite
data and nested network counting. Django tests cover empty/disabled data, allowlisting,
corrupt/missing files and gzip negotiation. Browser checks cover ages, fast changes,
loading failure/recovery, toggles, mobile width and English. Screenshots are local under
`test-results/`. These checks verify the import and display; no independent ParaView
image comparison or scientific validation of the original simulation is claimed.

Next: resolve the Müller 2019 regional networks with a pinned GPlates implementation,
reconstruct material meshes and establish compatible reference frames. Temperature
sections require a different archive. Strain, crustal thickness, uplift and an offline
solver remain subsequent P03 stages.
