// Preview: ocean currents as moving dots with fading trails, the technique of
// earth.nullschool and Mapbox's webgl-wind, kept in longitude/latitude so the surface
// shader draws it on the globe and every flat map like any other layer.
//
// A current field is a 360 x 180 texture (scripts/preview_currents.py): red and green the
// east and north speed, sqrt-encoded over +-2 m/s, blue where there is a value. The dots'
// positions live in a float texture (longitude, latitude, age, speed); each frame a
// full-screen pass moves every dot by the current under it (the east step divided by
// cos latitude, so a dot keeps its speed on the ground), and a dot that is old, on land or
// picked at random starts again anywhere on the sphere. The dots are then drawn as points
// into a longitude/latitude trail texture whose alpha fades a little every frame.
import * as THREE from 'three';

const QUAD = new THREE.PlaneGeometry(2, 2);
const CAMERA = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const PASS_VERTEX = 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';

function pass(fragmentShader, uniforms) {
  const material = new THREE.ShaderMaterial({ vertexShader: PASS_VERTEX, fragmentShader, uniforms,
    depthTest: false, depthWrite: false });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(QUAD, material));
  return { scene, material };
}

export function createFlow(renderer, { side = 128, width = 1024, height = 512 } = {}) {
  const count = side * side;
  const floatTarget = () => new THREE.WebGLRenderTarget(side, side, { type: THREE.FloatType,
    format: THREE.RGBAFormat, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter,
    depthBuffer: false });
  const trailTarget = () => new THREE.WebGLRenderTarget(width, height, { type: THREE.UnsignedByteType,
    minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false,
    wrapS: THREE.RepeatWrapping });
  let positions = [floatTarget(), floatTarget()];
  let trails = [trailTarget(), trailTarget()];
  // Start with every dot somewhere random and a random age, so they do not restart together.
  const start = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) {
    start[i * 4] = Math.random() * 360 - 180;
    start[i * 4 + 1] = THREE.MathUtils.radToDeg(Math.asin(Math.random() * 2 - 1));
    start[i * 4 + 2] = Math.random() * 120;
  }
  const seed = new THREE.DataTexture(start, side, side, THREE.RGBAFormat, THREE.FloatType);
  seed.needsUpdate = true;
  let source = seed;

  const move = pass(`
    uniform sampler2D positions;
    uniform sampler2D field;
    uniform float pace;
    uniform float maxAge;
    uniform float drop;
    uniform float seed;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    vec2 metres(vec2 e) { vec2 s = e * 2.0 - 1.0; return sign(s) * s * s * 2.0; }
    void main() {
      vec4 p = texture2D(positions, vUv);
      vec4 f = texture2D(field, vec2((p.x + 180.0) / 360.0, (p.y + 90.0) / 180.0));
      vec2 v = metres(f.rg);
      float wet = step(0.5, f.b);
      p.x += v.x * pace / max(cos(radians(p.y)), 0.05);
      p.y += v.y * pace;
      p.x = mod(p.x + 180.0, 360.0) - 180.0;
      p.z += 1.0;
      if (wet < 0.5 || p.z > maxAge || hash(vUv + seed) < drop || abs(p.y) > 88.0) {
        p.x = hash(vUv * 1.7 + seed + 0.31) * 360.0 - 180.0;
        p.y = degrees(asin(hash(vUv * 2.3 + seed + 0.77) * 2.0 - 1.0));
        p.z = 0.0;
      }
      p.w = length(v) * wet;
      gl_FragColor = p;
    }`, { positions: { value: null }, field: { value: null }, pace: { value: 0.12 },
          maxAge: { value: 140 }, drop: { value: 0.003 }, seed: { value: 0 } });

  const fade = pass(`
    uniform sampler2D previous;
    uniform float keep;
    varying vec2 vUv;
    void main() {
      vec4 c = texture2D(previous, vUv);
      c.a = max(c.a * keep - 0.004, 0.0);
      gl_FragColor = c;
    }`, { previous: { value: null }, keep: { value: 0.982 } });

  // One point per dot, placed in the trail texture's own longitude/latitude space.
  const refs = new Float32Array(count * 2);
  for (let i = 0; i < count; i++) {
    refs[i * 2] = ((i % side) + 0.5) / side;
    refs[i * 2 + 1] = (Math.floor(i / side) + 0.5) / side;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
  geometry.setAttribute('ref', new THREE.BufferAttribute(refs, 2));
  const dots = new THREE.Points(geometry, new THREE.ShaderMaterial({
    uniforms: { positions: { value: null }, size: { value: 2.0 }, colourBySpeed: { value: 0 } },
    vertexShader: `
      uniform sampler2D positions;
      uniform float size;
      attribute vec2 ref;
      varying float vSpeed;
      varying float vAge;
      void main() {
        vec4 p = texture2D(positions, ref);
        vSpeed = p.w;
        vAge = p.z;
        gl_Position = vec4(p.x / 180.0, p.y / 90.0, 0.0, 1.0);
        gl_PointSize = size;
      }`,
    fragmentShader: `
      uniform float colourBySpeed;
      varying float vSpeed;
      varying float vAge;
      void main() {
        if (vSpeed <= 0.0 || vAge < 2.0) discard;
        // White as NASA draws it, or by speed from dim blue-white to bright yellow; sRGB,
        // decoded by the surface shader.
        float t = clamp(sqrt(vSpeed / 0.8), 0.0, 1.0);
        vec3 speedColour = mix(vec3(0.62, 0.78, 0.95), vec3(1.0, 0.93, 0.35), t);
        // Faint in slow water, so the fast currents stand out as streaks.
        gl_FragColor = vec4(mix(vec3(1.0), speedColour, colourBySpeed), clamp(vSpeed / 0.25, 0.2, 1.0));
      }`,
    depthTest: false, depthWrite: false, transparent: false }));
  dots.frustumCulled = false;
  const dotScene = new THREE.Scene();
  dotScene.add(dots);

  let frame = 0;
  const api = {
    get texture() { return trails[0].texture; },
    colourBySpeed(on) { dots.material.uniforms.colourBySpeed.value = on ? 1 : 0; },
    clear() {
      const was = renderer.getRenderTarget();
      for (const target of trails) { renderer.setRenderTarget(target); renderer.setClearColor(0x000000, 0); renderer.clear(); }
      renderer.setRenderTarget(was);
    },
    // One frame: move the dots over the field, fade the trails, draw the dots.
    step(field, seconds = 1 / 60) {
      if (!field) return;
      const was = renderer.getRenderTarget();
      const autoClear = renderer.autoClear;
      const pace = Math.min(seconds * 60, 3);
      move.material.uniforms.positions.value = source.texture ?? source;
      move.material.uniforms.field.value = field;
      move.material.uniforms.pace.value = 0.2 * pace;
      move.material.uniforms.seed.value = (frame++ % 997) / 997;
      renderer.setRenderTarget(positions[1]);
      renderer.render(move.scene, CAMERA);
      positions = [positions[1], positions[0]];
      source = positions[0];
      fade.material.uniforms.previous.value = trails[0].texture;
      fade.material.uniforms.keep.value = Math.pow(0.982, pace);
      renderer.setRenderTarget(trails[1]);
      renderer.render(fade.scene, CAMERA);
      renderer.autoClear = false;
      dots.material.uniforms.positions.value = positions[0].texture;
      renderer.render(dotScene, CAMERA);
      renderer.autoClear = autoClear;
      trails = [trails[1], trails[0]];
      renderer.setRenderTarget(was);
    },
  };
  api.clear();
  return api;
}
