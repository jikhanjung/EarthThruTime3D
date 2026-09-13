# Reference globe viewer

The home page renders the 17 Scotese reference maps with Three.js 0.186.0. Selectors
use original image ages from the provenance catalogue, including 356 Ma and 50.2 Ma.
The slider carries sub-steps between neighbouring maps, so dragging it moves rather
than jumps. Only the stops that land on a published map are observations; the ones
between are interpolated, and the caption, the inspector and the slider's accessible
value all say so.

## Mapping pipeline

1. Django exposes only manifest-listed map IDs through `/globe/maps/<id>.jpg`.
2. The browser loads original JPEGs from the same origin, preserving attribution.
3. Manually estimated ellipse bounds in `core/globe.py` exclude exterior headings and
   legends. Interior geographic labels, boundaries, and the equatorial line remain.
4. Each texel of a 1024 × 512 equirectangular canvas is inverse-sampled from the source.
   For output longitude lambda and latitude phi, solve
   `2 theta + sin(2 theta) = pi sin(phi)`, then sample the source ellipse at
   `x = (lambda / pi) cos(theta)`, `y = sin(theta)`. Bilinear interpolation and a 1%
   ellipse inset reduce edge contamination. Original JPEG files are never modified.
5. A Three.js sphere uses the canvas texture in sRGB. Normal-based limb shading gives
   the globe volume without deriving elevation from the image. OrbitControls handles
   mouse/touch navigation; controls and globe rotation also support the keyboard.

