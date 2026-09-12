import * as THREE from 'three';
import { OrbitControls } from '../vendor/three/OrbitControls.js';
import { reproject } from './projection.js';

const $ = (id) => document.getElementById(id);
const frames = JSON.parse($('globe-frames').textContent);
const status = $('status');
const stage = $('globe');
const textures = new Map();
// Flat fills for the derived surface. Deliberately unlike the source palette, so a
// segmented globe is never mistaken for the published map.
const LAND_COLOUR = [205, 193, 148];
const OCEAN_COLOUR = [22, 86, 135];
// The slider's stops, built by the server as [from frame, to frame, blend, age]. A
// stop whose blend is zero is a published map; every other stop is interpolated, never
// observed. The viewer does not care how the stops were spaced, so an even count per
// map and a fixed span in millions of years both arrive the same way.
const stops = JSON.parse($('globe-stops').textContent);
const frameStops = frames.map((frame, index) =>
  stops.findIndex(([from, , blend]) => blend === 0 && from === index));
// Longitude of the texture's left edge, in the sphere's own sweep. Measured against
// the rendered globe rather than derived: the geometry's UV convention and the
// canvas flip cancel out, so a label goes where the reprojection put its pixels.
const TEXTURE_MERIDIAN = 0;
const surfaceToggle = $('surface');
let surface = 'map';
let nameLayer;
let nameGroupKey = '';
let uniforms;
let stop = stops.length - 1;
let selected = frames.length - 1;
let request = 0;
let playing = false;
let playTimer;
let scene, camera, renderer, controls, earth, grid;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function ageText(frame) {
  return frame.age === 0 ? '현재' : frame.age < 1 ? `${(frame.age * 1e6).toLocaleString()}년 전` : `${frame.age} Ma`;
}
function setPlaying(value) {
  playing = value;
  clearTimeout(playTimer);
  $('play').setAttribute('aria-pressed', String(value));
  $('play').textContent = value ? '❚❚ 재생 멈춤' : '▶ 시대 순서 재생';
}
function scheduleNext() {
  // Playback walks the sub-steps so the change reads as motion, at the same pace per
  // source map as before.
  // Playback walks the stops, holding the same pace per source map however densely
  // the timeline was sampled.
  const perFrame = (stops.length - 1) / Math.max(1, frames.length - 1);
  if (playing) {
    playTimer = setTimeout(() => selectStop(stop >= stops.length - 1 ? 0 : stop + 1),
                           Math.max(60, 2400 / perFrame));
  }
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Download failed: ${source}`));
    image.src = source;
  });
}
function cache(key, build) {
  if (!textures.has(key)) {
    const promise = build();
    textures.set(key, promise);
    promise.catch(() => textures.delete(key));
  }
  return textures.get(key);
}
function prepare(texture) {
  // The shader decodes colour itself, so every texture is handed over as raw data.
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return texture;
}
function loadMap(frame) {
  return cache(`${frame.id}:map`, async () =>
    prepare(new THREE.CanvasTexture(reproject(await loadImage(frame.url), frame.bounds))));
}
function loadField(frame) {
  return cache(`${frame.id}:field`, async () =>
    prepare(new THREE.Texture(await loadImage(frame.field), THREE.UVMapping)));
}
async function loadSurface(frame) {
  if (surface === 'mask' && frame.field) {
    const texture = await loadField(frame);
    texture.needsUpdate = true;
    return texture;
  }
  return loadMap(frame);
}
function stopAt(value) {
  const clamped = Math.max(0, Math.min(stops.length - 1, Math.round(value)));
  const [from, to, blend, age] = stops[clamped];
  return { value: clamped, blend, age, from: frames[from], to: frames[to],
           index: blend > 0.5 ? to : from };
}
function neighbourStop(direction) {
  const marks = frameStops.filter((mark) => direction < 0 ? mark < stop : mark > stop);
  if (!marks.length) return direction < 0 ? 0 : stops.length - 1;
  return direction < 0 ? Math.max(...marks) : Math.min(...marks);
}
function ageLabel(place) {
  if (place.blend === 0) return ageText(place.from);
  return place.age < 1
    ? `${Math.round(place.age * 1e6).toLocaleString()}년 전`
    : `${place.age.toFixed(1)} Ma`;
}
function periodLabel(place) {
  return place.blend === 0 ? place.from.label : `${place.from.label} → ${place.to.label}`;
}
async function selectStop(value, manual = false) {
  if (manual) setPlaying(false);
  clearTimeout(playTimer);
  const place = stopAt(value);
  stop = place.value;
  selected = place.index;
  const ticket = ++request;
  const between = place.blend > 0;
  const masked = surface === 'mask' && Boolean(place.from.field) && Boolean(place.to.field);
  const anchor = place.blend > 0.5 ? place.to : place.from;
  $('era').value = selected;
  $('timeline').value = stop;
  $('timeline').setAttribute('aria-valuetext',
    between ? `${periodLabel(place)} 사이, ${ageLabel(place)}, 보간` : `${place.from.label}, ${ageText(place.from)}`);
  $('period').textContent = periodLabel(place);
  $('age').textContent = ageLabel(place);
  $('source-title').textContent = between ? `${place.from.title} → ${place.to.title}` : place.from.title;
  $('globe-age').textContent = [periodLabel(place), ageLabel(place),
    masked ? '대륙 마스크' : null, between ? '보간' : null].filter(Boolean).join(' / ');
  $('source-link').href = anchor.source;
  $('source-preview').src = anchor.url;
  $('source-preview').alt = `${anchor.label} (${ageText(anchor)}) Scotese 원본 지도`;
  $('older').disabled = stop <= frameStops[0];
  $('newer').disabled = stop >= frameStops[frames.length - 1];
  $('frame-number').textContent = between
    ? `${ageLabel(place)} · 보간`
    : `${selected + 1} / ${frames.length}`;
  if (surfaceToggle) surfaceToggle.disabled = !place.from.field || !place.to.field;
  $('surface-note').hidden = !masked;
  $('between-note').hidden = !between;
  status.textContent = `${periodLabel(place)} ${masked ? '대륙 마스크를' : '지도를'} 불러오는 중…`;
  status.hidden = false;
  status.classList.remove('loaded');
  $('retry').hidden = true;
  stage.setAttribute('aria-busy', 'true');
  try {
    const [first, second] = await Promise.all([loadSurface(place.from), loadSurface(place.to)]);
    if (ticket !== request) return;
    uniforms.surfaceA.value = first;
    uniforms.surfaceB.value = second;
    uniforms.blend.value = place.blend;
    uniforms.masked.value = masked ? 1 : 0;
    earth.visible = true;
    showNames(place, masked);
    stage.dataset.frame = place.from.id;
    stage.dataset.blend = place.blend.toFixed(2);
    stage.setAttribute('aria-label', `${periodLabel(place)}, ${ageLabel(place)} ${masked ? '대륙 마스크 지구본' : '지구본'}${between ? ', 보간된 중간 형태' : ''}. 드래그 또는 방향키로 회전, 더하기 빼기로 확대 축소.`);
    stage.setAttribute('aria-busy', 'false');
    status.textContent = `${periodLabel(place)} ${masked ? '대륙 마스크' : '지구본'} 표시 완료${between ? ' (보간)' : ''}`;
    status.classList.add('loaded');
    scheduleNext();
  } catch (error) {
    if (ticket !== request) return;
    status.classList.remove('loaded');
    status.textContent = masked
      ? '대륙 거리장을 불러오지 못했습니다. 분할 결과 파일을 확인해 주세요.'
      : '지도를 불러오지 못했습니다. 로컬 원본 파일과 연결을 확인해 주세요.';
    stage.setAttribute('aria-busy', 'false');
    $('retry').hidden = false;
    setPlaying(false);
    console.error(error);
  }
}
function selectFrame(index, manual = false) {
  return selectStop(frameStops[Math.max(0, Math.min(frames.length - 1, index))], manual);
}
function globeMaterial() {
  const linear = (rgb) => new THREE.Color().setRGB(
    rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace);
  uniforms = {
    surfaceA: { value: null }, surfaceB: { value: null },
    blend: { value: 0 }, masked: { value: 0 },
    land: { value: linear(LAND_COLOUR) }, ocean: { value: linear(OCEAN_COLOUR) },
  };
  return new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      varying vec2 vUv;
      varying vec3 vGlobeNormal;
      void main() {
        vUv = uv;
        vGlobeNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D surfaceA;
      uniform sampler2D surfaceB;
      uniform float blend;
      uniform float masked;
      uniform vec3 land;
      uniform vec3 ocean;
      varying vec2 vUv;
      varying vec3 vGlobeNormal;
      vec3 decode(vec3 colour) {
        return mix(pow((colour + 0.055) / 1.055, vec3(2.4)), colour / 12.92,
                   step(colour, vec3(0.04045)));
      }
      void main() {
        vec3 colour;
        if (masked > 0.5) {
          // Both textures hold a signed distance to the coastline. Mixing the distances
          // and cutting at the midpoint moves the coastline; mixing pictures would only
          // dissolve one into the other.
          float distance = mix(texture2D(surfaceA, vUv).r, texture2D(surfaceB, vUv).r, blend) - 0.5;
          float edge = fwidth(distance) + 0.0012;
          colour = mix(ocean, land, smoothstep(-edge, edge, distance));
        } else {
          colour = mix(decode(texture2D(surfaceA, vUv).rgb),
                       decode(texture2D(surfaceB, vUv).rgb), blend);
        }
        // Limb shading gives the sphere volume without reading height from colour.
        colour *= 0.58 + 0.42 * pow(abs(vGlobeNormal.z), 0.45);
        gl_FragColor = vec4(colour, 1.0);
        #include <colorspace_fragment>
      }`,
  });
}
function onSphere(longitude, latitude, radius = 1) {
  const theta = THREE.MathUtils.degToRad(90 - latitude);
  const phi = (longitude + 180) / 360 * Math.PI * 2 + TEXTURE_MERIDIAN;
  return new THREE.Vector3(-Math.cos(phi) * Math.sin(theta), Math.cos(theta),
                           Math.sin(phi) * Math.sin(theta)).multiplyScalar(radius);
}
function nameSprite(text) {
  const scale = 3;
  const font = `600 ${16 * scale}px system-ui, "Noto Sans KR", sans-serif`;
  const canvas = document.createElement('canvas');
  let context = canvas.getContext('2d');
  context.font = font;
  const width = Math.ceil(context.measureText(text).width) + 18 * scale;
  canvas.width = width;
  canvas.height = 26 * scale;
  context = canvas.getContext('2d');
  context.font = font;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.lineWidth = 4 * scale;
  context.strokeStyle = 'rgba(11,26,36,0.85)';
  context.strokeText(text, canvas.width / 2, canvas.height / 2);
  context.fillStyle = '#fdf6e3';
  context.fillText(text, canvas.width / 2, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial(
    { map: texture, transparent: true, depthTest: false, depthWrite: false }));
  const height = 0.075;
  sprite.scale.set(height * canvas.width / canvas.height, height, 1);
  sprite.renderOrder = 2;
  return sprite;
}
function clearNames() {
  for (const sprite of nameLayer.children) {
    sprite.material.map.dispose();
    sprite.material.dispose();
  }
  nameLayer.clear();
  nameGroupKey = '';
  stage.dataset.names = '0';
}
function showNames(place, visible) {
  nameLayer.visible = visible;
  if (!visible) {
    clearNames();
    return;
  }
  const key = `${place.from.id}|${place.to.id}`;
  if (key !== nameGroupKey) {
    clearNames();
    nameGroupKey = key;
    const byName = new Map((place.to.names || []).map((entry) => [entry.name, entry]));
    for (const from of place.from.names || []) {
      const sprite = nameSprite(from.name);
      sprite.userData = { from, to: byName.get(from.name) || null, arriving: false };
      nameLayer.add(sprite);
      byName.delete(from.name);
    }
    for (const to of byName.values()) {
      const sprite = nameSprite(to.name);
      sprite.userData = { from: null, to, arriving: true };
      nameLayer.add(sprite);
    }
  }
  // A name on both sides travels between its two positions. One that exists on only
  // one side fades, because the piece it names has no counterpart to move to.
  const start = new THREE.Vector3();
  const finish = new THREE.Vector3();
  for (const sprite of nameLayer.children) {
    const { from, to } = sprite.userData;
    if (from && to) {
      start.copy(onSphere(from.lon, from.lat));
      finish.copy(onSphere(to.lon, to.lat));
      sprite.position.copy(start.lerp(finish, place.blend).normalize().multiplyScalar(1.015));
      sprite.userData.fade = 1;
    } else if (from) {
      sprite.position.copy(onSphere(from.lon, from.lat, 1.015));
      sprite.userData.fade = 1 - place.blend;
    } else {
      sprite.position.copy(onSphere(to.lon, to.lat, 1.015));
      sprite.userData.fade = place.blend;
    }
  }
  stage.dataset.names = String(
    nameLayer.children.filter((sprite) => sprite.userData.fade > 0.001).length);
}
function updateNameVisibility() {
  if (!nameLayer.visible) return;
  const toCamera = camera.position.clone().normalize();
  const position = new THREE.Vector3();
  for (const sprite of nameLayer.children) {
    sprite.getWorldPosition(position);
    const facing = position.normalize().dot(toCamera);
    sprite.material.opacity = THREE.MathUtils.clamp((facing - 0.12) / 0.18, 0, 1)
      * (sprite.userData.fade ?? 1);
    sprite.visible = sprite.material.opacity > 0.02;
  }
}
function createGrid() {
  const result = new THREE.Group();
  const material = new THREE.LineBasicMaterial({ color: 0xc4f7ef, transparent: true, opacity: 0.23 });
  function line(points) { result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material)); }
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    const phi = THREE.MathUtils.degToRad(latitude);
    const points = [];
    for (let i = 0; i <= 180; i++) {
      const theta = i / 180 * Math.PI * 2;
      points.push(new THREE.Vector3(Math.cos(phi) * Math.cos(theta), Math.sin(phi), Math.cos(phi) * Math.sin(theta)).multiplyScalar(1.004));
    }
    line(points);
  }
  for (let longitude = 0; longitude < 360; longitude += 30) {
    const theta = THREE.MathUtils.degToRad(longitude);
    const points = [];
    for (let i = 0; i <= 90; i++) {
      const phi = i / 90 * Math.PI - Math.PI / 2;
      points.push(new THREE.Vector3(Math.cos(phi) * Math.cos(theta), Math.sin(phi), Math.cos(phi) * Math.sin(theta)).multiplyScalar(1.004));
    }
    line(points);
  }
  result.visible = false;
  return result;
}
function resetView() {
  camera.position.set(0, 0.18, 3.45);
  earth.rotation.set(0, -Math.PI / 2, 0);
  controls.target.set(0, 0, 0);
  controls.update();
}
function init() {
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  stage.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = !reducedMotion;
  controls.enablePan = false;
  controls.minDistance = 1.65;
  controls.maxDistance = 5;
  controls.autoRotateSpeed = 0.55;
  earth = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), globeMaterial());
  earth.visible = false;
  grid = createGrid();
  earth.add(grid);
  nameLayer = new THREE.Group();
  nameLayer.visible = false;
  earth.add(nameLayer);
  scene.add(earth);
  resetView();
  const observer = new ResizeObserver(() => {
    const { width, height } = stage.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(21)) / Math.min(1, camera.aspect)));
    camera.updateProjectionMatrix();
  });
  observer.observe(stage);
  let previous = performance.now();
  renderer.setAnimationLoop((time) => {
    const delta = Math.min((time - previous) / 1000, 0.1);
    previous = time;
    if (document.hidden) return;
    controls.update(delta);
    updateNameVisibility();
    renderer.render(scene, camera);
  });
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    setPlaying(false);
    status.classList.remove('loaded');
    status.textContent = '그래픽 연결이 끊겼습니다. 페이지를 새로고침해 주세요.';
  });
  frames.forEach((frame, index) => $('era').add(new Option(`${frame.label} · ${ageText(frame)}`, index)));
  $('timeline').max = stops.length - 1;
  $('era').addEventListener('change', () => selectFrame(Number($('era').value), true));
  $('timeline').addEventListener('input', () => selectStop(Number($('timeline').value), true));
  $('older').addEventListener('click', () => selectStop(neighbourStop(-1), true));
  $('newer').addEventListener('click', () => selectStop(neighbourStop(1), true));
  $('retry').addEventListener('click', () => selectStop(stop, true));
  $('play').addEventListener('click', () => {
    setPlaying(!playing);
    if (playing) selectFrame(selected === frames.length - 1 ? 0 : selected + 1);
  });
  $('rotate').addEventListener('click', () => {
    controls.autoRotate = !controls.autoRotate;
    $('rotate').setAttribute('aria-pressed', String(controls.autoRotate));
  });
  $('grid').addEventListener('click', () => {
    grid.visible = !grid.visible;
    $('grid').setAttribute('aria-pressed', String(grid.visible));
  });
  if (surfaceToggle) {
    surfaceToggle.addEventListener('click', () => {
      surface = surface === 'mask' ? 'map' : 'mask';
      surfaceToggle.setAttribute('aria-pressed', String(surface === 'mask'));
      selectStop(stop, true);
    });
  }
  $('reset').addEventListener('click', resetView);
  stage.addEventListener('keydown', (event) => {
    const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'ArrowLeft') earth.rotation.y -= 0.12;
    if (event.key === 'ArrowRight') earth.rotation.y += 0.12;
    if (event.key === 'ArrowUp') earth.rotation.x -= 0.12;
    if (event.key === 'ArrowDown') earth.rotation.x += 0.12;
    if (['+', '=', '-'].includes(event.key)) {
      camera.position.multiplyScalar(event.key === '-' ? 1.1 : 0.9);
      camera.position.clampLength(controls.minDistance, controls.maxDistance);
    }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
  selectFrame(selected);
}
try { init(); }
catch (error) {
  status.textContent = '3D 화면을 시작하지 못했습니다. WebGL을 지원하는 브라우저에서 하드웨어 가속을 확인해 주세요.';
  for (const element of document.querySelectorAll('.explorer button, .explorer select, .timeline button, .timeline input')) element.disabled = true;
  console.error(error);
}
