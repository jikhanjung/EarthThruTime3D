import * as THREE from 'three';
import { OrbitControls } from '../vendor/three/OrbitControls.js';

// A local equidistant approximation for a comparison view, not a new plate frame.
const KM_PER_DEGREE = Math.PI*6371/180, UNIT_KM = 4000;
const COS_LATITUDE = Math.cos(10*Math.PI/180);
export function terrainPosition(lon, lat, metres, exaggeration) {
  return [(lon-77.5)*KM_PER_DEGREE*COS_LATITUDE/UNIT_KM,
    Math.max(0, metres)/1000*exaggeration/UNIT_KM,
    -(lat-10)*KM_PER_DEGREE/UNIT_KM];
}
export function createSurface(stage, select, reset) {
  const renderer = new THREE.WebGLRenderer({antialias: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  stage.appendChild(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#071820');
  const camera = new THREE.PerspectiveCamera(40, 1, .01, 30);
  camera.position.set(2.0, 2.4, 2.8);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false; controls.minDistance = 1; controls.maxDistance = 10;
  controls.listenToKeyEvents(stage); controls.saveState();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x416575, 2.5));
  const light = new THREE.DirectionalLight(0xffffff, 2.2); light.position.set(-3, 5, -2); scene.add(light);
  const material = new THREE.MeshStandardMaterial({vertexColors: true, roughness: .9, side: THREE.DoubleSide});
  const sectionMaterial = new THREE.LineBasicMaterial({color: 0xff83b2});
  let mesh, section, current, currentAge;
  let sectionVisible=true;const sectionLabels=[];
  const draw = () => renderer.render(scene, camera);
  const observer = new ResizeObserver(() => {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w/h; camera.updateProjectionMatrix(); draw();
  });
  observer.observe(stage); controls.addEventListener('change', draw);
  reset.addEventListener('click', () => { controls.reset(); draw(); });
  function label(text, z) {
    const canvas = document.createElement('canvas'); canvas.width = 64; canvas.height = 48;
    const ctx = canvas.getContext('2d'); ctx.font = 'bold 32px sans-serif'; ctx.fillStyle = '#ffb9d2'; ctx.fillText(text, 4, 35);
    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map: texture, depthTest: false}));
    const [x] = terrainPosition(85, 0, 0, 1);
    sprite.position.set(x, .12, z); sprite.scale.set(.16, .12, 1); scene.add(sprite);sectionLabels.push(sprite);
  }
  label('A', terrainPosition(85, -40, 0, 1)[2]);
  label('A′', terrainPosition(85, 60, 0, 1)[2]);
  function update(surface, age) {
    if (!surface) throw new Error('Missing regional terrain');
    current = surface; currentAge = age;
    const {nx, ny, heights_m: heights, bounds} = surface;
    if (heights.length !== nx*ny) throw new Error('Invalid terrain shape');
    const [west, east, south, north] = bounds;
    const exaggeration = Number(select.value), positions = [], colors = [], indices = [], sectionPoints = [];
    const color = new THREE.Color();
    for (let j=0; j<ny; j++) {
      const lat = north - j/(ny-1)*(north-south);
      for (let i=0; i<nx; i++) {
        const lon = west + i/(nx-1)*(east-west), height = heights[j*nx+i];
        positions.push(...terrainPosition(lon, lat, height, exaggeration));
        if (height <= 0) color.setRGB(.04, .21, .31);
        else if (height < 1500) color.setRGB(.20+height/1500*.25, .35+height/1500*.07, .19);
        else { const t = Math.min(1, (height-1500)/4500); color.setRGB(.45+t*.40, .42+t*.43, .25+t*.6); }
        colors.push(color.r, color.g, color.b);
        if (i<nx-1 && j<ny-1) {
          const a = j*nx+i; indices.push(a, a+nx, a+1, a+1, a+nx, a+nx+1);
        }
      }
      const col = (85-west)/(east-west)*(nx-1), left = Math.floor(col), u = col-left;
      const height = heights[j*nx+left]*(1-u) + heights[j*nx+left+1]*u;
      const p = terrainPosition(85, lat, height, exaggeration); p[1] += .008;
      sectionPoints.push(new THREE.Vector3(...p));
    }
    if (mesh) { mesh.geometry.dispose(); scene.remove(mesh); }
    if (section) { section.geometry.dispose(); scene.remove(section); }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(indices); geometry.computeVertexNormals();
    mesh = new THREE.Mesh(geometry, material); scene.add(mesh);
    section = new THREE.Line(new THREE.BufferGeometry().setFromPoints(sectionPoints), sectionMaterial); section.visible=sectionVisible;scene.add(section);
    stage.dataset.age = String(age); stage.dataset.ve = String(exaggeration);
    draw();
  }
  select.addEventListener('change', () => { if (current) update(current, currentAge); });
  return {update, setSectionVisible(visible) {sectionVisible=visible;if(section)section.visible=visible;sectionLabels.forEach(label=>label.visible=visible);draw();}, dispose() {
    observer.disconnect(); controls.dispose();
    scene.traverse(object => {
      object.geometry?.dispose(); object.material?.map?.dispose(); object.material?.dispose();
    });
    renderer.dispose();
  }};
}
