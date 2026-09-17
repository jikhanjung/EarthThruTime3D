import { cutBoundary, containsPoint, longitudeSpan } from './interior-cutaway.js';
import * as THREE from 'three';

export const CRUST_GLSL = `
  uniform sampler2D crustMap;
  uniform float crustColour;
  uniform float crustScale;
  float crustKm(vec2 uv) {
    vec2 code = floor(texture2D(crustMap, uv).rg * 255.0 + 0.5);
    float value = code.x + code.y * 256.0;
    return value > 65534.0 ? -1.0 : value * 0.01;
  }
  vec3 crustTint(float km) {
    float t = clamp(km / 80.0, 0.0, 1.0);
    vec3 blue = vec3(0.025, 0.12, 0.32);
    vec3 gold = vec3(0.86, 0.57, 0.13);
    vec3 pale = vec3(1.0, 0.96, 0.75);
    return t < 0.5 ? mix(blue, gold, t * 2.0) : mix(gold, pale, t * 2.0 - 1.0);
  }`;

export function decodeGrid(buffer) {
  if (buffer.byteLength !== 360 * 180 * 2) throw new Error('Invalid crust grid length');
  const view = new DataView(buffer);
  const grid = new Uint16Array(360 * 180);
  for (let i = 0; i < grid.length; i++) {
    grid[i] = view.getUint16(i * 2, true);
    if (grid[i] > 8000 && grid[i] !== 65535) throw new Error('Invalid crust thickness');
  }
  return grid;
}

export function sampleGrid(grid, longitude, latitude) {
  const x = Math.floor(((longitude + 180) % 360 + 360) % 360);
  const y = Math.max(0, Math.min(179, Math.floor(latitude + 90)));
  const value = grid[y * 360 + x];
  return value === 65535 ? null : value * 0.01;
}

// A thickness-equivalent display shell; deliberately not a reconstructed Moho.
export function shellRadius(displayRadius, km, scale) {
  return displayRadius - km * scale / 6371;
}

