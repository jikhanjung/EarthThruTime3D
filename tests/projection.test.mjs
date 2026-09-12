import test from 'node:test';
import assert from 'node:assert/strict';
import { mollweide, sourcePixel } from '../static/core/projection.js';
import * as projection from '../static/core/projection.js';

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

test('flat projections place the corners and the centre where they belong', () => {
  const { placeMollweide, placeEquirectangular, placeMercator, MERCATOR_LIMIT } = projection;
  for (const place of [placeMollweide, placeEquirectangular, placeMercator]) {
    const [x, y] = place(0, 0);
    assert.ok(Math.abs(x) < 1e-9 && Math.abs(y) < 1e-9, `${place.name} centre`);
  }
  // Mollweide fills an ellipse: the equator reaches the full width, the poles a point.
  assert.ok(Math.abs(placeMollweide(180, 0)[0] - 1) < 1e-6);
  assert.ok(Math.abs(placeMollweide(0, 90)[1] - 0.5) < 1e-6);
  assert.ok(Math.abs(placeMollweide(180, 60)[0]) < 0.8);
  // Equirectangular is linear in both axes.
  assert.deepStrictEqual(placeEquirectangular(90, 45), [0.5, 0.25]);
  // Mercator stretches toward its cut-off and reaches the square's edge there.
  assert.ok(Math.abs(placeMercator(0, MERCATOR_LIMIT)[1] - 1) < 1e-4);
  assert.ok(placeMercator(0, 60)[1] > placeEquirectangular(0, 60)[1]);
  assert.strictEqual(placeMercator(0, 89)[1], placeMercator(0, MERCATOR_LIMIT)[1]);
});
