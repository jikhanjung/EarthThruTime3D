// Bounds are degrees; west > east crosses the date line. ±180 endpoints span
// the whole longitude range, while equal endpoints have zero width.
export const INDIA_ASIA = { west: 35, east: 125, south: -35, north: 55 };
export function longitudeSpan({ west, east }) {
  return Math.abs(east - west) === 360 ? 360 : ((east - west) % 360 + 360) % 360;
}
export function cutCentre(bounds) {
  return { longitude: bounds.west + longitudeSpan(bounds) / 2, latitude: (bounds.south + bounds.north) / 2 };
}
export function containsPoint(point, bounds) {
  const length = Math.hypot(point.x, point.y, point.z);
  if (!length) return false;
  const latitude = Math.asin(Math.max(-1, Math.min(1, point.y / length))) * 180 / Math.PI;
  const longitude = Math.atan2(-point.z, point.x) * 180 / Math.PI;
  const offset = ((longitude - bounds.west) % 360 + 360) % 360;
  const span = longitudeSpan(bounds);
  return span > 0 && latitude > bounds.south && latitude < bounds.north && (span === 360 || offset < span);
}

// Separate loops for a full-longitude band: no artificial wall at the map seam.
// Parallel edges must be sampled along latitude, not as great-circle chords.
export function cutBoundary(bounds, step = 0.5) {
  const span = longitudeSpan(bounds);
  if (!span || bounds.south >= bounds.north) return [];
  function edge(lon0, lat0, lon1, lat1) {
    const n = Math.max(1, Math.ceil(Math.max(Math.abs(lon1 - lon0), Math.abs(lat1 - lat0)) / step));
    return Array.from({ length: n + 1 }, (_, i) => [lon0 + (lon1 - lon0) * i / n, lat0 + (lat1 - lat0) * i / n]);
  }
  const { west, south, north } = bounds, east = west + span;
  if (span === 360) {
    return [south > -90 ? edge(west, south, east, south) : null,
      north < 90 ? edge(east, north, west, north) : null].filter(Boolean);
  }
  return [[...edge(west, south, east, south).slice(0, -1),
    ...edge(east, south, east, north).slice(0, -1),
    ...edge(east, north, west, north).slice(0, -1),
    ...edge(west, north, west, south)]];
}

export const CUT_REGION_GLSL = `
  uniform vec4 interiorBounds; // west, eastward span, south, north (degrees)
  bool inInteriorCut(vec3 position) {
    vec3 p = normalize(position);
    float latitude = degrees(asin(clamp(p.y, -1.0, 1.0)));
    float longitude = degrees(atan(-p.z, p.x));
    float offset = mod(longitude - interiorBounds.x + 360.0, 360.0);
    return interiorBounds.y > 0.0 && latitude > interiorBounds.z && latitude < interiorBounds.w
      && (interiorBounds.y >= 360.0 || offset < interiorBounds.y);
  }`;
