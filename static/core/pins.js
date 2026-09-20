// Location pins: a present-day place, the plate its land rides on, and where that plate
// carries it at another age.
//
// A pin is a calculation from a rotation model, not an observation. The polygons are the
// model's present-day continents; the pin takes the plate of the polygon that holds it
// and is carried by that plate's rotation, rigidly, for as long as the polygon exists.
//
// scripts/assess_pin.py is the same test in Python, and devlog wwolf 014 is what it
// measured; tests/pins.test.mjs keeps this copy agreeing with the packed model.

import { conjugate, turn } from './rotation.js';

const TO_RADIANS = Math.PI / 180;
export const EARTH_RADIUS_KM = 6371;
export const MAX_PINS = 3;

function unit(longitude, latitude) {
  const lon = longitude * TO_RADIANS;
  const lat = latitude * TO_RADIANS;
  return [Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)];
}

// Whether a place lies inside a spherical ring of flat [lon, lat, lon, lat, ...]. Seen
// from inside, the bearings to the ring's vertices go once around; from outside they come
// back to where they started. That holds across the antimeridian and over a pole, where
// a longitude/latitude ray test does not. It cannot tell a place from its antipode, which
// is what facing() below is for.
export function inside(longitude, latitude, ring) {
  const [x, y, z] = unit(longitude, latitude);
  const flat = Math.max(Math.hypot(x, y), 1e-12);
  const east = [-y / flat, x / flat, 0];
  const north = [y * east[2] - z * east[1], z * east[0] - x * east[2], x * east[1] - y * east[0]];
  let turned = 0;
  let first = null;
  let previous = null;
  for (let index = 0; index <= ring.length; index += 2) {
    const closing = index === ring.length;
    const vertex = closing ? first : unit(ring[index], ring[index + 1]);
    const bearing = Math.atan2(vertex[0] * east[0] + vertex[1] * east[1],
                               vertex[0] * north[0] + vertex[1] * north[1] + vertex[2] * north[2]);
    if (previous !== null) {
      const step = bearing - previous;
      turned += step - 2 * Math.PI * Math.round(step / (2 * Math.PI));
    }
    first ??= vertex;
    previous = bearing;
  }
  return Math.abs(turned) > Math.PI;
}

const centres = new WeakMap();
// A continent is narrower than a hemisphere, so a place inside it faces its middle.
function facing(feature, longitude, latitude) {
  let centre = centres.get(feature);
  if (!centre) {
    centre = [0, 0, 0];
    for (const ring of feature.rings) {
      for (let index = 0; index < ring.length; index += 2) {
        const vertex = unit(ring[index], ring[index + 1]);
        for (let axis = 0; axis < 3; axis++) centre[axis] += vertex[axis];
      }
    }
    centres.set(feature, centre);
  }
  const place = unit(longitude, latitude);
  return place[0] * centre[0] + place[1] * centre[1] + place[2] * centre[2] > 0;
}

function holds(feature, longitude, latitude) {
  if (!facing(feature, longitude, latitude)) return false;
  let held = false;
  // Even-odd over the rings, so a hole is a hole.
  for (const ring of feature.rings) if (inside(longitude, latitude, ring)) held = !held;
  return held;
}

// How far back a plate can be carried: to the age its polygon begins, or to where the
// model's poles for it run out, whichever comes first. A polygon's own date is often
// nominal (PALEOMAP gives many 4500 Ma) while the rotation file stops well short of it.
export function reachOf(model, pid, from, deepest) {
  let older = Math.min(from, deepest);
  if (model.rotation(pid, older) !== null) return older;
  let newer = 0;
  while (older - newer > 0.01) {
    const middle = (older + newer) / 2;
    if (model.rotation(pid, middle) === null) older = middle;
    else newer = middle;
  }
  return Math.round(newer * 10) / 10;
}

// The pin for a place seen at `age`: its present-day coordinates, its plate, and the
// oldest age it can be carried to (`deepest` being the oldest the model claims to cover).
// Null over ocean floor, which no continent polygon covers and which subduction has
// mostly removed anyway. Where polygons overlap, the one that goes furthest back wins, so
// the pin lasts as long as the model allows.
export function pinAt(features, model, longitude, latitude, age, deepest = Infinity) {
  let best = null;
  for (const feature of features) {
    if (age > feature.from + 1e-9 || age < feature.to - 1e-9) continue;
    const rotation = model.rotation(feature.pid, age);
    if (rotation === null) continue;
    const [lon, lat] = turn(conjugate(rotation), longitude, latitude);
    if (!holds(feature, lon, lat)) continue;
    if (!best || feature.from > best.from) best = { lon, lat, pid: feature.pid, from: feature.from };
  }
  if (best) best.reach = reachOf(model, best.pid, best.from, deepest);
  return best;
}

// Where the pin's plate has carried it at `age`, or null before its land existed or
// where the model has no pole for it.
export function carried(model, pin, age) {
  if (age > pin.reach + 1e-9) return null;
  const rotation = model.rotation(pin.pid, age);
  return rotation === null ? null : turn(rotation, pin.lon, pin.lat);
}

// Where the viewer draws ground that a map holds at `origin`, part of the way across a
// gap. The shader samples a map at x - share * travel(x), so the ground appears at the x
// that solves x - share * travel(x) = origin; a few rounds settle it, the field being
// smooth. `travel` gives the gap's motion in degrees east and north at a place. The same
// solution as drawn_at() in scripts/assess_pin.py.
export function drawnAt(origin, travel, share) {
  let place = origin;
  for (let round = 0; round < 8; round++) {
    const [east, north] = travel(place[0], place[1]);
    place = [((origin[0] + share * east + 540) % 360) - 180,
             Math.max(-90, Math.min(90, origin[1] + share * north))];
  }
  return place;
}

export function distanceKm([lon1, lat1], [lon2, lat2]) {
  const a = unit(lon1, lat1);
  const b = unit(lon2, lat2);
  const cross = Math.hypot(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]);
  return Math.atan2(cross, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) * EARTH_RADIUS_KM;
}

// The address carries present-day coordinates: pin=lon,lat;lon,lat;lon,lat
export function parsePins(text) {
  // Number('') is 0, so an empty coordinate must not get as far as Number().
  const pair = /^(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$/;
  return (text ?? '').split(';').map((part) => pair.exec(part)?.slice(1).map(Number))
    .filter((place) => place && Math.abs(place[0]) <= 180 && Math.abs(place[1]) <= 90)
    .slice(0, MAX_PINS);
}

export function formatPins(pins) {
  return pins.map((pin) => `${pin.lon.toFixed(2)},${pin.lat.toFixed(2)}`).join(';');
}
