# Reconstruction direction

## Scope and phases

1. Surface reconstruction: register paleogeographic source maps, georeference them,
   and render dated surface reconstructions on a globe with a time selector.
2. Kinematic interpolation: preserve plate identities between dated keyframes and
   evaluate intermediate geometry on demand.
3. Deformation: add explicit regional deformation models, starting with the
   India–Eurasia collision and Himalayan uplift as a candidate case study.
4. Mantle coupling: add a separately validated solver and boundary conditions.

Phase 1 is implemented and deployed, and phase 2 is approximated. The viewer shows land
masks segmented from the 90 maps of the 2016 PALEOMAP PaleoAtlas (default, 750 Ma to
present), the 17 Scotese web maps of 2002 for comparison, and the PaleoDEM elevation
grids with temperature, sea-level and ice layers. Between maps, pieces travel with the
PALEOMAP rotation of the plate beneath them while their shapes blend; plate polygons
from several rotation models and PaleoCoastlines can be overlaid. Every source has a
pinned provenance manifest in `sources/`. No deformation model or solver has been
implemented. See `globe-viewer.md`.

## Proposed boundaries

Django will manage source metadata, reconstruction scenarios, parameters and artifact
references. A browser globe will consume prepared geometry. Numerical reconstruction
code should remain independent of HTTP and ORM code; expensive simulation jobs should
eventually run outside request handlers. Introduce domain apps and persistence models
when the first dataset makes their fields concrete.

## Time convention

Use integer years before the present-day reconstruction reference (0 = present).
Display Ma as years / 1,000,000. A forward evolution step subtracts 10,000 years;
10,000 years is 0.01 Ma. Record the exact temporal reference per dataset.
Keep source keyframe spacing, viewer tick and numerical solver timestep separate.
Do not pre-create one database row per tick. Evaluate or cache geometry on demand.

## Scientific provenance

Planned source records include author, original URL, permission/license, map projection,
age, spatial reference, checksum and processing history. Preserve source assets and
operator annotations independently of derived, regenerable outputs.

Treat interpolation as a visualization hypothesis. A fine tick does not establish
fine temporal accuracy. Separate rigid plate rotations from intraplate deformation,
and distinguish paleogeographic coastlines from tectonic plate boundaries. Maps alone
do not uniquely determine 3D displacement, crustal thickness or topography; record
additional constraints, assumptions and uncertainty for each reconstruction.

Before implementing a solver, compare candidate representations and constraints
against primary geological datasets and quantitative validation cases. Do not present
a visual crossfade as a physical collision or mantle simulation.
