# GPlates: what it does, and where this project stands

The GPlates feature overview below is based on its feature page, manual and tutorials,
listed at the end. The EarthThruTime3D comparison was checked against v0.10.3 on
2026-09-15. It distinguishes implemented plate kinematics from approximate surface
interpolation and from deformation capabilities that remain unimplemented.

## The idea that separates GPlates from what we do now

GPlates does not morph pictures. It reconstructs **data** through time using a
**rotation model**.

Every feature carries a plate ID. A rotation file holds, for each plate, a series of
**total reconstruction poles**: a fixed plate ID, a moving plate ID, a time, and a
finite rotation, which Euler's displacement theorem lets us write as an axis and an
angle. To draw the world at some time, GPlates composes the rotations along the plate
circuit down to the anchored plate and applies the result to each feature's present-day
coordinates. When the asked-for time falls between two samples in a sequence, it
interpolates between the two nearest ones.

EarthThruTime3D now also composes finite rotations through plate circuits and draws
reconstructed vector outlines. Its surface pipeline is still different: the default
90-map PaleoAtlas series uses regions whose centroids are carried by PALEOMAP plate
rotations, while the renderer translates their neighbourhoods and blends their shapes.
PaleoDEM borrows atlas regions and motions. The 17-map 2002 comparison series uses
named-landmass matching instead. These intermediate surfaces are approximations, not
rigidly rotated per-plate meshes or a dynamically deforming crust. Even published
source maps are reconstructions rather than direct observations of past geography.

## Functional areas

The referenced capabilities can be grouped by purpose:

**Reconstruction core**
- Total reconstruction sequences: the rotation file, edited as sequences per plate pair.
- Reconstructions: set a time, step frame by frame, animate over a range.
- Pole manipulation: adjust a reconstruction pole interactively and see features move.
- Topology tools: build closed plate boundaries that themselves change with time.
- Crustal deformation: deforming networks, tracking extension and contraction inside a
  plate rather than treating it as rigid.

**Data in and out**
- Load and save features in GPML, shapefile, GMT and others.
- Import rasters and 3D scalar fields, including time-dependent raster sets whose pixels
  change with time.
- Export reconstructed geometry, rasters and velocities as time-sequenced files.
- Cookie-cutting: assign plate IDs to unassigned features by intersecting them with
  static plate polygons.

**Drawing and editing**
- Digitise new points, lines and polygons; edit existing geometry.
- Feature property editing and querying.
- Small circles, as construction aids.

**Derived geometry through time**
- Flowlines: the track a point leaves as two plates spread apart.
- Motion paths: the path a point follows relative to another plate, updated as time
  changes.
- Surface velocities in topological plate polygons and deforming meshes, for feeding
  geodynamic models.
- Kinematics tool and the Hellinger tool, the latter for fitting rotations to magnetic
  anomaly picks.

**Display**
- Globe and several map projections, with vector and raster layers.
- Layer system with per-layer settings and connections between layers.
- 3D scalar field rendering for sub-surface data.

**Automation**
- PyGPlates for scripting the same operations, and GPlately above it.
- Spatiotemporal co-registration for comparing data sets through time.

## Time control, specifically

The reconstruction time sits under the menu bar as a text field, backward and forward
frame buttons, and an animation slider with present day at the right and the deep past
at the left. The step buttons move one frame, bound to Ctrl+I and Ctrl+Shift+I. A
Configure Animation dialog, under the Reconstruction menu, sets the time range, the
increment between frames and the frame rate.

Our viewer supports sub-steps per map or a fixed 0.5, 1, 2, 5, 10 or 25 Ma interval,
retaining source-map ages. Model-only stops extend beyond map coverage where a plate
model is available. There is no arbitrary-time input or 0.01 Ma viewer interval yet.
A finer stop spacing changes display sampling, not the source data's accuracy.

## What we have, against that list

