# GPlates: what it does, and where this project stands

Notes gathered to aim this project at the capability GPlates already has. GPlates is the
reference implementation of interactive plate reconstruction, from EarthByte at the
University of Sydney and collaborators. Nothing here is our own measurement; it is a
reading of the project's own feature page, user manual and tutorials, listed at the end.

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

That is why the GPlates time control is genuinely continuous: any time is as valid as
any other, because geometry is computed rather than looked up. Our timeline is the
opposite. We hold 17 published pictures and blend between them, so only 17 stops are
observations and everything between is a geometric guess with no plate in it.

## Functional areas

The user manual runs to 24 chapters. Grouped by what they do:

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

This is the shape our slider is moving toward. We already let the sampling be set as an
even number of sub-steps per published map, or as a fixed span in millions of years,
which is the GPlates-style constant time increment. What we do not have is a reason for
any particular intermediate frame to look the way it does.

## What we have, against that list

| GPlates capability | Here |
| --- | --- |
| Rotation model, plate IDs, plate circuit | none |
| Continuous reconstruction time | slider is continuous in appearance only |
| Reconstructing vector features | outlines exist as GeoJSON, never rotated |
| Reconstructing rasters | source maps are reprojected, not reconstructed |
| Topological plate boundaries | none |
| Deforming networks | none |
| Flowlines, motion paths, velocities | none |
| Globe and map display | globe only |
| Layers | one surface at a time, with a toggle |
| Scripting interface | offline Python scripts, no viewer API |

## What it would take to close the gap

In rough order of dependency:

1. **Plate IDs on our segmented pieces.** Each piece already has a name and an outline.
   Assigning a plate ID is the step that makes a piece something a rotation can act on.
2. **A rotation model.** Either adopt a published one, which pins us to its plate IDs
   and its reference frame, or fit rotations to our own pieces between the 17 maps. The
   second is a research task, and its output would be our interpretation, not Scotese's.
3. **Compose and apply rotations in the viewer**, replacing the distance-field blend for
   any time a rotation model covers. The distance-field blend stays useful for the parts
   no rotation model covers, such as shorelines and shelf, which move for reasons other
   than plate motion.
4. **Continuous time** then becomes meaningful, and the stop table can be dropped in
   favour of a plain time input.
5. Derived products, flowlines, motion paths, velocities, only make sense after 3.

Steps 1 and 2 are where the scientific content lives; everything else is engineering.
Until step 3 exists, our intermediate frames must keep saying they are interpolated.

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
