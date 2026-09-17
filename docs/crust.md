# Present-day CRUST 2.0 display

The main viewer provides a present-day crust thickness colour map, point readouts
and a cutaway shell. In **Earth interior**, enable **Crustal thickness** at 0 Ma.
Crust and mantle can be enabled independently and use the same **Surface cutaway**:
south/north latitude and west/east longitude. West greater than east crosses the
date line; -180 to 180 covers all longitudes; equal longitudes leave the surface
uncut. The shell walls follow the parallels and meridians without a wall at the
longitude seam for a full band. India–Asia is a location preset (35°E–125°E,
35°S–55°N), separate from the fixed scientific A–A′ section.

Enabling the mantle at 0 Ma keeps the crust visible and preserves the camera.
Elsewhere the mantle selects the nearest available 80/60/40/20/0 Ma frame.
Crust remains present-day only; selecting an older mantle age hides it and returning
to 0 Ma restores it. Shared cut settings survive either layer being switched off.
Thickness scale is 1× by default, with an explicitly labelled 5× illustration.
Planar projections show the colour map only and disable the shared cut controls.

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
The derivative contains 1,448 missing cells (including the sampled south-polar
location); these stay missing, shown grey in the map and omitted from the shell.

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

## 절개 안쪽과 조작

절개에서는 반대편 지표와 지각 안쪽도 그리며 카메라 방향에 따른 반구 제거를 하지 않는다.
지각 안쪽→절개 벽→지표 순서를 명시하여 100%에서 99% 불투명도로 바뀔 때
내부 갈색 면이 지표를 덮지 않게 한다. 투명 지각도 깊이를 기록하여 반대편 면의 덧칠을 막는다.
오른쪽 드래그는 이동, 휠/핀치는 확대, 휠 클릭 또는 Shift 드래그는 기울이기다.
이 조작은 고도 표시 여부와 관계없이 모든 지구본에서 같다.
