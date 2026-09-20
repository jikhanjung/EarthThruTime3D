import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { RotationModel } from '../static/core/rotation.js';
import { carried, distanceKm, formatPins, inside, parsePins, pinAt } from '../static/core/pins.js';

test('a ring holds what is inside it, across the antimeridian and over a pole', () => {
  const box = [-10, -10, 10, -10, 10, 10, -10, 10];
  assert.ok(inside(0, 0, box));
  assert.ok(!inside(20, 0, box));
  const seam = [170, -10, -170, -10, -170, 10, 170, 10];
  assert.ok(inside(180, 0, seam));
  assert.ok(inside(-175, 5, seam));
  assert.ok(!inside(160, 0, seam));
  const cap = [0, 80, 90, 80, 180, 80, -90, 80];
  assert.ok(inside(45, 89, cap));
  assert.ok(inside(0, 90, cap));
  assert.ok(!inside(45, 70, cap));
});

test('a quarter of the equator is a quarter of the way round', () => {
  assert.ok(Math.abs(distanceKm([0, 0], [90, 0]) - Math.PI / 2 * 6371) < 1e-6);
  assert.ok(Math.abs(distanceKm([170, 0], [-170, 0]) - Math.PI / 9 * 6371) < 1e-6);
});

test('the address keeps at most three well-formed pins', () => {
  assert.deepEqual(parsePins('126.98,37.57;-87.63,41.88'), [[126.98, 37.57], [-87.63, 41.88]]);
  assert.deepEqual(parsePins('1,2;3,4;5,6;7,8').length, 3);
  assert.deepEqual(parsePins('200,0;x,1;;1,2,3'), []);
  assert.deepEqual(parsePins(null), []);
  assert.equal(formatPins([{ lon: 126.978, lat: 37.566 }]), '126.98,37.57');
});

test('pins on the packed PALEOMAP model agree with scripts/assess_pin.py', (t) => {
  const base = new URL('../data/derived/plates/paleomap2016/', import.meta.url);
  if (!existsSync(new URL('rotations.json', base))) return t.skip('run scripts/pack_plates.py first');
  const model = new RotationModel(JSON.parse(readFileSync(new URL('rotations.json', base), 'utf8')));
  const { features } = JSON.parse(readFileSync(new URL('continents.json', base), 'utf8'));
  // Plate and carried positions as scripts/assess_pin.py gives them.
  const cases = [['Chicago', -87.63, 41.88, 101, [-31.4918, 21.4404], [-59.6217, -21.8552]],
                 ['Seoul', 126.98, 37.57, 604, [133.9388, 46.1732], [126.4587, -11.202]],
                 ['Vostok', 106.80, -78.46, 802, [44.1347, -46.481], [172.4699, -7.3409]]];
  for (const [name, lon, lat, pid, at200, at450] of cases) {
    const pin = pinAt(features, model, lon, lat, 0);
    assert.equal(pin?.pid, pid, name);
    for (const [age, expected] of [[200, at200], [450, at450]]) {
      const there = carried(model, pin, age);
      assert.ok(distanceKm(there, expected) < 0.1, `${name} at ${age} Ma`);
      // Dropped where it stands at that age, the pin is the same present-day place.
      const again = pinAt(features, model, there[0], there[1], age);
      assert.equal(again?.pid, pid, `${name} dropped at ${age} Ma`);
      assert.ok(distanceKm([again.lon, again.lat], [lon, lat]) < 0.1, `${name} back from ${age} Ma`);
    }
  }
  assert.equal(pinAt(features, model, -30, 0, 0), null, 'mid-Atlantic has no continent polygon');
  // Iceland rides Greenland's plate and is 15 Myr old in this model.
  const reykjavik = pinAt(features, model, -21.94, 64.15, 0);
  assert.equal(reykjavik.pid, 102);
  assert.equal(carried(model, reykjavik, 20), null);
  // Two pins on one plate keep their distance: the model's plates are rigid.
  const chicago = pinAt(features, model, -87.63, 41.88, 0);
  const winnipeg = pinAt(features, model, -97.14, 49.90, 0);
  const today = distanceKm([chicago.lon, chicago.lat], [winnipeg.lon, winnipeg.lat]);
  assert.ok(Math.abs(distanceKm(carried(model, chicago, 300), carried(model, winnipeg, 300)) - today) < 0.5);
});
