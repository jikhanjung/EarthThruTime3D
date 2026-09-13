# Reference globe viewer

## Languages

Korean is the source language and English lives in `locale/en/LC_MESSAGES/django.po`. The
KO|EN switch in the header calls `/lang/<code>/`, which sets Django's language cookie and
redirects to the page it came from. Templates use `{% trans %}`; the viewer script gets its
sentences translated by the server as `globe-strings` JSON and fills `{placeholders}`;
continent names take `name_en` from the piece reports. `scripts/compile_messages.py`
compiles the `.po` to `.mo` (no msgfmt here or in the image); `make check` and the Docker
build run it. A Django test renders every page in English and fails on any remaining
Hangul, which is how a missing translation shows up.

## Mask sources

The globe can draw its land masks from two sources, and `core.globe.MASK_SOURCES` lists
them:

- `paleoatlas2016`, the default: 90 maps from the PALEOMAP PaleoAtlas for GPlates
  (Scotese 2016), 750 Ma to present, segmented by `scripts/segment_paleoatlas.py`. They
  are the same edition as the PALEOMAP rotation model, so their land and that model's
  plates agree. The rasters are equirectangular, so no projection is assumed. Korean
  period labels come from each map's age with ICS 2023/09 boundaries; the English title is
  the file name's stage. The rasters themselves are never served.
- `scotese2002`: the 17 web maps described in the rest of this document, with names and
  named-landmass motion.
- `paleodem2018`: the 109 PALEOMAP PaleoDEMs (Scotese & Wright 2018, CC BY 4.0), 0 to
  540 Ma at 5 Myr, as elevation textures rather than masks, fronted by the three 2016
  atlas maps older than 540 Ma drawn as masks: 112 stops. See "Elevation series" below.
  A `?masks=paleodem2018` request is honoured only when every field of the series
  exists, since a frame without a field has no map to fall back to; `MASK_SOURCE` is
  trusted like the other sources, and `/healthz` fails on what is missing. The page links
  to the series for comparison only when it can be shown, and `deploy/pack_data.py` packs
  it only when `data/derived/paleodem/` exists (then all of it).

`MASK_SOURCE` sets the default; `?masks=scotese2002`, `?masks=paleoatlas2016` or
`?masks=paleodem2018` picks one per page, and anything else falls back to the default. `/globe/fields/<id>.png` finds a
field by map id in either source; `/globe/maps/` only ever has the 2002 maps.

The 2016 maps carry no lettering, so their names come from the plate model.
`scripts/segment_paleoatlas.py` rasterises the PALEOMAP polygons at each map's age and
splits every piece into regions by plate group (`annotations/paleomap-plate-groups.json`,
an operator-curated table of plate-id families with Korean names and older names such as
Laurentia and Baltica). The largest region of each group covering at least 0.2% of the
sphere is named. `scripts/atlas_motions.py` then carries each region's centroid across a
gap with its dominant plate's rotation, back to present-day coordinates at the older age
and forward to the newer one, and writes the pairs to `motions.json` in the form the morph
already reads. `core.globe.atlas_motions` uses that file only if its gaps match the frames
exactly. Unlike the 2002 motions, nothing here is matched between two segmentations; the
morph still translates each region's neighbourhood rather than rotating it, so turning
within a large region is approximated.

