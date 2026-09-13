// Composing a plate's rotation at a time, from the packed EarthByte rotation model.
//
// A rotation file lists total reconstruction poles: for a moving plate, a time, a pole
// and an angle, all relative to a fixed plate. Reconstructing means walking the chain of
// fixed plates up to the anchor and composing what is found, and interpolating inside a
// sequence when the asked-for time falls between two samples.
//
// scripts/rotation_model.py is the same algorithm in Python, checked against the GPlates
// Web Service; tests/rotation.test.mjs keeps this copy agreeing with it.

export const IDENTITY = [1, 0, 0, 0];
const TO_RADIANS = Math.PI / 180;
const TO_DEGREES = 180 / Math.PI;

export function fromPole(poleLatitude, poleLongitude, angleDegrees) {
  const latitude = poleLatitude * TO_RADIANS;
  const longitude = poleLongitude * TO_RADIANS;
  const half = angleDegrees * TO_RADIANS / 2;
  const scale = Math.sin(half);
  return [Math.cos(half),
          Math.cos(latitude) * Math.cos(longitude) * scale,
          Math.cos(latitude) * Math.sin(longitude) * scale,
          Math.sin(latitude) * scale];
}

export function multiply([a, b, c, d], [e, f, g, h]) {
  return [a * e - b * f - c * g - d * h,
          a * f + b * e + c * h - d * g,
          a * g - b * h + c * e + d * f,
          a * h + b * g - c * f + d * e];
}

export function conjugate([w, x, y, z]) {
  return [w, -x, -y, -z];
}

export function slerp(start, end, fraction) {
  let dot = start[0] * end[0] + start[1] * end[1] + start[2] * end[2] + start[3] * end[3];
  let target = end;
  if (dot < 0) {
    target = end.map((value) => -value);
    dot = -dot;
  }
  let blended;
  if (dot > 0.9999995) {
    blended = start.map((value, index) => value + (target[index] - value) * fraction);
  } else {
    const theta = Math.acos(Math.min(1, Math.max(-1, dot)));
    const sine = Math.sin(theta);
    const first = Math.sin((1 - fraction) * theta) / sine;
    const second = Math.sin(fraction * theta) / sine;
    blended = start.map((value, index) => value * first + target[index] * second);
  }
  const norm = Math.hypot(...blended) || 1;
  return blended.map((value) => value / norm);
}

// Apply a rotation to a longitude and latitude in degrees.
export function turn(quaternion, longitude, latitude) {
  const lon = longitude * TO_RADIANS;
  const lat = latitude * TO_RADIANS;
  const point = [0, Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)];
  const [, x, y, z] = multiply(multiply(quaternion, point), conjugate(quaternion));
  return [Math.atan2(y, x) * TO_DEGREES, Math.asin(Math.min(1, Math.max(-1, z))) * TO_DEGREES];
}

export class RotationModel {
  constructor(document) {
    this.anchor = document.anchor ?? 0;
    this.sequences = new Map();
    this.byMoving = new Map();
    for (const [key, flat] of Object.entries(document.sequences)) {
      const [moving, fixed] = key.split(':').map(Number);
      const samples = [];
      for (let index = 0; index < flat.length; index += 4) {
        samples.push(flat.slice(index, index + 4));
      }
      this.sequences.set(key, samples);
      const spans = this.byMoving.get(moving) ?? [];
      spans.push({ fixed, key, from: samples[0][0], to: samples[samples.length - 1][0] });
      this.byMoving.set(moving, spans);
    }
    // A narrow sequence laid over a broad one says the plate is measured against a
    // different neighbour for those years, so it has to be tried first.
    for (const spans of this.byMoving.values()) spans.sort((a, b) => b.from - a.from);
    this.cache = new Map();
    this.cachedAge = null;
  }

  relative(samples, time) {
    if (time < samples[0][0] - 1e-9 || time > samples[samples.length - 1][0] + 1e-9) return null;
    let previous = samples[0];
    for (const sample of samples) {
      if (sample[0] >= time - 1e-9) {
        if (Math.abs(sample[0] - previous[0]) < 1e-9 || Math.abs(sample[0] - time) < 1e-9) {
          return fromPole(sample[1], sample[2], sample[3]);
        }
        const fraction = (time - previous[0]) / (sample[0] - previous[0]);
        const start = fromPole(previous[1], previous[2], previous[3]);
        const end = fromPole(sample[1], sample[2], sample[3]);
        // Split the rotation from one sample to the next, not the poles themselves.
        return multiply(start, slerp(IDENTITY, multiply(conjugate(start), end), fraction));
      }
      previous = sample;
    }
    const last = samples[samples.length - 1];
    return fromPole(last[1], last[2], last[3]);
  }

  rotation(plate, time, seen) {
    if (plate === this.anchor) return IDENTITY;
    if (this.cachedAge !== time) {
      this.cache.clear();
      this.cachedAge = time;
    } else if (this.cache.has(plate)) {
      return this.cache.get(plate);
    }
    const visited = seen ?? new Set();
    if (visited.has(plate)) return null;
    visited.add(plate);
    for (const span of this.byMoving.get(plate) ?? []) {
      if (time < span.from - 1e-9 || time > span.to + 1e-9) continue;
      const relative = this.relative(this.sequences.get(span.key), time);
      if (relative === null) continue;
      const upstream = this.rotation(span.fixed, time, visited);
      if (upstream === null) continue;
      const total = multiply(upstream, relative);
      if (!seen) this.cache.set(plate, total);
      return total;
    }
    return null;
  }
}