| GPlates capability | EarthThruTime3D v0.10.3 |
| --- | --- |
| Rotation model, plate IDs, plate circuit | Finite-rotation composition and interpolation; multiple model manifests, with access restricted for unpublished sources |
| Continuous reconstruction time | Configurable stop table; rotations evaluated for the selected stop, surfaces interpolated between source frames |
| Reconstructing vector features | Packed plate outlines rotated in the viewer; PaleoCoastlines can also follow a surface gap's motion field |
| Reconstructing rasters | Atlas/PaleoDEM surface interpolation guided by plate-carried centroids; 2002 maps use named-landmass motions |
| Topological plate boundaries | Polygon overlays; no time-dependent topology editor or solver |
| Deforming networks | Not implemented |
| Flowlines, motion paths, velocities | No dedicated viewer products or validated velocity export |
| Globe and map display | Globe, Mollweide and equirectangular views; zoomed PaleoDEM terrain relief and tilt |
| Layers | Plate/coastline overlays and elevation, temperature, sea-level and ice controls where data supports them |
| Scripting interface | Offline Python data builders and validation scripts; no general reconstruction API |

The plate-model and source inventory is maintained in [sources/README.md](../sources/README.md).
Rendering details and their limits are in [globe-viewer.md](globe-viewer.md).

## Remaining work toward reconstruction and deformation

1. **Upgrade surface motion from local translation to per-plate rotation.** Atlas regions
   already have dominant plate IDs, and a rotation model is already used to move their
   centroids. The remaining step is to rotate all relevant surface geometry consistently,
   handling regions that span multiple plates rather than merely translating a neighbourhood.
2. **Separate tectonic transport from changing geography.** Shoreline, shelf, ice and
   sea-level changes cannot all be inferred from plate rotation. Preserve source ages,
   reference frames, assumptions and uncertainty while improving the interpolated shape.
3. **Add controlled time evaluation.** An arbitrary-time or 10,000-year display mode needs
   bounds and performance checks; it should not imply that the sources resolve that interval.
4. **Implement regional deformation.** India–Eurasia collision and Himalayan uplift need
   additional constraints and an explicit extension/shortening or crustal-thickness model.
   The current terrain display uses supplied elevation grids, not an uplift solver.
5. **Validate derived motion products and later mantle coupling.** Flowlines, velocities,
   deforming networks and mantle-convection coupling remain separate development tasks.

Existing rotation-guided interpolation must continue to be labelled as interpolation;
using a published rotation model does not make its blended coastlines a published result.

## Reference frames and palaeolongitude

Why models agree in the Mesozoic and diverge by up to 170 degrees of longitude in the
Palaeozoic, the hypotheses each camp uses to pin longitude, the criticisms of each, and
this project's own measurements are collected in
[docs/palaeolongitude.md](palaeolongitude.md).

## Sources

- [Features of GPlates](https://www.gplates.org/features/)
- [GPlates User Manual](https://www.gplates.org/docs/user-manual/)
- [Introducing the main window](https://www.gplates.org/docs/user-manual/introducing_the_main_window/)
- [Reconstructions chapter](https://gplates.sourceforge.net/user-manual/Reconstructions.html)
- [More on reconstructions](https://gplates.sourceforge.net/user-manual/MoreReconstructions.html)
- [Motion paths](https://www.gplates.org/docs/user-manual/motionpaths/)
- [Modify a reconstruction pole, pygplates](https://www.gplates.org/docs/pygplates/sample-code/pygplates_modify_reconstruction_pole)
- [Working with time-dependent rasters](https://www.earthbyte.org/Resources/GPlates_tutorials/All_Tutorials/GPlates_Rasters_Tutorial.html)
- [Plate reconstructions tutorial](https://www.earthbyte.org/Resources/GPlates_tutorials/All_Tutorials/GPlates_Plate_Tutorial.html)
- [The GPlates Geological Information Model](https://www.gplates.org/docs/gpgim/)
