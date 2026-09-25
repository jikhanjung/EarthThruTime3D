import test from 'node:test';
import assert from 'node:assert/strict';
import { KINDS, eventsAt, fractionalIndex, setEvents, spanText } from '../static/core/climate-events.js';
import { CLIMATE_EVENTS } from '../static/core/climate-events-data.js';

test('every event is well formed', () => {
  const ids = new Set();
  for (const event of CLIMATE_EVENTS) {
    assert.ok(!ids.has(event.id), event.id);
    ids.add(event.id);
    assert.ok(event.start_ma >= event.end_ma, event.id);
    if (event.peak_ma != null) assert.ok(event.peak_ma <= event.start_ma && event.peak_ma >= event.end_ma, event.id);
    assert.ok(event.kind.length && event.kind.every(kind => kind in KINDS), event.id);
    assert.ok(event.what && event.what_ko && event.name_ko, event.id);
    assert.ok(event.cites.length && event.cites.every(cite => /^10\.\d{4,9}\/\S+$/.test(cite.doi)), event.id);
  }
});

test('an age maps between the two stops that bracket it', () => {
  const stops = [[0, 1, 0, 100], [1, 2, 0, 50], [2, 2, 0, 0]];
  assert.equal(fractionalIndex(stops, 75), 0.5);
  assert.equal(fractionalIndex(stops, 200), 0);
  assert.equal(fractionalIndex(stops, -1), 2);
});

test('spans read apart at their own scale', () => {
  assert.equal(spanText({ start_ma: 251.941, end_ma: 251.880 }), '251.941–251.88 Ma');
  assert.equal(spanText({ start_ma: 66.043, end_ma: 66.043 }), '66.04 Ma');
  assert.equal(spanText({ start_ma: 0.0265, end_ma: 0.019 }), '26.5–19 ka');
  assert.equal(spanText({ start_ma: 16.9, end_ma: 14.7 }), '16.9–14.7 Ma');
});

test('the whole timeline and the time windows each show their own events', () => {
  setEvents(CLIMATE_EVENTS);
  const whole = [[0, 1, 0, 60], [1, 2, 0, 55], [2, 3, 0, 50], [3, 3, 0, 45]];
  // A stop covers half the gap to each neighbour, so every moment belongs to its nearest stop:
  // 55 Ma holds the PETM and the start of the EECO (53.26 Ma), 50 Ma the EECO alone.
  assert.deepEqual(eventsAt(whole, 1).map(event => event.id), ['petm', 'eeco']);
  assert.deepEqual(eventsAt(whole, 2).map(event => event.id), ['eeco']);
  assert.deepEqual(eventsAt(whole, 3).map(event => event.id), []);
  const window = [[0, 1, 0, 0.022], [1, 2, 0, 0.021], [2, 2, 0, 0.020]];
  assert.deepEqual(eventsAt(window, 1).map(event => event.id), ['lgm']);
  // The first and last stop have one neighbour, so that side's spacing stands for both;
  // clamping the pair instead would leave them a quarter of a spacing rather than a half.
  const ends = [[0, 1, 0, 56.2], [1, 2, 0, 51.2], [2, 2, 0, 46.2]];
  assert.deepEqual(eventsAt(ends, 0).map(event => event.id), ['petm'], 'the oldest stop reaches back a half spacing');
  assert.deepEqual(eventsAt([[0, 1, 0, 5]], 0).map(event => event.id), []);
});
