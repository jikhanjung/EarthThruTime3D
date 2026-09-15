import * as THREE from 'three';
import { OrbitControls } from '../vendor/three/OrbitControls.js';

const $ = (id) => document.getElementById(id);
const frames = JSON.parse($('mantle-frames').textContent);
const strings = JSON.parse($('mantle-strings').textContent);
const stage = $('mantle-stage');
const status = $('mantle-status');
const slider = $('mantle-time');
const names = ['slabs', 'piles', 'boundaries'];

function start() {
  const renderer = new THREE.WebGLRenderer({antialias: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  stage.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#09151f');
  const camera = new THREE.PerspectiveCamera(40, 1, .01, 30);
  camera.position.set(2.6, 1.4, 2.6);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.minDistance = 1.2;
  controls.maxDistance = 7;
  controls.enablePan = false;
  controls.listenToKeyEvents(stage);
  controls.saveState();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x455566, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2);
  light.position.set(3, 4, 2);
  scene.add(light);
  // A proper rotation, not a reflection: source north (+z) becomes screen up (+y).
  const globe = new THREE.Group();
  globe.rotation.x = -Math.PI / 2;
  scene.add(globe);
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(.546, 48, 24),
    new THREE.MeshStandardMaterial({color: 0x343c46, roughness: 1})));
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(1, 24, 12),
    new THREE.MeshBasicMaterial({color: 0x567083, wireframe: true, transparent: true, opacity: .15})));
  let displayed = null;
  let pending = null;
  let debounce;
  const draw = () => renderer.render(scene, camera);
  const resize = new ResizeObserver(() => {
    const width = stage.clientWidth, height = stage.clientHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    draw();
  });
  resize.observe(stage);
  controls.addEventListener('change', draw);
  function dispose(group) {
    group.traverse((object) => { object.geometry?.dispose(); object.material?.dispose(); });
    group.removeFromParent();
  }
  function visible() {
    displayed?.children.forEach((object) => { object.visible = $(`mantle-${object.name}`).checked; });
    draw();
  }
  names.forEach((name) => $(`mantle-${name}`).addEventListener('change', visible));
  $('mantle-reset').addEventListener('click', () => { controls.reset(); draw(); });
  async function load() {
    pending?.abort();
    const controller = new AbortController();
    pending = controller;
    const frame = frames[Number(slider.value)];
    $('mantle-age').textContent = `${frame.age_ma} Ma`;
    slider.setAttribute('aria-valuetext', `${frame.age_ma} Ma`);
    status.textContent = strings.loading;
    stage.dataset.loading = 'true';
    // Hide the old geometry while the label refers to a new age.
    if (displayed) displayed.visible = false;
    draw();
    const next = new THREE.Group();
    try {
      const payloads = await Promise.all(names.map(async (name) => {
        const info = frame.layers[name];
        const response = await fetch(info.url, {signal: controller.signal});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const buffer = await response.arrayBuffer();
        if (buffer.byteLength !== info.bytes || info.bytes !== 12 * info.points + 4 * info.indices) {
          throw new Error('Mesh byte count mismatch');
        }
        return {name, info, buffer};
      }));
      if (controller.signal.aborted) return;
      for (const {name, info, buffer} of payloads) {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buffer, 0, 3 * info.points), 3));
        geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer, 12 * info.points, info.indices), 1));
        let object;
        if (info.primitive === 'lines') {
          object = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({color: 0xdce6dd}));
        } else {
          geometry.computeVertexNormals();
          object = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
            color: name === 'slabs' ? 0x529dd6 : 0xef9546, side: THREE.DoubleSide, roughness: .8,
          }));
        }
        object.name = name;
        next.add(object);
      }
      if (displayed) dispose(displayed);
      displayed = next;
      globe.add(next);
      visible();
      stage.dataset.frame = String(frame.index);
      status.textContent = `${frame.age_ma} Ma · ${strings.ready}`;
    } catch (error) {
      dispose(next);
      if (!controller.signal.aborted) {
        controller.abort();
        status.textContent = strings.error;
        delete stage.dataset.frame;
      }
    } finally {
      if (pending === controller) stage.dataset.loading = 'false';
    }
  }
  slider.addEventListener('input', () => {
    // Do not download all crossed ages while a finger drags across the timeline.
    pending?.abort(); pending = null;
    clearTimeout(debounce);
    if (displayed) displayed.visible = false;
    delete stage.dataset.frame;
    stage.dataset.loading = 'true';
    const age = `${frames[Number(slider.value)].age_ma} Ma`;
    $('mantle-age').textContent = age;
    slider.setAttribute('aria-valuetext', age);
    status.textContent = strings.loading;
    draw();
    debounce = setTimeout(load, 180);
  });
  load();
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault(); clearTimeout(debounce); pending?.abort();
    slider.disabled = true; stage.dataset.loading = 'false';
    delete stage.dataset.frame; status.textContent = strings.webgl;
  });
  renderer.domElement.addEventListener('webglcontextrestored', () => {
    slider.disabled = false; load();
  });
  window.addEventListener('pagehide', () => {
    clearTimeout(debounce); pending?.abort(); resize.disconnect(); controls.dispose();
    dispose(globe); renderer.dispose();
  }, {once: true});
}
try { start(); } catch { status.textContent = strings.webgl; }
