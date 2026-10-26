import {test} from 'node:test';
import assert from 'node:assert/strict';
import {OCEAN, WIND, WIPE_PX, advance, decodeField, legendSteps, momentText, sampleField, speedBin, trailFade, warpField} from '../static/core/flux.js';

function field(width, height, fill, centred) {
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < width * height; i++) {
    const [r, g, b] = fill(i % width, Math.floor(i / width));
    rgba.set([r, g, b, 255], i * 4);
  }
  return decodeField(rgba, width, height, {u: [-10, 10], v: [-5, 5]}, centred);
}

test('wind decodes to m/s and samples grid nodes with longitude wrap', () => {
  // 1440x721 nodes from -180, 90: column 0 is -180, row 360 the equator
  const wind = field(1440, 721, (x) => [x === 0 ? 255 : 0, 255, 0], false);
  assert.deepEqual(sampleField(wind, -180, 0), [10, 5]);
  assert.deepEqual(sampleField(wind, 180, 0), [10, 5]);
  assert.deepEqual(sampleField(wind, 0, 0), [-10, 5]);
  const [u] = sampleField(wind, -179.875, 0);
  assert.ok(Math.abs(u - 0) < 1e-6, 'halfway between the seam column and its neighbour');
  assert.notEqual(sampleField(wind, 0, 90), null);
});

test('currents sample cell centres and return null on land', () => {
  // 1440x720 cells; the western half is sea, the eastern half land
  const ocean = field(1440, 720, (x) => [128, 128, x < 720 ? 255 : 0], true);
  assert.notEqual(sampleField(ocean, -90, 10), null);
  assert.equal(sampleField(ocean, 90, 10), null);
  assert.equal(sampleField(ocean, 0, 89.99), null, 'past the last cell centre');
});

test('a step moves east by u and north by v, wider near the poles, and wraps', () => {
  const metresPerDegree = Math.PI * 6371000 / 180;
  const [lon, lat] = advance(0, 0, 1, 0, metresPerDegree);
  assert.ok(Math.abs(lon - 1) < 1e-9 && lat === 0);
  const [, north] = advance(0, 0, 0, 1, metresPerDegree);
  assert.ok(Math.abs(north - 1) < 1e-9);
  const [high] = advance(0, 60, 1, 0, metresPerDegree);
  assert.ok(Math.abs(high - 2) < 1e-9);
  assert.ok(Math.abs(advance(179.5, 0, 1, 0, metresPerDegree)[0] + 179.5) < 1e-9);
});

test('speed bins and the legend share their steps', () => {
  assert.equal(speedBin(0, 12), 0);
  assert.equal(speedBin(4, 12), 1);
  assert.equal(speedBin(100, 12), 7);
  const wind = legendSteps(WIND, WIND.ref['10m']);
  assert.deepEqual(wind[0], ['0–4', WIND.colours[0]]);
  assert.equal(wind[7][0], '> 28');
  assert.equal(legendSteps(OCEAN, OCEAN.ref)[1][0], '0.10–0.20');
});

test('the moment is written in UTC first, the visitor clock after', () => {
  assert.match(momentText('2026-10-01T18:00Z', 'en'), /^2026-10-01 18:00 UTC/);
  assert.equal(momentText('2026-10-01T18:00Z', 'not a locale!!').slice(0, 20), '2026-10-01 18:00 UTC');
});

test('trails fade with the view shift, continuously, down to a wipe', () => {
  assert.equal(trailFade(WIND.fade, 0), WIND.fade);
  let last = WIND.fade;
  for (let moved = 0; moved <= WIPE_PX; moved += 0.05) {
    const kept = trailFade(WIND.fade, moved);
    assert.ok(kept <= last + 1e-12, 'never longer for a larger shift');
    assert.ok(last - kept < 0.03, `no jump at ${moved} px`);
    last = kept;
  }
  assert.ok(trailFade(WIND.fade, WIPE_PX) < 0.01, 'nearly wiped where the wipe takes over');
});

test('a past field: code 128 is still water, and a warp moves sea and flow together', () => {
  // 360x180 one-degree cells over a symmetric range; sea from 0 to 20 E flowing east, land elsewhere.
  const m = 0.5;
  const range = {u: [-m * 128 / 127, m], v: [-m * 128 / 127, m]};
  const rgba = new Uint8ClampedArray(360 * 180 * 4);
  for (let i = 0; i < 360 * 180; i++) {
    const sea = i % 360 >= 180 && i % 360 < 200;
    rgba.set([sea ? 255 : 128, 128, sea ? 255 : 0, 255], i * 4);
  }
  const past = decodeField(rgba, 360, 180, range, true);
  assert.ok(Math.abs(past.v[0]) < 1e-9, 'code 128 decodes to exactly zero');
  assert.ok(Math.abs(sampleField(past, 10, 0)[0] - m) < 1e-9);
  assert.equal(sampleField(past, 25, 0), null);
  // The map moved 10 degrees east: the sea and its flow move with it.
  const moved = warpField(past, () => [10, 0]);
  assert.ok(Math.abs(sampleField(moved, 25, 0)[0] - m) < 1e-9);
  assert.equal(sampleField(moved, 5, 0), null);
  assert.equal(warpField(past, () => [0, 0]).sea.join(), past.sea.join(), 'no shift, same sea');
});