The Mollweide transform is an explicit **preview assumption**, not a verified CRS.
[PROJ's Mollweide reference](https://proj.org/en/stable/operations/projections/moll.html)
describes the projection. Scotese's later atlases use Mollweide, but this does not
establish the precise projection, crop, orientation or central meridian of these older
web JPEGs. Ellipse extents are visual estimates. Grid lines use viewer coordinates,
not validated geographic reference coordinates. Seams, polar distortion and baked-in
annotations remain possible. Source maps are low resolution and contain relief shading,
not elevation measurements. Do not use this display as a deformation reconstruction.

## Sampling the timeline

The server builds the slider's stops and sends them as `[from frame, to frame, blend,
age]`, so the viewer consumes a table rather than a rule and does not care how the stops
were spaced. Two samplings exist:

- `SCOTESE_VIEWER_STEPS` divides every gap into the same number of sub-steps, 1, 2, 4,
  8, 16 or 32, defaulting to 4, which gives 65 stops over the 17 maps. A stop is then a
  fraction of the way from one map to the next, regardless of how much time that gap
  covers, so the slider moves faster through deep time than through the Cenozoic.
- `SCOTESE_VIEWER_INTERVAL_MA` instead places a stop every so many million years, 0.5,
  1, 2, 5, 10 or 25, which makes the slider move at a constant rate through time. One
  stop per million year gives 653 stops. This is the sampling GPlates-style continuous
  time would want; see `docs/gplates-reference.md`.

The interval wins when both are set. Either way the published map ages are always stops
of their own, so the slider can still land on what the source actually drew, and the
blend at every stop is linear in age between the two maps that bracket it. `?steps=` and
`?interval=` override per request so a density can be tried without a restart; every
path goes through the same allowlists, so none can hand the slider an odd range.

More stops cost nothing in texture memory. Only 17 fields are ever loaded, whatever the
sampling; the extra stops are positions between them.

## Interpolated stops

Two textures are always bound, the maps or fields either side of the current stop, with
one shader mixing them. On the source-map surface that mix is a cross-fade: one picture
dissolving into the next, which is all a photograph of a map can support. On the derived
surface the textures are signed-distance fields rather than pictures, and mixing them
moves a coastline: each texel holds its distance to the nearest coast, positive on land,
so the midpoint of two distances is the coastline halfway between. Continents grow,
shrink and drift instead of fading through each other.

Blending two fields in place makes a landmass melt where it was and grow where it will
be. To move it instead, each side is sampled through a **travel field** first. The
server pairs the pieces on the two maps that share an identity, keeping only one-to-one
correspondences: a piece the segmentation split or merged across the gap has no single
place to travel to, so it is dropped rather than read as motion. Identity is the
annotated name, or the `track` where a map renames a body that has not changed, as when
the Asian landmass is drawn as Eurasia once Europe has joined it.

A shared identity is taken at its word however fast the implied motion is. India crossed
the Tethys at roughly 18 to 20 centimetres a year, close to two degrees of arc per
million years, so a speed limit tight enough to catch segmentation noise also throws
away the best-known journey on these maps. Each pair reports the rate it implies and is
flagged above two degrees per million years, so an implausible pairing stays visible
instead of being silently dropped.

What is dropped is measured rather than physical. A pair is refused when a piece is too
small to carry a morph, and when the two mapped areas differ by more than three times,
because then the centroids describe different extents of the same landmass rather than
a journey. Antarctica is the clearest case: these maps draw it as a broken ice fringe
and the segmentation keeps a different share of it each time, which moved its centroid
23 degrees between the Last Glacial Maximum and today, across eighteen thousand years.

What survives is a handful of control points per gap, each one a landmass with a start,
an end and an angular size taken from its area.

The shader turns those points into a displacement for every texel: a Gaussian falling
off over each piece's own radius, normalised across whichever points reach that texel,
and faded out where none do. A texel inside Africa moves with Africa; the open ocean
between continents stays put. The field is sampled at the texel's origin on the older
map and at its destination on the newer one, so the coastline morphs around a continent
that is moving rather than one that is melting. At most 16 control points are carried at
once, which is more than any of these maps needs.

Gaps with no surviving pair fall back to blending in place. So does any landmass with no
counterpart, which is why India shrinks rather than travels between 50 and 14 Ma: by 14
Ma the maps draw it as part of Eurasia, and a merge has no single destination.

`scripts/segment_landmass.py` writes each field as an equirectangular 1024 x 512 PNG,
land positive around mid-grey at two grey levels per pixel of distance. The distance
transform is run on the mask tiled three times in longitude so it crosses the
antimeridian rather than treating it as an edge; latitude keeps its real edges at the
poles. Django serves the fields from `/globe/fields/<id>.png` under the map allowlist.
Because the field is already equirectangular, the derived surface needs no reprojection
in the browser.

A name that exists on both sides of a stop travels between its two positions. A name on
only one side fades, because the piece it names has no counterpart to move to. Playback
walks the sub-steps at the same pace per source map as before, so it reads as motion.

What an interpolated stop shows is neither observation nor reconstruction. It is a
geometric blend of two published maps, with each landmass carried along a straight path
between the two positions the segmentation found for it. No plate motion, sea level or deformation is
computed, and the intermediate coastline belongs to no reconstruction anyone published.
Only the stops that land on a source map show what the source drew.

## Projections

A picker in the toolbar chooses what the map is drawn on: the globe, a Mollweide sheet,
or equirectangular. Mollweide is the one to compare against the source, because it is
the projection the Scotese maps are assumed to use, so the sheet reproduces their
layout. Equirectangular is the fields' own storage laid out flat, a 2:1 box with
longitude and latitude both linear.

One shader serves all three. On the globe the geometry's own coordinates already say
where to sample; on a sheet the fragment undoes the projection to a longitude and
latitude, then samples the same equirectangular fields. Undoing it is also what decides
whether a fragment is on the map at all: a Mollweide fragment outside the ellipse is
discarded rather than painted. Nothing about the data changes with the projection, so an
interpolated stop morphs the same way on a sheet as on the globe.

The grid is built from parallels and meridians rather than from the mesh, so it curves
on the globe and on Mollweide and rules straight lines on the equirectangular sheet.
Labels are placed through the same projection.

Web Mercator was offered for a while and then dropped. It is square rather than 2:1,
because the 85.0511 degree cut-off web maps use is chosen to make the projected height
equal the width, and a square world map of deep time is more confusing than useful next
to the ellipse the source itself draws.

Flat views pan instead of rotating, and auto-rotation is disabled there because a sheet
has nothing to spin. The sheet is held at one distance and the lens opens until it fits,
so resizing the window reframes the map without undoing the reader's zoom.

## Derived surface option

A toolbar toggle, **대륙 마스크**, swaps the source-map texture for the distance field
described above, cut at its midpoint into land and ocean. The cut is antialiased against
the field's own gradient, so the coastline stays crisp at any zoom. Land and ocean are
painted as two flat colours chosen to look nothing like the source palette, so the
derived globe cannot be mistaken for the published map.

Each named piece carries its name on the sphere while the mode is on. Names come from
`annotations/landmass-labels.json`, where an anchor point decides which segmented piece
holds which name. Most anchors are the positions of names the source map itself prints,
transcribed in source pixels, so a piece is identified by which present-day landmasses
it carries rather than by guesswork; the rest are geographic positions, and each
resolved name records which of the two it came from. A piece with one name is labelled
at its own interior point, found as the pixel furthest from its edge, so a label never
lands offshore. A piece holding several names is labelled at each anchor, which is what
makes a merged mass such as Afro-Eurasia or the Pangaea-Gondwana mass read correctly.
Names fade out as a piece turns past the limb. Small blocks can be kept in the data but
off the sphere with `display: false`, so the globe does not crowd.

These names are an interpretation. The source maps label present-day landmass outlines
drawn over the reconstruction, so a name says what a piece became, not what the map
calls the ancient landmass.

The toggle appears only when at least one field file exists, and it is disabled at a
stop whose neighbouring maps have not both been segmented. Fields live in gitignored
`data/derived/`, so a fresh checkout shows the source-map globe alone until the script
has been run.

What the mask surface shows is an interpretation: land and ocean as segmented from
printed colour, with continental shelf counted as ocean and ice sheets counted as land.
It is not the coastline the source map draws, and morphological cleanup rounds off
roughly a quarter of the raw land pixels at the edges. The inspector states this
whenever the mode is active. Pre-Mesozoic maps use a different palette and their masks
capture only the darker core of each landmass; see `devlog/20260912_003_*` for detail.

## Panel sizing

The notes about the derived surface and about an interpolated stop appear and disappear
as the viewer is used. Without a definite row height the explorer grid grew with them
and resized the globe, so the globe panel now has one height per breakpoint and the
inspector scrolls inside it, with a reserved scrollbar gutter so a scrollbar appearing
does not shift its text. The browser run asserts the globe panel keeps the same box
across the plain map, the derived surface and an interpolated stop.

## Runtime and data boundaries

Three.js modules and their MIT license are vendored locally using `npm run vendor`.
No browser CDN requests are needed. The only outgoing links are user-opened citations.
The browser caches a texture promise per frame. A monotonically increasing request ID
ensures stale asynchronous loads cannot replace the latest selected era. Failures are
retryable. Playback pauses on manual selection or when the page becomes hidden.

Development enables `SCOTESE_VIEWER_ENABLED`; production defaults it off. Activating
the production flag exposes all 17 original JPEGs to site visitors, so it is an explicit
operator choice after checking deployment and data-use terms. This does not grant a
new license. The allowlist does not expose arbitrary files, HTML snapshots, or DB files.

## Verification

- `make check`, `make test`: catalogue, age exceptions, allowlisting, disabled and
  missing-data behavior, plus the existing site tests.
- `npm test`: projection landmarks, hemisphere signs, ellipse containment and raster
  axis orientation.
- `npm run test:browser` with the development server running: all 17 maps, keyboard
  rotation, mouse drag/zoom, playback, rapid selection, the land-mask toggle, mobile
  overflow, failed-load recovery and JS errors. Screenshots go to gitignored
  `data/screenshots/`.
- `.venv/bin/python tests/segmentation_check.py` with `requirements-processing.txt`
  installed: the inverse projection against the viewer's forward mapping, the inset
  ellipse mask and the colour conversion. Kept out of the Django suite because the web
  app does not depend on those packages.

## Elevation series

The viewer can show a second timeline: the 1° PALEOMAP PaleoDEMs of Scotese and Wright
(2018), 109 elevation and bathymetry grids from 540 Ma to the present at 5 Myr, CC BY 4.0.
`sources/paleodem-slices.json` lists them oldest first; `scripts/fetch_paleodem.py`
fetches the pinned archives and `scripts/build_paleodem.py` writes one texture per
slice, `paleodem-<age×10>-field.png`, beside the segmentation fields.

Two builds exist. The default reads the 1° grids into 1024 × 512 textures, which is
already a 2.8× upsample and shows all that data has. The sharper build reads the
6-minute grids (0.1°, the same slices, 207 MB archive) into 2048 × 1024:

```bash
.venv/bin/python scripts/build_paleodem.py --width 2048 \
  --source data/sources/paleodem/nc6/<unzipped directory>
