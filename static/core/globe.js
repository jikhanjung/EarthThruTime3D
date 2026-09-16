import * as THREE from 'three';
import { OrbitControls } from '../vendor/three/OrbitControls.js';
import { placeEquirectangular, placeMollweide, reproject } from './projection.js';
import { RotationModel, turn } from './rotation.js';
import { densifySegments } from './surface-lines.js';
import { createMantleOverlay, CUT_UNIFORMS, CUT_SURFACE } from './mantle-overlay.js';
let mantleOverlay = null;

const $ = (id) => document.getElementById(id);
const frames = JSON.parse($('globe-frames').textContent);
const status = $('status');
const stage = $('globe');
const textures = new Map();
// Flat fills for the derived surface. Deliberately unlike the source palette, so a
// segmented globe is never mistaken for the published map.
const LAND_COLOUR = [205, 193, 148];
const OCEAN_COLOUR = [22, 86, 135];
// The slider's stops, built by the server as [from frame, to frame, blend, age]. A
// stop whose blend is zero is a published map; every other stop is interpolated, never
// observed. The viewer does not care how the stops were spaced, so an even count per
// map and a fixed span in millions of years both arrive the same way.
const stops = JSON.parse($('globe-stops').textContent);
// How the server spaced the stops: so many per map, or one every so many Myr.
const sampling = JSON.parse($('globe-sampling')?.textContent ?? '{}');
// The time window, when the page shows one: every frame is then the present grid at one
// age of the last deglaciation, carrying its dated ice slice and sea level as `deglacial`.
const timeWindow = sampling.window || null;
// With a fixed span in Myr, or the window's thousand years, playback moves at one stop per
// this many milliseconds, so time runs evenly; per-map sampling keeps its pace per source map.
const INTERVAL_STEP_MS = 300;
// ICS period boundaries as [upper age, Korean name], to name a stop by its own age.
const periods = JSON.parse($('globe-periods')?.textContent ?? '[]');
// Every sentence the script shows, translated by the server for the page's language.
const L = JSON.parse($('globe-strings').textContent);
const fmt = (text, values) => text.replace(/\{(\w+)\}/g, (match, key) => (key in values ? values[key] : match));
// Per gap, where each matched landmass sits on both of its maps. These are the control
// points that carry a continent across the gap instead of dissolving it in place.
const motions = JSON.parse($('globe-motions')?.textContent ?? '[]');
const MAX_MOTIONS = 16;
const frameStops = frames.map((frame, index) =>
  stops.findIndex(([from, , blend]) => blend === 0 && from === index));
