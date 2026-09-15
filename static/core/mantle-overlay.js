import * as THREE from 'three';

// Earth-local coordinates: geographic xyz → (x,z,-y); no depth exaggeration.
export function overlayMatrix(rotation) {
  const r = rotation;
  return new THREE.Matrix4().set(
    r[0][0], r[0][1], r[0][2], 0,
    r[2][0], r[2][1], r[2][2], 0,
    -r[1][0], -r[1][1], -r[1][2], 0,
    0, 0, 0, 1);
}

// Shared local-space cut: climate/ice live in the surface shader, lines share it.
export const CUT_UNIFORMS = `
  uniform float mantleCutaway;
  uniform vec3 mantleCutCentre;
  uniform float mantleCutCos;
  varying vec3 vCutPosition;`;
export const CUT_SURFACE = `
  if (mantleCutaway > 0.5 && dot(normalize(vCutPosition), mantleCutCentre) > mantleCutCos) discard;`;

const $ = id => document.getElementById(id);
function dispose(group) {
  group?.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
  group?.removeFromParent();
}

export function closestFrame(frames, age) {
  return frames.reduce((a,b)=>Math.abs(b.age_ma-age)<Math.abs(a.age_ma-age)?b:a);
}
export function sectionPath(rotation) {
  const matrix=overlayMatrix(rotation);
  return Array.from({length:101},(_,i)=>{
    const lat=(-40+i)*Math.PI/180,lon=85*Math.PI/180;
    return new THREE.Vector3(Math.cos(lat)*Math.cos(lon),Math.cos(lat)*Math.sin(lon),Math.sin(lat))
      .applyMatrix4(matrix).multiplyScalar(1.006);
  });
}
export function createMantleOverlay({config, earth, uniforms, stage, surfaceMaterial, capture, enter, focus, restore, getCamera}) {
  if (!config || !$('mantle-overlay')) return null;
  const toggle=$('mantle-overlay'), options=$('mantle-overlay-options'), caption=$('mantle-overlay-caption');
  const status=$('mantle-overlay-status'), retry=$('mantle-overlay-retry');
  let active=false,saved=null,controller=null,displayed=null,trace=null,debounce=null,frame=config.frames[0],ready=false;
  const centre=new THREE.Vector3();
  const fmt=(s)=>s.replace('{age}',String(frame.age_ma));
  const message=s=>{status.textContent=fmt(s);caption.textContent=fmt(s)};
  function linkedState() {
    document.dispatchEvent(new CustomEvent('globe-section-state',{detail:{active,ready,age:frame.age_ma,error:stage.dataset.mantleOverlay==='error'}}));
  }
  function visibility() {
    const opacity=active&&ready?Number($('mantle-opacity').value)/100:1;
    uniforms.mantleSurfaceOpacity.value=opacity;
    if(surfaceMaterial.transparent!==(opacity<1)) {surfaceMaterial.transparent=opacity<1;surfaceMaterial.needsUpdate=true;}
    surfaceMaterial.depthWrite=opacity===1;
    uniforms.mantleCutaway.value=active&&ready&&$('mantle-cutaway').checked?1:0;

    if(displayed) {
      displayed.visible=ready;
      for(const name of ['slabs','piles','core'])displayed.getObjectByName(name).visible=$(`overlay-${name}`).checked;
    }
    if(trace)trace.visible=active&&ready&&$('mantle-section').checked;
    stage.dataset.mantleCutaway=String(uniforms.mantleCutaway.value===1);
    stage.dataset.mantleOpacity=String(opacity);
  }
  function cutPosition() {
    const lon=Number($('mantle-longitude').value)*Math.PI/180,lat=Number($('mantle-latitude').value)*Math.PI/180;
    centre.set(Math.cos(lat)*Math.cos(lon),Math.sin(lat),-Math.cos(lat)*Math.sin(lon));
    uniforms.mantleCutCentre.value.copy(centre);
    uniforms.mantleCutCos.value=Math.cos(Number($('mantle-radius').value)*Math.PI/180);
    for(const id of ['longitude','latitude','radius'])$(`mantle-${id}-value`).textContent=$(`mantle-${id}`).value+'°';
    $('mantle-opacity-value').textContent=$('mantle-opacity').value+'%';
    visibility();
  }
  function removeTrace() {
    trace?.traverse(o=>o.material?.map?.dispose());dispose(trace);trace=null;
  }
  function buildTrace() {
    removeTrace();trace=new THREE.Group();
    const path=sectionPath(frame.rotation_matrix);
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(path),new THREE.LineBasicMaterial({color:0xff83b2}));
    line.name='section-line';trace.add(line);
    for(const [text,point] of [['A',path[0]],["A′",path.at(-1)]]) {
      const canvas=document.createElement('canvas');canvas.width=80;canvas.height=64;
      const ctx=canvas.getContext('2d');ctx.fillStyle='#ffb9d2';ctx.font='bold 44px sans-serif';ctx.fillText(text,4,48);
      const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas)}));
      sprite.position.copy(point).multiplyScalar(1.014);sprite.scale.set(.065,.052,1);trace.add(sprite);
    }
    earth.add(trace);
  }
  function leave(restorePrevious=true) {
    if(!active)return;
    active=false;ready=false;controller?.abort();controller=null;clearTimeout(debounce);
    dispose(displayed);displayed=null;removeTrace();
    toggle.checked=false;options.hidden=true;retry.hidden=true;caption.hidden=true;
    $('play').disabled=false;stage.dataset.mantleOverlay='off';delete stage.dataset.mantleAge;visibility();linkedState();
    const previous=saved;saved=null;if(restorePrevious&&previous)restore(previous);
  }
  async function load(first=false) {
    controller?.abort();const pending=new AbortController();controller=pending;
    const selected=frame;ready=false;stage.dataset.mantleOverlay='loading';visibility();linkedState();
    message(config.strings.loading);retry.hidden=true;caption.hidden=false;stage.dataset.mantleOverlay='loading';
    let next=null;
    try {
      await enter(selected.age_ma,first);
      if(pending.signal.aborted||!active)return;
      const payloads=await Promise.all(['slabs','piles'].map(async name=>{
        const info=selected.layers[name],response=await fetch(info.url,{signal:pending.signal});
        if(!response.ok)throw new Error(`HTTP ${response.status}`);
        const buffer=await response.arrayBuffer();
        if(info.primitive!=='triangles'||info.indices%3||buffer.byteLength!==info.bytes||info.bytes!==info.points*12+info.indices*4)throw new Error('Invalid mantle mesh length');
        const positions=new Float32Array(buffer,0,info.points*3),indices=new Uint32Array(buffer,info.points*12,info.indices);
        if(positions.some(v=>!Number.isFinite(v))||indices.some(i=>i>=info.points))throw new Error('Invalid mantle mesh');
        return {name,positions,indices};
      }));
      if(pending.signal.aborted||!active)return;
      next=new THREE.Group();next.add(new THREE.HemisphereLight(0xdbefff,0x152234,2));
      const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(2,3,2);next.add(light);
      const matrix=overlayMatrix(selected.rotation_matrix);
      for(const {name,positions,indices} of payloads) {
        const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.setIndex(new THREE.BufferAttribute(indices,1));
        geometry.applyMatrix4(matrix);geometry.computeVertexNormals();
        const material=new THREE.MeshStandardMaterial({color:name==='slabs'?0x529dd6:0xef9546,side:THREE.DoubleSide,roughness:.8});
        const mesh=new THREE.Mesh(geometry,material);mesh.name=name;next.add(mesh);
      }
      const core=new THREE.Mesh(new THREE.SphereGeometry(.546,64,32),new THREE.MeshStandardMaterial({color:0x69727c,roughness:.85}));
      core.name='core';next.add(core);
      dispose(displayed);displayed=next;next=null;earth.add(displayed);buildTrace();ready=true;visibility();
      stage.dataset.mantleOverlay='ready';stage.dataset.mantleAge=String(selected.age_ma);
      $('mantle-age').value=String(selected.age_ma);
      $('mantle-residual').textContent=config.strings.residual.replace('{error}',selected.india_position_p95_deg.toFixed(2));
      message(config.strings.ready);linkedState();
      if(first&&matchMedia('(max-width:899px)').matches){$('inspector').classList.add('closed');$('info-toggle').setAttribute('aria-expanded','false');$('info-toggle').focus();}
    } catch(error) {
      dispose(next);
      if(!pending.signal.aborted&&active){pending.abort();ready=false;dispose(displayed);displayed=null;removeTrace();visibility();stage.dataset.mantleOverlay='error';linkedState();message(config.strings.error);retry.hidden=false;}
    }
  }
  function requestAge(age) {
    if(!active)return false;
    if(!Number.isFinite(age)||age<0||age>80){leave(false);return false;}
    const next=closestFrame(config.frames,age);
    if(next===frame&&ready&&age===frame.age_ma)return false;
    controller?.abort();clearTimeout(debounce);frame=next;ready=false;stage.dataset.mantleOverlay='loading';visibility();linkedState();
    delete stage.dataset.mantleAge;stage.dataset.mantleOverlay='loading';message(config.strings.loading);
    $('mantle-age').value=String(frame.age_ma);debounce=setTimeout(()=>load(),180);return true;
  }
  toggle.addEventListener('change',()=>{
    if(!toggle.checked){leave();return;}
    saved=capture();active=true;$('play').disabled=true;frame=config.frames[0];options.hidden=false;cutPosition();load(true);
  });
  retry.addEventListener('click',()=>load());
  $('mantle-age').addEventListener('change',()=>requestAge(Number($('mantle-age').value)));
  for(const id of ['mantle-cutaway','overlay-slabs','overlay-piles','overlay-core','mantle-section'])$(id).addEventListener('change',visibility);
  for(const id of ['longitude','latitude','radius','opacity'])$(`mantle-${id}`).addEventListener('input',cutPosition);
  $('mantle-focus').addEventListener('click',()=>focus(centre));
  document.addEventListener('globe-section-age',e=>{if(active&&[80,60,40,20,0].includes(e.detail.age))requestAge(e.detail.age)});
  const raycaster=new THREE.Raycaster();raycaster.params.Line.threshold=.02;let down;
  stage.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY]});
  stage.addEventListener('pointerup',e=>{
    if(!active||!ready||!trace?.visible||!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
    const box=stage.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((e.clientX-box.left)/box.width*2-1,-(e.clientY-box.top)/box.height*2+1),getCamera());
    const hit=raycaster.intersectObject(trace.getObjectByName('section-line'))[0];
    if(hit&&hit.point.dot(getCamera().position.clone().sub(hit.point))>0)$('mantle-section-open').click();
  });
  stage.dataset.mantleOverlay='off';
  return {leave,requestAge,isActive:()=>active,neighbourAge:direction=>active?config.frames[Math.max(0,Math.min(config.frames.length-1,config.frames.indexOf(frame)+direction))].age_ma:null,onProjection:name=>{if(active&&name!=='globe')leave(false)},
    cutsPoint:point=>uniforms.mantleCutaway.value>.5&&point.clone().normalize().dot(centre)>uniforms.mantleCutCos.value};
}
