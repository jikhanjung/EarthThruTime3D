import { test } from 'node:test';
import assert from 'node:assert/strict';
import { INDIA_ASIA, cutBoundary, cutCentre, containsPoint, longitudeSpan } from '../static/core/interior-cutaway.js';

const point = (lon, lat) => {
  lon *= Math.PI / 180; lat *= Math.PI / 180;
  return { x: Math.cos(lat) * Math.cos(lon), y: Math.sin(lat), z: -Math.cos(lat) * Math.sin(lon) };
};
test('geographic cut includes only the specified latitude and longitude range', () => {
  assert.equal(containsPoint(point(80, 10), INDIA_ASIA), true);
  for (const [lon, lat] of [[0, 10], [150, 10], [80, 60], [80, -40]]) {
    assert.equal(containsPoint(point(lon, lat), INDIA_ASIA), false);
  }
  assert.deepEqual(cutCentre(INDIA_ASIA), { longitude: 80, latitude: 10 });
});
test('date-line crossing, full longitude and zero width stay distinct', () => {
  const bounds = { west: 170, east: -170, south: -80, north: 80 };
  assert.equal(longitudeSpan(bounds), 20);
  for (const lon of [175, -175, 180, -180]) assert.equal(containsPoint(point(lon, 0), bounds), true);
  assert.equal(containsPoint(point(0, 0), bounds), false);
  assert.equal(cutCentre(bounds).longitude, 180);
  assert.equal(containsPoint(point(0, 0), { ...bounds, west: -180, east: 180 }), true);
  assert.equal(containsPoint(point(175, 0), { ...bounds, east: 170 }), false);
});
test('wall edges follow parallels and meridians with no seam wall for full bands', () => {
  const bounds = { west: 170, east: -170, south: -90, north: 65 };
  const [ring] = cutBoundary(bounds);
  assert.deepEqual(ring[0], ring.at(-1));
  for (const [lon, lat] of ring) {
    assert.ok(lon === 170 || lon === 190 || lat === -90 || lat === 65);
    assert.ok(lon >= 170 && lon <= 190 && lat >= -90 && lat <= 65);
  }
  const bands = cutBoundary({ west: -180, east: 180, south: -30, north: 30 });
  assert.equal(bands.length, 2);
  assert.ok(bands[0].every(([, lat]) => lat === -30));
  assert.ok(bands[1].every(([, lat]) => lat === 30));
  assert.equal(cutBoundary({ west: -180, east: 180, south: -90, north: 90 }).length, 0);
  assert.equal(cutBoundary({ ...bounds, east: 170 }).length, 0);
});
