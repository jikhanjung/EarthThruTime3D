# Reference globe viewer

The separate [`/mantle/` experiment](geodynamics.md) displays published Müller 2022
OPT1 mantle surfaces and their accompanying plate boundaries. The new
[80–0 Ma approximate overlay](globe-mantle-overlay.md) places slab and pile surfaces
beneath the main PALEOMAP globe using an explicitly approximate Africa-anchored rotation.
Neither view calculates convection or crustal deformation.
The inspector's [India–Asia A–A′ popup](india-asia-section.md) compares the regional
mantle section and PaleoDEM 3D terrain, with independent vertical exaggeration controls.

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

The globe offers three surface datasets in `core.globe.MASK_SOURCES`: two segmented
land-mask series and one elevation series. This document describes v0.14.0 (2026-09-16).

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
field by map id across the three sources; `/globe/maps/` only ever has the 2002 maps.

The 2016 maps carry no lettering, so their names come from the plate model.
`scripts/segment_paleoatlas.py` rasterises the PALEOMAP polygons at each map's age, a
ring that winds around a pole closed through the pole so Antarctica keeps its cap, and
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

The viewer uses Three.js 0.186.0 for all three datasets. The original 2002 path keeps
its image-title ages, including 356 Ma and 50.2 Ma, and its approximate image reprojection;
those details do not describe the equirectangular 2016 atlas or PaleoDEM grids.
The slider carries intermediate stops between source maps. Source-map stops reproduce
published reconstructions, not direct observations of the past; intervening surfaces
are this project's interpolations and are labelled accordingly. The sections below
cover both shared viewer behavior and dataset-specific processing.

## Elevation series

`sources/paleodem.json` pins the Zenodo archives of the PaleoDEMs by SHA-256, the 1°
and the 6-minute grids; `scripts/fetch_paleodem.py` fetches or verifies them (and any
other manifest with `--manifest`), and `sources/paleodem-slices.json` catalogues the
109 grids in the shape the other catalogues use. `scripts/build_paleodem.py` writes one
texture per grid into `PALEODEM_DERIVED_DIR`, `paleodem-<age×10>-field.png`, from the
6-minute grids when `scripts/fetch_paleodem.py` has unpacked them and from the 1° grids
otherwise; the builder prints which. The pinned 6-minute archive holds all 109 slices,
385.2 and 390.5 Ma rounded to whole numbers, which the lookup matches by age. A 2048-wide
texture from the 1° grids shows every cell as a six-pixel block, the Caspian as Lego, so
a deployment wants the 6-minute set fetched before building (`--width 2048`, the default
1024 wide; `--bits`; `--source` to override).

Each texture is an RGB PNG on the equirectangular grid. Red is the signed coastline
distance the segmentations write, taken at the 0 m contour of the bilinearly resampled
grid, so mask mode, the stop table and the blend between stops work unchanged; the
distance transform is `scripts/segment_paleoatlas.py`'s. Green is the high byte of
elevation over -9000 to 6000 m, which puts sea level at 0.6, and blue four more bits
(`--bits 12`, 3.7 m steps) or nothing (`--bits 8`, 59 m steps, files 1.8 times smaller,
the default); the shader decodes both the same way. A 16-bit low byte was tried and
dropped: it is noise to the PNG compressor and tripled the set.

A third shader mode colours the height with a hypsometric ramp, blue by depth and green
through tan to a light grey by height, white being kept for the ice layer, and decides land against ocean from the distance rather
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
the other sources, of distance and of height. The grids carry no piece identities of
their own, so the travel field is borrowed from the atlas (next section). Sea level is inside each grid as its 0 m
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

### 3D terrain when zoomed in

On the globe, closer than about a third of the default height, the series stands up in
3D. The vertex shader reads the height from the same field textures as the fragment
shader, through the same travel field and blend (the shared `TRAVEL_GLSL` and
`METRES_GLSL`), and lifts each vertex by the height above the displayed sea level, so a
moving continent carries its mountains and a lowered sea raises the shelf it uncovers.
The sea stays flat at its level. Real proportions would leave Everest at 0.14% of the
radius, invisible, so heights are exaggerated 25 times (`RELIEF_SCALE`; 10 left the
Tibetan plateau and the Andes barely above the horizon), and the inspector's relief note
says so. The camera the controls move always looks at the centre of the sphere, from
where lifted ground cannot be seen, so the drawn view is that camera turned about the
ground beneath it by 50° (`RELIEF_TILT`) by default; the controls never see the tilt. While
the terrain stands, a middle (wheel) drag or a shift drag changes the tilt (up and down, to 80°)
and turns its heading (sideways); `setTilt` keeps both, the stage reports them as
`data-tilt` and `data-heading` in degrees, the gesture hint says so, and reset returns
to the default. On a touch screen two fingers
do the same: moved together up or down for the tilt, twisted for the heading. The gesture
is told from a pinch once the fingers have moved 12 px, if their spread changed less than
half as much as their midpoint moved; the controls are disabled until a finger lifts.