export function createCrust({ config, earth, uniforms, surface, stage, camera, lift, cut, interior }) {
  const $ = id => document.getElementById(id);
  if (!config || !$('crust-enabled')) return null;
  const toggle = $('crust-enabled'), colour = $('crust-colour'), status = $('crust-status');
  const strings = JSON.parse($('crust-strings').textContent);
  let age = null, data = null, pending = null, failed = false;
  let group = null, bottom = null, wall = null, ringKey = '';
  let lastState = '';
  const raycaster = new THREE.Raycaster();
  const point = new THREE.Vector3();
  let down = null;

  function makeMaterial(isWall) {
    return new THREE.ShaderMaterial({
      uniforms, side: THREE.DoubleSide,
      vertexShader: `
        ${lift.uniforms}
        ${CRUST_GLSL}
        ${lift.travel}
        ${lift.metres}
        ${lift.lift}
        uniform float mantleSurfaceOpacity;
        ${isWall ? 'attribute float crustDepth;' : ''}
        varying vec3 vCutPosition;
        varying float vThickness;
        void main() {
          vec3 p = normalize(position);
          vec2 uv = vec2(fract(atan(p.z, -p.x) / (2.0 * PI)), asin(clamp(p.y,-1.0,1.0))/PI + 0.5);
          vThickness = crustKm(uv);
          vCutPosition = p;
          float depth = ${isWall ? 'crustDepth' : '1.0'};
          float r = terrainLift(p) - max(vThickness, 0.0) * crustScale * depth / 6371.0;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(p * r, 1.0);
        }`,
      fragmentShader: `
        ${cut.uniforms}
        uniform float mantleSurfaceOpacity;
        uniform vec3 mantleCamera;
        varying float vThickness;
        void main() {
          ${isWall ? '' : cut.surface}
          if (vThickness < 0.0 || dot(vCutPosition, mantleCamera - vCutPosition) < 0.0) discard;
          gl_FragColor = vec4(${isWall ? 'vec3(0.55, 0.29, 0.105)' : 'vec3(0.24, 0.12, 0.045)'}, mantleSurfaceOpacity);
          #include <colorspace_fragment>
        }`,
    });
  }

  function createShell() {
    group = new THREE.Group();
    bottom = new THREE.Mesh(new THREE.SphereGeometry(1, 360, 180), makeMaterial(false));
    bottom.frustumCulled = false;
    wall = new THREE.Mesh(new THREE.BufferGeometry(), makeMaterial(true));
    wall.frustumCulled = false;
    group.add(bottom, wall);
    group.visible = false;
    earth.add(group);
  }

  function updateWall(bounds) {
    const key = JSON.stringify(bounds);
    if (key === ringKey) return;
    ringKey = key;
    const positions = [], depth = [], indices = [];
    for (const ring of cutBoundary(bounds)) {
      const offset = depth.length;
      ring.forEach(([longitude, latitude], i) => {
        const lon = longitude * Math.PI / 180, lat = latitude * Math.PI / 180;
        const xyz = [Math.cos(lat) * Math.cos(lon), Math.sin(lat), -Math.cos(lat) * Math.sin(lon)];
        positions.push(...xyz, ...xyz);
        depth.push(0, 1);
        if (i < ring.length - 1) {
          const j = offset + i * 2;
          indices.push(j, j + 1, j + 2, j + 1, j + 3, j + 2);
        }
      });
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('crustDepth', new THREE.Float32BufferAttribute(depth, 1));
    geometry.setIndex(indices);
    wall.geometry.dispose();
    wall.geometry = geometry;
  }

  function sync() {
    const section = interior.read();
    const key = [JSON.stringify(section), age, Boolean(data), failed, ...['crust-enabled', 'crust-colour'].map(id => $(id).checked),
      ...['crust-scale'].map(id => $(id).value),
      uniforms.projection.value, uniforms.mode.value, uniforms.mantleCutaway.value,
      uniforms.mantleSurfaceOpacity.value].join('|');
    if (key === lastState) return;
    lastState = key;
    const active = toggle.checked && data !== null && age === 0;
    const globe = uniforms.projection.value === 0;
    uniforms.crustColour.value = active && colour.checked ? 1 : 0;
    uniforms.crustCutaway.value = active && globe && section.enabled && longitudeSpan(section) > 0 ? 1 : 0;
    uniforms.crustScale.value = Number($('crust-scale').value);
    uniforms.interiorBounds.value.set(section.west, longitudeSpan(section), section.south, section.north);
    const mantleCut = uniforms.mantleCutaway.value > 0.5;
    if (group) {
      group.visible = active && globe && (mantleCut || uniforms.crustCutaway.value > 0.5);
      if (group.visible) {
        updateWall(section);
        for (const mesh of [bottom, wall]) {
          const transparent = uniforms.mantleSurfaceOpacity.value < 1;
          if (mesh.material.transparent !== transparent) {
            mesh.material.transparent = transparent;
            mesh.material.needsUpdate = true;
          }
          mesh.material.depthWrite = !transparent;
        }
      }
    }
    $('crust-options').hidden = !toggle.checked;
    $('crust-panel').hidden = !toggle.checked;
    $('crust-legend').hidden = !(active && colour.checked);
    $('crust-section-controls').disabled = !globe;
    $('crust-scale-note').hidden = !(active && uniforms.crustScale.value !== 1 && globe);
    $('crust-caption').hidden = !group?.visible;
    $('crust-caption').textContent = strings.caption.replace('{scale}', String(uniforms.crustScale.value));
    $('crust-retry').hidden = !failed;
    const state = !toggle.checked ? 'off' : age !== 0 ? 'unavailable' : failed ? 'error' : data ? 'ready' : 'loading';
    if (stage.dataset.crust !== state) {
      stage.dataset.crust = state;
      status.textContent = strings[state] || '';
      $('crust-readout').textContent = '';
    }
    stage.dataset.crustSection = String(Boolean(group?.visible));
    stage.dataset.crustColour = String(uniforms.crustColour.value === 1);
    if ($('temp-legend')) $('temp-legend').hidden = uniforms.crustColour.value === 1 || uniforms.mode.value !== 3;
  }

  async function load() {
    if (data || pending) return;
    failed = false;
    pending = (async () => {
      try {
        const response = await fetch(config.url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const buffer = await response.arrayBuffer();
        const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', buffer))].map(x => x.toString(16).padStart(2, '0')).join('');
        if (digest !== config.asset.sha256) throw new Error('Crust checksum mismatch');
        const grid = decodeGrid(buffer);
        const rgba = new Uint8Array(grid.length * 4);
        for (let i = 0; i < grid.length; i++) {
          rgba[i * 4] = grid[i] & 255; rgba[i * 4 + 1] = grid[i] >> 8; rgba[i * 4 + 3] = 255;
        }
        const texture = new THREE.DataTexture(rgba, 360, 180);
        texture.wrapS = THREE.RepeatWrapping;
        texture.magFilter = texture.minFilter = THREE.NearestFilter;
        texture.needsUpdate = true;
        uniforms.crustMap.value = texture;
        createShell();
        data = grid;
      } catch (error) {
        failed = true;
        console.warn('Crust data unavailable', error);
      } finally {
        pending = null;
        sync();
      }
    })();
    sync();
    await pending;
  }

  toggle.addEventListener('change', () => { sync(); if (toggle.checked && age === 0) load(); });
  $('crust-retry').addEventListener('click', load);
  for (const id of ['crust-colour', 'crust-scale']) $(id).addEventListener('input', sync);
  for (const id of ['temperature', 'surface']) $(id)?.addEventListener('click', () => { colour.checked = false; sync(); });
  interior.subscribe(sync);
  stage.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; });
  stage.addEventListener('pointerup', e => {
    if (!data || !toggle.checked || age !== 0 || !down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
    const box = stage.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2((e.clientX - box.left) / box.width * 2 - 1, 1 - (e.clientY - box.top) / box.height * 2), camera());
    const hit = raycaster.intersectObject(surface)[0];
    if (!hit) return;
    let lon, lat;
    if (uniforms.projection.value === 0) {
      point.copy(hit.point); earth.worldToLocal(point); point.normalize();
      if ((uniforms.mantleCutaway.value > .5 || uniforms.crustCutaway.value > .5) && containsPoint(point, interior.read())) return;
      lon = Math.atan2(-point.z, point.x) * 180 / Math.PI;
      lat = Math.asin(point.y) * 180 / Math.PI;
    } else if (uniforms.projection.value === 1) {
      lon = (hit.uv.x - .5) * 360 + uniforms.meridian.value;
      lat = (hit.uv.y - .5) * 180;
    } else {
      const x = hit.uv.x * 2 - 1, y = hit.uv.y * 2 - 1;
      if (x * x + y * y > 1) return;
      const theta = Math.asin(y);
      lon = 180 * x / Math.max(Math.cos(theta), 1e-6) + uniforms.meridian.value;
      lat = Math.asin(Math.max(-1, Math.min(1, (2 * theta + Math.sin(2 * theta)) / Math.PI))) * 180 / Math.PI;
    }
    const km = sampleGrid(data, lon, lat);
    $('crust-readout').textContent = km === null ? strings.missing : strings.value.replace('{km}', Math.round(km)).replace('{lon}', ((((lon + 180) % 360) + 360) % 360 - 180).toFixed(1)).replace('{lat}', lat.toFixed(1));
  });
  sync();
  return {
    frame(value) { age = value; lastState = ''; sync(); if (toggle.checked && age === 0 && !data && !failed) load(); },
    sync,
    cutsPoint: p => uniforms.mantleCutaway.value <= .5 && uniforms.crustCutaway.value > .5 && containsPoint(p, interior.read()),
  };
}
