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
server pairs the pieces on the two maps that share a name, keeping only one-to-one
correspondences: a piece the segmentation split or merged across the gap has no single
place to travel to, so it is dropped rather than read as motion. It also drops any pair
whose centroids are further apart than 1.5 degrees of arc per million years, about 15
centimetres a year, which is faster than any plate anyone measures; two maps that
disagree by more than that disagree for some other reason. What survives is a handful
of control points per gap, each one a landmass with a start, an end and an angular size
taken from its area.

The shader turns those points into a displacement for every texel: a Gaussian falling
off over each piece's own radius, normalised across whichever points reach that texel,
and faded out where none do. A texel inside Africa moves with Africa; the open ocean
between continents stays put. The field is sampled at the texel's origin on the older
map and at its destination on the newer one, so the coastline morphs around a continent
that is moving rather than one that is melting. At most 16 control points are carried at
once, which is more than any of these maps needs.

Gaps with no surviving pair, 237 to 195 Ma among them, fall back to blending in place.

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
