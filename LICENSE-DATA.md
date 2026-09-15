# Data licence

The code of EarthThruTime3D is under the MIT licence (`LICENSE`). The data is not
code, and its terms follow the sources it was made from. Three groups.

## Derived data this project publishes: CC BY 4.0

The files this project computes from CC BY sources are released under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/):

- the elevation, temperature and ice textures, the sea-level curves and the motion
  fields of the elevation series (from Scotese & Wright 2018, Scotese 2021, van der
  Meer et al. 2022, Spratt & Lisiecki 2016, Natural Earth, and the PALEOMAP
  rotation model);
- the packed coastlines (from Kocsis & Scotese 2021);
- the experimental mantle surface meshes (from Müller et al. 2022 OPT1 supplementary
  data v3.0; see `docs/geodynamics.md` for attribution and transformations);
- the India–Asia section bundle (OPT1 surface intersections, craton outlines and
  plate boundaries, plus resampled Scotese & Wright 2018 PaleoDEM regional terrain;
  see `docs/india-asia-section.md`);
- the packed plate polygons and rotations (from Merdith et al. 2021, Müller et al.
  2022, Cao et al. 2024, Matthews et al. 2016 and Scotese 2016);
- the catalogues and annotations under `sources/` and `annotations/`.

Attribution: "EarthThruTime3D (PaleoBytes), derived from …" naming the source
dataset, whose own citation appears in `sources/README.md` and on the About page.
Each source's CC BY licence still applies to what was derived from it; the
citations there are the attribution those licences require.

## Derived data whose source terms are not settled

- The land masks segmented from the **PALEOMAP PaleoAtlas (2016)** rasters: the
  Zenodo record lists CC BY 4.0, but this project has not confirmed who attached that
  licence, so the masks are published under the record's terms as they stand and no
  further licence is asserted here.
- The land masks segmented from the **2002 PALEOMAP web maps**: the PALEOMAP terms
  allow personal, educational and research use with attribution and treat Internet
  publication as needing the author's consent. The masks are this project's
  measurements, published with attribution; the original images are not distributed.
- The **Torsvik & Cocks 2017** plate model carries no licence and is not published.

## Source datasets

The archives under `data/sources/` are not part of this repository. Each is pinned
in a manifest under `sources/` that records its licence and citation; the terms are
the publishers'.