// Longitude of the texture's left edge, in the sphere's own sweep. Measured against
// the rendered globe rather than derived: the geometry's UV convention and the
// canvas flip cancel out, so a label goes where the reprojection put its pixels.
const TEXTURE_MERIDIAN = 0;
// Each projection is a shape to draw on and a way to place a longitude and latitude on
// it. The shader undoes the projection per texel; these place the labels and the grid.
const PROJECTIONS = {
  globe: { sheet: null, code: 0, place: null, half: [1, 1] },
  equirect: { sheet: [2, 1], code: 1, place: placeEquirectangular, half: [1, 0.5] },
  mollweide: { sheet: [2, 1], code: 2, place: placeMollweide, half: [1, 0.5] },
};
// The plate model is a second, unrelated dataset: EarthByte's rotation model rather
// than a measurement of the Scotese maps. It is drawn as an overlay so the two can be
// compared at one time without either being mistaken for the other.
const plates = JSON.parse($('globe-plates')?.textContent ?? '[]');
const PLATE_COLOUR = 0xff62c0;
// PaleoCoastlines (Kocsis & Scotese 2021): coastlines moved to where marine fossils say
// the sea reached. Same PALEOMAP frame as the 2016 masks, so drawn without rotation.
const coastlines = JSON.parse($('globe-coastlines')?.textContent ?? 'null');
// Amber vanished against the tan land; this reads on land and on sea, and is not the
// plate overlay's pink.
const COASTLINE_COLOUR = 0xff4d1a;
// The coastline ages run every 5 Myr with a few wider gaps; further than this from the
// reader's age, the nearest one would be a different coastline, so none is drawn.
const COASTLINE_REACH_MA = 10;
const coastlineData = new Map();
let coastlineLayer;
let coastlineKey = '';
const surfaceToggle = $('surface');
// Global mean surface temperature per published map, [age, C], oldest first: the
// area-weighted mean of the Scotese 2021 maps. Empty until the climate build has run.
const temperatureCurve = JSON.parse($('globe-temperature')?.textContent ?? '[]');
const temperatureToggle = $('temperature');
// Sea level: the long-term Phanerozoic curve as [age Ma, mean, min, max, ice Mkm3]
// metres above present, oldest first (van der Meer et al. 2022), and the Late
// Pleistocene stack as [age ka, metres] (Spratt & Lisiecki 2016). Each PaleoDEM already
// carries the sea level of its time, so the curve is drawn for reading and, when asked,
// applied only as its departure from the slice's own datum.
const seaLevel = JSON.parse($('globe-sealevel')?.textContent ?? '{"long":[],"pleistocene":[]}');
const seaLevelControl = $('sealevel');
const seaLevelCurveToggle = $('sealevel-curve');
// The ice overlay can be hidden in any surface mode; the masks stay loaded.
const iceToggle = $('ice');
let iceVisible = true;
// Rivers likewise: the fields stay bound while the lines are hidden.
const riverToggle = $('rivers');
let riversVisible = true;
let plateLayer;
let plateAge = null;
// Empty means the Scotese surface alone, which is where the viewer starts.
let plateChoice = '';
// One entry per model, so switching back does not refetch.
const plateData = new Map();
// Without the published maps there is nothing to show but the derived surface, so the
// viewer starts there and the toggle is not rendered at all.
const sourceMapsPublic = frames.some((frame) => Boolean(frame.url));
// A relief series carries elevation in its fields, so its plain view is coloured by
// height rather than by a photographed map, and the mask toggle returns to it.
const reliefSeries = frames.some((frame) => frame.relief);
let surface = reliefSeries ? 'relief' : sourceMapsPublic ? 'map' : 'mask';
let projection = 'globe';
let surfaceMesh;
let gridVisible = true;
// Centre longitude of a flat sheet. The globe turns by moving the camera; a sheet turns by
// shifting which longitude sits in its middle, so the camera and its zoom stay put.
let meridian = 0;
let spinning = false;
let lastPlace = null;
let lastPlates = null;
let lastCoastline = null;
let flatRefresh = 0;
let nameLayer;
let nameGroupKey = '';
let uniforms;
let stop = stops.length - 1;
let selected = frames.length - 1;
let request = 0;
let playing = false;
let playTimer;
let scene, camera, renderer, controls, earth, grid;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function ageText(frame) {
  return frame.age === 0 ? '0 Ma' : frame.age < 1 ? fmt(L.yearsAgo, { years: Math.round(frame.age * 1e6).toLocaleString() }) : `${frame.age} Ma`;
}
function periodAt(age) {
  if (age === 0) return L.present;
  for (const [upper, name] of periods) if (age < upper) return name;
  return L.proterozoic;
}
function setPlaying(value) {
  if (value && mantleOverlay?.isActive()) return;
  playing = value;
  clearTimeout(playTimer);
  $('play').setAttribute('aria-pressed', String(value));
  $('play').textContent = value ? L.playStop : L.playStart;
}
function scheduleNext() {
  // Playback walks the sub-steps so the change reads as motion, at the same pace per
  // source map as before.
  // Playback walks the stops, holding the same pace per source map however densely
  // the timeline was sampled.
  const perFrame = (stops.length - 1) / Math.max(1, frames.length - 1);
  const delay = sampling.interval_ma || timeWindow ? INTERVAL_STEP_MS : Math.max(60, 2400 / perFrame);
  if (playing) {
    playTimer = setTimeout(() => selectStop(stop >= stops.length - 1 ? 0 : stop + 1), delay);
  }
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Download failed: ${source}`));
    image.src = source;
  });
}
// Textures kept in GPU memory. Two are bound at any stop; the rest are a cache so
// scrubbing back and forth does not re-download. A phone that has scrubbed the whole
// timeline would otherwise hold every slice, which at 2048 x 1024 is near a gigabyte.
const TEXTURE_CACHE = 12;
function cache(key, build) {
  if (textures.has(key)) {
    const promise = textures.get(key);
    textures.delete(key);       // re-insert so Map order is least recently used first
    textures.set(key, promise);
    return promise;
  }
  const promise = build();
  textures.set(key, promise);
  promise.catch(() => textures.delete(key));
  for (const [stale, old] of textures) {
    if (textures.size <= TEXTURE_CACHE) break;
    textures.delete(stale);
    old.then((texture) => texture.dispose(), () => {});
  }
  stage.dataset.cached = String(textures.size);
  return promise;
}
function prepare(texture) {
  // The shader decodes colour itself, so every texture is handed over as raw data.
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return texture;
}
function loadMap(frame) {
  return cache(`${frame.id}:map`, async () =>
    prepare(new THREE.CanvasTexture(reproject(await loadImage(frame.url), frame.bounds))));
}
function loadField(frame) {
  return loadData(`${frame.id}:field`, frame.field);
}
function loadTemperature(frame) {
  return loadData(`${frame.id}:temp`, frame.temp);
}
// Ice masks exist where ice was drawn: Natural Earth at the present, the atlas's white
// elsewhere. A frame without one contributes no ice, so the overlay fades out across
// the gap to it, which reads as retreat.
function loadIce(frame) {
  return frame.ice ? loadData(`${frame.id}:ice`, frame.ice) : Promise.resolve(null);
}
// A river field exists for every grid of the elevation series once built. A frame
// without one contributes no rivers, so the network fades out across the gap. Which of a
// frame's fields show at a sea-level offset, and how far between them: a frame with
// fields routed over the ice of the last glacial cycle (`rivers_ice`, youngest first, each
// at its age's level) shows the two bracketing the offset, its own field standing at 0 m
// and the deepest holding below it; otherwise its own field toward the one routed with the
// sea at the slider's lowest level (`rivers_low`, the shelf's rivers) by the offset's share
// of that level. Each side is {key, url} for the cache, or null.
function riverChoice(frame, offset) {
  const own = frame?.rivers ? { key: `${frame.id}:rivers`, url: frame.rivers } : null;
  const slices = frame?.rivers_ice || [];
  if (own && slices.length && offset < 0) {
    let index = slices.findIndex(slice => slice.level_m <= offset);
    if (index < 0) index = slices.length - 1;
    const upper = index ? slices[index - 1] : { level_m: 0, age_ka: 0 };
    const lower = slices[index];
    const t = Math.min(1, (offset - upper.level_m) / (lower.level_m - upper.level_m));
    return { base: index ? { key: `${frame.id}:rivers-ice:${upper.age_ka}`, url: upper.url } : own,
             low: { key: `${frame.id}:rivers-ice:${lower.age_ka}`, url: lower.url },
             t, age: upper.age_ka + (lower.age_ka - upper.age_ka) * t };
  }
  const low = frame?.rivers_low;
  return { base: own, low: low ? { key: `${frame.id}:rivers-low`, url: low.url } : null,
           t: low && offset < 0 ? Math.min(1, offset / low.level_m) : 0, age: null };
}
function loadRiverField(choice) {
  return choice ? loadData(choice.key, choice.url) : Promise.resolve(null);
}
// A frame with a dated deglaciation carries lowstand slices, youngest first, each with
// the sea level of its age; index -1 is the frame's own field, the slice at 0 m.
function loadIceLow(frame, index) {
  const low = frame.ice_lows && index >= 0 ? frame.ice_lows[index] : null;
  return low ? loadData(`${frame.id}:ice-low:${low.age_ka}`, low.url) : Promise.resolve(null);
}
// In the time window a frame's ice is its age's dated slice; at 0 ka the present's own
// mask stands, so there is nothing more to load.
function loadDeglacial(frame) {
  const slice = frame.deglacial;
  return slice?.url ? loadData(`${frame.id}:deglacial:${slice.age_ka}`, slice.url) : Promise.resolve(null);
}
// The sea-level offset as a volume of ice, the paper's ratio, and the level of a frame's
// ice field that encloses the area that volume implies: area goes as volume to the 0.8,
// and the builder tabulated the share of the globe inside each level. Above 1 cuts
// everything, the ice-free end; 0 keeps everything the field reaches.
const SEA_PER_MKM3 = 2.5;
const AREA_EXPONENT = 0.8;
function iceCutFor(sheet, offset) {
  if (!sheet || !sheet.volume) return 0.5;
  const volume = sheet.volume - offset / SEA_PER_MKM3;
  if (volume <= 0) return 1.01;
  const levels = sheet.areas.length - 1;
  const target = sheet.areas[levels / 2] * Math.pow(volume / sheet.volume, AREA_EXPONENT);
  if (target >= sheet.areas[0]) return 0;
  for (let index = 0; index < levels; index++) {
    if (sheet.areas[index + 1] <= target) {
      const span = sheet.areas[index] - sheet.areas[index + 1];
      return (index + (span > 0 ? (sheet.areas[index] - target) / span : 0)) / levels;
    }
  }
  return 1.01;
}
// What the offset does to one frame's ice: the cut, and for a frame with dated lowstand
// slices which two bracket the offset and how far between them (`low`), the frame's own
// field standing at 0 m and the area law taking over below the deepest slice.
function iceState(frame, offset) {
  const lows = frame.ice_lows || [];
  if (!frame.ice || offset >= 0 || !lows.length) return { cut: iceCutFor(frame.ice_sheet, offset), low: null };
  const index = lows.findIndex(low => low.level_m <= offset);
  if (index < 0) {
    const deepest = lows[lows.length - 1];
    return { cut: iceCutFor(deepest, offset - deepest.level_m),
             low: { from: lows.length - 1, to: lows.length - 1, t: 0, age: deepest.age_ka } };
  }
  const upper = index ? lows[index - 1] : { level_m: 0, age_ka: 0 };
  const t = (offset - upper.level_m) / (lows[index].level_m - upper.level_m);
  return { cut: 0.5, low: { from: index - 1, to: index, t, age: upper.age_ka + (lows[index].age_ka - upper.age_ka) * t } };
}
function loadData(key, url) {
  // A field is data, not a picture: distance in red, height in green and blue.
  // Decoding it as an <img> lets the browser colour-manage the bytes on the way to
  // WebGL, which some engines do even when asked not to, and a shifted distance moves
  // the coastline. WebGL only colour-converts DOM image sources; bytes handed over as
  // an array are uploaded as they are, by specification. So decode to a 2D canvas,
  // read the bytes back and upload those.
  return cache(key, async () => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Download failed: ${url}`);
    const bitmap = await createImageBitmap(await response.blob(), {
      colorSpaceConversion: 'none', premultiplyAlpha: 'none',
    });
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const context = canvas.getContext('2d', { colorSpace: 'srgb', willReadFrequently: true });
    context.drawImage(bitmap, 0, 0);
    bitmap.close();
    const { data, width, height } = context.getImageData(0, 0, canvas.width, canvas.height);
    const texture = prepare(new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.UnsignedByteType));
    texture.flipY = true;   // row 0 of the field is north; the sphere's v runs south to north
    texture.needsUpdate = true;   // a DataTexture uploads nothing until told to
    return texture;
  });
}
async function loadSurface(frame) {
  if ((surface !== 'map' || !frame.url) && frame.field) return loadField(frame);
  return loadMap(frame);
}
function stopAt(value) {
  const clamped = Math.max(0, Math.min(stops.length - 1, Math.round(value)));
  const [from, to, blend, age] = stops[clamped];
  // A map frame index of -1 marks a stop older than any published map: there is a plate
  // model to reconstruct there but no surface to show.
  if (from < 0) {
    return { value: clamped, blend: 0, age, from: null, to: null, index: 0, mapless: true };
  }
  return { value: clamped, blend, age, from: frames[from], to: frames[to],
           index: blend > 0.5 ? to : from, mapless: false };
}
function neighbourStop(direction) {
  const age=mantleOverlay?.neighbourAge(direction);
  if (age != null) return stops.findIndex(s=>Math.abs(s[3]-age)<1e-8);
  const marks = frameStops.filter((mark) => direction < 0 ? mark < stop : mark > stop);
  if (!marks.length) return direction < 0 ? 0 : stops.length - 1;
  return direction < 0 ? Math.max(...marks) : Math.min(...marks);
}
function ageLabel(place) {
  if (place.mapless) return `${place.age} Ma`;
  if (place.blend === 0) return ageText(place.from);
  return place.age < 1
    ? fmt(L.yearsAgo, { years: Math.round(place.age * 1e6).toLocaleString() })
    : `${place.age.toFixed(1)} Ma`;
}
function periodLabel(place) {
  if (place.mapless) return L.mapless;
  // A published map keeps its own label; a stop between two maps is named for its age.
  return place.blend === 0 ? place.from.label : periodAt(place.age);
}
async function selectStop(value, manual = false, overlayManaged = false, transition = null) {
  if (!overlayManaged && mantleOverlay?.requestAge(stopAt(value).age)) return;
  if (manual) setPlaying(false);
  clearTimeout(playTimer);
  const place = stopAt(value);
  const displayedLabel = $('globe-age').textContent;
  stop = place.value;
  selected = place.index;
  const ticket = ++request;
  const between = place.blend > 0;
  const fielded = !place.mapless && Boolean(place.from.field) && Boolean(place.to.field);
  // Temperature needs a map on both sides; a stop without one shows its relief instead.
  const heated = surface === 'temp' && fielded && Boolean(place.from.temp) && Boolean(place.to.temp);
  // A stop needs heights on both sides to be drawn by height; the atlas prelude has none.
  const relief = !heated && (surface === 'relief' || surface === 'temp') && fielded
    && Boolean(place.from.relief) && Boolean(place.to.relief);
  const masked = !relief && !heated && fielded && (surface === 'mask' || !sourceMapsPublic);
  const anchor = place.mapless ? null : (place.blend > 0.5 ? place.to : place.from);
  $('era').value = selected;
  $('timeline').value = stop;
  $('timeline').setAttribute('aria-valuetext', place.mapless
    ? fmt(L.maplessValue, { age: ageLabel(place) })
    : (between ? fmt(L.betweenValue, { period: periodLabel(place), age: ageLabel(place) })
               : `${place.from.label}, ${ageText(place.from)}`));
  $('period').textContent = periodLabel(place);
  $('age').textContent = ageLabel(place);
  $('source-title').textContent = place.mapless
    ? L.olderThanMaps
    : (between ? `${place.from.title} → ${place.to.title}` : place.from.title);
  $('globe-age').textContent = [periodLabel(place), ageLabel(place),
    place.mapless ? null : (masked ? L.mask : relief ? L.relief : heated ? L.temperature : null),
    place.mapless ? L.noMap : (between ? L.interpolated : null),
    !place.mapless && place.from.ice_kind === 'analogue' ? L.analogueIce : null].filter(Boolean).join(' / ');
  const nextLabel = $('globe-age').textContent;
  if (transition) $('globe-age').textContent = displayedLabel;
  // Older than any map there is no source to preview, and leaving the last one up
  // would read as if it applied.
  if ($('source-figure')) $('source-figure').hidden = place.mapless;
  if (anchor) {
    $('source-link').href = anchor.source;
    if ($('source-preview')) {
      $('source-preview').src = anchor.url;
      $('source-preview').alt = fmt(L.sourceAlt, { label: anchor.label, age: ageText(anchor) });
    }
  }
  $('older').disabled = stop <= 0;
  $('newer').disabled = stop >= frameStops[frames.length - 1];
  $('frame-number').textContent = place.mapless
    ? fmt(L.maplessCount, { age: place.age })
    : (between ? fmt(L.betweenCount, { age: ageLabel(place) }) : `${selected + 1} / ${frames.length}`);
  if (surfaceToggle) {
    surfaceToggle.disabled = place.mapless || !place.from.field || !place.to.field;
    surfaceToggle.setAttribute('aria-pressed', String(masked));
  }
  if (temperatureToggle) temperatureToggle.setAttribute('aria-pressed', String(heated));
  if ($('temp-note')) $('temp-note').hidden = !heated;
  if ($('temp-legend')) $('temp-legend').hidden = !heated;
  showMeanTemperature(place);
  // Decided here, synchronously, so the readout and the shader agree at every stop.
  const seaOffset = seaLevelOffset(place, fielded);
  showSeaLevel(place, seaOffset);
  $('surface-note').hidden = !masked;
  $('between-note').hidden = !between;
  if ($('mapless-note')) $('mapless-note').hidden = !place.mapless;
  status.textContent = place.mapless
    ? fmt(L.loadingPlates, { age: ageLabel(place) })
    : fmt(masked ? L.loadingMask : relief ? L.loadingRelief : heated ? L.loadingTemperature : L.loadingMap, { period: periodLabel(place) });
  status.hidden = false;
  status.classList.remove('loaded');
  $('retry').hidden = true;
  stage.setAttribute('aria-busy', 'true');
  let commitOverlay = null;
  try {
    if (place.mapless) {
      uniforms.blank.value = 1;
      uniforms.blend.value = 0;
      applyIce(null, null);
      applyRivers(null, null, null, null, [0, 0]);
      stage.dataset.riverIce = '';
      showIceKind(place);
      uniforms.iceCut.value.set(0.5, 0.5);
      uniforms.iceLowMix.value.set(0, 0);
      uniforms.iceLowT.value = 0;
      stage.dataset.iceCut = '';
      stage.dataset.iceLow = '';
    } else {
      // In a time window each frame is the present at one age, the age setting the sea level.
      // Where a dated slice exists it stands in for the frame's own ice and no offset cuts
      // it; older than any slice the frame takes the what-if path at that level.
      const dated = Boolean(place.from.deglacial?.url);
      const stateA = dated ? { cut: 0.5, low: null } : iceState(place.from, seaOffset);
      const stateB = dated ? { cut: 0.5, low: null } : iceState(place.to, seaOffset);
      // One stop carries slices today, the present; a side without them loads nothing.
      const sliced = stateA.low ? 'from' : stateB.low ? 'to' : null;
      const low = sliced ? (sliced === 'from' ? stateA : stateB).low : null;
      const riversA = riverChoice(place.from, seaOffset);
      const riversB = riverChoice(place.to, seaOffset);
      const [first, second, warmA, warmB, iceA, iceB, low0, low1, riverA, riverB, riverLowA, riverLowB, preparedOverlay] = await Promise.all([
        loadSurface(place.from), loadSurface(place.to),
        heated ? loadTemperature(place.from) : null, heated ? loadTemperature(place.to) : null,
        fielded ? loadIce(place.from) : null, fielded ? loadIce(place.to) : null,
        !fielded ? null : dated ? loadDeglacial(place.from) : low ? loadIceLow(place[sliced], low.from) : null,
        !fielded ? null : dated ? loadDeglacial(place.to) : low ? loadIceLow(place[sliced], low.to) : null,
        fielded ? loadRiverField(riversA.base) : null, fielded ? loadRiverField(riversB.base) : null,
        fielded ? loadRiverField(riversA.low) : null, fielded ? loadRiverField(riversB.low) : null,
        transition?.prepare(),
        // Prepare line data too; committing the surface must not wait on another fetch.
        transition && showPlates() && !locked() ? loadPlateModel() : null,
        transition && $('coastline')?.checked && coastlineEntry(place.age)
          ? loadCoastline(coastlineEntry(place.age)) : null]);
      if (ticket !== request || (transition && !transition.isCurrent())) return;
      commitOverlay = preparedOverlay;
      uniforms.surfaceA.value = first;
      uniforms.surfaceB.value = second;
      uniforms.tempA.value = warmA;
      uniforms.tempB.value = warmB;
      applyIce(iceA, iceB);
      applyRivers(riverA, riverB, riverLowA, riverLowB, [riversA.t, riversB.t]);
      // The age of the ice the rivers run off, where they do: each side's own, mixed by the blend.
      const iced = [riversA, riversB].filter(choice => choice.age != null);
      stage.dataset.riverIce = iced.length ? (iced.length === 1 ? iced[0].age : riversA.age + (riversB.age - riversA.age) * place.blend).toFixed(1) : '';
      showIceKind(place);
      if (dated) {
        // Each side's slice replaces its own red, the shelves stay from the present's mask,
        // and the lowstand pair follows the blend.
        uniforms.iceLow0.value = low0 || iceA;
        uniforms.iceLow1.value = low1 || iceB;
        uniforms.iceLowT.value = place.blend;
        uniforms.iceCut.value.set(0.5, 0.5);
        uniforms.iceLowMix.value.set(low0 ? 1 : 0, low1 ? 1 : 0);
        stage.dataset.iceCut = '0.500';
        stage.dataset.iceLow = '';
      } else {
        const own = sliced === 'from' ? iceA : iceB;
        uniforms.iceLow0.value = low0 || own;
        uniforms.iceLow1.value = low1 || own;
        uniforms.iceLowT.value = low ? low.t : 0;
        uniforms.iceCut.value.set(stateA.cut, stateB.cut);
        uniforms.iceLowMix.value.set(sliced === 'from' && own ? 1 : 0, sliced === 'to' && own ? 1 : 0);
        stage.dataset.iceCut = (stateA.cut + (stateB.cut - stateA.cut) * place.blend).toFixed(3);
        stage.dataset.iceLow = low && own ? low.age.toFixed(1) : '';
      }
      uniforms.blend.value = place.blend;
      uniforms.blank.value = 0;
    }
    uniforms.mode.value = heated ? 3 : relief ? 2 : masked ? 1 : 0;
    if (!place.mapless) {
      uniforms.texel.value.set(1 / uniforms.surfaceA.value.image.width, 1 / uniforms.surfaceA.value.image.height);
      uniforms.vegetation.value = vegetationAt(place.age);
    }
    uniforms.seaLevel.value = seaOffset;
    stage.dataset.iceAge = !place.mapless && place.from.deglacial ? String(place.from.deglacial.age_ka) : '';
    if ($('sea-note')) $('sea-note').hidden = seaOffset === 0;
    stage.dataset.sealevel = String(Math.round(seaOffset));
    applyMotion(place);
    surfaceMesh.visible = true;
    commitOverlay?.();
    $('globe-age').textContent = nextLabel;
    lastPlace = place;
    // Names go on any surface without lettering of its own: the mask, and on the
    // elevation series the relief and the temperature; a photographed map has its own.
    showNames(place, !place.mapless && (masked || relief || heated));
    await updatePlates(place, ticket);
    if (ticket !== request) return;
    await updateCoastlines(place, ticket);
    if (ticket !== request) return;
    stage.dataset.frame = place.mapless ? 'none' : place.from.id;
    stage.dataset.blend = place.blend.toFixed(2);
    stage.dataset.mapless = String(place.mapless);
    stage.dataset.surface = place.mapless ? 'none' : heated ? 'temp' : relief ? 'relief' : masked ? 'mask' : 'map';
    stage.setAttribute('aria-label', place.mapless
      ? fmt(L.maplessLabel, { age: ageLabel(place) })
      : fmt(L.globeLabel, { period: periodLabel(place), age: ageLabel(place),
                            surface: masked ? L.maskGlobe : relief ? L.reliefGlobe : heated ? L.temperatureGlobe : L.globe, between: between ? L.betweenSuffix : '' }));
    stage.setAttribute('aria-busy', 'false');
    status.textContent = place.mapless
      ? fmt(L.shownPlates, { age: ageLabel(place) })
      : fmt(L.shownSurface, { period: periodLabel(place), surface: masked ? L.mask : relief ? L.relief : heated ? L.temperature : L.globe,
                              between: between ? L.shownBetween : '' });
    status.classList.add('loaded');
    scheduleNext();
    return true;
  } catch (error) {
    if (ticket !== request || (transition && !transition.isCurrent())) return;
    if (overlayManaged) {
      // A neutral globe is explicit missing data, never old terrain under a new age.
      uniforms.blank.value = 1;
      surfaceMesh.visible = true;
      nameLayer.visible = false;
      if (plateLayer) plateLayer.visible = false;
      if (coastlineLayer) coastlineLayer.visible = false;
      stage.dataset.surface = 'unavailable';
    }
    status.classList.remove('loaded');
    status.textContent = masked
      ? L.failedField
      : L.failedMap;
    stage.setAttribute('aria-busy', 'false');
    $('retry').hidden = false;
    setPlaying(false);
    console.error(error);
    return false;
  }
}
// Which kind of ice the bound masks are: a drawing (Natural Earth, the atlas) or a cap at
// the paper's modelled limit where the atlas paints nothing; the limit note shows for the
// latter only, and only while the layer is on.
function showIceKind(place) {
  const pair = place && !place.mapless ? [place.from, place.to] : [];
  const limit = pair.some(frame => frame.ice && frame.ice_kind === 'limit');
  // In a time window, ice older than any dated slice is the retreat's shape borrowed at the
  // same sea level, an assumption rather than a reconstruction.
  const analogue = pair.some(frame => frame.ice && frame.ice_kind === 'analogue');
  const shown = stage.dataset.ice === 'true';
  stage.dataset.iceKind = shown ? (limit ? 'limit' : analogue ? 'analogue' : 'drawn') : '';
  if ($('ice-limit-note')) $('ice-limit-note').hidden = !(shown && limit);
  if ($('ice-analogue-note')) $('ice-analogue-note').hidden = !(shown && analogue);
}
// Rivers over the surface, under the ice. The fields stay bound while hidden so a toggle
// needs no reload; a missing field on one side weighs nothing, so the network fades
// across that gap.
// `lowT` is how far each side stands from its base field toward its low one (see
// riverChoice); `data-river-low` on the stage is the larger of the two.
function applyRivers(riverA, riverB, lowA, lowB, lowT) {
  const shown = riversVisible && Boolean(riverA || riverB);
  uniforms.riverA.value = riverA;
  uniforms.riverB.value = riverB;
  uniforms.riverLow0.value = lowA || riverA;
  uniforms.riverLow1.value = lowB || riverB;
  uniforms.riverLowT.value.set(lowA ? lowT[0] : 0, lowB ? lowT[1] : 0);
  uniforms.riverWeight.value.set(riversVisible && riverA ? 1 : 0, riversVisible && riverB ? 1 : 0);
  stage.dataset.rivers = String(shown);
  stage.dataset.riverLow = Math.max(lowA ? lowT[0] : 0, lowB ? lowT[1] : 0).toFixed(2);
  if ($('river-note')) $('river-note').hidden = !shown;
  if (riverToggle) {
    riverToggle.setAttribute('aria-pressed', String(riversVisible));
    riverToggle.disabled = !(riverA || riverB);
  }
}
function applyIce(iceA, iceB) {
  const shown = iceVisible && Boolean(iceA || iceB);
  uniforms.iceA.value = iceA;
  uniforms.iceB.value = iceB;
  uniforms.iceWeight.value.set(iceVisible && iceA ? 1 : 0, iceVisible && iceB ? 1 : 0);
  stage.dataset.ice = String(shown);
  if ($('ice-note')) $('ice-note').hidden = !shown;
  if (iceToggle) {
    iceToggle.setAttribute('aria-pressed', String(iceVisible));
    iceToggle.disabled = !(iceA || iceB);
  }
}
// Long-term sea level at an age, metres above present, linear between the 1 Myr
// points; null outside the curve.
function seaLevelAt(age) {
  const curve = seaLevel.long;
  for (let index = 0; index + 1 < curve.length; index++) {
    const [older, high] = curve[index];
    const [newer, low] = curve[index + 1];
    if (older >= age && age >= newer) {
      return older === newer ? high : high + (low - high) * (older - age) / (older - newer);
    }
  }
  return null;
}
// The offset to apply at a stop, in metres above the slice's own datum. A fixed
// choice is a what-if; the curve choice is the published curve's departure from the
// datum the bracketing slices already carry, which is what changes between slices.
function seaLevelOffset(place, fielded) {
  if (!seaLevelControl || !fielded || place.mapless || !place.from.relief || !place.to.relief) return 0;
  // The slider is a what-if in metres, held to the ice the stop has (see seaRange); the
  // curve box adds the published curve's departure from the bracketing grids' own datum,
  // zero at a grid stop.
  // In the time window the age sets the level: the stack's, held from the present.
  if (place.from.deglacial) {
    const [from, to] = [place.from.deglacial.level_m, place.to.deglacial.level_m];
    return from + (to - from) * place.blend;
  }
  const range = seaRange(place);
  const fixed = Math.min(range[1], Math.max(range[0], Number(seaLevelControl.value) || 0));
  if (!seaLevelCurveToggle?.checked) return fixed;
  const now = seaLevelAt(place.age);
  const from = place.from.sea_m;
  const to = place.to.sea_m;
  if (now == null || from == null || to == null) return fixed;
  return fixed + now - (from + (to - from) * place.blend);
}
const signed = (value) => `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(0)} m`;
function showSeaLevel(place, offset) {
  const out = $('sea-level');
  if (!out) return;
  const level = place.mapless ? null : seaLevelAt(place.age);
  // The ice that offset stands for, by the paper's ratio: a metre of sea level is 0.4
  // million km3 of land ice, more ice when the sea is lower, and never less than none.
  const from = place.mapless ? 0 : (place.from.ice_sheet?.volume || 0);
  const to = place.mapless ? 0 : (place.to.ice_sheet?.volume || 0);
  const volume = from + (to - from) * (place.blend || 0);
  const ice = Math.max(-offset / SEA_PER_MKM3, -volume);
  const change = offset !== 0
    ? fmt(L.seaLevelOffset, { value: signed(offset) })
      + (volume > 0 ? fmt(L.seaLevelIce, { value: `${ice >= 0 ? '+' : '−'}${Math.abs(ice).toFixed(0)}` }) : '')
    : '';
  showSeaMarks(place);
  // In the time window the level shown is the one applied, the age's own.
  const dated = !place.mapless && Boolean(place.from.deglacial);
  out.textContent = dated
    ? fmt(L.seaLevelDated, { value: signed(offset) })
    : level == null ? L.seaLevelNone : fmt(L.seaLevel, { value: signed(level), offset: change });
  stage.dataset.seaCurve = dated ? offset.toFixed(0) : level == null ? '' : level.toFixed(0);
  const mark = $('sea-now');
  if (mark) {
    mark.setAttribute('x1', String(stop + 0.5));
    mark.setAttribute('x2', String(stop + 0.5));
  }
}
// The slider's range at a stop is the ice the stop has: from its glacial maximum, an
// anchor from the literature, to its whole ice melted. Between two grids the ends slide
// from one grid's to the other's. A stop with no ice has no range, and the slider rests.
function seaRange(place) {
  if (!place || place.mapless) return [0, 0];
  const from = place.from.ice_sheet?.range_m || [0, 0];
  const to = place.to.ice_sheet?.range_m || [0, 0];
  const blend = place.blend || 0;
  return [Math.round((from[0] + (to[0] - from[0]) * blend) / 10) * 10,
          Math.round((from[1] + (to[1] - from[1]) * blend) / 10) * 10];
}
function showSeaSetting() {
  if ($('sealevel-value')) $('sealevel-value').textContent = signed(Number(seaLevelControl.value) || 0);
}
// Give the slider the stop's range and mark its two ends: the glacial maximum, where
// the anchors give one, and no ice at all, the stop's whole volume melted.
function showSeaMarks(place) {
  const marks = $('sealevel-marks');
  const notes = $('sealevel-notes');
  if (!marks || !notes || !seaLevelControl) return;
  if (!place.mapless && place.from.deglacial) {
    // The age sets the level here; the slider shows it and does not move.
    const level = String(Math.round(seaLevelOffset(place, true)));
    seaLevelControl.min = level;
    seaLevelControl.max = level;
    seaLevelControl.value = level;
    seaLevelControl.disabled = true;
    showSeaSetting();
    marks.replaceChildren();
    notes.textContent = L.seaFromAge;
    notes.hidden = false;
    return;
  }
  const range = seaRange(place);
  seaLevelControl.min = String(range[0]);
  seaLevelControl.max = String(range[1]);
  seaLevelControl.disabled = range[0] === range[1];
  showSeaSetting();
  const entries = [];
  if (range[0] < 0) entries.push([range[0], L.seaMarkMax]);
  if (range[1] > 0) entries.push([range[1], L.seaMarkNone]);
  marks.replaceChildren(...entries.map(([value]) => new Option('', value)));
  notes.textContent = entries.length ? entries.map(([value, text]) => fmt(text, { value: signed(value) })).join(' · ') : L.seaNoIce;
  notes.hidden = false;
}
// Tick labels are HTML placed over the chart, because the charts stretch to the
// slider's width and SVG text would stretch with them.
function labelAxis(container, ticks) {
  for (const { top, left, text, align } of ticks) {
    const label = document.createElement('span');
    label.className = left == null ? 'axis-tick' : `axis-tick x ${align || 'center'}`;
    if (top != null) label.style.top = `${top}%`;
    if (left != null) label.style.left = `${left}%`;
    label.textContent = text;
    container.appendChild(label);
  }
}
const SEA_STRIP = { height: 60, lowest: -150, highest: 250 };
function seaY(metres) {
  const { height, lowest, highest } = SEA_STRIP;
  return (height - 2) - (metres - lowest) / (highest - lowest) * (height - 4);
}
// The band above the slider: the long-term curve as a line with its min–max band,
// one column per stop, baseline at present sea level, a metre axis, columns shaded
// where the same paper's land-ice estimate says glacial cycles exist that a 1 Myr
// curve smooths over, and a whisker at the present column for the last 800,000 years.
function drawSeaLevelStrip() {
  const svg = $('sea-strip');
  if (!svg || !seaLevel.long.length) return;
  if (timeWindow) {
    drawWindowSeaStrip(svg);
    return;
  }
  const { height } = SEA_STRIP;
  const y = seaY;
  const n = stops.length;
  svg.setAttribute('viewBox', `0 0 ${n} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  const ns = 'http://www.w3.org/2000/svg';
  const make = (tag, attrs) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  };
  const points = { mean: [], low: [], high: [] };
  const icy = [];
  stops.forEach(([, , , age], index) => {
    const curve = seaLevel.long;
    let bracket = null;
    for (let i = 0; i + 1 < curve.length; i++) {
      if (curve[i][0] >= age && age >= curve[i + 1][0]) { bracket = [curve[i], curve[i + 1]]; break; }
    }
    if (!bracket) return;
    const [a, b] = bracket;
    const k = a[0] === b[0] ? 0 : (a[0] - age) / (a[0] - b[0]);
    const lerp = (i) => a[i] + (b[i] - a[i]) * k;
    points.mean.push(`${index + 0.5},${y(lerp(1)).toFixed(1)}`);
    points.low.push(`${index + 0.5},${y(lerp(2)).toFixed(1)}`);
    points.high.push(`${index + 0.5},${y(lerp(3)).toFixed(1)}`);
    // 5 million km3 of land ice, a fifth of today's, is the cut.
    if (a.length > 4 && lerp(4) > 5) icy.push(index);
  });
  const children = [];
  for (const index of icy) children.push(make('rect', { x: index, y: 0, width: 1, height, class: 'sea-ice' }));
  for (const level of [200, 100, -100]) {
    children.push(make('line', { x1: 0, x2: n, y1: y(level).toFixed(1), y2: y(level).toFixed(1), class: 'sea-grid' }));
  }
  children.push(make('polygon', { points: [...points.high, ...points.low.slice().reverse()].join(' '), class: 'sea-band' }));
  children.push(make('line', { x1: 0, x2: n, y1: y(0).toFixed(1), y2: y(0).toFixed(1), class: 'sea-base' }));
  children.push(make('polyline', { points: points.mean.join(' '), class: 'sea-line' }));
  if (seaLevel.pleistocene.length) {
    const recent = seaLevel.pleistocene.map((point) => point[1]);
    const x = n - 0.5;
    children.push(make('line', { x1: x, x2: x, y1: y(Math.max(...recent)).toFixed(1), y2: y(Math.min(...recent)).toFixed(1), class: 'sea-whisker' }));
  }
  // The chosen stop, moved by showSeaLevel; the curve no longer sits under the slider.
  children.push(make('line', { id: 'sea-now', x1: n - 0.5, x2: n - 0.5, y1: 0, y2: height, class: 'sea-now' }));
  svg.replaceChildren(...children);
  const axis = $('sea-axis');
  if (axis) {
    axis.replaceChildren();
    labelAxis(axis, [200, 100, 0, -100].map((level) => ({ top: y(level) / height * 100, text: `${level > 0 ? '+' : ''}${level} m` })));
  }
}
// The strip in the time window: the level each stop stands at, the stack's running minimum
// held from the present, one column per thousand years, on a scale that fits a lowstand.
function drawWindowSeaStrip(svg) {
  const { height } = SEA_STRIP;
  const y = (metres) => (height - 2) - (metres + 140) / 160 * (height - 4);
  const n = stops.length;
  svg.setAttribute('viewBox', `0 0 ${n} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  const ns = 'http://www.w3.org/2000/svg';
  const make = (tag, attrs) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  };
  const children = [];
  for (const level of [-50, -100]) {
    children.push(make('line', { x1: 0, x2: n, y1: y(level).toFixed(1), y2: y(level).toFixed(1), class: 'sea-grid' }));
  }
  children.push(make('line', { x1: 0, x2: n, y1: y(0).toFixed(1), y2: y(0).toFixed(1), class: 'sea-base' }));
  children.push(make('polyline', {
    points: stops.map(([from], index) => `${index + 0.5},${y(frames[from].deglacial.level_m).toFixed(1)}`).join(' '),
    class: 'sea-line',
  }));
  // The chosen stop, moved by showSeaLevel.
  children.push(make('line', { id: 'sea-now', x1: n - 0.5, x2: n - 0.5, y1: 0, y2: height, class: 'sea-now' }));
  svg.replaceChildren(...children);
  const axis = $('sea-axis');
  if (axis) {
    axis.replaceChildren();
    labelAxis(axis, [0, -50, -100].map((level) => ({ top: y(level) / height * 100, text: `${level} m` })));
  }
}
// The last 800,000 years, glacial cycles that no 5 Myr slice can show: a chart of the
// Pleistocene stack with its own axes, older to the left, present at the right.
function drawPleistocene() {
  const svg = $('pleistocene');
  if (!svg || !seaLevel.pleistocene.length) return;
  const width = 200;
  const height = 50;
  const lowest = -140;
  const highest = 20;
  const oldest = seaLevel.pleistocene[seaLevel.pleistocene.length - 1][0];
  const y = (metres) => (height - 2) - (metres - lowest) / (highest - lowest) * (height - 4);
  const x = (ka) => width - ka / oldest * width;
  const ns = 'http://www.w3.org/2000/svg';
  const make = (tag, attrs) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  };
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  const children = [];
  for (const level of [-50, -100]) children.push(make('line', { x1: 0, x2: width, y1: y(level).toFixed(1), y2: y(level).toFixed(1), class: 'sea-grid' }));
  for (const ka of [600, 400, 200]) children.push(make('line', { x1: x(ka).toFixed(1), x2: x(ka).toFixed(1), y1: 0, y2: height, class: 'sea-grid' }));
  children.push(make('line', { x1: 0, x2: width, y1: y(0).toFixed(1), y2: y(0).toFixed(1), class: 'sea-base' }));
  children.push(make('polyline', { points: seaLevel.pleistocene.map(([ka, metres]) => `${x(ka).toFixed(1)},${y(metres).toFixed(1)}`).join(' '), class: 'sea-line' }));
  svg.replaceChildren(...children);
  const axis = $('pleistocene-axis');
  if (axis) {
    axis.replaceChildren();
    labelAxis(axis, [
      ...[0, -50, -100].map((level) => ({ top: y(level) / height * 100, text: `${level} m` })),
      ...[800, 400, 0].map((ka) => ({ left: x(ka) / width * 100, text: ka === 0 ? L.present : `${ka} ka`,
                                       align: ka === 800 ? 'start' : ka === 0 ? 'end' : 'center' })),
    ]);
  }
}
// Global mean at an age, linear between the published maps; null outside their span.
function meanTemperatureAt(age) {
  for (let index = 0; index + 1 < temperatureCurve.length; index++) {
    const [older, warmOlder] = temperatureCurve[index];
    const [newer, warmNewer] = temperatureCurve[index + 1];
    if (older >= age && age >= newer) {
      return older === newer ? warmOlder : warmOlder + (warmNewer - warmOlder) * (older - age) / (older - newer);
    }
  }
  return null;
}
function showMeanTemperature(place) {
  const out = $('mean-temp');
  if (!out) return;
  let value = null;
  if (!place.mapless) {
    const from = place.from.mean_c;
    const to = place.to.mean_c;
    if (from != null && to != null) value = from + (to - from) * place.blend;
    else if (place.blend === 0 && from != null) value = from;
  }
  let text = value == null
    ? L.meanTemperatureNone
    : fmt(L.meanTemperature, { value: value.toFixed(1), between: place.blend > 0 ? L.meanTemperatureBetween : '' });
  // The colour key: today's global mean as a fixed tick, this stop's mean as a marker,
  // both on the shader's -30..40 C ramp, and the readout says how far from today.
  const legend = $('temp-legend');
  if (legend) {
    const today = frames.find(frame => frame.age === 0 && frame.mean_c != null)?.mean_c ?? null;
    const along = celsius => `${(Math.max(0, Math.min(1, (celsius + 30) / 70)) * 100).toFixed(1)}%`;
    if (today != null) $('temp-today').style.left = along(today);
    $('temp-now').hidden = value == null;
    if (value != null) $('temp-now').style.left = along(value);
    const delta = value != null && today != null ? value - today : null;
    legend.dataset.delta = delta == null ? '' : delta.toFixed(1);
    if (delta != null) text += fmt(L.meanTemperatureDelta, { delta: (delta < 0 ? '−' : '+') + Math.abs(delta).toFixed(1) });
  }
  out.textContent = text;
  stage.dataset.meanTemp = value == null ? '' : value.toFixed(1);
}
// The strip above the slider: one column per stop, coloured by the global mean at that
// stop's age. Same hues as the temperature surface, but over the range global means
// actually take, 5 to 35 C, so an icehouse reads blue and a hothouse red. Grey where no
// map reaches.
function thermalCss(celsius) {
  const t = Math.max(0, Math.min(1, (celsius - 5) / 30));
  const lerp = (a, b, k) => a.map((channel, i) => Math.round(channel + (b[i] - channel) * k));
  const cold = [41, 69, 168], mild = [240, 237, 224], hot = [184, 33, 28];
  const rgb = t < 0.43 ? lerp(cold, mild, t / 0.43) : lerp(mild, hot, (t - 0.43) / 0.57);
  return `rgb(${rgb.join(',')})`;
}
function drawTemperatureStrip() {
  const strip = $('temp-strip');
  if (!strip || !temperatureCurve.length) return;
  strip.width = stops.length;
  strip.height = 1;
  const context = strip.getContext('2d');
  stops.forEach(([, , , age], index) => {
    const mean = meanTemperatureAt(age);
    context.fillStyle = mean == null ? 'rgba(128,128,128,0.35)' : thermalCss(mean);
    context.fillRect(index, 0, 1, 1);
  });
}
// Land plants appear in the Ordovician, about 470 Ma, and forests by the Middle
// Devonian, about 385 Ma. Before that the land is drawn bare; between, the tints blend.
function vegetationAt(age) {
  return THREE.MathUtils.clamp((470 - age) / (470 - 385), 0, 1);
}
function selectFrame(index, manual = false) {
  return selectStop(frameStops[Math.max(0, Math.min(frames.length - 1, index))], manual);
}
function applyMotion(place) {
  const gap = place.blend > 0 ? motions[frames.indexOf(place.from)] ?? [] : [];
  const count = Math.min(gap.length, MAX_MOTIONS);
  for (let index = 0; index < count; index++) {
    const pair = gap[index];
    uniforms.motionPoints.value[index].set(pair.lon, pair.lat, pair.to_lon, pair.to_lat);
    uniforms.motionRadius.value[index] = pair.radius;
  }
  uniforms.motionCount.value = count;
  stage.dataset.motions = String(count);
}
function setMeridian(value) {
  meridian = (((value % 360) + 540) % 360) - 180;
  if (uniforms) uniforms.meridian.value = meridian;
  stage.dataset.meridian = meridian.toFixed(1);
  // Rebuild the drawn layers at most once a frame, however fast a drag reports.
  if (flatRefresh || !earth) return;
  flatRefresh = requestAnimationFrame(() => {
    flatRefresh = 0;
    earth.remove(grid);
    grid.traverse((node) => node.geometry?.dispose());
    grid = createGrid();
    earth.add(grid);
    if (plateLayer?.visible && lastPlates) drawPlates(lastPlates.age, lastPlates.loaded);
    if (coastlineLayer?.visible && lastCoastline) drawCoastline(lastCoastline.entry, lastCoastline.rings);
    if (lastPlace && nameLayer.visible) showNames(lastPlace, true);
  });
}
function setProjection(name, refresh = true) {
  if (!PROJECTIONS[name] || name === projection) return;
  mantleOverlay?.onProjection(name);
  projection = name;
  const globe = projection === 'globe';
  uniforms.projection.value = PROJECTIONS[projection].code;
  surfaceMesh.geometry.dispose();
  reliefDetailed = false;
  uniforms.surfaceLineLift.value = .00085;
  surfaceMesh.geometry = globe
    ? new THREE.SphereGeometry(1, 96, 64)
    : new THREE.PlaneGeometry(...PROJECTIONS[projection].sheet, 1, 1);
  earth.remove(grid);
  grid.traverse((node) => node.geometry?.dispose());
  grid = createGrid();
  earth.add(grid);
  controls.enableRotate = globe;
  controls.enablePan = !globe;
  // A flat sheet zooms toward the pointer, so a close look lands where the reader points.
  controls.zoomToCursor = !globe;
  // One switch for turning: the camera orbits the globe, while a sheet turns its centre
  // meridian under a fixed camera.
  controls.autoRotate = spinning && globe;
  $('rotate').disabled = false;
  $('rotate').setAttribute('aria-pressed', String(spinning));
  $('gesture').textContent = globe
    ? L.gestureGlobe
    : L.gestureSheet;
  stage.dataset.projection = projection;
  nameGroupKey = '';
  plateAge = null;
  fitCamera();
  resetView();
  if (refresh) selectStop(stop);
}
// Shared by both shaders: the vertex shader lifts the ground by the same height, carried
// by the same travel field, that the fragment shader colours.
//
// Where the ground under this texel came from and is going to, in degrees. Each
// control point pulls its own neighbourhood by the distance that landmass
// travels, with a Gaussian falling off over the piece's own angular size, so
// continents move as bodies and the open ocean between them stays put.
const TRAVEL_GLSL = `
      vec2 travel(vec2 lonlat) {
        vec2 sum = vec2(0.0);
        float weight = 0.0;
        for (int index = 0; index < ${MAX_MOTIONS}; index++) {
          if (index >= motionCount) break;
          vec4 point = motionPoints[index];
          float eastward = mod(lonlat.x - point.x + 540.0, 360.0) - 180.0;
          float northward = lonlat.y - point.y;
          float shrink = cos(radians(0.5 * (lonlat.y + point.y)));
          float span = sqrt(eastward * eastward * shrink * shrink + northward * northward);
          float radius = max(motionRadius[index], 1.0);
          float pull = exp(-0.5 * span * span / (radius * radius));
          sum += pull * vec2(mod(point.z - point.x + 540.0, 360.0) - 180.0, point.w - point.y);
          weight += pull;
        }
        if (weight <= 0.0) return vec2(0.0);
        return sum / weight * smoothstep(0.05, 0.45, weight);
      }`;
