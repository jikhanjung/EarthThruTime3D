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

export function createMantleOverlay({config, earth, uniforms, stage, capture, enter, restore}) {
  if (!config || !$('mantle-overlay')) return null;
  const toggle = $('mantle-overlay'), options = $('mantle-overlay-options');
  const status = $('mantle-overlay-status'), retry = $('mantle-overlay-retry');
  const caption = $('mantle-overlay-caption');
  function message(text) {status.textContent=text;caption.textContent=text;}
  let active = false, saved = null, controller = null, displayed = null;
  const rotation = overlayMatrix(config.rotation_matrix);
  const centre = new THREE.Vector3(
    Math.cos(config.cutaway.latitude*Math.PI/180)*Math.cos(config.cutaway.longitude*Math.PI/180),
    Math.sin(config.cutaway.latitude*Math.PI/180),
    -Math.cos(config.cutaway.latitude*Math.PI/180)*Math.sin(config.cutaway.longitude*Math.PI/180));
  uniforms.mantleCutCentre.value.copy(centre);
  uniforms.mantleCutCos.value = Math.cos(config.cutaway.radius_degrees*Math.PI/180);
  function visibility() {
    uniforms.mantleCutaway.value = active && displayed && $('mantle-cutaway').checked ? 1 : 0;
    if (displayed) for (const name of ['slabs','piles']) displayed.getObjectByName(name).visible = $(`overlay-${name}`).checked;
    stage.dataset.mantleCutaway = String(uniforms.mantleCutaway.value === 1);
  }
  function leave(restorePrevious = true) {
    if (!active) return;
    active = false;
    controller?.abort(); controller = null;
    dispose(displayed); displayed = null;
    toggle.checked = false; options.hidden = true; retry.hidden = true;caption.hidden=true;
    stage.dataset.mantleOverlay = 'off';
    visibility();
    const previous = saved; saved = null;
    if (restorePrevious && previous) restore(previous);
  }
  async function load() {
    controller?.abort();
    const pending = new AbortController(); controller = pending;
    message(config.strings.loading); retry.hidden = true;caption.hidden=false;
    stage.dataset.mantleOverlay = 'loading';
    let next = null;
    try {
      await enter(config.age_ma);
      if (pending.signal.aborted || !active) return;
      const payloads = await Promise.all(['slabs','piles'].map(async name => {
        const info = config.layers[name];
        const response = await fetch(info.url, {signal: pending.signal});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const buffer = await response.arrayBuffer();
        if (info.primitive !== 'triangles' || info.indices % 3 || buffer.byteLength !== info.bytes
          || buffer.byteLength !== info.points*12+info.indices*4) throw new Error('Invalid mantle mesh length');
        const positions = new Float32Array(buffer,0,info.points*3);
        const indices = new Uint32Array(buffer,info.points*12,info.indices);
        if (positions.some(v=>!Number.isFinite(v)) || indices.some(i=>i>=info.points)) throw new Error('Invalid mantle mesh coordinates');
        return {name,positions,indices};
      }));
      if (pending.signal.aborted || !active) return;
      next = new THREE.Group();
      // Local lighting only affects these standard materials, not the surface shader.
      next.add(new THREE.HemisphereLight(0xdbefff,0x152234,2));
      const light = new THREE.DirectionalLight(0xffffff,2);light.position.copy(centre).multiplyScalar(4);next.add(light);
      for (const {name,positions,indices} of payloads) {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
        geometry.setIndex(new THREE.BufferAttribute(indices,1));
        geometry.applyMatrix4(rotation);geometry.computeVertexNormals();
        const material = new THREE.MeshStandardMaterial({color:name==='slabs'?0x529dd6:0xef9546,side:THREE.DoubleSide,roughness:.8});
        // Only the radial sector under the opening is included. This prevents the
        // opposite hemisphere's mantle from appearing through a near-side opening.
        material.onBeforeCompile = shader => {
          shader.uniforms.mantleCutCentre = uniforms.mantleCutCentre;
          shader.uniforms.mantleCutCos = uniforms.mantleCutCos;
          shader.vertexShader = 'varying vec3 vSectorPosition;\n'+shader.vertexShader;
          shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvSectorPosition = position;');
          shader.fragmentShader = 'varying vec3 vSectorPosition; uniform vec3 mantleCutCentre; uniform float mantleCutCos;\n'+shader.fragmentShader;
          shader.fragmentShader = shader.fragmentShader.replace('void main() {','void main() {\nif(dot(normalize(vSectorPosition),mantleCutCentre)<mantleCutCos) discard;');
        };
        material.customProgramCacheKey = () => 'mantle-sector-v1';
        const mesh = new THREE.Mesh(geometry,material);mesh.name=name;next.add(mesh);
      }
      dispose(displayed); displayed=next;next=null;
      earth.add(displayed);visibility();
      stage.dataset.mantleOverlay='ready';message(config.strings.ready);
      if (matchMedia('(max-width: 899px)').matches) {
        // Temporary folding reveals the model without changing the saved preference.
        $('inspector').classList.add('closed');$('info-toggle').setAttribute('aria-expanded','false');
        $('info-toggle').focus();
      }
    } catch (error) {
      dispose(next);
      if (!pending.signal.aborted && active) {
        pending.abort();dispose(displayed);displayed=null;visibility();
        stage.dataset.mantleOverlay='error';message(config.strings.error);retry.hidden=false;
      }
    }
  }
  toggle.addEventListener('change', () => {
    if (!toggle.checked) {leave();return;}
    saved=capture();active=true;options.hidden=false;load();
  });
  retry.addEventListener('click',load);
  for (const id of ['mantle-cutaway','overlay-slabs','overlay-piles']) $(id).addEventListener('change',visibility);
  stage.dataset.mantleOverlay='off';
  return {leave, onAge:age=>{if(active && Math.abs(age-config.age_ma)>1e-8)leave(false);},
    onProjection:name=>{if(active && name!=='globe')leave(false);},
    cutsPoint:point=>uniforms.mantleCutaway.value>.5 && point.clone().normalize().dot(centre)>uniforms.mantleCutCos.value};
}