Lift and tilt fade in together from a zoom factor of 0.3 to 0.12, and the sphere is
512 × 256 segments only while they are on. Flat sheets, the mask surface, the atlas
prelude without heights and mapless stops stay flat. The toolbar's 3D terrain button
switches it off; `data-relief` on the stage reports the strength from 0 to 1. The plate
boundaries, the fossil coastlines and the graticule are drawn with a line material that
applies the same lift (`terrainLineMaterial`, sharing the surface's uniform objects), so
they ride the mountains rather than being buried under them; a line recovers its
longitude and latitude from the point itself, the inverse of `onSphere()`. Only the
vertices are lifted, so a long straight segment can still cut through a ridge between
them.

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

That datum is the authors' own, by construction. The documentation in the archive
(`Scotese_Wright2018_PALEOMAP_PaleoDEMs.pdf`) describes editing the rotated modern
heights cell by cell until the model matches the paleoenvironmental evidence, and calls
the map coloured from the finished grid "the best guess or average paleogeography for
the time interval"; highstand and lowstand variants are made from the same grid "by
digitally flooding the topography" or lowering sea level, and the authors found the
Haq and Schutter (2009) sea levels reduced by 30 to 40% the best match to the extent of
ancient shallow seas. So no offset in the viewer recovers a published curve's value:
the grid already contains whatever level its authors judged right, and where they drew
land high a fixed offset moves little. The Sunda Shelf at 20 Ma is the example: the
long-term curve reads +109 m there, but the grid holds the block at a median 360 m, so
even +120 m leaves it dry. The grids' vertical resolution is 40 m, a 256-level
greyscale over ±10,000 m, which is why the lowest land cells sit at exactly 40 m.

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

A slider in the inspector moves sea level, −150 to +150 m in 10 m steps, with its value
in the label. It is a what-if and the note says so. The offset shifts the height channel
by that much and cuts the coast from the height instead of the distance field,
antialiased over the height's own screen-space change; the hypsometric colours follow
the new level, live as the slider moves, since the cut happens in the shader. A box
beside it adds the published curve's departure from the datum the bracketing grids
already carry, `curve(age) − mix(sea_m_from, sea_m_to, blend)`, zero at a grid stop,
because adding the curve itself would count the slice's own sea level twice.

The ice layer follows the same offset, so ice growth and sea-level fall read as one
thing. Each ice mask's red channel is a signed distance to the drawn edge, 128 at the
edge and 8 levels per degree, and the shader cuts it at `0.5 + rate × offset` instead of
at the edge; a lower sea moves the cut outward, a higher one inward, and a mask missing
on one side of a gap mixes toward zero, so a sheet recedes from its edge across that gap
rather than fading. Where to cut is decided on the page from two things the builder
writes in `ice-sources.json` and the frame carries as `ice_sheet`: the paper's land-ice
volume at that age, and the share of the globe inside each level of the field. A metre
of sea level is 0.4 million km³ of land ice, the paper's ratio; a sheet's area goes as
its volume to the 0.8; the page cuts at the level whose enclosed area matches, so the
ice is gone once the offset has melted the stop's whole volume, +59 m today and +73 m
at 300 Ma, and grows by the same law below. That growth is even, from the drawn edge,
and real sheets grow from centres, so the present, the one stop with a dated
deglaciation, carries it as lowstand slices: one field per thousand years from 1 to 25
ka, `<id>-ice-low-<ka>.png`, served at `/globe/ice-low/<id>/<ka>.png`; the frame
carries those that lower the sea as `ice_lows`, youngest first, each with the sea level
of its age. The margins are the
optimal North American isochrones of NADI-1 (Dalton et al. 2023, CC BY 4.0) and the
most-credible Eurasian time slices of DATED-1 (Hughes et al. 2016, CC BY 3.0), both
pinned in `sources/ice.json`, laid over today's ice, so Antarctica, Greenland, Iceland
and the mountain glaciers keep their present extent; DATED-1 ends at 10 ka, after which
Eurasia is ice-free. A slice's level is the Spratt & Lisiecki stack at its age, taken as
the running minimum back from the present so the levels fall with age. A slice that
lowers nothing further, 1–5, 20 and 25 ka, is written with `lowers: false` and left out
of `ice_lows`, since a level that holds has no single age to mix toward; the time window
below still steps through it. 24 ka is the deepest at −130 m, the anchor's glacial
maximum. The page finds the two slices bracketing the
offset, the frame's own field standing at 0 m, and mixes their distance fields; the
intervals are a thousand years, so the linear mix stays close, and the Laurentide
retreats toward Hudson Bay and parts from the Cordilleran as the sea rises, as the
isochrones say. Below the deepest slice the area law takes over. The slider marks both
ends of the ice at a stop, no ice at the melted volume and the glacial maximum where one
is anchored; the readout adds the ice the offset stands for, never more melt than the
stop holds.

The slider's range is the ice a stop has, not a fixed ±150 m. Its ice-free end is exact
everywhere, the stop's whole volume melted, +60 m today and +100 m at 445 Ma. Its
glacial-maximum end comes from `sources/ice-anchors.json`, an operator-curated table of
the icehouses' glacio-eustatic swings with their citations: 130 m at the Last Glacial
Maximum, about 50 m across the Eocene–Oligocene and middle Miocene transitions, more
than 100 m at the late Palaeozoic apex and tens of metres at its start and end, 70 m or
more in the Hirnantian. A grid inside an interval gets the full swing where it sits at
an interglacial, the present, and half the swing elsewhere, since the PaleoDEM authors
call each grid the average paleogeography of its interval; a grid outside every
interval has no maximum end beyond the drawn ice, and a stop with no ice has no range
and the slider rests. The builder writes both ends beside the masks as `range_m`, the
page sets them on the slider at every stop and holds the applied offset inside them.
`data-ice-cut` and `data-ice-low`, the age in thousands of years of the slice shown, on
the stage carry the state for tests. The atlas prelude has no
heights and takes no offset. With the default 8-bit textures the height is in 59 m steps, so a
fixed offset moves the coast in those steps; build with `--bits 12` for 3.7 m.

### Time window: the last 25,000 years

The sea-level slider is a what-if: it does not say when. `?window=deglacial`, the "time
range" choice beside the timeline, replaces the elevation series' stops with the last
deglaciation, one stop per thousand years from 25 ka to the present (plan jikhanjung P01).
Every frame is the 0 Ma grid, so the terrain is today's and nothing is interpolated between
grids; the server sends it once per slice as `deglacial` `{age_ka, level_m, url}`, with no
`ice_sheet` and no `ice_lows`, and no deep stops. The page binds the slice as the frame's
lowstand (the present's own mask keeps the shelves and stands alone at 0 ka), applies the
slice's level as the offset, and locks the slider and the curve box to it; the sea strip
draws the held levels on a lowstand scale and the temperature strip is left out, as a
5 Myr curve has one value here. The ice is a published reconstruction at every stop, the
level the stack's running minimum, and the crust is not depressed under the ice, which
the note says. `data-ice-age` on the stage is the age shown. The window is only offered
where the slices have been built, and any other value, or another series, gets the whole
timeline.

`?window=lastcycle` reaches 130 ka instead, one glacial cycle (plan jikhanjung P02): the
end of the previous glacial, the last interglacial, the growth to the maximum and the
retreat, 131 stops. Up to 25 ka the frames are the dated slices as above (`ice_kind`
`dated`). Older, no open reconstruction exists, so a frame keeps the present's `ice_sheet`
and `ice_lows` and carries the stack's own level for its age, not the running minimum, as
the cycle rises and falls; the page takes the what-if path at that level, which mixes the
two slices of the retreat that bracket it (`ice_kind` `analogue`, `data-ice-kind`
`analogue`, "assumed ice" in the caption, and a note). That borrows the retreat's shape at
the same sea level and ignores that sheets grow and melt in different shapes. The stack is
a principal component of many records and peaks at +0.4 m at 121 ka, not the last
interglacial's +6 to 9 m, which the note says too. So that a hundred metres of sea level
moves the coast visibly, the present grid's texture is 12-bit whatever `--bits` says
(`build_paleodem.py`, 3.7 m steps, about 1.2 MB more); the other grids stay 8-bit.

## Ice

`scripts/build_ice.py` writes one ice mask per grid of the elevation series onto the
grid's 2048 × 1024 texture, `<id>-ice.png` in `PALEODEM_DERIVED_DIR`: red is grounded
ice, green a floating shelf, 255 inside and 0 outside, longitude and latitude linear to
the pixels. `/globe/ice/<id>.png` serves it and a frame carries `ice` only where a mask
exists.

The present day comes from Natural Earth's 10 m glaciated areas and Antarctic ice
shelves, public domain; polygon parts are filled one by one. Every older grid
takes the ice the 2016 PaleoAtlas paints on the map nearest its age, within 5 Myr and
the younger map on a tie, as the names and motions are borrowed. `segment_paleoatlas.ice`
reads it with the same pale threshold and overprint refill as the land masks, then keeps
only the pale pieces whose centroid lies poleward of 45°. The atlas's own legend has no
ice; white is "the highest peaks in the mountains", so Tibet, the Altiplano and the
Central Pangean Mountains come out pale too, and every drawn sheet sits poleward of that
line while every plateau sits inside it. The continental polygons are not used: the
atlas draws one white for sheet, shelf and sea ice alike, and where a polygon happens to
end says nothing about which is which, so all of it goes in the red channel and the sea
ice the atlas paints, the Arctic at 4 Ma, stays, and a piece under 0.01% of the sphere is a
speck at the map's polar edge and is dropped. 46 of the 109 grids get a mask, 14 of
them from a map up to 5 Myr away. A grid whose map paints no ice gets no file, so the
overlay fades out across that gap, which there means retreat rather than missing data. The atlas
prelude older than 540 Ma gets none, and no map draws a mountain glacier, so those
appear only at the present. Before the mask is written its edge is smoothed by half a
degree, and wider along longitude toward the poles, up to 8° at the pole: the atlas's
white is read from one-degree cells whose staircase shows at close zoom, and every
column of the texture becomes a wedge at the pole, where a hard edge turned into spokes
when the globe was viewed from above Antarctica. Every mask then has its enclosed gaps
below 500,000 km² filled, one rule for all three sources. The atlas draws hachures,
grey mountains and blue basins inside its white sheets, and the opening that cleans the
pale pieces turned the hachured white into holes, 660,000 km² of them in Antarctica at
20 Ma and 580,000 km² in the Gondwana sheet at 300 Ma, about 4% of the ice; Natural
Earth leaves nunataks and slivers between neighbouring polygons, 57,000 km². No drawn
sheet holds a real ice-free enclave near that size, and Hudson Bay, 1.2 million km²,
stays open if a reconstruction leaves it so. The relief ramp used to run to white above
4000 m as well; its top is now a grey, so white on the globe means ice.

The shader draws grounded ice near-opaque white and shelves paler over whatever
surface is showing, in relief, mask and temperature modes, sampled through the same
motion field as the surface so a sheet rides its continent between stops; a 빙하
toggle hides it. One third of the present grounded ice lies where the PaleoDEM reads
ocean, because the West Antarctic ice sheet rests on bedrock below sea level and the
grid holds the bed; so the overlay ignores what is beneath, and the note says why.

Where the atlas paints nothing but the land-ice volume of van der Meer et al. (2022) is
at least 5 million km³, the cut the sea-level strip already shades, the grid gets a cap
instead: everything poleward of the same paper's ice latitude for that age, in both
hemispheres, the edge eased over 2°. So the strip and the globe agree at every stop:
no shading means no ice, shading means the atlas's sheet or the paper's cap. The cap is
a modelled limit, not an outline, and the page says so: `ice-sources.json` beside the
masks records for every grid whether its mask is `natural-earth`, `atlas` or `limit`,
the frame carries that as `ice_kind`, `data-ice-kind` on the stage reads `drawn` or
`limit`, and a second note appears for a limit. The Early Cretaceous is the clearest
case, 145 to 135 Ma: the paper has 5 to 10 million km³ of ice and the deposit
compilation has high-latitude dropstone localities, while the atlas draws nothing.

The masks are per map, 5 to 10 Myr apart, so they cannot show glacial cycles; the
sea-level strip shades the spans where the land-ice estimate says such cycles existed.
As a check, the glacial deposits Cao et al. (2018) compiled, 394 tillite and diamictite
localities since the Devonian, CC BY 4.0 and pinned in `sources/ice.json`, ride the
PALEOMAP plate under them to each map's age and are counted inside the mask, within 5°
of its edge, inside a pale piece the latitude rule dropped, or farther; `ice-check.json`
beside the masks holds the counts and lists the far ones. At the Late Palaeozoic peak,
330 to 290 Ma, 154 of 197 localities are inside or within 5° of the drawn sheets, and
the two inside a dropped piece sit at the palaeo-equator in the Central Pangean
Mountains, the debated tropical upland glaciation the rule leaves out. The atlas draws
less than the deposits say at the ice age's start and end, 380 to 340 Ma and 280 to
255 Ma, where it paints a small polar cap and the localities sit at 55 to 70°, and it
draws nothing for the Early Cretaceous dropstone localities or the Miocene mountain and
tidewater glaciers of Alaska, Iceland and Kamchatka. The compilation has nothing before
the Devonian, so the Ordovician sheets go unchecked.

The ice the rivers of the glacial stops run off is not this layer's: it is PaleoMIST 1.0
(see Rivers, "Over the ice"), a reconstruction with thickness and a depressed crust,
which the ice layer does not draw; it keeps NADI-1 and DATED-1 to 25 ka and the
same-sea-level analogue beyond. PaleoMIST could replace the analogue at 26–80 ka with
reconstructed margins and supply the crustal depression the 130 ka window lacks; that
proposal, and the caveat that PaleoMIST's own sea level at 26–80 ka sits well above the
stack's (a minimal MIS 3 reconstruction), is on issue #30.

Tibet and the Himalaya carry no sheet at any stop, and that is what the evidence says.
The atlas paints the plateau white as high ground, which the 45° rule drops, and at the
last glacial maximum no reconstruction puts an ice sheet there: the plateau-wide sheet
once proposed by Kuhle was rejected by field mapping and cosmogenic exposure dating
(Owen & Dortch 2014, Quaternary Science Reviews 88, 14–54; Heyman 2014, Quaternary
Science Reviews 91, 30–41), which find valley glaciers and small ice caps advancing
kilometres to a few tens of kilometres beyond their present fronts, the dry plateau
interior ice-free, and in the monsoon-fed ranges the largest advances before the global
maximum, in marine isotope stage 3, when the monsoon was stronger. So the sea-level
control leaves the present mountain glaciers of High Asia, the Andes and Alaska as they
are, and the Miocene and Eocene icehouses show none there, since no reconstruction of
their extent exists and the atlas white is high ground.

## Rivers

**Resolution:** the published 0.1° (6-minute) grids are resampled to a 2048×1024
calculation grid (0.176°, about 20 km at the equator). Grid spacing describes sampling,
not how accurately ancient terrain is known. Individual valleys, narrow outlets and
watershed divides are not independently resolved by drawing a finer texture. The lines
are potential drainage under the stated assumptions; a present-day river comparison
does not validate ancient river courses. The underlying 1° grid fallback is coarser still.

The field spreads across the longitude seam but never wraps from the north edge to the
south edge. Rebuild river textures made before this boundary fix before a release.


`scripts/build_rivers.py` routes water over every grid of the elevation series and writes
`<id>-rivers.png` beside the fields, 2048 × 1024, RGB: red the river field, green the
lakes (below), blue 0. `/globe/rivers/<id>.png`
serves it and a frame carries `rivers` only where the file exists; the `#rivers` toggle
hides the lines without unloading the fields, `#river-note` says what they are, and
`data-rivers` on the stage says whether any are drawn.

What it draws is potential drainage, not a reconstruction. The Paleo-Physiography Project of
Salles, Husson, Lorcery & Boggiani (HydroShare; goSPL run on these same grids with the
Valdes et al. 2021 rain), is CC BY-NC-SA 4.0 for three of its four time ranges, so it is
a comparison, not a source (issue #30). The builder resamples the 6-minute grid to the
texture, takes land as z > 0, fills every pit to the level at which it spills (grayscale
reconstruction on the grid tiled three times in longitude, so a basin across the
antimeridian fills as one), sends each land cell's water to the steepest of its eight
neighbours over true distances, resolves a level lake in waves from its outlet inward,
and sums the drained area in km² from the highest cell down. Rain is even and
evaporation nil, so the number is drained area, not discharge. Every basin spills: the
grids are too smooth to tell a basin closed by a gorge narrower than a cell (the Congo
below Kinshasa, the Sichuan basin above the Three Gorges, the Pannonian plain above the
Iron Gates) from one closed for real (Chad, Tarim, Eyre); a depth cap of 50, 100 or
200 m stopped 30–50 % of all land from draining, so none is applied, as Salles et al.
also assumed. Present-day check: the Amazon drains 5.65 Mkm² (published 6.3–7.0) with
its mouth at 0.6° S, 51.6° W, and the Congo, Nile, Niger, Mississippi, Mackenzie, Ob,
Yenisei, Lena, Amur, Yangtze, Ganges and Murray come out where they are.

The texture is a field the shader cuts, not a picture: at each texel the largest, over
the river cells within 4 texels, of that cell's size less 0.35 per texel of distance,
where size is log10 of the drained area over 10³–10⁷ km² scaled to 0..1, and a cell
drains at least 1,000 km² to count. The page draws where the field passes 0.25
(10,000 km²), so a line's width follows its size (two texels either side for the
largest), its edge is antialiased over `fwidth`, and the two grids' fields mix through
the travel offsets as the coastline's distance does, a plausible in-between rather than
a cross-fade of pictures; a missing side weighs nothing, so the network fades across
that gap. Rivers draw on the mask, relief and temperature surfaces, under the ice, and
only over land after the sea-level cut. A raised sea covers them. A lowered one needs
rivers on the exposed shelf, which the field routed at 0 m cannot hold, so every grid
whose slider reaches below its datum (the bottom of the ice sidecar's `range_m`, 31
grids: the present at −130 m, the icehouse stops at −20 to −50 m) is routed a second
time with the sea at that level, land being everything above it, and written as
`<id>-rivers-low.png` (`scripts/build_rivers.py --lows` writes only these). The frame
carries `rivers_low` with the file's URL and level; the shader mixes each side's own
field toward its lowstand field by the offset's share of that level (`data-river-low`
on the stage, 0 at the datum, 1 at the bottom), so a shelf river fades in as the shelf
emerges while its land part, which both fields share, stays put. The time windows set
the level per stop and get the same. A channel that truly shifts as the coast retreats
only cross-fades.

**Over the ice.** The present grid is routed a third way, over the ice of the last
glacial cycle, so that the glacial stops have meltwater along the ice margins and lakes
dammed by ice rather than today's rivers running under a white overlay. The ice is
PaleoMIST 1.0 (Gowan et al. 2021, Nature Communications 12, 1199; PANGAEA
10.1594/PANGAEA.905800, CC BY 4.0, pinned in `sources/paleomist.json`): grounded ice
thickness, the crust's glacial isostatic deformation from SELEN and the resulting
paleo-topography, 80 ka to the present every 2,500 years, as global 0.25° and 1° NetCDF
grids. Only the two global grids are extracted from the 3.5 GB archive (`members` in
the manifest) and the archive is deleted afterwards (`discard`); `fetch_paleodem.py
--manifest sources/paleomist.json` then verifies every extracted file against a SHA-256/size receipt tied to the verified archive. Existing folders without that receipt require the archive again.
`scripts/build_rivers.py --ice` writes `paleodem-0000-rivers-ice-<years>.png` for
each step to 25 ka (`--ice-to 80` for all of them) and a sidecar
`paleodem-0000-rivers-ice.json` with each step's age, sea level and whether it lowers
the sea below every younger step's.

The routing surface is the 0 Ma grid with today's ice taken off where the grid holds it
(the grid carries Greenland's ice surface but Antarctica's bed, so as much of the
present thickness as the grid stands above the present bed is removed), the crust
pressed down by the step's deformation (the `sea_level` field less its mean over
today's ocean, so the eustatic part, which the page's own level supplies, is left out),
and the step's grounded ice laid on top. The sea is at the level the page gives that
age: the ice sidecar's held level to 25 ka, the stack beyond, a half step the mean of
its neighbours. Three surfaces were compared at 12.5, 10 and 20 ka: PaleoMIST's own
paleo-topography (0.25°, blockier, its own sea level, and RTopo-2 puts the Great Lakes'
floors below the sea, so the St Lawrence ended in Lake Michigan); the grid plus the
thickness alone; and the grid plus thickness and deformation, which was kept, because
the depression at the margins is what makes the proglacial lakes and the Champlain Sea.
A depression the deformation opens inland without reaching the ocean (the Great Slave
lowland at 12.5 ka, the southern North Sea between the joined British and Scandinavian
sheets at 20 ka) is land, a lake that fills to its spill, while a basin the grid itself holds below the
datum stays sea as in every other field; that rule is what sends the Elbe and Weser
west through the Dover Strait. The Caspian is not such a basin: the grid holds its
surface at exactly 0 m, not its floor, so below the datum the page shows it as land
and the routing crosses it, on every field alike. Water is routed over the
ice as terrain, so a sheet's whole surface drains to its margin, but only cells off the
ice are drawn. Checks: at 20 ka the Channel River drains 2.65 Mkm² through the Strait
(the literature figure is about 2.5 Mkm², the Rhine, Thames, Meuse, Seine and the
ice-marginal valleys of the Elbe and Weser); Lake Agassiz spills east into the
Champlain Sea at 12.5 ka and south to the Mississippi at 10 ka. The 20 km grid cannot
resolve the real sills, so the outlets are plausible, not dated, and the ice the rivers
run off is PaleoMIST's, whose margins differ by up to a few hundred kilometres from the
NADI-1 and DATED-1 margins the ice layer draws; where the drawn ice is wider it covers
the rivers, where narrower a strip goes without.

