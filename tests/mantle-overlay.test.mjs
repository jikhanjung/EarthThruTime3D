import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Matrix4,Vector3} from 'three';
import {overlayMatrix,closestFrame,sectionPath} from '../static/core/mantle-overlay.js';
const config=JSON.parse(readFileSync(new URL('../annotations/mantle-overlay.json',import.meta.url)));
const audit=JSON.parse(readFileSync(new URL('../docs/validation/mantle-frame-alignment.json',import.meta.url)));
test('approximate overlay uses the audited 80 Ma transform and preserves depth',()=>{
 const sample=config.frames[0];assert.equal(sample.age_ma,80);assert.equal(config.mode,'approximate_overlay');
 assert.deepEqual(sample.rotation_matrix,audit.frames.find(f=>f.age_ma===80).africa_anchor.opt1_to_paleomap_matrix);
 const m=overlayMatrix(sample.rotation_matrix);
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

test('all five transforms preserve the original section and snap without interpolation',()=>{
 for(const f of config.frames){
  const path=sectionPath(f.rotation_matrix), inverse=overlayMatrix(f.rotation_matrix).invert();
  const normal=new Vector3(-Math.sin(85*Math.PI/180),Math.cos(85*Math.PI/180),0);
  for(const p of path)assert.ok(Math.abs(p.clone().applyMatrix4(inverse).dot(normal))<1e-12);
 }
 assert.equal(closestFrame(config.frames,31).age_ma,40);
 assert.equal(closestFrame(config.frames,29).age_ma,20);
 assert.equal(closestFrame(config.frames,30).age_ma,40);
});
