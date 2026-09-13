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

## PaleoDEM catalogue

`paleodem.json` pins the PALEOMAP PaleoDEMs (Scotese & Wright 2018, Zenodo record
5460860, CC BY 4.0): 109 elevation/bathymetry grids, 0–540 Ma at 5 Myr, as 1° NetCDF and
CSV, the 6-minute NetCDF set (207 MB) for the sharper texture build, plus the
documentation PDF. Fetch or verify with `.venv/bin/python scripts/fetch_paleodem.py`
(`--verify-only` for offline); building textures needs `requirements-processing.txt`. Archives unzip into `data/sources/paleodem/{nc,csv}/`
(gitignored); GPlates cache files are not extracted. Unlike the web JPEGs, these grids
may be redistributed with attribution.