The frame carries `rivers_ice`, youngest first, only the steps that lower the sea below
every younger step's and only where the file exists, each with its level and URL
(`/globe/rivers-ice/<id>/<years>.png`). `riverChoice` in the page picks, for a frame with
slices and a lowered sea, the two bracketing the offset, the frame's own field standing
at 0 m and the deepest holding below it, and mixes them by the offset's share of the
gap through the same `riverLow0/1` and `riverLowT` uniforms the shelf fields use, so
the shader is unchanged; `data-river-low` is that share and `data-river-ice` the
interpolated age of the ice. The time windows inherit the list with the present frame,
and their stops set the offset to the age's level, so a dated stop shows the step at its
level (20 ka shows the 20 ka field) and an older stop of the 130 ka window the step at
the same sea level, the analogue the ice layer already draws there. Grids without
slices keep the 0 m and lowstand fields.

**Lakes.** Filling the pits is the first step of the routing, and the fill is where
water pools before it spills. The ice slices carry it in their green channel as the
pooling the ice adds: the slice's pooled depth (filled surface less the routing
surface, ice and deformation included) for each pool the bare grid does not hold at
the same sea level (`ice_lakes`: a pool is dropped whole when the bare grid pools over
half of its ground or more, since subtracting depths would leave the deformation's tilt
across a closed basin as a lake), in metres on a square-root scale that saturates at
250 m (`LAKE_M`), so that 2.5 m is already 0.1, a shallow pool shows and Agassiz
saturates; only cells off the ice carry it. The shader paints a lake
where the mixed green passes 0.1 (`LAKE_CUT`, 2.5 m), over land after the sea-level
cut, under the river line and the ice, and the two fields' greens mix like their reds
through the same lowstand and ice-slice weights, so a lake dammed by ice fills and
drains between steps as the slider moves. The plain and lowstand fields carry a zero
green channel. Their pits are the grid's own closures, and painting them showed the
every-basin-spills assumption as lakes the size of countries: not only Chad, Tarim
and Eyre but the Congo cuvette, Sichuan and the Pannonian plain, whose gorge outlets
the grid closes; subtracting the bare grid's pooling from the ice slices is what keeps
Tarim, the Congo or the Pannonian plain from appearing as a lake at −60 m and
vanishing at 0 m. Every field is RGB
because a one-channel PNG decodes grey in all three channels and its rivers would read
as lakes, so fields built before this change must be rebuilt (or their green zeroed).

