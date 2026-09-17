import {test} from 'node:test';
import assert from 'node:assert/strict';
import {decodeGrid, sampleGrid, shellRadius} from '../static/core/crust.js';

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