Over the 2016 masks the inspector also offers a checkbox for the fossil-checked coastlines of
PaleoCoastlines v7.1 (Kocsis & Scotese 2021). `scripts/pack_coastlines.py` verifies the
archive against `sources/paleogeography/paleocoastlines2021.json` and writes one JSON per
age (81 ages, 0-535 Ma, simplified to 0.1 degree) plus an index. The lines are already in
reconstructed PALEOMAP coordinates, so they are drawn without rotation, in orange, at the
coastline age nearest the reader's age within 10 Myr; further than that, or older than
535 Ma, nothing is drawn and the note says why. Between two maps the surface is carried
by the gap's motion field, and a coastline published at either end of that gap rides the
same field (`carryRings`, with `travelAt` as a JavaScript twin of the shader's `travel()`):
forward by the blend from the older end, back by the rest of the way from the newer end,
so the line and the coast under it agree and the note says the line was carried. A
coastline from outside the gap, where both ends are missing from the set, stays where it
was published. `/globe/coastlines/<age>.json` serves only
ages the index lists. The layer is not offered over the 2002 maps, whose longitudes drift
from the PALEOMAP frame. Where the orange line runs inside the mask's edge, marine fossils
say that ground was sea.

The rest of this document describes the 2002 path, which is where the viewer began.

The home page renders the 17 Scotese reference maps with Three.js 0.186.0. Selectors
use original image ages from the provenance catalogue, including 356 Ma and 50.2 Ma.
The slider carries sub-steps between neighbouring maps, so dragging it moves rather
than jumps. Only the stops that land on a published map are observations; the ones
between are interpolated, and the caption, the inspector and the slider's accessible
value all say so.

## Elevation series

`sources/paleodem.json` pins the Zenodo archives of the PaleoDEMs by SHA-256, the 1°
and the 6-minute grids; `scripts/fetch_paleodem.py` fetches or verifies them (and any
other manifest with `--manifest`), and `sources/paleodem-slices.json` catalogues the
109 grids in the shape the other catalogues use. `scripts/build_paleodem.py` writes one
texture per grid into `PALEODEM_DERIVED_DIR`, `paleodem-<age×10>-field.png`, 2048 × 1024
by default from the 6-minute grids (`--width`, `--source`, `--bits`).

Each texture is an RGB PNG on the equirectangular grid. Red is the signed coastline
distance the segmentations write, taken at the 0 m contour of the bilinearly resampled
grid, so mask mode, the stop table and the blend between stops work unchanged; the
distance transform is `scripts/segment_paleoatlas.py`'s. Green is the high byte of
elevation over -9000 to 6000 m, which puts sea level at 0.6, and blue four more bits
(`--bits 12`, 3.7 m steps, the default) or nothing (`--bits 8`, 59 m steps, files 1.8
times smaller); the shader decodes both the same way. A 16-bit low byte was tried and
dropped: it is noise to the PNG compressor and tripled the set.

A third shader mode colours the height with a hypsometric ramp, blue by depth and green
through tan to white by height, and decides land against ocean from the distance rather
than from the height so the coastline stays antialiased. The mask toggle returns to this
relief view rather than to a photographed map. A frame without heights, the atlas
prelude, draws as a mask, and so does the gap down to 540 Ma.

Fields are uploaded as raw bytes rather than as decoded images. A Samsung phone was
found reading both channels low through the `<img>` path, and through an ImageBitmap
decoded with conversion off, which put the coastline where the distance byte is about
188 instead of 128 and drew every interior at the lowest height. WebGL colour-converts
only DOM image sources, so the viewer decodes to a 2D canvas, reads the bytes back and
uploads a `DataTexture`, which the specification leaves untouched. The texture cache is
bounded at twelve, least recently used first, and the stage reports its size as
`data-cached`; without the bound a phone that had scrubbed the whole timeline would hold
every slice, near a gigabyte at 2048 × 1024.

What this series shows at a published slice is the reconstruction grid as its authors
released it, not a measurement of ours. Between slices it is the same geometric blend as
the other sources, of distance and of height, with no travel field: the grids carry no
piece identities, so nothing moves as a body. Sea level is inside each grid as its 0 m
datum, so flooded interiors are the reconstruction's; floating ice shelves are sea floor
in the grids and read as ocean, while grounded ice shows its surface height.

### Names and motion between grids

The grids are never segmented, so they have no pieces of their own. They are the same
paleogeography as the 2016 atlas, from the same edition, and 81 of the 109 grids sit at
the age of an atlas map, the rest within 5 Myr of one. `core.globe.piece_report` therefore
gives a grid the pieces of the nearest atlas map (`nearest_atlas_map`, `NEAREST_ATLAS_MA`),
which is where its landmass names come from; on a borrowed age a name sits where the atlas
drew it, a few degrees off at most. `scripts/paleodem_motions.py` does the same for the
motion between grids: for each gap of the series it takes the plate-group regions of the
atlas map nearest the older end, carries every centroid from that map's age to the gap's
older age and on to its newer age with the region's plate, and writes
`data/derived/paleodem/motions.json` in the form `atlas_motions` reads. The packer ships
the file with the series. Without it the grids blend in place.

## Temperature

`sources/paleotemp.json` pins Scotese (2021), *Global Mean Surface Temperatures for 100
Phanerozoic Time Intervals*, Zenodo 8238875, CC BY 4.0: 1° surface air temperature maps,
climate-model output (Valdes et al. 2021) nudged to proxies. `scripts/build_paleotemp.py`
turns them into one grayscale 1024 × 512 texture per grid of the elevation series,
`<id>-temp.png` in `PALEODEM_DERIVED_DIR`, encoded over −60..60 °C, taking the nearest
map within 5 Myr; the atlas prelude has none. It also writes `paleotemp-curve.json`: the
area-weighted global mean of every map, and the mean each grid was given. The server
passes the curve to the page and each frame its texture route and mean.

A 기온 toggle switches the surface to a fourth mode: a diverging ramp, blue at −30 °C
through pale at 0 to red at 40 °C, with the coastline from the distance field drawn as
a dark line so the continents stay readable. Between stops the two maps are mixed like
the fields. Above the slider a strip colours every stop by the global mean at its age,
linear between maps and grey where none reaches, over 5 to 35 °C so an icehouse reads
blue; the inspector reads out the mean at the current stop, interpolated between the
neighbouring maps' means when the stop is between them, and adds its difference from
today's mean. Under the readout a colour key draws the surface ramp with its −30, 0, 20
and 40 °C marks, today's global mean as a white tick and the stop's mean as a marker,
so a colour on the globe can be read against the present. It shows only while the
temperature surface does; `data-delta` on the key carries the difference for tests.

These are model fields nudged to proxies, not observations, and the note says so. The
global mean is this project's own reduction of the published maps. PhanDA (Judd et al.
2024), the current reference curve, is cited and not shipped: its repository carries no
licence.

