import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { buildBelt, fadeOf } from '../static/core/circulation.js';

test('a bottom-water line fades out over its last 25 points; the others do not', () => {
  const points = Array.from({ length: 40 }, (_, i) => [i, 0]);
  const fade = fadeOf({ points, fade: true });
  assert.equal(fade[0], 1);
  assert.equal(fade[14], 1);
  assert.equal(fade[39], 0);
  assert.equal(fade[27], 12 / 25);
  assert.ok(fadeOf({ points, fade: false }).every((alpha) => alpha === 1));
});

test('the belt leaves out every triangle across a flat map\'s seam', () => {
  const data = { lines: [{ kind: 'deep', fade: false, points: Array.from({ length: 40 }, (_, i) => [i, -50]) }],
    marks: [['sink', -2, 74.5], ['rise', 162, 40]] };
  const place = (lon, lat) => new THREE.Vector3(lon, lat, 0);
  const count = (group) => group.children.reduce((sum, mesh) => sum + mesh.geometry.attributes.position.count, 0);
  const drawn = count(buildBelt(data, place, () => false));
  assert.ok(drawn > 0);
  assert.equal(count(buildBelt(data, place, () => true)), 0);
});
