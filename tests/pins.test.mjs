import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { RotationModel } from '../static/core/rotation.js';
import { carried, distanceKm, drawnAt, formatPins, inside, parsePins, pinAt, reachOf }
  from '../static/core/pins.js';

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
  // Number('') is 0: an empty coordinate is not the Gulf of Guinea, nor 20 E on the equator.
  assert.deepEqual(parsePins(',;20,;,5;1e2,3; 4,5'), []);
  assert.deepEqual(parsePins('-0.5,-89'), [[-0.5, -89]]);
  assert.deepEqual(parsePins(null), []);
  assert.equal(formatPins([{ lon: 126.978, lat: 37.566 }]), '126.98,37.57');
});

test('a plate is carried no further back than its poles, whatever its polygon says', () => {
  // Poles to 50 Ma under a polygon dated 4500 Ma, as PALEOMAP dates many of its cratons.
  const model = new RotationModel({ anchor: 0, sequences: { '1:0': [0, 90, 0, 0, 50, 90, 0, 40] } });
  assert.equal(reachOf(model, 1, 4500, 1100), 50);
  assert.equal(reachOf(model, 1, 30, 1100), 30);
  assert.equal(reachOf(model, 1, 4500, 20), 20);
  const pin = { lon: 10, lat: 20, pid: 1, from: 4500, reach: 50 };
  assert.ok(carried(model, pin, 50));
  assert.equal(carried(model, pin, 51), null);
});

test('ground between two maps is drawn where the travel field, undone, returns it', () => {
  // A field that varies from place to place, so one step from the origin is not enough.
  const travel = (longitude, latitude) => [6 * Math.exp(-((longitude - 20) ** 2 + latitude ** 2) / 200), 3 * Math.cos(longitude / 30)];
  for (const share of [0.5, -0.5, 1]) {
    const origin = [12, 4];
    const drawn = drawnAt(origin, travel, share);
    const [east, north] = travel(drawn[0], drawn[1]);
    assert.ok(Math.abs(drawn[0] - share * east - origin[0]) < 1e-3, `longitude at ${share}`);
    assert.ok(Math.abs(drawn[1] - share * north - origin[1]) < 1e-3, `latitude at ${share}`);
  }
  // Across the seam and at a pole the place stays a place.
  assert.ok(Math.abs(drawnAt([179, 0], () => [4, 0], 1)[0] + 177) < 1e-9);
  assert.equal(drawnAt([0, 89], () => [0, 5], 1)[1], 90);
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
    const pin = pinAt(features, model, lon, lat, 0, 1100);
    assert.equal(pin?.pid, pid, name);
    for (const [age, expected] of [[200, at200], [450, at450]]) {
      const there = carried(model, pin, age);
      assert.ok(distanceKm(there, expected) < 0.1, `${name} at ${age} Ma`);
      // Dropped where it stands at that age, the pin is the same present-day place.
      const again = pinAt(features, model, there[0], there[1], age, 1100);
      assert.equal(again?.pid, pid, `${name} dropped at ${age} Ma`);
      assert.ok(distanceKm([again.lon, again.lat], [lon, lat]) < 0.1, `${name} back from ${age} Ma`);
    }
  }
  assert.equal(pinAt(features, model, -30, 0, 0), null, 'mid-Atlantic has no continent polygon');
  // Iceland rides Greenland's plate and is 15 Myr old in this model.
  const reykjavik = pinAt(features, model, -21.94, 64.15, 0, 1100);
  assert.equal(reykjavik.pid, 102);
  assert.equal(reykjavik.reach, 15);
  assert.equal(carried(model, reykjavik, 20), null);
  // Chicago's polygon is dated 4500 Ma; the model covers 1100, and that is its reach.
  assert.equal(pinAt(features, model, -87.63, 41.88, 0, 1100).reach, 1100);
  // Two pins on one plate keep their distance: the model's plates are rigid.
  const chicago = pinAt(features, model, -87.63, 41.88, 0, 1100);
  const winnipeg = pinAt(features, model, -97.14, 49.90, 0, 1100);
  const today = distanceKm([chicago.lon, chicago.lat], [winnipeg.lon, winnipeg.lat]);
  assert.ok(Math.abs(distanceKm(carried(model, chicago, 300), carried(model, winnipeg, 300)) - today) < 0.5);
});
