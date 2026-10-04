import test from 'node:test';
import assert from 'node:assert/strict';
import { fadeOf, markCorners, markShift, ribbonParts, seamOf, sectionTitle } from '../static/core/circulation.js';

test('a bottom-water line fades out over its last 25 points; the others do not', () => {
  const points = Array.from({ length: 40 }, (_, i) => [i, 0]);
  const fade = fadeOf({ points, fade: true });
  assert.equal(fade[0], 1);
  assert.equal(fade[14], 1);
  assert.equal(fade[39], 0);
  assert.equal(fade[27], 12 / 25);
  assert.ok(fadeOf({ points, fade: false }).every((alpha) => alpha === 1));
});

test('a flat map\'s edge is found from the centre longitude; the globe has none', () => {
  const atZero = seamOf('equalearth', 0);
  assert.equal(atZero(179, -179), true);
  assert.equal(atZero(-10, 10), false);
  const atHundredEighty = seamOf('mollweide', 180);
  assert.equal(atHundredEighty(179, -179), false);
  assert.equal(atHundredEighty(-1, 1), true);
  assert.equal(seamOf('globe', 0)(179, -179), false);
});

test('a mark straddling the edge moves whole to one side; others stay', () => {
  const seam = seamOf('equalearth', 0);
  const ross = ['sink', 172, -77.5];
  const shift = markShift(ross, seam);
  assert.notEqual(shift, 0);
  assert.equal(seam(...markCorners([ross[0], ross[1] + shift, ross[2]], 3.3).map((c) => c[0])), false);
  assert.equal(markShift(['sink', -50, -73.5], seam), 0);
  assert.equal(markShift(ross, seamOf('globe', 0)), 0);
});

test('the ribbons are built once in degrees: three vertices and four colour values each', () => {
  const lines = [{ kind: 'deep', fade: false, points: Array.from({ length: 40 }, (_, i) => [i, -50]) }];
  const deep = ribbonParts(lines).filter((part) => part.corners.length);
  assert.equal(deep.length, 2);                       // its rim and fill
  for (const part of deep) {
    assert.equal(part.corners.length / 2 * 4, part.colours.length);
    assert.equal((part.corners.length / 2) % 3, 0);
  }
});

test('a section title names the numbers where they were read', () => {
  const L = { basinAtlantic: 'Atlantic', basinIndoPacific: 'Indo-Pacific', sectionRed: 'red {sv} Sv at {lat}',
    sectionBlue: 'blue {sv} Sv at {lat}' };
  const fmt = (text, values) => text.replace(/\{(\w+)\}/g, (match, key) => values[key]);
  assert.equal(sectionTitle({ basin: 'atlantic', red: { lat: 26.5, sv: 10.1 }, blue: { lat: -30, sv: 1.6 } }, L, fmt),
    'Atlantic · red 10.1 Sv at 26.5°N · blue 1.6 Sv at 30°S');
  assert.equal(sectionTitle({ basin: 'indopacific', blue: { lat: -30, sv: 1.6 } }, L, fmt),
    'Indo-Pacific · blue 1.6 Sv at 30°S');
});