`tests/rivers_check.py` covers the routing: every drop of an island with a pit reaches
the sea, an island across the antimeridian drains as one, a lowered sea routes over the
exposed shelf, the field is a cone the size of its river, a depression pressed open
inland is a lake and not the sea, the ice surface strips today's ice only where the
grid holds it, and the lake channel is the pooled depth on its square-root scale, RGB,
nothing under the ice or at sea.

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

- `SCOTESE_VIEWER_STEPS` divides each source-map gap into 1, 2, 4, 8, 16 or 32
  sub-steps, defaulting to 4. Within source coverage, N maps produce
  `(N - 1) * steps + 1` stops: 357 for the default 90-map atlas, 65 for the
  17-map comparison series, and 445 for the 112-frame elevation series at 4 steps.
  Equal sub-step counts do not mean equal durations across gaps.
- `SCOTESE_VIEWER_INTERVAL_MA` uses 0.5, 1, 2, 5, 10 or 25 million years between
  regular stops, also retaining every source age. Counts therefore depend on the
  selected series and on source ages that fall between regular stops. A 10,000-year
  (0.01 Ma) viewer interval is not currently supported.

The interval wins when both are set. `?steps=` and `?interval=` override the setting
per request through the same allowlists. Within each gap the blend is linear in age.
Older, model-only stops may extend the timeline beyond the oldest source map; the
counts above exclude that extension. More display stops do not add source information
or establish the accuracy of the intervening reconstruction.

