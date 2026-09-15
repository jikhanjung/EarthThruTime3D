import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Matrix4,Vector3} from 'three';
import {overlayMatrix} from '../static/core/mantle-overlay.js';
const config=JSON.parse(readFileSync(new URL('../annotations/mantle-overlay-80ma.json',import.meta.url)));
const audit=JSON.parse(readFileSync(new URL('../docs/validation/mantle-frame-alignment.json',import.meta.url)));
test('approximate overlay uses the audited 80 Ma transform and preserves depth',()=>{
 assert.equal(config.age_ma,80);assert.equal(config.mode,'approximate_overlay');
 assert.deepEqual(config.rotation_matrix,audit.frames.find(f=>f.age_ma===80).africa_anchor.opt1_to_paleomap_matrix);
 const m=overlayMatrix(config.rotation_matrix);
 assert.ok(Math.abs(m.determinant()-1)<1e-12);
 for(const v of [new Vector3(.5,.2,.3),new Vector3(0,0,1)]){
  const p=v.clone().applyMatrix4(m);
  assert.ok(Math.abs(p.length()-v.length())<1e-12);
  assert.ok(p.applyMatrix4(m.clone().invert()).distanceTo(v)<1e-12);
 }
});
test('geographic-to-globe axis mapping is proper and not reflected',()=>{
 const m=overlayMatrix([[1,0,0],[0,1,0],[0,0,1]]);
 assert.deepEqual(new Vector3(1,0,0).applyMatrix4(m).toArray(),[1,0,0]);
 assert.deepEqual(new Vector3(0,1,0).applyMatrix4(m).toArray(),[0,0,-1]);
 assert.deepEqual(new Vector3(0,0,1).applyMatrix4(m).toArray(),[0,1,0]);
 assert.ok(m.clone().multiply(m.clone().invert()).equals(new Matrix4()));
});
