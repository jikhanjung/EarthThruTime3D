# EarthThruTime3D

[한국어](README.ko.md)

A PaleoBytes research project that reconstructs Earth's history in 3D from palaeogeographic
data. The first goal is the surface through time; crustal motion and deformation and mantle
convection come later.

It is now a **Django 5.2 + Three.js palaeogeographic globe**, running at
https://earththrutime.nopeoplestime.info.

- Default view: land masks segmented from the 90 maps of the PALEOMAP PaleoAtlas (2016),
  750 Ma to the present. Between maps, the pieces travel with the PALEOMAP plate rotation
  while their shapes blend.
- Elevation series (`?masks=paleodem2018`): the 109 PaleoDEM grids (Scotese & Wright 2018)
  with relief shading and 3D terrain, surface temperature (Scotese 2021), sea-level curves
  (van der Meer 2022, Spratt & Lisiecki 2016), ice, and potential rivers computed on the grids.
- Time windows of the last 25,000 and 130,000 years: dated ice slices and modelled vegetation
  and rainfall (Krapp et al. 2021).
- The present day (0 Ma): a NASA Blue Marble satellite base, with wind (NOAA GFS analysis,
  10 m and 250 hPa), surface currents (ECCO2 1992–2018 mean) and clouds (NOAA/NESDIS GMGSI
  or GFS) as moving layers. Not live: wind and clouds are refreshed once a day, and the
  screen states the time of every layer that is on. Crustal thickness (CRUST 2.0).
- Plate-model overlays (Merdith 2021, Müller 2022, Cao 2024, Matthews 2016, PALEOMAP 2016),
  PaleoCoastlines (Kocsis & Scotese 2021), and location pins carried back through time.
- The 2002 web maps (17) kept for comparison (`?masks=scotese2002`).
- Korean and English (KO | EN).

Interpolated views, modelled fields and sea-level what-ifs are not observations or published
reconstructions; the screen and the documents keep source data, interpolation, models and
assumptions apart. What changed in each release and how to see it on screen is in
[CHANGELOG.md](CHANGELOG.md) (in Korean). Report problems in
[GitHub Issues](https://github.com/jikhanjung/EarthThruTime3D/issues).

## Running locally

Python 3.11 or later. `.venv` is this repository's own environment.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p data/db
.venv/bin/python manage.py migrate
.venv/bin/python scripts/compile_messages.py   # build the English .mo
.venv/bin/python manage.py runserver
```

With uv: `uv pip install --python .venv/bin/python -r requirements.txt`. To build data,
install `requirements-processing.txt` as well.

- Home: http://127.0.0.1:8000/
- About `/about/`, privacy `/privacy/`, contact `/contact/`
- Health: `/healthz` (version, database, migrations, required fields; the present-day
  weather's source and age for information)
- Admin: `/admin/` in development only (`createsuperuser` for an account); production
  leaves the route out (`ADMIN_ENABLED`)

```bash
make check
make test
npm ci
npm test
# with the development server running (npx playwright install chromium if needed):
npm run test:browser
```

The other browser checks run as `VIEWER_URL=http://127.0.0.1:8000/ node tests/<name>-browser.mjs`.
`tests/flux-browser.mjs` needs the present-day data (`data/derived/present-earth`); the
older suites expect the elevation colours at 0 Ma, so run them against a server started
with `PRESENT_DERIVED_DIR=/nonexistent`. See [docs/globe-viewer.md](docs/globe-viewer.md)
"Verification".

## Using the globe

Drag to turn, right-drag to pan, middle-click or Shift-drag to tilt, wheel or pinch to zoom.
Projections: globe, Mollweide, Equal Earth and equirectangular; a flat map turns its central
meridian. The timeline has a period menu, a slider, a step choice (so many steps per map, or
one every so many Myr), playback, and older/newer buttons, in a long bar at the foot. The
left panel (folded and unfolded with ☰; a drawer on a phone) holds the dataset, projection
and reset, and the layers: auto-rotate, grid, the surface and climate views, 3D terrain,
ice, rivers, the present-day layers, pins, the sea-level chart and the plate overlays.
Legends dock at the bottom right and fold away. With keyboard focus on the globe, the arrow keys
turn it and `+`/`-` zoom. The view is kept in the address, so a link reopens it.

A separate [mantle model experiment](docs/geodynamics.md) at `/mantle/` shows the published
3D surfaces of Müller 2022 OPT1 by time; no convection of our own is computed. The
**India–Asia A–A′ section** button opens an [80 Ma–present section and 3D surface](docs/india-asia-section.md);
its crustal shortening is a labelled assumption.

Screens, controls and data paths are listed in the [site map](docs/site-map.md) (Korean); the
rendering, interpolation and their limits in the [globe viewer document](docs/globe-viewer.md);
the palaeolongitude problem in [docs/palaeolongitude.md](docs/palaeolongitude.md).

Three.js 0.186.0 and its MIT licence are vendored under `static/vendor/three/`. Running the
site needs neither npm nor a CDN; `npm ci && npm run vendor` updates the vendored files.

## Layout

- `config/settings/`: common, development and production settings. `manage.py` defaults to
  development, WSGI/ASGI to production.
- `core/`, `templates/`, `static/`: pages, the globe viewer, the access-key gate, health checks.
- `locale/`: English translations (`django.po`). `scripts/compile_messages.py` builds the
  `.mo`, which Git ignores.
- `scripts/`: fetching and verifying sources, segmentation, and the derived motion, elevation,
  temperature, sea-level, ice, river, climate and present-day data.
- `sources/`, `annotations/`: source manifests and operator annotations.
- `config/version.py`: the single definition of name, brand, version and release date.
- `deploy/`: image and data-bundle builds and deployment; procedure in
  [deploy/README.md](deploy/README.md) (Korean). `deploy/cron/` holds what the server's cron
  runs (the daily present-day weather), copied out of the image at every container start;
  its Python needs are `requirements-present.txt`.
- `data/`: sources, derived data and the local SQLite, all ignored by Git, as is `media/`.
- [Architecture](docs/architecture.md), [operations](docs/operations.md), and the work log in
  [devlog](devlog/README.md) (Korean).

Production settings come from the environment. `.env.example` is a reference and is not read
automatically. Production needs an explicit secret key, hosts and a persistent database path.
Images are built on the development host; the server verifies the versioned image and data
bundle as a pair and only swaps them. See the
[Django 5.2 deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## Shared guides

`.guides -> ../devdocs/guides` is a relative symlink, ignored by Git. In a new checkout,
with the private devdocs beside it, link it with `ln -s ../devdocs/guides .guides`. Never
copy or commit the guides.

## Data and licences

The [source list](sources/README.md) gives each dataset's origin, age, licence and how it is
verified. Sources are stored locally under `data/sources/`, outside Git, and fetched with
pinned SHA-256 (`scripts/fetch_scotese.py`, `scripts/fetch_paleodem.py --manifest
sources/<name>.json`, …). The original PALEOMAP map images are not distributed until their
terms are confirmed, and are kept out of the image and the data bundle.

The code is [MIT](LICENSE). Data this project derives from CC BY sources is CC BY 4.0; masks
from the PaleoAtlas and the 2002 maps, whose source terms are not settled, follow those
sources; the present-day layers derive from US government and NASA open data. The details are
in [LICENSE-DATA.md](LICENSE-DATA.md).
