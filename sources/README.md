# Source catalogues

Two datasets, kept apart on purpose. The Scotese maps are published pictures this
project measures; the EarthByte plate model is a rotation model that reconstructs
geometry. Different authors, different licences, different limits. Anything built from
them has to say which one it came from.

- [Scotese Earth History](#scotese-earth-history-source-catalogue): 17 maps, 650 Ma to
  present, measured into land masks. `scotese-earth-history.json`.
- [EarthByte Merdith et al. 2021](#earthbyte-plate-model): a 1 Ga rotation model with
  plate polygons. `earthbyte-merdith2021.json`.

# EarthByte plate model

Merdith et al. (2021), a continuous full-plate motion model from 1 Ga to present,
distributed by the EarthByte Group at the University of Sydney. The archive and the
five files this project uses are pinned in `earthbyte-merdith2021.json` with byte counts
and SHA-256 checksums, and extracted into `data/sources/earthbyte/` (gitignored).

```bash
.venv/bin/python scripts/fetch_earthbyte.py
.venv/bin/python scripts/fetch_earthbyte.py --verify-only
```

What the files are: a rotation file of total reconstruction poles, coastlines and
continent shapes carrying plate IDs, and static polygons saying which plate a present-day
location belongs to. `scripts/rotation_model.py` reads the rotation file and composes a
plate's rotation at any time, interpolating inside a sequence and walking the chain of
fixed plates to the anchor.

Licence: **Creative Commons Attribution 3.0 Unported**, with the citation recorded in the
catalogue. Unlike the PALEOMAP maps, publishing derived work on a website needs no
further consent. The authors state the model sits in a purely palaeomagnetic reference
frame and is unsuitable for Pacific hotspot kinematics or for analyses shorter than 5 Ma.

## Checking the composition

`scripts/rotation_model.py` is this project's own implementation, so it is checked
against the GPlates Web Service, which runs the reference implementation:

```bash
.venv/bin/python scripts/check_rotation_against_gws.py --samples 60   # needs network
.venv/bin/python tests/rotation_check.py                              # offline, synthetic
```

Sixty random plate-and-time reconstructions agreed to within 0.00007 degrees of arc,
about seven metres, which is the precision the service reports. Getting there needed one
correction: 32 of the model's 1184 plates carry overlapping sequences, a narrow window
inserted over a broad one to say that for those years the plate is measured against a
different neighbour. The narrower sequence has to win, or India at 50 Ma lands 2.5
degrees away from where the reference puts it.

# Scotese Earth History source catalogue

The initial dataset contains 17 original JPEG maps from the
[PALEOMAP Earth History index](http://www.scotese.com/earth.htm), by
Christopher R. Scotese. Future projections are excluded from this historical dataset.

Original images and page snapshots live in `data/sources/scotese/` (gitignored).
`scotese-earth-history.json` records URLs, retrieval time, byte counts, SHA-256 checksums,
actual JPEG dimensions, image titles and ages. Every image was visually inspected.
The originals retain their labels, legends and attribution without editing.

## Reproduce or verify

```bash
.venv/bin/python scripts/fetch_scotese.py
.venv/bin/python scripts/fetch_scotese.py --verify-only
```

Requires curl for downloading; verification uses Python's standard library only.
Existing files are verified and left untouched. Changed upstream content fails checksum
verification and requires explicit inspection and a catalogue update. The initial
download used HTTP because both website hostnames had mismatched HTTPS certificates;
the checksums pin downloaded bytes but cannot authenticate the publisher.

## Time slices

| Image title | Ma | Original file |
| --- | ---: | --- |
| Late Proterozoic | 650 | 650.jpg |
| Late Cambrian | 514 | 514.jpg |
| Middle Ordovician | 458 | 458.jpg |
| Middle Silurian | 425 | 425.jpg |
| Early Devonian | 390 | 390.jpg |
| Early Carboniferous | **356** | **342.jpg** |
| Late Carboniferous | 306 | 306.jpg |
| Late Permian | 255 | 255.jpg |
| Early Triassic | 237 | 237.jpg |
| Early Jurassic | 195 | 195.jpg |
| Late Jurassic | 152 | 152.jpg |
| Late Cretaceous | 94 | 094.jpg |
| K/T Boundary | 66 | 066.jpg |
| Middle Eocene | **50.2** | **050.jpg** |
| Middle Miocene | **14** | 014.jpg |
| Last Glacial Maximum | 0.018 | LGM.jpg |
| Modern World | 0 | 000.jpg |

Ages follow the image titles, not the filenames. The Miocene page's prose mentions
20 million years, but its image says 14 Ma. Source terminology and the 18,000-year LGM
label are preserved as historical source metadata, not updated scientific assertions.

These are 720-pixel-wide annotated maps, not georeferenced raster textures, elevation
grids, plate polygons or rotation models. Projection/central meridian are unverified.
Before mapping to a globe, establish the projection and control points and separate
map content from labels/legends. The 17 keyframes alone do not constrain 10,000-year
physical deformation or unique crustal motions.

## Attribution and use

The site's [license information](http://www.scotese.com/license.htm) permits credited
personal, teaching, research and scientific-publication uses, while reserving commercial
uses for written consent. It also discusses Internet websites among restricted uses.
This catalogue is for local research; no public redistribution permission is assumed.
Original images and page snapshots are not committed. The local development viewer
serves only the 17 allowlisted JPEGs; page snapshots remain inaccessible. The viewer
and image route default off in production (`SCOTESE_VIEWER_ENABLED=false`).

Attribution: C. R. Scotese, PALEOMAP Project, www.scotese.com.
Reference: Scotese, C. R. (2001), *Atlas of Earth History*, Volume 1, Paleogeography,
PALEOMAP Project, Arlington, Texas, 52 pp. See the license page for citation guidance.