Intermediate stops reuse source textures rather than generating a texture per tick.
The main texture cache is an LRU cache capped at 12 entries (`TEXTURE_CACHE` in
`static/core/globe.js`); it is not an always-resident set of 17 maps. Climate and other
layers also have resources, so this cap is not a bound on all viewer memory.

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
The main texture loader caches promises by frame and texture kind, with LRU eviction
and disposal at 12 entries. A monotonically increasing request ID
ensures stale asynchronous loads cannot replace the latest selected era. Failures are
retryable. Playback pauses on manual selection or when the page becomes hidden.

`SCOTESE_VIEWER_ENABLED` controls the viewer. Production settings default it off, while
the deployed environment enables it. Original 2002 JPEGs have a separate gate,
`SCOTESE_SOURCE_MAPS_PUBLIC`, which defaults off in production and stays off in the
operating deployment. Enabling the viewer alone does not expose originals: it displays
derived fields, while `/globe/maps/<id>.jpg` returns 404 and original-map UI is hidden.
Original assets are omitted from both the container image and the runtime data bundle.
Where both flags and local files permit originals, only the 17 allowlisted 2002 JPEGs
are served; arbitrary files, HTML snapshots and DB files remain inaccessible.
Neither flag grants data-use rights. See `sources/README.md`, `LICENSE-DATA.md` and
`deploy/README.md` for source terms and deployment boundaries.

