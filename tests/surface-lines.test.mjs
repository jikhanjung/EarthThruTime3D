import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {densifySegments} from '../static/core/surface-lines.js';

test('long surface lines keep endpoints and stay above the chord clearance', () => {
  const a = new THREE.Vector3(1, 0, 0);
  const b = new THREE.Vector3(Math.cos(.04), Math.sin(.04), 0);
  const points = densifySegments([a, b]);
  assert.equal(points[0], a);
  assert.equal(points.at(-1), b);
  assert.ok(points.length > 2);
  for (let i = 0; i < points.length; i += 2) {
    assert.ok(1 - points[i].clone().add(points[i + 1]).multiplyScalar(.5).length() < 4e-7);
    assert.ok(Math.abs(points[i].length() - 1) < 1e-12);
  }
});

test('seam-crossing lines follow the short arc and disconnected segments stay separate', () => {
  const at = degrees => new THREE.Vector3(Math.cos(degrees * Math.PI / 180), 0, Math.sin(degrees * Math.PI / 180));
  const a = at(179), b = at(-179), c = at(0), d = at(.05);
  const points = densifySegments([a, b, c, d]);
  assert.ok(points.slice(0, -2).every(point => point.x < -.99));
  assert.equal(points.at(-2), c);
  assert.equal(points.at(-1), d);
});
