import * as THREE from 'three';

// Earth-local coordinates: geographic xyz → (x,z,-y); no depth exaggeration.
export function overlayMatrix(rotation) {
  const r = rotation;
  // prettier-ignore -- keep the matrix rows visible.
  return new THREE.Matrix4().set(
    r[0][0], r[0][1], r[0][2], 0,
    r[2][0], r[2][1], r[2][2], 0,
    -r[1][0], -r[1][1], -r[1][2], 0,
    0, 0, 0, 1,
  );
}

// Shared local-space cut: climate/ice live in the surface shader, lines share it.
export const CUT_UNIFORMS = `
  uniform float mantleCutaway;
  uniform vec3 mantleCutCentre;
  uniform float mantleCutCos;
  varying vec3 vCutPosition;`;
export const CUT_SURFACE = `
  if (mantleCutaway > 0.5 && dot(normalize(vCutPosition), mantleCutCentre) > mantleCutCos) discard;`;

export function sectionPath(rotation) {
  const matrix = overlayMatrix(rotation);
  return Array.from({ length: 101 }, (_, i) => {
    const lat = ((-40 + i) * Math.PI) / 180;
    const lon = (85 * Math.PI) / 180;
    return new THREE.Vector3(
      Math.cos(lat) * Math.cos(lon),
      Math.cos(lat) * Math.sin(lon),
      Math.sin(lat),
    )
      .applyMatrix4(matrix)
      .multiplyScalar(1.006);
  });
}

export function decodeMantleMesh(buffer, info) {
  if (
    info.primitive !== 'triangles' ||
    info.indices % 3 ||
    buffer.byteLength !== info.bytes ||
    info.bytes !== info.points * 12 + info.indices * 4
  ) {
    throw new Error('Invalid mantle mesh length');
  }
  const positions = new Float32Array(buffer, 0, info.points * 3);
  const indices = new Uint32Array(buffer, info.points * 12, info.indices);
  if (positions.some((v) => !Number.isFinite(v)) || indices.some((i) => i >= info.points)) {
    throw new Error('Invalid mantle mesh');
  }
  return { positions, indices };
}

function dispose(group) {
  group?.traverse((object) => {
    object.geometry?.dispose();
    object.material?.map?.dispose();
    object.material?.dispose();
  });
  group?.removeFromParent();
}

function mantleGroup(frame, payloads) {
  const group = new THREE.Group();
  group.add(new THREE.HemisphereLight(0xdbefff, 0x152234, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2);
  light.position.set(2, 3, 2);
  group.add(light);
  const matrix = overlayMatrix(frame.rotation_matrix);
  for (const { name, positions, indices } of payloads) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.applyMatrix4(matrix);
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({
      color: name === 'slabs' ? 0x529dd6 : 0xef9546,
      side: THREE.DoubleSide,
      roughness: 0.8,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = name;
    group.add(mesh);
  }
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.546, 64, 32),
    new THREE.MeshStandardMaterial({ color: 0x69727c, roughness: 0.85 }),
  );
  core.name = 'core';
  group.add(core);
  return group;
}

function sectionTrace(rotation) {
  const trace = new THREE.Group();
  const path = sectionPath(rotation);
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(path),
    new THREE.LineBasicMaterial({ color: 0xff83b2 }),
  );
  line.name = 'section-line';
  trace.add(line);
  for (const [text, point] of [
    ['A', path[0]],
    ['A′', path.at(-1)],
  ]) {
    const canvas = document.createElement('canvas');
    canvas.width = 80;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffb9d2';
    ctx.font = 'bold 44px sans-serif';
    ctx.fillText(text, 4, 48);
    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas) }),
    );
    sprite.position.copy(point).multiplyScalar(1.014);
    sprite.scale.set(0.065, 0.052, 1);
    trace.add(sprite);
  }
  return trace;
}

// Owns GPU resources and uniforms. The controller supplies values, never DOM ids.
export function createMantleScene({ earth, uniforms, surfaceMaterial }) {
  let displayed = null;
  let trace = null;
  const centre = new THREE.Vector3();
  const raycaster = new THREE.Raycaster();
  raycaster.params.Line.threshold = 0.02;

  function clear() {
    dispose(displayed);
    dispose(trace);
    displayed = null;
    trace = null;
  }

  async function prepare(frame, signal) {
    const payloads = await Promise.all(
      ['slabs', 'piles'].map(async (name) => {
        const info = frame.layers[name];
        const response = await fetch(info.url, { signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return { name, ...decodeMantleMesh(await response.arrayBuffer(), info) };
      }),
    );
    if (signal.aborted) throw new DOMException('Superseded', 'AbortError');
    let next = mantleGroup(frame, payloads);
    // Preparing a frame never replaces the displayed globe. The surface loader
    // commits both together, or the controller disposes this uncommitted frame.
    return {
      commit() {
        clear();
        displayed = next;
        next = null;
        earth.add(displayed);
        trace = sectionTrace(frame.rotation_matrix);
        earth.add(trace);
      },
      dispose() {
        dispose(next);
        next = null;
      },
    };
  }

  function update({ active, opacity, cutaway, layers, showSection }) {
    const visible = active && Boolean(displayed);
    const surfaceOpacity = visible ? opacity : 1;
    uniforms.mantleSurfaceOpacity.value = surfaceOpacity;
    const transparent = surfaceOpacity < 1;
    if (surfaceMaterial.transparent !== transparent) {
      surfaceMaterial.transparent = transparent;
      surfaceMaterial.needsUpdate = true;
    }
    surfaceMaterial.depthWrite = surfaceOpacity === 1;
    uniforms.mantleCutaway.value = visible && cutaway ? 1 : 0;
    if (displayed) {
      displayed.visible = visible;
      for (const name of ['slabs', 'piles', 'core']) {
        displayed.getObjectByName(name).visible = layers[name];
      }
    }
    if (trace) trace.visible = visible && showSection;
    return { opacity: surfaceOpacity, cutaway: uniforms.mantleCutaway.value === 1 };
  }

  function setCutaway({ longitude, latitude, radius }) {
    const lon = (longitude * Math.PI) / 180;
    const lat = (latitude * Math.PI) / 180;
    centre.set(Math.cos(lat) * Math.cos(lon), Math.sin(lat), -Math.cos(lat) * Math.sin(lon));
    uniforms.mantleCutCentre.value.copy(centre);
    uniforms.mantleCutCos.value = Math.cos((radius * Math.PI) / 180);
  }

  function sectionHit(x, y, box, camera) {
    if (!trace?.visible) return false;
    raycaster.setFromCamera(
      new THREE.Vector2(
        ((x - box.left) / box.width) * 2 - 1,
        (-(y - box.top) / box.height) * 2 + 1,
      ),
      camera,
    );
    const hit = raycaster.intersectObject(trace.getObjectByName('section-line'))[0];
    return Boolean(hit && hit.point.dot(camera.position.clone().sub(hit.point)) > 0);
  }

  return {
    prepare,
    update,
    clear,
    setCutaway,
    sectionHit,
    focusPoint: () => centre.clone(),
    cutsPoint: (point) =>
      uniforms.mantleCutaway.value > 0.5 &&
      point.clone().normalize().dot(centre) > uniforms.mantleCutCos.value,
  };
}
