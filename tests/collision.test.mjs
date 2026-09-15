import test from 'node:test';
import assert from 'node:assert/strict';
import { crustState } from '../static/core/collision-math.js';
import { terrainPosition } from '../static/core/collision-surface.js';

test('Terrain exaggeration changes only land height; sea level and horizontal position stay fixed', () => {
  const original = terrainPosition(85, 30, 4000, 1);
  const exaggerated = terrainPosition(85, 30, 4000, 50);
  assert.equal(exaggerated[0], original[0]);
  assert.equal(exaggerated[2], original[2]);
  assert.equal(exaggerated[1], original[1]*50);
  assert.equal(terrainPosition(85, 30, -4000, 50)[1], 0);
});

test('No deformation before the selected onset or with zero imposed shortening', () => {
  for (const age of [80, 65, 60]) {
    assert.equal(crustState(age).thickness, 35);
    assert.equal(crustState(age).uplift, 0);
  }
  assert.equal(crustState(0, 60, 0).thickness, 35);
});
test('Each material column conserves cross-sectional area throughout the scenario', () => {
  for (const onset of [50, 60, 65]) for (let age=0; age<=80; age++) {
    const state = crustState(age, onset, 1000);
    assert.ok(Math.abs(state.width*state.thickness - 2000*35) < 1e-8);
    assert.ok(state.uplift >= 0 && state.width > 0);
  }
  assert.equal(crustState(0).thickness, 70);
  assert.ok(crustState(40, 60).thickness > crustState(40, 50).thickness);
});
test('Reject inputs outside the documented scenario domain', () => {
  for (const args of [[-1], [81], [NaN], [0, 0], [0, 60, 2000], [0, 60, -1]]) {
    assert.throws(() => crustState(...args));
  }
});
