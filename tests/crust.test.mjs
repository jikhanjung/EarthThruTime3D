import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Vector3} from 'three';
import {decodeGrid, sampleGrid, shellRadius, cutRing} from '../static/core/crust.js';

test('grid decoding distinguishes missing, zero, poles, hemispheres and longitude wrap', () => {
  const bytes = new ArrayBuffer(129600), view = new DataView(bytes);
  view.setUint16(0, 65535, true);
  view.setUint16((179 * 360) * 2, 8000, true);
  view.setUint16((90 * 360 + 180) * 2, 3542, true);
  const grid = decodeGrid(bytes);
  assert.equal(sampleGrid(grid, -180, -90), null);
  assert.equal(sampleGrid(grid, 180, 90), 80);
  assert.equal(sampleGrid(grid, -540, 90), 80);
  assert.equal(sampleGrid(grid, .5, .5), 35.42);
  assert.equal(sampleGrid(grid, 1.5, .5), 0);
  view.setUint16(2, 8001, true);
  assert.throws(() => decodeGrid(bytes));
  assert.throws(() => decodeGrid(new ArrayBuffer(1)));
});

test('radial thickness uses km at true scale and declared exaggeration', () => {
  for (const scale of [1, 5]) {
    assert.ok(Math.abs((1.02 - shellRadius(1.02, 40, scale)) * 6371 - 40 * scale) < 1e-9);
  }
});

test('cut ring is closed and stays on the small circle at poles and date line', () => {
  for (const centre of [new Vector3(0,1,0), new Vector3(0,-1,0), new Vector3(-1,0,0), new Vector3(.1,.8,.4).normalize()]) {
    for (const angle of [10, 45, 90]) {
      const cosine = Math.cos(angle * Math.PI / 180), ring = cutRing(centre, cosine);
      assert.ok(ring[0].distanceTo(ring.at(-1)) < 1e-12);
      for (const point of ring) {
        assert.ok(Math.abs(point.length() - 1) < 1e-12);
        assert.ok(Math.abs(point.dot(centre) - cosine) < 1e-12);
      }
    }
  }
});
