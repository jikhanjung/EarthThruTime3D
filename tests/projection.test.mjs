import test from 'node:test';
import assert from 'node:assert/strict';
import { mollweide, sourcePixel } from '../static/core/projection.js';

const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-6, `${actual} != ${expected}`);
test('equator, antimeridian and poles map to the correct ellipse landmarks', () => {
  for (const [lon, lat, x, y] of [[0, 0, 0, 0], [Math.PI, 0, 1, 0], [-Math.PI, 0, -1, 0], [0, Math.PI / 2, 0, 1], [0, -Math.PI / 2, 0, -1]]) {
    const actual = mollweide(lon, lat);
    close(actual[0], x); close(actual[1], y);
  }
});
test('forward projection preserves hemisphere direction and remains in the ellipse', () => {
  for (let lat = -89; lat <= 89; lat += 7) {
    for (let lon = -180; lon <= 180; lon += 11) {
      const [x, y] = mollweide(lon * Math.PI / 180, lat * Math.PI / 180);
      assert.ok(x * x + y * y <= 1 + 1e-10);
      assert.ok(y * lat >= 0);
      assert.ok(x * lon >= 0);
    }
  }
});
test('raster sampling has north at the top and west at the left', () => {
  const bounds = [10, 40, 710, 390];
  const center = sourcePixel(0, 0, bounds);
  close(center[0], 360); close(center[1], 215);
  assert.ok(sourcePixel(0, 1, bounds)[1] < center[1]);
  assert.ok(sourcePixel(-1, 0, bounds)[0] < center[0]);
});