## Sea level

Each PaleoDEM is paleotopography and paleobathymetry with its own sea level as the
0 m datum, so the shoreline the viewer cuts is the reconstructed shoreline of that
time, flooded interiors included: land covers 28% of the globe at present, 23% at 80
Ma and 15% at 430 Ma in the grids. What the grids lack is variation inside a 5 Myr gap
and the glacial cycles inside a slice.

`scripts/build_sealevel.py` writes `sealevel-curve.json` into `PALEODEM_DERIVED_DIR`
from two pinned curves (`sources/sealevel.json`), both CC BY: the long-term Phanerozoic
curve of van der Meer et al. (2022) at 1 Myr with min, max and the same paper's land-ice
volume, and the Late Pleistocene stack of Spratt & Lisiecki (2016) at 1 kyr. The server
passes both to the page and gives every grid the long-term value at its age as `sea_m`,
the slice's datum.

The page draws the long-term curve above the slider as a line with its min–max band,
one column per stop, a baseline at present sea level and a labelled metre axis. Columns
are shaded where the land-ice estimate exceeds 5 million km³, a fifth of today's ice:
the spans where glacial cycles exist that a 1 Myr curve smooths over, and the legend
says so. The present-day column carries a whisker for the range of the last 800,000
years, −130 to +8 m, which that single column hides. The inspector reads out the value
at the current stop and shows the last 800,000 years as a chart with its own axes.

A control in the inspector moves sea level. It is a what-if and the note says so. A fixed
choice, −120 to +120 m, shifts the height channel by that much and cuts the coast from
the height instead of the distance field, antialiased over the height's own
screen-space change; the hypsometric colours follow the new level. The curve choice
applies only the published curve's departure from the datum the bracketing grids
already carry, `curve(age) − mix(sea_m_from, sea_m_to, blend)`, because adding the
curve itself would count the slice's own sea level twice. The atlas prelude has no
heights and takes no offset. This control is why the textures default to 12 bits.

