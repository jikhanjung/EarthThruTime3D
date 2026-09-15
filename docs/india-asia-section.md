# India–Asia A–A′ section experiment

The globe inspector and the mantle page have an **인도–아시아 A–A′ 단면** button. It
opens a native modal dialog containing `/collision/` in a same-origin iframe. The
iframe is loaded only on opening and removed on closing, stopping playback and
releasing rendering resources. Escape works inside the iframe, and focus returns to
the opener. `/collision/` also works as a standalone page.

## Chosen window and section

- Viewing starts at **80 Ma**, before the commonly discussed collision intervals; it
  is not a claim that collision began then. Collision timing depends on location and
  the event being dated; see [Najman et al. 2010](https://doi.org/10.1029/2010JB007673).
- A–A′ is a **fixed 85°E meridian**, from 40°S to 60°N, through the present central
  Himalayan region. The wide southern extent includes the older Indian position.
  This is a spatial section, not a section following the same material through time.
- Five original OPT1 frames are used: **80, 60, 40, 20, 0 Ma**. Playback switches between
  them; no interpolation of different mantle surface topologies is performed.

## What each view represents

| View | Source or calculation | Interpretation |
|---|---|---|
| Expandable regional map | OPT1 companion Cratons and plate-boundary VTUs | Published moving continental interiors and plate boundaries; not full coastlines |
| Mantle section | Triangle intersections of OPT1 Slabs and Piles with 85°E | Actual cuts of published extracted surfaces; neither a temperature volume nor a velocity field |
| 3D regional terrain | Existing Scotese & Wright 2018 PaleoDEM field textures at the same five ages | Published reconstruction sampled for display; uses PALEOMAP, not OPT1's reference frame |
| Conceptual convection | Three illustrative circulation loops in a separate strip, off by default | No measured or simulated velocity; no coupling to the crust calculation |
| Local crust scenario | Adjustable shortening, area conservation and simple isostasy | An uncalibrated explanatory model in its own distance coordinates |

The terrain and mantle share age labels and geographic bounds, **not an established
reference-frame transformation**. They are shown side by side, not merged into one
physical geometry. The 3D terrain marks its own 85°E line. Deforming Müller 2019 networks
are not yet used to calculate the local crust scenario.

The section source is [Müller et al. 2022 OPT1 supplementary data v3.0](https://zenodo.org/records/6622194).
Terrain comes from [Scotese & Wright 2018](https://doi.org/10.5281/zenodo.5460860).
Both are CC BY 4.0 and credited inside the popup.

## Processing and transfer

With the existing OPT1 source files and PaleoDEM field textures available:

```bash
.venv/bin/python scripts/build_india_asia.py
```

The builder verifies the pinned OPT1 archive and metadata using the existing source
manifest. It reads the archive directly, intersects each triangle with the meridian
plane, selects the 85°E half-plane, clips to the latitude/depth window, and deduplicates
shared-edge segments. Tangent vertices and fully coplanar faces do not create arbitrary
line segments. Analytic intersection tests cover these cases independently of OPT1.

The regional map clips line segments to 40–115°E, 40°S–60°N. The terrain samples that
same window on a 129×161 grid, bilinearly decoding the existing field PNG's green/blue
height channels. Its grid is deliberately coarser than the underlying PaleoDEM.
Heights rounded to metres do not acquire metre-scale scientific accuracy. Each frame
records the input field's SHA-256 and ID. Source archive provenance is in
`sources/paleodem.json` and `sources/geodynamics/muller2022-opt1.json`.

The terrain display is a planar regional projection using a constant longitude scale
at 10°N. It is not a curved globe or a distance-preserving projection across the full
region. Heights above 0 m displace vertices; ocean water remains at 0 m. Colour follows
unexaggerated elevation. No ice, vegetation or photorealistic surface is inferred.

The five-frame output measured on 2026-09-15 is **1,510,100 bytes raw / 420,502 bytes
gzip**, including the 3D terrain heights. Before adding terrain it was 242,091 bytes
gzip. The original global 3D meshes are not downloaded by the popup. One data request
loads all five frames; timeline changes, layer toggles and exaggeration controls then
need no additional data requests. Three.js and other page assets are additional and
can share browser cache with the main globe.

Output goes to `data/derived/india-asia/` (`--output` can override). Content-addressed
JSON and gzip assets are published before `catalogue.json`. Django serves only the
catalogued hash with size/hash verification, gzip negotiation and immutable caching.
`INDIA_ASIA_DERIVED_DIR` selects the runtime directory. Missing data or a disabled
viewer produces an explanatory empty state. The v0.11.0 runtime bundle includes these files and all 51 mantle frames; packaging
requires the complete source-age selections and verifies their hashes.

## Exaggeration and local assumptions

Three independent controls keep view exaggeration separate from physical parameters:

- Mantle section: ×1, ×2 (default), ×5, ×10.
- Local crust section: ×1, ×5, ×10 (default), ×20, ×50.
- 3D terrain elevation: ×1, ×10, ×25, ×50 (default), ×100.

For both 2D sections, pixels per vertical km equal pixels per horizontal km times the
selected factor. The mantle horizontal scale converts latitude degrees using a 6371 km
radius. The canvas grows in height rather than changing or clipping the underlying
depth range. A scrollable viewport retains the full section at large factors. The
rendered factor is printed on each section. The 3D terrain applies the selected factor
to elevation, leaving horizontal coordinates and colour unchanged.

The local crust model assumes initial width W₀=2000 km and thickness H₀=35 km.
The user selects a shortening onset T of 50, 60 or 65 Ma and a total shortening S₀
between 0 and 1200 km (default 1000). These control ranges are **not confidence intervals**.
At age t, S=S₀·clamp((T−t)/T,0,1), W=W₀−S, H=W₀H₀/W. Material columns conserve area
per unit strike length. With crust/mantle densities 2800/3300 kg/m³, illustrative
isostatic uplift is (H−H₀)·(3300−2800)/3300.

The default reaches 70 km thickness and approximately 5.3 km uplift at the present by
construction. Those values are not measurements, a calibrated Himalaya reconstruction
or independent predictions. Erosion, subduction, flexure, rheology and mantle traction
are absent. The dashed outline is the initial crust; the solid columns show the local
assumption. Changing visual exaggeration does not change these physical values.

## Validation

```bash
make check
make test
.venv/bin/python tests/india_asia_check.py
node --test tests/collision.test.mjs
# With a development server and the regional data built:
VIEWER_URL=http://127.0.0.1:8140/ node tests/collision-browser.mjs
```

The checks cover analytic slicing, clipping and duplicate edges; area conservation and
scenario bounds; verified data delivery and same-origin framing; lazy popup loading,
frame/terrain age synchronization, vertical scaling, toggles, playback, Escape/focus,
mobile layout and English. They do not validate mantle convection or crustal evolution.