// Height in metres at a pair of field coordinates, one per bound texture. Green holds
// the high byte and blue four more bits of a 12-bit value over -9000..6000 m; an 8-bit
// texture has blue at zero and decodes 9 m low, below its own step.
const METRES_GLSL = `
      float metresAt(vec2 uvA, vec2 uvB) {
        vec4 a = texture2D(surfaceA, uvA);
        vec4 b = texture2D(surfaceB, uvB);
        float here = (a.g * 16.0 + a.b) * 255.0 / 4095.0;
        float there = (b.g * 16.0 + b.b) * 255.0 / 4095.0;
        return mix(here, there, blend) * 15000.0 - 9000.0;
      }`;
// The lift the 3D terrain gives a point of the unit sphere: its height above the
// displayed sea level, through the travel field, exaggerated and faded with the zoom.
// Lines drawn on the surface use it too, so they ride the mountains instead of being
// buried under them. Longitude and latitude come back from the point itself, the
// inverse of onSphere(), so a line needs no uv of its own.
const LIFT_GLSL = `
      float terrainLift(vec3 point) {
        if (relief <= 0.0 || projection != 0 || mode < 2 || blank > 0.5) return 1.0;
        vec3 unit = normalize(point);
        float theta = acos(clamp(unit.y, -1.0, 1.0));
        float phi = atan(unit.z, -unit.x);
        vec2 uv = vec2(fract(phi / (2.0 * PI)), 1.0 - theta / PI);
        vec2 shift = travel(vec2((uv.x - 0.5) * 360.0, (uv.y - 0.5) * 180.0));
        vec2 offset = vec2(shift.x / 360.0, shift.y / 180.0);
        float metres = metresAt(uv - blend * offset, uv + (1.0 - blend) * offset) - seaLevel;
        return 1.0 + relief * reliefScale * max(metres, 0.0) / EARTH_RADIUS;
      }`;
