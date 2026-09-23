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
  const { placeMollweide, placeEquirectangular } = projection;
  for (const place of [placeMollweide, placeEquirectangular]) {
    const [x, y] = place(0, 0);
    assert.ok(Math.abs(x) < 1e-9 && Math.abs(y) < 1e-9, `${place.name} centre`);
  }
  // Mollweide fills an ellipse: the equator reaches the full width, the poles a point.
  assert.ok(Math.abs(placeMollweide(180, 0)[0] - 1) < 1e-6);
  assert.ok(Math.abs(placeMollweide(0, 90)[1] - 0.5) < 1e-6);
  assert.ok(Math.abs(placeMollweide(180, 60)[0]) < 0.8);
  // Equirectangular is linear in both axes.
  assert.deepStrictEqual(placeEquirectangular(90, 45), [0.5, 0.25]);
  assert.deepStrictEqual(placeEquirectangular(-180, -90), [-1, -0.5]);
});

test('Equal Earth keeps its own aspect and a pole line, not a pole point', () => {
  const { placeEqualEarth, EQUAL_EARTH_HALF } = projection;
  // The paper's figure: 2.055:1, against Mollweide's 2:1.
  assert.ok(Math.abs(1 / EQUAL_EARTH_HALF - 2.0552) < 1e-3, String(1 / EQUAL_EARTH_HALF));
  const [x, y] = placeEqualEarth(0, 0);
  assert.ok(Math.abs(x) < 1e-12 && Math.abs(y) < 1e-12);
  assert.ok(Math.abs(placeEqualEarth(180, 0)[0] - 1) < 1e-9, 'the equator reaches the full width');
  assert.ok(Math.abs(placeEqualEarth(0, 90)[1] - EQUAL_EARTH_HALF) < 1e-9, 'the pole reaches the full height');
  // The pole is a line 59% of the equator's width; Mollweide's is a point.
  assert.ok(Math.abs(placeEqualEarth(180, 90)[0] - 0.5925) < 1e-3, String(placeEqualEarth(180, 90)[0]));
  // Mollweide's own pole is a point; its bisection leaves a millionth there, not a zero.
  assert.ok(Math.abs(projection.placeMollweide(180, 90)[0]) < 1e-4);
  // Equal-area, so the width falls with latitude, but less steeply than Mollweide's.
  for (const lat of [30, 45, 60, 75]) {
    assert.ok(placeEqualEarth(180, lat)[0] > projection.placeMollweide(180, lat)[0]);
  }
});

test('a sheet placement undone returns the longitude and latitude', () => {
  for (const [place, unplace] of [[projection.placeEquirectangular, projection.unplaceEquirectangular],
                                  [projection.placeMollweide, projection.unplaceMollweide],
                                  [projection.placeEqualEarth, projection.unplaceEqualEarth]]) {
    for (const [longitude, latitude] of [[0, 0], [126.98, 37.57], [-87.63, 41.88], [106.8, -78.46], [-179, 89]]) {
      const back = unplace(...place(longitude, latitude));
      close(back[0], longitude);
      close(back[1], latitude);
    }
    assert.equal(unplace(0, 0.6), null);
  }
  assert.equal(projection.unplaceMollweide(0.99, 0.45), null);
  // Past the Equal Earth outline at that latitude, and past its shorter half-height.
  assert.equal(projection.unplaceEqualEarth(0.99, 0.45), null);
  assert.equal(projection.unplaceEqualEarth(0, 0.49), null);
});
