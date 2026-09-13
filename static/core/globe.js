import * as THREE from 'three';
import { OrbitControls } from '../vendor/three/OrbitControls.js';
import { placeEquirectangular, placeMollweide, reproject } from './projection.js';
import { RotationModel, turn } from './rotation.js';

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
// Per gap, where each matched landmass sits on both of its maps. These are the control
// points that carry a continent across the gap instead of dissolving it in place.
const motions = JSON.parse($('globe-motions')?.textContent ?? '[]');
const MAX_MOTIONS = 16;
const frameStops = frames.map((frame, index) =>
  stops.findIndex(([from, , blend]) => blend === 0 && from === index));
// Longitude of the texture's left edge, in the sphere's own sweep. Measured against
// the rendered globe rather than derived: the geometry's UV convention and the
// canvas flip cancel out, so a label goes where the reprojection put its pixels.
const TEXTURE_MERIDIAN = 0;
// Each projection is a shape to draw on and a way to place a longitude and latitude on
// it. The shader undoes the projection per texel; these place the labels and the grid.
const PROJECTIONS = {
  globe: { sheet: null, code: 0, place: null, half: [1, 1] },
  equirect: { sheet: [2, 1], code: 1, place: placeEquirectangular, half: [1, 0.5] },
  mollweide: { sheet: [2, 1], code: 2, place: placeMollweide, half: [1, 0.5] },
};
// The plate model is a second, unrelated dataset: EarthByte's rotation model rather
// than a measurement of the Scotese maps. It is drawn as an overlay so the two can be
// compared at one time without either being mistaken for the other.
const plates = JSON.parse($('globe-plates')?.textContent ?? 'null');
const PLATE_COLOUR = 0xff62c0;
const surfaceToggle = $('surface');
let plateLayer;
let plateModel;
let plateShapes;
let plateAge = null;
let showPlates = false;
// Without the published maps there is nothing to show but the derived surface, so the
// viewer starts there and the toggle is not rendered at all.
const sourceMapsPublic = frames.some((frame) => Boolean(frame.url));
let surface = sourceMapsPublic ? 'map' : 'mask';
let projection = 'globe';
let surfaceMesh;
let gridVisible = false;
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
  if ((surface === 'mask' || !frame.url) && frame.field) {
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
  const masked = (surface === 'mask' || !sourceMapsPublic)
    && Boolean(place.from.field) && Boolean(place.to.field);
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
  if ($('source-preview')) {
    $('source-preview').src = anchor.url;
    $('source-preview').alt = `${anchor.label} (${ageText(anchor)}) Scotese 원본 지도`;
  }
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
    applyMotion(place);
    surfaceMesh.visible = true;
    showNames(place, masked);
    await updatePlates(place, ticket);
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
function applyMotion(place) {
  const gap = place.blend > 0 ? motions[frames.indexOf(place.from)] ?? [] : [];
  const count = Math.min(gap.length, MAX_MOTIONS);
  for (let index = 0; index < count; index++) {
    const pair = gap[index];
    uniforms.motionPoints.value[index].set(pair.lon, pair.lat, pair.to_lon, pair.to_lat);
    uniforms.motionRadius.value[index] = pair.radius;
  }
  uniforms.motionCount.value = count;
  stage.dataset.motions = String(count);
}
function setProjection(name) {
  if (!PROJECTIONS[name] || name === projection) return;
  projection = name;
  const globe = projection === 'globe';
  uniforms.projection.value = PROJECTIONS[projection].code;
  surfaceMesh.geometry.dispose();
  surfaceMesh.geometry = globe
    ? new THREE.SphereGeometry(1, 96, 64)
    : new THREE.PlaneGeometry(...PROJECTIONS[projection].sheet, 1, 1);
  earth.remove(grid);
  grid.traverse((node) => node.geometry?.dispose());
  grid = createGrid();
  earth.add(grid);
  controls.enableRotate = globe;
  controls.enablePan = !globe;
  controls.autoRotate = controls.autoRotate && globe;
  $('rotate').disabled = !globe;
  $('rotate').setAttribute('aria-pressed', String(controls.autoRotate));
  $('gesture').textContent = globe
    ? '드래그로 회전 · 스크롤 / 핀치로 확대'
    : '드래그로 이동 · 스크롤 / 핀치로 확대';
  stage.dataset.projection = projection;
  nameGroupKey = '';
  plateAge = null;
  fitCamera();
  resetView();
  selectStop(stop);
}
function globeMaterial() {
  const linear = (rgb) => new THREE.Color().setRGB(
    rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace);
  uniforms = {
    surfaceA: { value: null }, surfaceB: { value: null },
    blend: { value: 0 }, masked: { value: 0 },
    land: { value: linear(LAND_COLOUR) }, ocean: { value: linear(OCEAN_COLOUR) },
    projection: { value: 0 },
    motionCount: { value: 0 },
    motionPoints: { value: Array.from({ length: MAX_MOTIONS }, () => new THREE.Vector4()) },
    motionRadius: { value: new Float32Array(MAX_MOTIONS) },
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
      const float PI = 3.141592653589793;
      uniform int projection;
      uniform int motionCount;
      uniform vec4 motionPoints[${MAX_MOTIONS}];
      uniform float motionRadius[${MAX_MOTIONS}];
      varying vec2 vUv;
      varying vec3 vGlobeNormal;

      // Where the ground under this texel came from and is going to, in degrees. Each
      // control point pulls its own neighbourhood by the distance that landmass
      // travels, with a Gaussian falling off over the piece's own angular size, so
      // continents move as bodies and the open ocean between them stays put.
      vec2 travel(vec2 lonlat) {
        vec2 sum = vec2(0.0);
        float weight = 0.0;
        for (int index = 0; index < ${MAX_MOTIONS}; index++) {
          if (index >= motionCount) break;
          vec4 point = motionPoints[index];
          float eastward = mod(lonlat.x - point.x + 540.0, 360.0) - 180.0;
          float northward = lonlat.y - point.y;
          float shrink = cos(radians(0.5 * (lonlat.y + point.y)));
          float span = sqrt(eastward * eastward * shrink * shrink + northward * northward);
          float radius = max(motionRadius[index], 1.0);
          float pull = exp(-0.5 * span * span / (radius * radius));
          sum += pull * vec2(mod(point.z - point.x + 540.0, 360.0) - 180.0, point.w - point.y);
          weight += pull;
        }
        if (weight <= 0.0) return vec2(0.0);
        return sum / weight * smoothstep(0.05, 0.45, weight);
      }
      vec3 decode(vec3 colour) {
        return mix(pow((colour + 0.055) / 1.055, vec3(2.4)), colour / 12.92,
                   step(colour, vec3(0.04045)));
      }
      // Where on the equirectangular fields this fragment looks. On the sphere the
      // geometry already carries that; on a sheet the projection has to be undone,
      // which is also what decides whether a fragment is on the map at all.
      bool locate(out vec2 found) {
        if (projection <= 1) { found = vUv; return true; }
        float x = vUv.x * 2.0 - 1.0;
        float y = vUv.y * 2.0 - 1.0;
        if (x * x + y * y > 1.0) return false;
        float theta = asin(clamp(y, -1.0, 1.0));
        float latitude = asin(clamp((2.0 * theta + sin(2.0 * theta)) / PI, -1.0, 1.0));
        float longitude = PI * x / max(cos(theta), 1e-6);
        if (abs(longitude) > PI) return false;
        found = vec2(longitude / (2.0 * PI) + 0.5, latitude / PI + 0.5);
        return true;
      }
      void main() {
        vec2 surfaceUv;
        if (!locate(surfaceUv)) discard;
        vec3 colour;
        if (masked > 0.5) {
          // Both textures hold a signed distance to the coastline. Mixing the distances
          // and cutting at the midpoint moves the coastline; mixing pictures would only
          // dissolve one into the other. Sampling each side through the travel field
          // first carries each landmass along its own path, so the coastline morphs
          // around a continent that is moving rather than melting in place.
          vec2 shift = travel(vec2((surfaceUv.x - 0.5) * 360.0, (surfaceUv.y - 0.5) * 180.0));
          vec2 offset = vec2(shift.x / 360.0, shift.y / 180.0);
          float here = texture2D(surfaceA, surfaceUv - blend * offset).r;
          float there = texture2D(surfaceB, surfaceUv + (1.0 - blend) * offset).r;
          float distance = mix(here, there, blend) - 0.5;
          float edge = fwidth(distance) + 0.0012;
          colour = mix(ocean, land, smoothstep(-edge, edge, distance));
        } else {
          colour = mix(decode(texture2D(surfaceA, surfaceUv).rgb),
                       decode(texture2D(surfaceB, surfaceUv).rgb), blend);
        }
        // Limb shading gives the sphere volume without reading height from colour. A
        // flat sheet has no limb, so it is left alone.
        if (projection == 0) colour *= 0.58 + 0.42 * pow(abs(vGlobeNormal.z), 0.45);
        gl_FragColor = vec4(colour, 1.0);
        #include <colorspace_fragment>
      }`,
  });
}
const FLAT_DISTANCE = 2.6;
const NAME_LIFT = 0.015;
function onSheet(longitude, latitude, lift = 0) {
  const [x, y] = PROJECTIONS[projection].place(longitude, latitude);
  return new THREE.Vector3(x, y, lift);
}
function pointAt(longitude, latitude, lift) {
  return projection === 'globe'
    ? onSphere(longitude, latitude, 1 + lift)
    : onSheet(longitude, latitude, lift);
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
  for (const sprite of nameLayer.children) {
    const { from, to } = sprite.userData;
    if (from && to) {
      sprite.position.copy(between(from, to, place.blend));
      sprite.userData.fade = 1;
    } else if (from) {
      sprite.position.copy(labelPoint(from.lon, from.lat));
      sprite.userData.fade = 1 - place.blend;
    } else {
      sprite.position.copy(labelPoint(to.lon, to.lat));
      sprite.userData.fade = place.blend;
    }
  }
  stage.dataset.names = String(
    nameLayer.children.filter((sprite) => sprite.userData.fade > 0.001).length);
}
function labelPoint(longitude, latitude) {
  return pointAt(longitude, latitude, NAME_LIFT);
}
function between(from, to, blend) {
  const start = labelPoint(from.lon, from.lat);
  const finish = labelPoint(to.lon, to.lat);
  if (projection !== 'globe') return start.lerp(finish, blend);
  // On the sphere a straight line cuts through it, so come back out to the surface.
  return start.lerp(finish, blend).normalize().multiplyScalar(1 + NAME_LIFT);
}
function updateNameVisibility() {
  if (!nameLayer.visible) return;
  const flat = projection !== 'globe';
  const toCamera = camera.position.clone().normalize();
  const position = new THREE.Vector3();
  for (const sprite of nameLayer.children) {
    let facing = 1;
    if (!flat) {
      sprite.getWorldPosition(position);
      facing = THREE.MathUtils.clamp((position.normalize().dot(toCamera) - 0.12) / 0.18, 0, 1);
    }
    sprite.material.opacity = facing * (sprite.userData.fade ?? 1);
    sprite.visible = sprite.material.opacity > 0.02;
  }
}
async function loadPlateModel() {
  if (plateModel && plateShapes) return true;
  const [rotations, shapes] = await Promise.all([
    fetch(plates.rotations).then((response) => response.json()),
    fetch(plates.continents).then((response) => response.json()),
  ]);
  plateModel = new RotationModel(rotations);
  plateShapes = shapes.features;
  return true;
}
function drawPlates(age) {
  // Rebuilt per stop rather than animated: the geometry is a few thousand segments and
  // the rotation is exact at whatever age the reader is on, not an eased approximation.
  const flat = projection !== 'globe';
  const lift = flat ? 0.004 : 0.006;
  const points = [];
  let visible = 0;
  for (const feature of plateShapes) {
    if (age > feature.from + 1e-9 || age < feature.to - 1e-9) continue;
    const rotation = plateModel.rotation(feature.pid, age);
    if (rotation === null) continue;
    visible += 1;
    for (const ring of feature.rings) {
      let previous = null;
      let previousLongitude = 0;
      for (let index = 0; index < ring.length; index += 2) {
        const [longitude, latitude] = turn(rotation, ring[index], ring[index + 1]);
        const here = pointAt(longitude, latitude, lift);
        // On a sheet a ring that crosses the antimeridian would draw a line straight
        // back across the map, so the run is broken there instead.
        const jumped = flat && previous && Math.abs(longitude - previousLongitude) > 180;
        if (previous && !jumped) points.push(previous, here);
        previous = here;
        previousLongitude = longitude;
      }
    }
  }
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  if (plateLayer) {
    plateLayer.geometry.dispose();
    plateLayer.geometry = geometry;
  } else {
    plateLayer = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial(
      { color: PLATE_COLOUR, transparent: true, opacity: 0.85 }));
    plateLayer.renderOrder = 1;
    earth.add(plateLayer);
  }
  plateLayer.visible = true;
  plateAge = age;
  stage.dataset.plates = String(visible);
}
function clearPlates() {
  if (plateLayer) plateLayer.visible = false;
  plateAge = null;
  stage.dataset.plates = '0';
}
async function updatePlates(place, ticket) {
  if (!showPlates || !plates) {
    clearPlates();
    return;
  }
  await loadPlateModel();
  if (ticket !== request) return;
  drawPlates(Number(place.age.toFixed(3)));
}
function createGrid() {
  // Built from longitude and latitude rather than from the mesh, so the same parallels
  // and meridians follow whichever projection is showing, curved or straight.
  const result = new THREE.Group();
  const material = new THREE.LineBasicMaterial({ color: 0xc4f7ef, transparent: true, opacity: 0.23 });
  const lift = projection === 'globe' ? 0.004 : 0.003;
  function line(points) {
    result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material));
  }
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    const points = [];
    for (let step = 0; step <= 180; step++) points.push(pointAt(-180 + step * 2, latitude, lift));
    line(points);
  }
  for (let longitude = -180; longitude < 180; longitude += 30) {
    const points = [];
    for (let step = 0; step <= 90; step++) {
      points.push(pointAt(longitude, -90 + step * 2, lift));
    }
    line(points);
  }
  result.visible = gridVisible;
  return result;
}
function fitCamera() {
  const { width, height } = stage.getBoundingClientRect();
  if (!width || !height) return;
  renderer.setSize(width, height);
  camera.aspect = width / height;
  if (projection === 'globe') {
    camera.fov = THREE.MathUtils.radToDeg(
      2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(21)) / Math.min(1, camera.aspect)));
  } else {
    // Hold the sheet at one distance and open the lens until it fits both ways, so a
    // resize reframes the map without undoing the reader's zoom.
    const [halfWidth, halfHeight] = PROJECTIONS[projection].half;
    const tangent = Math.max(halfHeight * 1.08 / FLAT_DISTANCE,
                             halfWidth * 1.08 / (FLAT_DISTANCE * camera.aspect));
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(tangent));
  }
  camera.updateProjectionMatrix();
}
function resetView() {
  const globe = projection === 'globe';
  earth.rotation.set(0, globe ? -Math.PI / 2 : 0, 0);
  camera.position.set(0, globe ? 0.18 : 0, globe ? 3.45 : FLAT_DISTANCE);
  controls.target.set(0, 0, 0);
  controls.minDistance = globe ? 1.65 : FLAT_DISTANCE * 0.3;
  controls.maxDistance = globe ? 5 : FLAT_DISTANCE * 2.2;
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

  controls.autoRotateSpeed = 0.55;
  earth = new THREE.Group();
  surfaceMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), globeMaterial());
  surfaceMesh.visible = false;
  earth.add(surfaceMesh);
  grid = createGrid();
  earth.add(grid);
  nameLayer = new THREE.Group();
  nameLayer.visible = false;
  earth.add(nameLayer);
  scene.add(earth);
  resetView();
  const observer = new ResizeObserver(fitCamera);
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
  stage.dataset.projection = projection;
  $('projection').value = projection;
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
    gridVisible = !gridVisible;
    grid.visible = gridVisible;
    $('grid').setAttribute('aria-pressed', String(gridVisible));
  });
  if (surfaceToggle) {
    surfaceToggle.addEventListener('click', () => {
      surface = surface === 'mask' ? 'map' : 'mask';
      surfaceToggle.setAttribute('aria-pressed', String(surface === 'mask'));
      selectStop(stop, true);
    });
  }
  if ($('plates')) {
    $('plates').addEventListener('click', () => {
      showPlates = !showPlates;
      $('plates').setAttribute('aria-pressed', String(showPlates));
      $('plate-note').hidden = !showPlates;
      selectStop(stop);
    });
  }
  $('projection').addEventListener('change', () => setProjection($('projection').value));
  $('reset').addEventListener('click', resetView);
  stage.addEventListener('keydown', (event) => {
    const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const step = 0.12;
    if (projection === 'globe') {
      if (event.key === 'ArrowLeft') earth.rotation.y -= step;
      if (event.key === 'ArrowRight') earth.rotation.y += step;
      if (event.key === 'ArrowUp') earth.rotation.x -= step;
      if (event.key === 'ArrowDown') earth.rotation.x += step;
    } else {
      // A sheet has nothing to turn, so the arrows slide the view instead.
      const pan = camera.position.z * 0.08;
      const shift = new THREE.Vector3(
        (event.key === 'ArrowRight' ? 1 : 0) - (event.key === 'ArrowLeft' ? 1 : 0),
        (event.key === 'ArrowUp' ? 1 : 0) - (event.key === 'ArrowDown' ? 1 : 0), 0).multiplyScalar(pan);
      camera.position.add(shift);
      controls.target.add(shift);
      controls.update();
    }
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