## Verification

- `make check`, `make test`: catalogue, age exceptions, allowlisting, disabled and
  missing-data behavior, plus the existing site tests.
- `npm test`: projection and rotation tests (`tests/projection.test.mjs` and
  `tests/rotation.test.mjs`).
- `npm run test:browser` with the development server running: the 2002 comparison
  frames, default 2016 atlas, dataset selection, interpolation and deep time, plate and
  coastline overlays, languages, projections, navigation, mobile layouts and failed-load
  recovery. Elevation, climate, sea-level and terrain checks run when the elevation
  series is built; the script reports that section as skipped otherwise. Screenshots
  go to gitignored `data/screenshots/`.
- `VIEWER_URL=http://127.0.0.1:8153/ node tests/river-browser.mjs`: river PNG, shader,
  toggle, grid-spacing explanation, mobile layout and both languages (requires a built 0 Ma river field).
- `VIEWER_URL=http://127.0.0.1:8153/ node tests/firefox-browser.mjs`: the globe in desktop
  Firefox through WebDriver BiDi, no Playwright browser needed: the globe reaches a frame
  with rivers on, the sea at −60 m brackets the ice-river slices when they are built, the
  deglacial window at 20 ka shows `data-river-ice` 20.0 and `data-ice-age` 20, and no
  console error or failed request. `FIREFOX_BIN` names the binary (default the macOS
  app; on Linux the `firefox` on the path); it runs headless with a throwaway profile where WebGL2 is available,
  and only its own process is killed afterwards. See the Linux fallback below. Screenshots go to
  gitignored `test-results/`.
- `.venv/bin/python tests/rivers_check.py` with `requirements-processing.txt`
  installed: the river routing (see Rivers), the ice surface included.
- `.venv/bin/python tests/segmentation_check.py` with `requirements-processing.txt`
  installed: the inverse projection against the viewer's forward mapping, the inset
  ellipse mask and the colour conversion. Kept out of the Django suite because the web
  app does not depend on those packages.
- Processing checks also include `tests/paleoatlas_check.py` (segmentation and motion),
  `tests/rotation_check.py` (rotation math) and `tests/ice_check.py` (ice-mask helpers).
  Run each with `.venv/bin/python` and `requirements-processing.txt` installed; these
  are separate from the Django suite. A passing web test alone does not validate the
  scientific accuracy of the source reconstructions or interpolated surfaces.

Firefox defaults to the macOS application on macOS and `firefox` on PATH elsewhere;
`FIREFOX_BIN` overrides it. If Linux headless WebGL2 is unavailable, use a display
(or `xvfb-run -a`) with `FIREFOX_HEADLESS=0`; software rendering can use
`LIBGL_ALWAYS_SOFTWARE=1`. Startup is bounded to 30 seconds, BiDi commands to 10 seconds.
Failures print collected browser errors and clean up the process/profile started by the test.