## Ice

Only the present day has an open outline of ice. `scripts/build_ice.py` rasterises
Natural Earth's 10 m glaciated areas and Antarctic ice shelves, public domain, onto the
0 Ma grid's texture, `paleodem-0000-ice.png` in `PALEODEM_DERIVED_DIR`: red is grounded
ice, green a floating shelf. Longitude and latitude map linearly to the equirectangular
grid, so there is no reprojection; polygon parts are filled one by one, so a hole is
filled as ice too, which touches a few nunataks and nothing else at this resolution.
`/globe/ice/<id>.png` serves it and a frame of the elevation series carries `ice` only
where a mask exists.

The shader draws grounded ice near-opaque white and shelves paler over whatever
surface is showing, in relief, mask and temperature modes; a 빙하 toggle hides it. One
third of the grounded ice lies where the PaleoDEM reads ocean, because the West
Antarctic ice sheet rests on bedrock below sea level and the grid holds the bed; so the
overlay ignores what is beneath, and the note says why. Between 5 Ma and now the
overlay fades, because the 5 Ma grid has no mask; the note says that the fade is
missing data, not ice loss. Past ice is issue #7.

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

The flat sheets turn about the pole. A left drag, the left and right arrow keys, or the
auto-rotate button shift the sheet's centre meridian; the shader samples the fields that far
round, and the grid, names, plate boundaries and coastlines are placed through the same shift
and broken at the new seam. A right drag pans and the wheel zooms; reset returns the meridian
to 0.

Beside the timeline a spacing picker offers steps per map or one stop every 1, 5 or 10 Myr.
The server builds the stops, so a change reloads the page with `interval` or `steps` and the
current `age`, and the viewer opens at the stop nearest that age. With a spacing in Myr,
playback advances one stop every 300 ms.

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

## Older than any map

The published maps stop at 650 Ma, but the plate models reach 1000 and one reaches 1800.
The slider now runs past the oldest map, every 25 Ma, into stops that carry no map at
all. A map frame index of -1 is what marks them on the wire.

At such a stop the globe is painted bare ocean and the reconstruction is drawn over it.
Nothing about the surface is being claimed: there is no measurement of land there, and
the inspector says so. The source preview is hidden, because leaving the last map up
would read as if it applied. Coming back inside the map range restores everything.

A model that does not reach the chosen age leaves the globe empty, which looks like a
failure and is not one, so the inspector names the models that do reach it. With Merdith
selected at 1300 Ma the note points at Cao; with Cao selected the reconstruction appears.

## The plate model overlay

A second toolbar toggle, **판 재구성**, draws EarthByte's Merdith et al. (2021) plate
model over whatever the globe is showing. This is a different dataset, not a different
view of the same one: the Scotese surface is this project's measurement of published
pictures, while these lines are computed from a rotation model. Where the two disagree,
two models disagree; neither is a correction of the other. The inspector says so
whenever the overlay is on, and carries the citation the CC BY licence requires.

`scripts/pack_plates.py` repacks the model for the browser. Continent outlines are
simplified with Douglas-Peucker at 0.12 degrees, which takes 75,000 points down to
15,000, far finer than a globe a few hundred pixels across can show. The rotation file
becomes sequences keyed by moving and fixed plate. Both ship in the runtime bundle and
are served from `/plates/<name>.json` behind a three-name allowlist. Coastlines are
packed too; the continents layer is the one drawn, because the authors say coastlines
are mainly meaningful for the past 400 Ma while continents span the billion years.

`static/core/rotation.js` composes a plate's rotation at any age: walk the chain of
fixed plates to the anchor, and inside a sequence split the rotation from one sample to
the next. It is the same algorithm as `scripts/rotation_model.py`, which is checked
against the GPlates Web Service, and `tests/rotation.test.mjs` keeps the two from
drifting apart. Outlines are rebuilt per stop rather than eased, so the geometry is
exact at the age on screen. Rings crossing the antimeridian are broken on flat
projections, where a wrap would otherwise draw a line back across the map.

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