const LIFT_UNIFORMS_GLSL = `
      uniform sampler2D surfaceA;
      uniform sampler2D surfaceB;
      uniform float blend;
      uniform int mode;
      uniform float blank;
      uniform int projection;
      uniform float seaLevel;
      uniform float relief;
      uniform float reliefScale;
      uniform int motionCount;
      uniform vec4 motionPoints[${MAX_MOTIONS}];
      uniform float motionRadius[${MAX_MOTIONS}];
      const float EARTH_RADIUS = 6371000.0;
      const float PI = 3.141592653589793;`;
// A line on the surface: the same lift as the ground beneath it, in one flat colour.
// Shares the surface's uniform objects, so it follows every change without bookkeeping.
function terrainLineMaterial(colour, opacity) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, colour: { value: new THREE.Color(colour) }, opacity: { value: opacity } },
    transparent: true,
    vertexShader: `
      ${LIFT_UNIFORMS_GLSL}
      uniform float surfaceLineLift;
      varying vec3 vCutPosition;
      ${TRAVEL_GLSL}
      ${METRES_GLSL}
      ${LIFT_GLSL}
      void main() {
        vCutPosition = position;
        vec3 attached = projection == 0 ? normalize(position) * (terrainLift(position) + surfaceLineLift) : position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(attached, 1.0);
      }`,
    fragmentShader: `
      ${CUT_UNIFORMS}
      uniform float mantleSurfaceOpacity;
      uniform vec3 mantleCamera;
      uniform vec3 colour;
      uniform float opacity;
      void main() {
        ${CUT_SURFACE}
        if ((mantleCutaway > 0.5 || mantleSurfaceOpacity < 1.0) && dot(vCutPosition, mantleCamera - vCutPosition) < 0.0) discard;
        gl_FragColor = vec4(colour, opacity * mantleSurfaceOpacity);
        #include <colorspace_fragment>
      }`,
  });
}
function globeMaterial() {
  const linear = (rgb) => new THREE.Color().setRGB(
    rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace);
  uniforms = {
    mantleCutaway: { value: 0 }, mantleCutCentre: { value: new THREE.Vector3(1,0,0) },
    mantleSurfaceOpacity: { value: 1 }, surfaceLineLift: { value: .00085 },
    mantleCutCos: { value: 1 }, mantleCamera: { value: new THREE.Vector3() },
    surfaceA: { value: null }, surfaceB: { value: null },
    tempA: { value: null }, tempB: { value: null },
    iceA: { value: null }, iceB: { value: null },
    // Which of the two bound ice masks exist; a missing one counts as no ice.
    iceWeight: { value: new THREE.Vector2(0, 0) },
    // Where to cut each bound mask's distance field (0.5 is the drawn edge), decided on
    // the page from the sea-level offset; and a drawn lowstand to morph toward, with how
    // far to go, for a side that has one (the present's last glacial maximum).
    iceCut: { value: new THREE.Vector2(0.5, 0.5) },
    iceLow0: { value: null },
    iceLow1: { value: null },
    iceLowT: { value: 0 },
    iceLowMix: { value: new THREE.Vector2(0, 0) },
    riverA: { value: null }, riverB: { value: null },
    // Which of the two bound river fields exist; a missing one counts as no rivers.
    riverWeight: { value: new THREE.Vector2(0, 0) },
    // The lowstand fields and how far each side stands toward its own.
    riverLow0: { value: null }, riverLow1: { value: null },
    riverLowT: { value: new THREE.Vector2(0, 0) },
    blend: { value: 0 }, mode: { value: 0 },
    // Shaded relief: texel spacing of the bound fields, and how much the slopes are
    // exaggerated before lighting. 0 switches the shading off.
    texel: { value: new THREE.Vector2(1 / 2048, 1 / 1024) },
    exaggeration: { value: 1 },
    // Metres to move sea level from the slice's datum; 0 keeps the distance-field
    // coastline, anything else cuts the height channel instead.
    seaLevel: { value: 0 },
    // 1 draws land in vegetated tints, 0 in bare rock. See vegetationAt().
    vegetation: { value: 1 },
    land: { value: linear(LAND_COLOUR) }, ocean: { value: linear(OCEAN_COLOUR) },
    projection: { value: 0 },
    meridian: { value: 0 },
    blank: { value: 0 },
    // 3D terrain: 0 flat, 1 fully lifted; set from the zoom by updateRelief().
    relief: { value: 0 },
    reliefScale: { value: RELIEF_SCALE },
    motionCount: { value: 0 },
    motionPoints: { value: Array.from({ length: MAX_MOTIONS }, () => new THREE.Vector4()) },
    motionRadius: { value: new Float32Array(MAX_MOTIONS) },
  };
  return new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      ${LIFT_UNIFORMS_GLSL}
      varying vec3 vCutPosition;
      varying vec2 vUv;
      varying vec3 vGlobeNormal;
      ${TRAVEL_GLSL}
      ${METRES_GLSL}
      ${LIFT_GLSL}
      void main() {
        vUv = uv;
        // Close in on the elevation series the ground rises by its own height, exaggerated
        // and faded in with the zoom, carried by the same motion as its colour. The sea
        // stays flat at its level, so a coastline is where the land leaves the water.
        vGlobeNormal = normalize(normalMatrix * normal);
        vCutPosition = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position * terrainLift(position), 1.0);
      }`,
    fragmentShader: `
      ${CUT_UNIFORMS}
      uniform float mantleSurfaceOpacity;
      uniform sampler2D surfaceA;
      uniform sampler2D surfaceB;
      uniform sampler2D tempA;
      uniform sampler2D tempB;
      uniform sampler2D iceA;
      uniform sampler2D iceB;
      uniform vec2 iceWeight;
      uniform vec2 iceCut;
      uniform sampler2D iceLow0;
      uniform sampler2D iceLow1;
      uniform float iceLowT;
      uniform vec2 iceLowMix;
      uniform sampler2D riverA;
      uniform sampler2D riverB;
      uniform vec2 riverWeight;
      uniform sampler2D riverLow0;
      uniform sampler2D riverLow1;
      uniform vec2 riverLowT;
      // The river field's cut: drained area above 10,000 km2, a quarter of its 10^3..10^7 span.
      const float RIVER_CUT = 0.25;
      uniform float blend;
      uniform int mode;
      uniform float blank;
      uniform vec2 texel;
      uniform float exaggeration;
      uniform float vegetation;
      uniform float seaLevel;
      const float EARTH_RADIUS = 6371000.0;
      uniform vec3 land;
      uniform vec3 ocean;
      const float PI = 3.141592653589793;
      uniform int projection;
      uniform float meridian;
      uniform int motionCount;
      uniform vec4 motionPoints[${MAX_MOTIONS}];
      uniform float motionRadius[${MAX_MOTIONS}];
      varying vec2 vUv;
      varying vec3 vGlobeNormal;

      ${TRAVEL_GLSL}
      vec3 decode(vec3 colour) {
        return mix(pow((colour + 0.055) / 1.055, vec3(2.4)), colour / 12.92,
                   step(colour, vec3(0.04045)));
      }
      // Height and depth as colour, the usual hypsometric convention: shallow to deep
      // blue under water, green through tan to white above it. Which side of the coast
      // a texel is on comes from the distance field, not from the height alone. Land
      // plants are Ordovician and forests Devonian, so before that the land is drawn in
      // bare rock tones rather than green; vegetation blends the two ramps.
      vec3 hypsometric(float metres, float landness) {
        float depth = clamp(-metres / 6000.0, 0.0, 1.0);
        vec3 sea = mix(decode(vec3(0.53, 0.75, 0.90)), decode(vec3(0.05, 0.14, 0.38)), depth);
        float rise = clamp(metres / 4000.0, 0.0, 1.0);
        vec3 low = mix(decode(vec3(0.58, 0.49, 0.37)), decode(vec3(0.27, 0.53, 0.27)), vegetation);
        vec3 mid = mix(decode(vec3(0.70, 0.60, 0.47)), decode(vec3(0.78, 0.70, 0.45)), vegetation);
        // Grey at the top, not white: white is the ice layer's, and Tibet is not ice.
        vec3 high = decode(vec3(0.80, 0.77, 0.72));
        vec3 ground = rise < 0.35 ? mix(low, mid, rise / 0.35) : mix(mid, high, (rise - 0.35) / 0.65);
        return mix(sea, ground, landness);
      }
      // Surface air temperature as colour, blue at -30 C through pale at 0 to red at
      // 40 C, the range the maps actually span. Grey holds it over -60..60 C.
      vec3 thermal(float celsius) {
        float t = clamp((celsius + 30.0) / 70.0, 0.0, 1.0);
        vec3 cold = decode(vec3(0.16, 0.27, 0.66));
        vec3 mild = decode(vec3(0.94, 0.93, 0.88));
        vec3 hot = decode(vec3(0.72, 0.13, 0.11));
        return t < 0.43 ? mix(cold, mild, t / 0.43) : mix(mild, hot, (t - 0.43) / 0.57);
      }
      ${METRES_GLSL}
      // Shaded relief from the height gradient, lit from the upper left. Texel spacing
      // is converted to metres so a slope is a true slope before exaggeration.
      float shade(vec2 uvA, vec2 uvB, float latitude) {
        if (exaggeration <= 0.0) return 1.0;
        vec2 du = vec2(texel.x, 0.0);
        vec2 dv = vec2(0.0, texel.y);
        float east = metresAt(uvA + du, uvB + du) - metresAt(uvA - du, uvB - du);
        float north = metresAt(uvA + dv, uvB + dv) - metresAt(uvA - dv, uvB - dv);
        float spanEast = 2.0 * texel.x * 2.0 * PI * EARTH_RADIUS * max(cos(radians(latitude)), 0.05);
        float spanNorth = 2.0 * texel.y * PI * EARTH_RADIUS;
        vec3 normal = normalize(vec3(-east / spanEast * exaggeration, -north / spanNorth * exaggeration, 1.0));
        vec3 light = normalize(vec3(-0.6, 0.6, 0.55));
        return 0.45 + 0.55 * clamp(dot(normal, light), 0.0, 1.0);
      }
      // Where on the equirectangular fields this fragment looks. On the sphere the
      // geometry already carries that; on a sheet the projection has to be undone,
      // which is also what decides whether a fragment is on the map at all.
      bool locate(out vec2 found) {
        if (projection == 0) { found = vUv; return true; }
        // A flat sheet turns about the pole: sample the fields at the longitude the sheet's
        // centre meridian puts under this fragment. The textures wrap in longitude.
        if (projection == 1) { found = vec2(fract(vUv.x + meridian / 360.0), vUv.y); return true; }
        float x = vUv.x * 2.0 - 1.0;
        float y = vUv.y * 2.0 - 1.0;
        if (x * x + y * y > 1.0) return false;
        float theta = asin(clamp(y, -1.0, 1.0));
        float latitude = asin(clamp((2.0 * theta + sin(2.0 * theta)) / PI, -1.0, 1.0));
        float longitude = PI * x / max(cos(theta), 1e-6);
        if (abs(longitude) > PI) return false;
        found = vec2(fract(longitude / (2.0 * PI) + 0.5 + meridian / 360.0), latitude / PI + 0.5);
        return true;
      }
      void main() {
        ${CUT_SURFACE}
        vec2 surfaceUv;
        if (!locate(surfaceUv)) discard;
        vec3 colour;
        if (blank > 0.5) {
          // Older than any published map: bare water, so the reconstruction drawn over
          // it is plainly the only claim being made.
          colour = ocean;
        } else if (mode >= 1) {
          // Both textures hold a signed distance to the coastline. Mixing the distances
          // and cutting at the midpoint moves the coastline; mixing pictures would only
          // dissolve one into the other. Sampling each side through the travel field
          // first carries each landmass along its own path, so the coastline morphs
          // around a continent that is moving rather than melting in place.
          vec2 shift = travel(vec2((surfaceUv.x - 0.5) * 360.0, (surfaceUv.y - 0.5) * 180.0));
          vec2 offset = vec2(shift.x / 360.0, shift.y / 180.0);
          vec2 uvA = surfaceUv - blend * offset;
          vec2 uvB = surfaceUv + (1.0 - blend) * offset;
          float here = texture2D(surfaceA, uvA).r;
          float there = texture2D(surfaceB, uvB).r;
          float distance = mix(here, there, blend) - 0.5;
          float edge = fwidth(distance) + 0.0012;
          float landness = smoothstep(-edge, edge, distance);
          float metres = metresAt(uvA, uvB) - seaLevel;
          if (abs(seaLevel) > 0.0) {
            // A moved sea level has no distance field, so the coast is cut from the
            // height itself, antialiased over the height's own screen-space change.
            float width = fwidth(metres) * 0.75 + 4.0;
            landness = smoothstep(-width, width, metres);
            distance = metres / 400.0;
          }
          if (mode == 3) {
            float celsius = mix(texture2D(tempA, uvA).r, texture2D(tempB, uvB).r, blend) * 120.0 - 60.0;
            // The coastline as a dark line, so the continents stay readable under colour.
            float coast = 1.0 - smoothstep(0.0, 0.008, abs(distance));
            colour = thermal(celsius) * (1.0 - 0.55 * coast);
          } else if (mode == 2) {
            float latitude = (surfaceUv.y - 0.5) * 180.0;
            colour = hypsometric(metres, landness) * shade(uvA, uvB, latitude);
          } else {
            colour = mix(ocean, land, landness);
          }
          // Rivers over the surface, under the ice. Each field is a cone the size of its
          // river, so the cut draws a line as wide as the river is large; the two grids'
          // fields mix like the coastline's distance, and a missing side weighs nothing.
          // A raised sea covers them; a lowered one mixes in the field routed with the sea at
          // the slider's lowest level, so the rivers run on across the exposed shelf.
          if ((riverWeight.x + riverWeight.y) > 0.0) {
            float flowA = mix(texture2D(riverA, uvA).r, texture2D(riverLow0, uvA).r, riverLowT.x) * riverWeight.x;
            float flowB = mix(texture2D(riverB, uvB).r, texture2D(riverLow1, uvB).r, riverLowT.y) * riverWeight.y;
            float flow = mix(flowA, flowB, blend);
            float softFlow = fwidth(flow) + 0.02;
            float river = smoothstep(RIVER_CUT - softFlow, RIVER_CUT + softFlow, flow) * landness;
            colour = mix(colour, decode(vec3(0.16, 0.42, 0.78)), 0.85 * river);
          }
        } else {
          colour = mix(decode(texture2D(surfaceA, surfaceUv).rgb),
                       decode(texture2D(surfaceB, surfaceUv).rgb), blend);
        }
        // Ice over whatever is beneath: grounded ice near-opaque white, floating shelf
        // ice paler, since a shelf rests on ocean the grid still shows as ocean.
        if (blank < 0.5 && mode >= 1 && (iceWeight.x + iceWeight.y) > 0.0) {
          vec2 shiftIce = travel(vec2((surfaceUv.x - 0.5) * 360.0, (surfaceUv.y - 0.5) * 180.0));
          vec2 offsetIce = vec2(shiftIce.x / 360.0, shiftIce.y / 180.0);
          vec2 uvIceA = surfaceUv - blend * offsetIce;
          vec2 uvIceB = surfaceUv + (1.0 - blend) * offsetIce;
          vec2 a = texture2D(iceA, uvIceA).rg;
          vec2 b = texture2D(iceB, uvIceB).rg;
          // A side with dated lowstand slices shows the two bracketing the sea level,
          // mixed; the intervals are a thousand years, so the linear mix stays close.
          a.x = mix(a.x, mix(texture2D(iceLow0, uvIceA).r, texture2D(iceLow1, uvIceA).r, iceLowT), iceLowMix.x);
          b.x = mix(b.x, mix(texture2D(iceLow0, uvIceB).r, texture2D(iceLow1, uvIceB).r, iceLowT), iceLowMix.y);
          vec2 ice = mix(a * iceWeight.x, b * iceWeight.y, blend);
          // The edge sits where the distance field crosses 0.5; the page moves the cut so
          // the enclosed area follows the ice volume the offset stands for. A missing mask
          // on one side mixes toward zero, so a sheet recedes from its edge across that gap.
          float cut = mix(iceCut.x, iceCut.y, blend);
          float soft = fwidth(ice.x) + 0.01;
          float grounded = smoothstep(cut - soft, cut + soft, ice.x);
          float shelf = smoothstep(0.3, 0.7, ice.y) * (1.0 - grounded);
          colour = mix(colour, decode(vec3(0.96, 0.97, 0.98)), 0.9 * grounded);
          colour = mix(colour, decode(vec3(0.85, 0.92, 0.97)), 0.65 * shelf);
        }
        // Limb shading gives the sphere volume without reading height from colour. A
        // flat sheet has no limb, so it is left alone.
        if (projection == 0) colour *= 0.58 + 0.42 * pow(abs(vGlobeNormal.z), 0.45);
        gl_FragColor = vec4(colour, mantleSurfaceOpacity);
        #include <colorspace_fragment>
      }`,
  });
}
const FLAT_DISTANCE = 2.6;
// Closer than about a third of the default height, the elevation series stands up in 3D:
// the ground rises by its height 25 times over (the relief note in the inspector says
// so), and the drawn view tilts toward the horizon so the relief can be seen at all from
// a camera that otherwise looks straight down. Both fade in together and are fully on by
// an eighth of the default height. The sphere gets finer only while lifted.
// At 10 the Tibetan plateau and the Andes barely rose above the horizon; 25 reads as relief.
const RELIEF_SCALE = 25;
const RELIEF_TILT = Math.PI * 50 / 180;
// The reader can tilt further, to 80 degrees, and turn the tilt to look along any
// heading; a middle (wheel) drag or a shift drag does both. Reset returns to the default.
const TILT_MAX = Math.PI * 80 / 180;
let tiltAngle = RELIEF_TILT;
let tiltHeading = 0;
function setTilt(angle, heading) {
  tiltAngle = THREE.MathUtils.clamp(angle, 0, TILT_MAX);
  tiltHeading = heading;
  stage.dataset.tilt = THREE.MathUtils.radToDeg(tiltAngle).toFixed(0);
  stage.dataset.heading = ((THREE.MathUtils.radToDeg(tiltHeading) % 360) + 360).toFixed(0).replace(/^360$/, '0');
}
const RELIEF_DETAIL = [512, 256];
let reliefWanted = true;
let reliefDetailed = false;
function updateRelief(factor) {
  const able = reliefWanted && projection === 'globe' && uniforms.mode.value >= 2 && uniforms.blank.value < 0.5;
  const strength = able ? 1 - THREE.MathUtils.smoothstep(factor, 0.12, 0.3) : 0;
  const was = uniforms.relief.value;
  const detailed = projection === 'globe' && factor < .3;
  if (strength === was && detailed === reliefDetailed) return;
  uniforms.relief.value = strength;
  stage.dataset.relief = strength.toFixed(2);
  if (detailed !== reliefDetailed) {
    reliefDetailed = detailed;
    surfaceMesh.geometry.dispose();
    surfaceMesh.geometry = new THREE.SphereGeometry(1, ...(reliefDetailed ? RELIEF_DETAIL : [96, 64]));
  }
  const [segments, rings] = reliefDetailed ? RELIEF_DETAIL : [96,64];
  uniforms.surfaceLineLift.value = 1 - Math.cos(Math.PI/segments)*Math.cos(Math.PI/(2*rings)) + .000002;
  stage.dataset.lineLift = uniforms.surfaceLineLift.value.toFixed(7);
  if ((was > 0) !== (strength > 0)) {
    if ($('relief-note')) $('relief-note').hidden = strength === 0;
    // Tilting is a gesture of its own while the terrain stands, so the hint says so.
    $('gesture').textContent = strength > 0 ? L.gestureTerrain : L.gestureGlobe;
  }
}
// The controls move `camera`; what is drawn is that view turned about the ground beneath
// it by the relief's tilt, so the tilt never feeds back into the controls.
let viewCamera = null;
const tiltAxis = new THREE.Vector3();
const tiltTurn = new THREE.Quaternion();
function tiltedView() {
  const tilt = tiltAngle * uniforms.relief.value;
  if (tilt <= 0 || projection !== 'globe') return camera;
  viewCamera ??= new THREE.PerspectiveCamera();
  viewCamera.copy(camera);
  const ground = camera.position.clone().normalize();
  // The tilt axis is the screen's horizontal, turned about the ground by the heading.
  tiltAxis.set(1, 0, 0).applyQuaternion(camera.quaternion).applyAxisAngle(ground, -tiltHeading);
  tiltTurn.setFromAxisAngle(tiltAxis, tilt);
  viewCamera.position.sub(ground).applyQuaternion(tiltTurn).add(ground);
  viewCamera.quaternion.premultiply(tiltTurn);
  viewCamera.updateMatrixWorld();
  return viewCamera;
}
// How close the view is, 1 at the default distance and smaller in: the height above the
// sphere against the default 2.45, or the distance to a sheet against its default.
function zoomFactor() {
  const distance = camera.position.distanceTo(controls.target);
  return projection === 'globe'
    ? THREE.MathUtils.clamp((distance - 1) / 2.45, 0.02, 1)
    : Math.min(1, distance / FLAT_DISTANCE);
}
// Close in, a drag or a wheel step should move the surface about as far as it does from
// the default distance, and names keep their size on screen instead of growing with it.
let nameFactor = 1;
function followZoom() {
  const factor = zoomFactor();
  controls.rotateSpeed = Math.max(0.05, factor);
  controls.zoomSpeed = projection === 'globe' ? Math.max(0.1, Math.sqrt(factor)) : 1;
  updateRelief(factor);
  if (Math.abs(factor - nameFactor) < 0.005) return;
  nameFactor = factor;
  stage.dataset.zoom = factor.toFixed(2);
  for (const sprite of nameLayer.children) {
    const [width, height] = sprite.nameSize;
    sprite.scale.set(width * factor, height * factor, 1);
  }
}
const NAME_LIFT = 0.015;
// Longitude as it sits on a flat sheet turned to `meridian`, in [-180, 180).
function sheetLongitude(longitude) {
  return (((longitude - meridian) % 360) + 540) % 360 - 180;
}
function onSheet(longitude, latitude, lift = 0) {
  const [x, y] = PROJECTIONS[projection].place(sheetLongitude(longitude), latitude);
  return new THREE.Vector3(x, y, lift);
}
function pointAt(longitude, latitude, lift) {
  return projection === 'globe'
    ? onSphere(longitude, latitude, 1 + lift)
    : onSheet(longitude, latitude, lift);
}
function onSphere(longitude, latitude, radius = 1) {
  const theta = THREE.MathUtils.degToRad(90 - latitude);
  const phi = (longitude + 180) / 360 * Math.PI * 2 + TEXTURE_MERIDIAN;
  return new THREE.Vector3(-Math.cos(phi) * Math.sin(theta), Math.cos(theta),
                           Math.sin(phi) * Math.sin(theta)).multiplyScalar(radius);
}
function nameSprite(text) {
  const scale = 3;
  const font = `600 ${16 * scale}px system-ui, "Noto Sans KR", sans-serif`;
  const canvas = document.createElement('canvas');
  let context = canvas.getContext('2d');
  context.font = font;
  const width = Math.ceil(context.measureText(text).width) + 18 * scale;
  canvas.width = width;
  canvas.height = 26 * scale;
  context = canvas.getContext('2d');
  context.font = font;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.lineWidth = 4 * scale;
  context.strokeStyle = 'rgba(11,26,36,0.85)';
  context.strokeText(text, canvas.width / 2, canvas.height / 2);
  context.fillStyle = '#fdf6e3';
  context.fillText(text, canvas.width / 2, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial(
    { map: texture, transparent: true, depthTest: false, depthWrite: false }));
  const height = 0.075;
  // Kept off userData, which the name placement replaces wholesale.
  sprite.nameSize = [height * canvas.width / canvas.height, height];
  sprite.scale.set(sprite.nameSize[0] * nameFactor, height * nameFactor, 1);
  sprite.renderOrder = 2;
  return sprite;
}
function clearNames() {
  for (const sprite of nameLayer.children) {
    sprite.material.map.dispose();
    sprite.material.dispose();
  }
  nameLayer.clear();
  nameGroupKey = '';
  stage.dataset.names = '0';
}
function showNames(place, visible) {
  nameLayer.visible = visible;
  if (!visible) {
    clearNames();
    return;
  }
  const key = `${place.from.id}|${place.to.id}`;
  if (key !== nameGroupKey) {
    clearNames();
    nameGroupKey = key;
    const byName = new Map((place.to.names || []).map((entry) => [entry.name, entry]));
    for (const from of place.from.names || []) {
      const sprite = nameSprite(from.name);
      sprite.userData = { from, to: byName.get(from.name) || null, arriving: false };
      nameLayer.add(sprite);
      byName.delete(from.name);
    }
    for (const to of byName.values()) {
      const sprite = nameSprite(to.name);
      sprite.userData = { from: null, to, arriving: true };
      nameLayer.add(sprite);
    }
  }
  // A name on both sides travels between its two positions. One that exists on only
  // one side fades, because the piece it names has no counterpart to move to.
  for (const sprite of nameLayer.children) {
    const { from, to } = sprite.userData;
    if (from && to) {
      sprite.position.copy(between(from, to, place.blend));
      sprite.userData.fade = 1;
    } else if (from) {
      sprite.position.copy(labelPoint(from.lon, from.lat));
      sprite.userData.fade = 1 - place.blend;
    } else {
      sprite.position.copy(labelPoint(to.lon, to.lat));
      sprite.userData.fade = place.blend;
    }
  }
  stage.dataset.names = String(
    nameLayer.children.filter((sprite) => sprite.userData.fade > 0.001).length);
}
function labelPoint(longitude, latitude) {
  return pointAt(longitude, latitude, NAME_LIFT);
}
function between(from, to, blend) {
  const start = labelPoint(from.lon, from.lat);
  const finish = labelPoint(to.lon, to.lat);
  if (projection !== 'globe') {
    // Across the sheet's seam a straight slide would sweep over the whole map; jump instead.
    if (Math.abs(finish.x - start.x) > 1) return blend < 0.5 ? start : finish;
    return start.lerp(finish, blend);
  }
  // On the sphere a straight line cuts through it, so come back out to the surface.
  return start.lerp(finish, blend).normalize().multiplyScalar(1 + NAME_LIFT);
}
function updateNameVisibility() {
  if (!nameLayer.visible) return;
  const flat = projection !== 'globe';
  const toCamera = camera.position.clone().normalize();
  const position = new THREE.Vector3();
  for (const sprite of nameLayer.children) {
    let facing = 1;
    if (!flat) {
      sprite.getWorldPosition(position);
      facing = THREE.MathUtils.clamp((position.normalize().dot(toCamera) - 0.12) / 0.18, 0, 1);
    }
    sprite.material.opacity = facing * (sprite.userData.fade ?? 1) * uniforms.mantleSurfaceOpacity.value;
    sprite.visible = sprite.material.opacity > 0.02 && !mantleOverlay?.cutsPoint(sprite.position);
  }
}
function plateEntry() {
  return plates.find((model) => model.id === plateChoice) ?? null;
}
function showPlates() {
  return Boolean(plateEntry());
}
function locked() {
  const entry = plateEntry();
  return Boolean(entry && entry.locked);
}
async function loadPlateModel() {
  const entry = plateEntry();
  if (!entry || entry.locked) return null;
  if (!plateData.has(entry.id)) {
    plateData.set(entry.id, (async () => {
      const [rotations, shapes] = await Promise.all([
        fetch(entry.layers.rotations).then((response) => response.json()),
        fetch(entry.layers.continents).then((response) => response.json()),
      ]);
      return { model: new RotationModel(rotations), shapes: shapes.features };
    })());
    plateData.get(entry.id).catch(() => plateData.delete(entry.id));
  }
  return plateData.get(entry.id);
}
function drawPlates(age, loaded) {
  const { model: plateModel, shapes: plateShapes } = loaded;
  // Rebuilt per stop rather than animated: the geometry is a few thousand segments and
  // the rotation is exact at whatever age the reader is on, not an eased approximation.
  const flat = projection !== 'globe';
  const lift = flat ? 0.004 : 0.006;
  const points = [];
  let visible = 0;
  for (const feature of plateShapes) {
    if (age > feature.from + 1e-9 || age < feature.to - 1e-9) continue;
    const rotation = plateModel.rotation(feature.pid, age);
    if (rotation === null) continue;
    visible += 1;
    for (const ring of feature.rings) {
      let previous = null;
      let previousLongitude = 0;
      for (let index = 0; index < ring.length; index += 2) {
        const [longitude, latitude] = turn(rotation, ring[index], ring[index + 1]);
        const here = pointAt(longitude, latitude, lift);
        // On a sheet a ring that crosses the antimeridian would draw a line straight
        // back across the map, so the run is broken there instead.
        const jumped = flat && previous && Math.abs(sheetLongitude(longitude) - sheetLongitude(previousLongitude)) > 180;
        if (previous && !jumped) points.push(previous, here);
        previous = here;
        previousLongitude = longitude;
      }
    }
  }
  const geometry = new THREE.BufferGeometry().setFromPoints(flat ? points : densifySegments(points));
  if (plateLayer) {
    plateLayer.geometry.dispose();
    plateLayer.geometry = geometry;
  } else {
    plateLayer = new THREE.LineSegments(geometry, terrainLineMaterial(PLATE_COLOUR, 0.85));
    plateLayer.renderOrder = 1;
    earth.add(plateLayer);
  }
  plateLayer.visible = true;
  plateAge = age;
  lastPlates = { age, loaded };
  stage.dataset.plates = String(visible);
}
function clearPlates() {
  if ($('plate-reach')) $('plate-reach').hidden = true;
  for (const id of ['plate-frame', 'plate-cite', 'plate-note-model']) {
    if ($(id)) $(id).textContent = '';
  }
  if (plateLayer) plateLayer.visible = false;
  plateAge = null;
  stage.dataset.plates = '0';
}
async function updatePlates(place, ticket) {
  if ($('plate-unlock')) $('plate-unlock').hidden = !locked();
  if (!showPlates() || locked()) {
    clearPlates();
    return;
  }
  const loaded = await loadPlateModel();
  if (ticket !== request || !loaded) return;
  drawPlates(Number(place.age.toFixed(3)), loaded);
  const entry = plateEntry();
  if ($('plate-reach')) {
    // An empty globe here means the model stops short of this age, not that anything
    // failed. Name the models that do reach it.
    const short = place.age > entry.covers[1] + 1e-9;
    const deeper = plates.filter((model) => model.covers[1] >= place.age - 1e-9)
                         .map((model) => model.title);
    $('plate-reach').hidden = !short;
    $('plate-reach').textContent = short
      ? (fmt(L.modelReach, { title: entry.title, reach: entry.covers[1] })
         + (deeper.length ? fmt(L.modelsDeeper, { models: deeper.join(', ') }) : L.noModelDeeper))
      : '';
  }
  if ($('plate-cite')) {
    $('plate-cite').textContent = `${entry.citation} · ${entry.license}`;
  }
  if ($('plate-note-model')) $('plate-note-model').textContent = entry.note ?? '';
  if ($('plate-frame')) {
    $('plate-frame').textContent = fmt(L.modelFrame, { title: entry.title, frame: entry.frame, reach: entry.covers[1] });
  }
}
function coastlineEntry(age) {
  if (!coastlines) return null;
  let best = null;
  for (const entry of coastlines.ages) {
    if (!best || Math.abs(entry.age - age) < Math.abs(best.age - age)) best = entry;
  }
  return best && Math.abs(best.age - age) <= COASTLINE_REACH_MA + 1e-9 ? best : null;
}
function loadCoastline(entry) {
  if (!coastlineData.has(entry.age)) {
    const loading = fetch(entry.url).then((response) => {
      if (!response.ok) throw new Error(`Coastlines unavailable: ${entry.url}`);
      return response.json();
    });
    coastlineData.set(entry.age, loading);
    loading.catch(() => coastlineData.delete(entry.age));
  }
  return coastlineData.get(entry.age);
}
function drawCoastline(entry, rings, key = `${entry.age}|${projection}`) {
  const flat = projection !== 'globe';
  const lift = flat ? 0.005 : 0.007;
  const points = [];
  for (const ring of rings) {
    let previous = null;
    let previousLongitude = 0;
    for (let index = 0; index < ring.length; index += 2) {
      const longitude = ring[index];
      const here = pointAt(longitude, ring[index + 1], lift);
      const jumped = flat && previous && Math.abs(sheetLongitude(longitude) - sheetLongitude(previousLongitude)) > 180;
      if (previous && !jumped) points.push(previous, here);
      previous = here;
      previousLongitude = longitude;
    }
  }
  const geometry = new THREE.BufferGeometry().setFromPoints(flat ? points : densifySegments(points));
  if (coastlineLayer) {
    coastlineLayer.geometry.dispose();
    coastlineLayer.geometry = geometry;
  } else {
    coastlineLayer = new THREE.LineSegments(geometry, terrainLineMaterial(COASTLINE_COLOUR, 1));
    coastlineLayer.renderOrder = 1;
    earth.add(coastlineLayer);
  }
  coastlineKey = key;
  lastCoastline = { entry, rings };
  stage.dataset.coastlines = String(rings.length);
  stage.dataset.coastlineAge = String(entry.age);
}
function hideCoastline() {
  if (coastlineLayer) coastlineLayer.visible = false;
  stage.dataset.coastlines = '0';
  stage.dataset.coastlineAge = '';
  stage.dataset.coastlineCarried = 'false';
}
async function updateCoastlines(place, ticket) {
  const toggle = $('coastline');
  if (!toggle) return;
  $('coastline-note').hidden = !toggle.checked;
  if (!toggle.checked) {
    hideCoastline();
    return;
  }
  const entry = place.mapless ? null : coastlineEntry(place.age);
  if (!entry) {
    hideCoastline();
    const oldest = coastlines.ages[coastlines.ages.length - 1].age;
    $('coastline-age').textContent = fmt(L.noCoastline, { age: ageLabel(place), reach: COASTLINE_REACH_MA, oldest });
    return;
  }
  const { rings } = await loadCoastline(entry);
  if (ticket !== request) return;
  // Between two maps the surface is carried by the gap's motion field. A coastline
  // published at either end of the gap rides the same field, so the line and the coast
  // under it agree; one from outside the gap stays where it was published.
  const carried = carryRings(rings, entry.age, place);
  const moved = carried !== rings;
  const key = `${entry.age}|${projection}` + (moved ? `|${place.from.id}|${place.blend.toFixed(5)}` : '');
  if (coastlineKey !== key) drawCoastline(entry, carried, key);
  coastlineLayer.visible = true;
  stage.dataset.coastlines = String(rings.length);
  stage.dataset.coastlineAge = String(entry.age);
  stage.dataset.coastlineCarried = String(moved);
  $('coastline-age').textContent = Math.abs(entry.age - place.age) < 1e-6
    ? fmt(L.coastlineAt, { age: entry.age })
    : fmt(moved ? L.coastlineCarried : L.coastlineNearest, { age: entry.age, now: ageLabel(place) });
}
// The coastline's rings moved along the current gap's motion field: forward by the
// blend from the older end, or back by the rest of the way from the newer end. The
// rings come back untouched when there is nothing to carry them with.
function carryRings(rings, age, place) {
  const gap = place.blend > 0 ? motions[frames.indexOf(place.from)] ?? [] : [];
  const older = Math.abs(age - place.from.age) < 1e-6;
  const newer = Math.abs(age - place.to.age) < 1e-6;
  if (!gap.length || (!older && !newer)) return rings;
  const share = older ? place.blend : -(1 - place.blend);
  return rings.map((ring) => {
    const out = new Array(ring.length);
    for (let index = 0; index < ring.length; index += 2) {
      const [east, north] = travelAt(ring[index], ring[index + 1], gap);
      out[index] = ((ring[index] + share * east + 540) % 360) - 180;
      out[index + 1] = Math.max(-90, Math.min(90, ring[index + 1] + share * north));
    }
    return out;
  });
}
// The shader's travel() again, for line geometry: each control point pulls its
// neighbourhood by the distance its landmass travels across the gap, with a Gaussian
// falling off over the piece's own angular size. Kept in step with the shader.
function travelAt(longitude, latitude, gap) {
  let east = 0;
  let north = 0;
  let weight = 0;
  const count = Math.min(gap.length, MAX_MOTIONS);
  for (let index = 0; index < count; index++) {
    const point = gap[index];
    const eastward = ((longitude - point.lon + 540) % 360) - 180;
    const northward = latitude - point.lat;
    const shrink = Math.cos(THREE.MathUtils.degToRad(0.5 * (latitude + point.lat)));
    const span = Math.hypot(eastward * shrink, northward);
    const radius = Math.max(point.radius, 1);
    const pull = Math.exp(-0.5 * span * span / (radius * radius));
    east += pull * (((point.to_lon - point.lon + 540) % 360) - 180);
    north += pull * (point.to_lat - point.lat);
    weight += pull;
  }
  if (weight <= 0) return [0, 0];
  const t = Math.max(0, Math.min(1, (weight - 0.05) / 0.4));
  const ease = t * t * (3 - 2 * t);
  return [east / weight * ease, north / weight * ease];
}
function createGrid() {
  // Built from longitude and latitude rather than from the mesh, so the same parallels
  // and meridians follow whichever projection is showing, curved or straight.
  const result = new THREE.Group();
  const material = terrainLineMaterial(0xc4f7ef, 0.23);
  const lift = projection === 'globe' ? 0.004 : 0.003;
  function line(points) {
    result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material));
  }
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    const points = [];
    // Run each parallel from seam to seam of the turned sheet, so it never wraps back.
    for (let step = 0; step <= 180; step++) {
      points.push(pointAt(meridian - 179.999 + step * (359.998 / 180), latitude, lift));
    }
    line(points);
  }
  for (let longitude = -180; longitude < 180; longitude += 30) {
    const points = [];
    for (let step = 0; step <= 90; step++) {
      points.push(pointAt(longitude, -90 + step * 2, lift));
    }
    line(points);
  }
  result.visible = gridVisible;
  return result;
}
// The control panel floats over the foot of the map. Report how much of the map it
// covers, for the inspector to stop above it, and return the part the framing avoids.
function coveredByControls(height) {
  const panel = document.querySelector('.controls');
  if (!panel) return 0;
  const covered = Math.max(0, stage.getBoundingClientRect().bottom - panel.getBoundingClientRect().top);
  $('explorer')?.style.setProperty('--controls-space', `${Math.round(covered)}px`);
  return Math.min(covered, height * 0.45);
}
function fitCamera() {
  const { width, height } = stage.getBoundingClientRect();
  if (!width || !height) return;
  renderer.setSize(width, height);
  camera.aspect = width / height;
  // Fit the sphere or sheet to the height left above the control panel, then shift the
  // view up by half the covered strip so it sits in the middle of what can be seen.
  const covered = coveredByControls(height);
  const open = height - covered;
  const stretch = height / open;
  if (projection === 'globe') {
    camera.fov = THREE.MathUtils.radToDeg(
      2 * Math.atan(stretch * Math.tan(THREE.MathUtils.degToRad(21)) / Math.min(1, width / open)));
  } else {
    // Hold the sheet at one distance and open the lens until it fits both ways, so a
    // resize reframes the map without undoing the reader's zoom.
    const [halfWidth, halfHeight] = PROJECTIONS[projection].half;
    const tangent = stretch * Math.max(halfHeight * 1.08 / FLAT_DISTANCE,
                                       halfWidth * 1.08 / (FLAT_DISTANCE * width / open));
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(tangent));
  }
  if (covered > 0) camera.setViewOffset(width, height, 0, covered / 2, width, height);
  else camera.clearViewOffset();
  camera.updateProjectionMatrix();
}
function resetView() {
  const globe = projection === 'globe';
  earth.rotation.set(0, globe ? -Math.PI / 2 : 0, 0);
  camera.position.set(0, globe ? 0.18 : 0, globe ? 3.45 : FLAT_DISTANCE);
  controls.target.set(0, 0, 0);
  setMeridian(0);
  setTilt(RELIEF_TILT, 0);
  // Close enough to read a coastline: 0.06 above the unit sphere, or a twelfth of a sheet.
  controls.minDistance = globe ? 1.06 : FLAT_DISTANCE * 0.08;
  controls.maxDistance = globe ? 5 : FLAT_DISTANCE * 2.2;
  controls.update();
}
function init() {
  scene = new THREE.Scene();
  // The near plane has to sit well inside the closest zoom, or the surface is clipped.
  camera = new THREE.PerspectiveCamera(42, 1, 0.005, 50);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  stage.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = !reducedMotion;
  controls.enablePan = false;
  // The middle button is the terrain tilt's; the wheel already dollies.
  controls.mouseButtons.MIDDLE = null;

  controls.autoRotateSpeed = 0.55;
  earth = new THREE.Group();
  surfaceMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), globeMaterial());
  surfaceMesh.visible = false;
  earth.add(surfaceMesh);
  grid = createGrid();
  earth.add(grid);
  nameLayer = new THREE.Group();
  nameLayer.visible = false;
  earth.add(nameLayer);
  scene.add(earth);
  resetView();
  const mantleConfig = JSON.parse($('globe-mantle-overlay')?.textContent ?? 'null');
  mantleOverlay = createMantleOverlay({config: mantleConfig, earth, uniforms, stage, surfaceMaterial:surfaceMesh.material,
    getCamera: tiltedView,
    snapTimeline: age => {
      $('timeline').value = stops.findIndex(entry => Math.abs(entry[3] - age) < 1e-8);
      $('era').value = selected;
    },
    focus: centre => {earth.rotation.set(0,0,0);camera.position.copy(centre).multiplyScalar(3.2);controls.target.set(0,0,0);controls.update();},
    capture: () => ({stop, projection, rotation:earth.quaternion.clone(), camera:camera.position.clone(),
      target:controls.target.clone(), spinning, meridian, tiltAngle, tiltHeading}),
    enter: async (age, first, transition) => {
      const target = stops.findIndex(entry=>Math.abs(entry[3]-age)<1e-8);
      if (target < 0) throw new Error('80 Ma unavailable in this timeline');
      setPlaying(false);
      setProjection('globe',false);$('projection').value='globe';
      spinning=false;controls.autoRotate=false;$('rotate').setAttribute('aria-pressed','false');
      if (first) {
        earth.rotation.set(0,0,0);
        camera.position.copy(onSphere(mantleConfig.cutaway.longitude,mantleConfig.cutaway.latitude,3.2));
        controls.target.set(0,0,0);controls.update();
      }
      if (!await selectStop(target,true,true,transition)) throw new Error('Surface unavailable');
    },
    restore: previous => {
      setProjection(previous.projection,false);$('projection').value=previous.projection;
      setMeridian(previous.meridian);setTilt(previous.tiltAngle,previous.tiltHeading);
      earth.quaternion.copy(previous.rotation);camera.position.copy(previous.camera);controls.target.copy(previous.target);
      spinning=previous.spinning;controls.autoRotate=spinning&&projection==='globe';
      $('rotate').setAttribute('aria-pressed',String(spinning));controls.update();selectStop(previous.stop,true);
    }});
  const observer = new ResizeObserver(fitCamera);
  observer.observe(stage);
  // The control panel changes height with the layers on show, which moves the framing.
  if (document.querySelector('.controls')) observer.observe(document.querySelector('.controls'));
  let previous = performance.now();
  renderer.setAnimationLoop((time) => {
    const delta = Math.min((time - previous) / 1000, 0.1);
    previous = time;
    if (document.hidden) return;
    followZoom();
    controls.update(delta);
    if (spinning && projection !== 'globe' && !reducedMotion) setMeridian(meridian + delta * 12);
    updateNameVisibility();
    const view = tiltedView();
    if (uniforms.mantleCutaway.value > .5 || uniforms.mantleSurfaceOpacity.value < 1) {
      earth.updateWorldMatrix(true,false);
      uniforms.mantleCamera.value.copy(view.position);
      earth.worldToLocal(uniforms.mantleCamera.value);
    }
    renderer.render(scene, view);
  });
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    mantleOverlay?.leave(false);
    setPlaying(false);
    status.classList.remove('loaded');
    status.textContent = L.contextLost;
  });
  stage.dataset.projection = projection;
  stage.dataset.plateModel = plateChoice;
  stage.dataset.coastlines = '0';
  stage.dataset.relief = '0.00';
  // Browsers restore a form control's last value on reload, which left the dropdown
  // naming a model while nothing was drawn. The page state is the authority: start both
  // overlays off and make the controls say so.
  if ($('plate-overlay')) $('plate-overlay').value = plateChoice;
  if ($('coastline')) $('coastline').checked = false;
  $('projection').value = projection;
  frames.forEach((frame, index) => $('era').add(new Option(`${frame.label} · ${ageText(frame)}`, index)));
  $('timeline').max = stops.length - 1;
  const oldest = stops[0];
  if ($('timeline-oldest')) {
    $('timeline-oldest').textContent = oldest[0] < 0
      ? fmt(L.oldestNoMap, { age: oldest[3] })
      : timeWindow ? fmt(L.oldestWindow, { age: frames[oldest[0]].deglacial.age_ka })
        : fmt(L.oldestPast, { age: oldest[3] });
  }
  $('era').addEventListener('change', () => selectFrame(Number($('era').value), true));
  $('timeline').addEventListener('input', () => selectStop(Number($('timeline').value), true));
  $('older').addEventListener('click', () => selectStop(neighbourStop(-1), true));
  $('newer').addEventListener('click', () => selectStop(neighbourStop(1), true));
  $('retry').addEventListener('click', () => selectStop(stop, true));
  $('play').addEventListener('click', () => {
    setPlaying(!playing);
    if (playing) selectFrame(selected === frames.length - 1 ? 0 : selected + 1);
  });
  $('rotate').addEventListener('click', () => {
    spinning = !spinning;
    controls.autoRotate = spinning && projection === 'globe';
    $('rotate').setAttribute('aria-pressed', String(spinning));
  });
  // On a sheet a left drag turns the centre meridian, as a drag spins the globe.
  // OrbitControls keeps the right button for panning and the wheel or a pinch for zoom.
  let dragging = null;
  // While the terrain stands, a middle (wheel) drag or a shift drag tilts the view: up
  // and down for the angle, sideways for the heading. OrbitControls uses the middle
  // button for dolly, which the wheel already does, so it is taken from it here.
  let tilting = null;
  // On a touch screen two fingers tilt the standing terrain: moved together up or down for
  // the angle, twisted for the heading. The gesture is told from a pinch once the fingers
  // have moved 12 px: if their spread changed less than half as much as their midpoint
  // moved, it is a tilt, and the controls stand aside until a finger lifts.
  const touches = new Map();
  let touchStart = null;
  let touchTilt = false;
  const twoFingers = () => {
    if (touches.size !== 2) return null;
    const [a, b] = [...touches.values()];
    return { y: (a.y + b.y) / 2, d: Math.hypot(b.x - a.x, b.y - a.y), a: Math.atan2(b.y - a.y, b.x - a.x) };
  };
  renderer.domElement.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'touch') {
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      touchStart = twoFingers();
    }
    if (dragging && event.pointerId !== dragging.id) {
      dragging = null;  // a second finger means a pinch, not a turn
      return;
    }
    if (projection === 'globe') {
      if (uniforms.relief.value > 0 && (event.button === 1 || (event.button === 0 && event.shiftKey))) {
        event.preventDefault();
        tilting = { id: event.pointerId, x: event.clientX, y: event.clientY };
      }
      return;
    }
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return;
    dragging = { id: event.pointerId, x: event.clientX };
  });
  window.addEventListener('pointermove', (event) => {
    if (touches.has(event.pointerId)) {
      const before = twoFingers();
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      const after = twoFingers();
      if (before && after && touchStart && projection === 'globe' && uniforms.relief.value > 0) {
        const moved = Math.abs(after.y - touchStart.y);
        if (!touchTilt && moved > 12 && Math.abs(after.d - touchStart.d) < moved * 0.5) {
          touchTilt = true;
          controls.enabled = false;
        }
        if (touchTilt) {
          const twist = Math.atan2(Math.sin(after.a - before.a), Math.cos(after.a - before.a));
          setTilt(tiltAngle - (after.y - before.y) * 0.005, tiltHeading + twist);
        }
      }
    }
    if (tilting && event.pointerId === tilting.id) {
      // Dragging up leans further toward the horizon, as in the usual map applications.
      setTilt(tiltAngle - (event.clientY - tilting.y) * 0.005, tiltHeading + (event.clientX - tilting.x) * 0.005);
      tilting.x = event.clientX;
      tilting.y = event.clientY;
      return;
    }
    if (!dragging || event.pointerId !== dragging.id) return;
    const height = renderer.domElement.clientHeight || 1;
    const distance = camera.position.distanceTo(controls.target);
    const worldPerPixel = 2 * distance * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) / height;
    // The sheet is two units wide for 360 degrees, so the map follows the pointer.
    setMeridian(meridian - (event.clientX - dragging.x) * worldPerPixel * 180);
    dragging.x = event.clientX;
  });
  for (const type of ['pointerup', 'pointercancel']) {
    window.addEventListener(type, (event) => {
      if (dragging && event.pointerId === dragging.id) dragging = null;
      if (tilting && event.pointerId === tilting.id) tilting = null;
      if (touches.delete(event.pointerId) && touches.size < 2) {
        touchStart = null;
        if (touchTilt) {
          touchTilt = false;
          controls.enabled = true;
        }
      }
    });
  }
  $('grid').addEventListener('click', () => {
    gridVisible = !gridVisible;
    grid.visible = gridVisible;
    $('grid').setAttribute('aria-pressed', String(gridVisible));
  });
  if (surfaceToggle) {
    surfaceToggle.addEventListener('click', () => {
      surface = surface === 'mask' ? (reliefSeries ? 'relief' : 'map') : 'mask';
      surfaceToggle.setAttribute('aria-pressed', String(surface === 'mask'));
      selectStop(stop, true);
    });
  }
  if (iceToggle) {
    iceToggle.addEventListener('click', () => {
      iceVisible = !iceVisible;
      applyIce(uniforms.iceA.value, uniforms.iceB.value);
      showIceKind(lastPlace);
    });
  }
  if (riverToggle) {
    riverToggle.addEventListener('click', () => {
      riversVisible = !riversVisible;
      applyRivers(uniforms.riverA.value, uniforms.riverB.value, uniforms.riverLow0.value, uniforms.riverLow1.value,
                  [uniforms.riverLowT.value.x, uniforms.riverLowT.value.y]);
    });
  }
  if (temperatureToggle) {
    temperatureToggle.addEventListener('click', () => {
      surface = surface === 'temp' ? 'relief' : 'temp';
      selectStop(stop, true);
    });
  }
  drawTemperatureStrip();
  drawSeaLevelStrip();
  drawPleistocene();
  if (seaLevelControl) {
    seaLevelControl.value = '0';   // the page state is the authority, not a restored control
    showSeaSetting();
    seaLevelControl.addEventListener('input', () => { showSeaSetting(); selectStop(stop, true); });
    if (seaLevelCurveToggle) {
      seaLevelCurveToggle.checked = false;
      // In the time window the age already takes the level from the stack.
      seaLevelCurveToggle.disabled = Boolean(timeWindow);
      seaLevelCurveToggle.addEventListener('change', () => selectStop(stop, true));
    }
  }
  if ($('plate-unlock')) {
    // Unlock in place: the reader keeps the age and the view they had set up.
    $('plate-unlock').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = $('plate-unlock');
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(form),
      });
      const granted = response.ok && (await response.json()).granted;
      $('unlock-wrong').hidden = Boolean(granted);
      if (!granted) return;
      for (const model of plates) model.locked = false;
      $('plate-key').value = '';
      form.hidden = true;
      selectStop(stop, true);
    });
  }
  if ($('plate-overlay')) {
    $('plate-overlay').addEventListener('change', () => {
      plateChoice = $('plate-overlay').value;
      plateAge = null;
      stage.dataset.plateModel = plateChoice;
      $('plate-note').hidden = !showPlates();
      if ($('plate-hint')) $('plate-hint').hidden = showPlates();
      selectStop(stop, true);
    });
  }
  if ($('coastline')) $('coastline').addEventListener('change', () => selectStop(stop, true));
  $('projection').addEventListener('change', () => setProjection($('projection').value));
  if ($('shading')) {
    const apply = () => {
      uniforms.exaggeration.value = Number($('shading').value);
      stage.dataset.shading = $('shading').value;
    };
    $('shading').value = '1';   // the page state is the authority, not a restored control
    $('shading').addEventListener('change', apply);
    apply();
  }
  $('reset').addEventListener('click', resetView);
  stage.addEventListener('keydown', (event) => {
    const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const step = 0.12 * zoomFactor();
    if (projection === 'globe') {
      if (event.key === 'ArrowLeft') earth.rotation.y -= step;
      if (event.key === 'ArrowRight') earth.rotation.y += step;
      if (event.key === 'ArrowUp') earth.rotation.x -= step;
      if (event.key === 'ArrowDown') earth.rotation.x += step;
    } else {
      // Left and right turn the sheet about the pole, as they turn the globe; up and down
      // slide the view.
      if (event.key === 'ArrowLeft') setMeridian(meridian - 10 * zoomFactor());
      if (event.key === 'ArrowRight') setMeridian(meridian + 10 * zoomFactor());
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        const shift = new THREE.Vector3(0, event.key === 'ArrowUp' ? 1 : -1, 0)
          .multiplyScalar(camera.position.z * 0.08);
        camera.position.add(shift);
        controls.target.add(shift);
        controls.update();
      }
    }
    if (['+', '=', '-'].includes(event.key)) {
      // Step the height above the surface rather than the distance to the centre, so the
      // steps stay even all the way down to the closest view.
      const ground = projection === 'globe' ? 1 : 0;
      const offset = camera.position.clone().sub(controls.target);
      const next = ground + (offset.length() - ground) * (event.key === '-' ? 1.25 : 0.8);
      offset.setLength(THREE.MathUtils.clamp(next, controls.minDistance, controls.maxDistance));
      camera.position.copy(controls.target).add(offset);
    }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
  if ($('sampling')) {
    // The server builds the stops, so a new spacing is a new page; carry the age across so
    // the reader lands where they were.
    $('sampling').addEventListener('change', () => {
      const [kind, value] = $('sampling').value.split(':');
      const url = new URL(location.href);
      url.searchParams.delete('steps');
      url.searchParams.delete('interval');
      url.searchParams.set(kind === 'interval' ? 'interval' : 'steps', value);
      url.searchParams.set('age', String(stops[stop][3]));
      location.assign(url.href);
    });
  }
  if ($('window')) {
    // The window is its own stop table, so a new page too. It opens at the present, and
    // leaving it lands on the present of the whole series, where its ages all round to.
    $('window').addEventListener('change', () => {
      const url = new URL(location.href);
      url.searchParams.delete('age');
      if ($('window').value) url.searchParams.set('window', $('window').value);
      else url.searchParams.delete('window');
      location.assign(url.href);
    });
  }
  if ($('relief3d')) {
    $('relief3d').addEventListener('click', () => {
      reliefWanted = !reliefWanted;
      $('relief3d').setAttribute('aria-pressed', String(reliefWanted));
    });
  }
  if ($('sea-chart')) {
    // The long-term curve floats over the map, opened and closed from the toolbar.
    $('sea-chart').addEventListener('click', () => {
      const open = $('sea-overlay').hidden;
      $('sea-overlay').hidden = !open;
      $('sea-chart').setAttribute('aria-pressed', String(open));
    });
  }
  if ($('dataset')) {
    // Each dataset has its own stops, built by the server, so it is a new page too; the
    // age carries across and lands on the nearest stop there.
    $('dataset').addEventListener('change', () => {
      const url = new URL(location.href);
      url.searchParams.set('masks', $('dataset').value);
      url.searchParams.delete('window');   // the window belongs to the elevation series
      url.searchParams.set('age', String(stops[stop][3]));
      location.assign(url.href);
    });
  }
  const askedAge = Number(new URL(location.href).searchParams.get('age'));
  if (new URL(location.href).searchParams.has('age') && Number.isFinite(askedAge)) {
    let nearest = 0;
    stops.forEach(([, , , age], index) => {
      if (Math.abs(age - askedAge) < Math.abs(stops[nearest][3] - askedAge)) nearest = index;
    });
    selectStop(nearest);
  } else {
    selectFrame(selected);
  }
}
// The inspector floats over the map and folds away. It starts open where there is room
// beside the sphere, closed on a phone, and a reader's own choice is kept in this browser.
function setupInspector() {
  const inspector = $('inspector');
  const toggle = $('info-toggle');
  if (!inspector || !toggle) return;
  const show = (open) => {
    inspector.classList.toggle('closed', !open);
    toggle.setAttribute('aria-expanded', String(open));
  };
  let remembered = null;
  try { remembered = localStorage.getItem('earththrutime.inspector'); } catch { /* storage blocked */ }
  show(remembered ? remembered === 'open' : matchMedia('(min-width: 900px)').matches);
  toggle.addEventListener('click', () => {
    const open = inspector.classList.contains('closed');
    show(open);
    try { localStorage.setItem('earththrutime.inspector', open ? 'open' : 'closed'); } catch { /* storage blocked */ }
  });
}
// Settings beyond the essentials sit behind the menu button. The menu stays open while the
// reader works the map, closes from its button or with Escape, and is kept in this browser.
function setupSettingsMenu() {
  const menu = $('settings-menu');
  const toggle = $('settings-toggle');
  if (!menu || !toggle) return;
  // The sea-level curve floats in the same corner, so it stacks above the open menu.
  // On a short screen the menu takes the toolbar's row inside the panel instead, and pushes nothing.
  const space = () => $('explorer')?.style.setProperty('--menu-space', menu.hidden || menu.offsetTop >= 0 ? '0px' : `${menu.offsetHeight + 8}px`);
  new ResizeObserver(space).observe(menu);
  const show = (open, remember = true) => {
    menu.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    space();
    if (!remember) return;
    try { localStorage.setItem('earththrutime.settings', open ? 'open' : 'closed'); } catch { /* storage blocked */ }
  };
  let remembered = null;
  try { remembered = localStorage.getItem('earththrutime.settings'); } catch { /* storage blocked */ }
  show(remembered === 'open', false);
  toggle.addEventListener('click', () => show(menu.hidden));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) show(false);
  });
}
setupInspector();
setupSettingsMenu();
try { init(); }
catch (error) {
  status.textContent = document.getElementById('globe-strings')
    ? JSON.parse(document.getElementById('globe-strings').textContent).webglFailed
    : 'WebGL unavailable.';
  for (const element of document.querySelectorAll('.explorer button:not(#info-toggle):not(#settings-toggle), .explorer select, .explorer input')) element.disabled = true;
  console.error(error);
}