```

About 1 MB per slice instead of 180 KB; the 6-minute source is bilinearly downsampled
about 1.8× on the way, so it aliases slightly rather than smearing. 4096 was measured
and rejected: 3 MB per stop on mobile data and 34 MB of GPU memory per texture.

Each texture is an RGB PNG on the same 1024 × 512 equirectangular grid. Red is the
signed coastline distance the segmentation writes, taken at the 0 m contour of the
bilinearly resampled grid, so mask mode, the stop table and the blend between stops work
unchanged. Green is elevation quantised over -9000 to 6000 m, which puts sea level at
0.6; the shader colours it with a hypsometric ramp, blue by depth and green through tan
to white by height, and decides land against ocean from the distance rather than from
the height so the coastline stays antialiased. The mask toggle returns to this relief
view rather than to a photographed map.

`GLOBE_SERIES` picks the series (`paleodem` by default, `scotese` for the 17 web maps);
`?series=` overrides per request through the same allowlist. A checkout or deployment
without the complete set of PaleoDEM textures falls back to the Scotese series, all or
nothing, because a frame without a field has no map to fall back to; so the runtime
bundle, which does not yet pack these textures, keeps serving what it has. `/healthz`
validates whichever series is served and names it. The browser check
pins `?series=scotese` because its assertions count that series' names and motions.

Fields are uploaded as raw bytes rather than as decoded images. A Samsung phone was
found reading both channels low through the `<img>` path, and through an ImageBitmap
decoded with conversion off, which put the coastline where the distance byte is about
188 instead of 128 and drew every interior at the lowest height. WebGL colour-converts
only DOM image sources, so the viewer decodes to a 2D canvas, reads the bytes back and
uploads a `DataTexture`, which the specification leaves untouched.

The texture cache is bounded at twelve, least recently used first, and the stage reports
its size as `data-cached`. Two textures are bound at any stop; the rest only save a
re-download when scrubbing back. Without the bound a phone that had scrubbed the whole
timeline would hold every slice, near a gigabyte at 2048 × 1024.

What this series shows at a published slice is the reconstruction grid as its authors
released it, not a measurement of ours. Between slices it is the same geometric blend as
before, of distance and of height, with no travel field: the grids carry no piece
identities, so nothing moves as a body. The elevation values are the grid's own; the
palette is this project's choice.
