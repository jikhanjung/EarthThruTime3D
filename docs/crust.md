# Present-day CRUST 2.0 display

The main viewer provides a present-day crust thickness colour map, point readouts
and a cutaway shell. Enable **Crustal thickness** at 0 Ma. The independent cutaway
works without the mantle overlay; when the mantle cutaway is on, both use its
centre and radius. Thickness scale is 1× by default, with an explicitly labelled
5× illustration. Planar projections show the colour map only.

## Scientific meaning

Source: Laske, G., Masters, G., and Reif, C. (2000), *CRUST 2.0: A new global
crustal model at 2×2 degrees*, IGPP, UC San Diego, distributed in
[EarthByte GPlates 2.3](https://www.earthbyte.org/webdav/ftp/earthbyte/GPlates/GPlates2.3_GeoData/Rasters/Crustal_Thickness.zip).
The package License.txt states CC BY 4.0. The packaged legend establishes km units.
The NetCDF has been resampled to 2 arc minutes; the underlying model remains 2°.

This is a model, not an observation at every displayed pixel. Our 1-degree
cell-centred grid samples the already resampled derivative without an additional
averaging kernel; colours use nearest cells, and surface geometry interpolates
between its vertices. Quantization is 0.01 km for storage, not a precision claim.
Point readouts round to whole km and use the same cell as the colour map.

The package does **not** establish the water/ice inclusion and vertical datum of
its z variable. The mesh therefore draws a **thickness-equivalent reference shell**
below the displayed surface, not a physical Moho surface or seabed-to-Moho model.
Its radius is `displayRadius - thicknessKm * scale / 6371`. The top follows the
existing display relief, including its exaggeration. This schematic shell is
not coupled to the separately sourced OPT1 mantle surfaces; 5× may intersect them.
Confirm the layer conventions and consistent topography before any future physical
Moho interpretation. This is an explicit adjustment to the physical-shell step in P07.

The data apply only at **0 Ma**. Age changes hide the layer atomically with the new
surface and restore the retained option at 0 Ma. No present-day thickness field is
rotated back in time or presented as a palaeocrust reconstruction. Downloading is
lazy, cached within the page, and does not block the existing globe. A late response
is checked against the committed age and toggle state before it is displayed.

## Reproduce

```sh
.venv/bin/python scripts/build_crust.py --archive /path/to/Crustal_Thickness.zip
```

The builder checks the pinned source hash/size, ZIP CRC, licence, coordinates,
longitude seam and value range. It stores the verified archive in `data/raw/crust/`
and writes `data/derived/crust/`. The catalogue describes south-to-north rows,
west-to-east cell centres, little-endian uint16, 0.01 km units and missing=65535.
The source manifest is `sources/crust/crust2.json`.

- Raw display grid: **129,600 bytes**.
- Gzip HTTP representation: **65,829 bytes**.
- Runtime bundle: catalogue, binary and gzip only; no original archive or source PNGs.
- `CRUST_DERIVED_DIR` defaults beside `PALEODEM_DERIVED_DIR`, so the Docker runtime
  layout resolves to `/runtime/crust` without a new production secret or DB change.
- Server checks catalogued hash/size and supports ETag/gzip. Browser checks decoded
  byte length, SHA-256 and value range before creating a GPU texture.

## Validation

`make check`, `make test`, `npm test`; browser checks:

```sh
VIEWER_URL=http://127.0.0.1:8151/ node tests/crust-browser.mjs
FIREFOX_CRUST=1 VIEWER_URL=http://127.0.0.1:8151/ node tests/firefox-browser.mjs
```

On Linux installations without headless WebGL2, use `FIREFOX_HEADLESS=0` under
Xvfb and set `FIREFOX_BIN` to an available Firefox executable.
