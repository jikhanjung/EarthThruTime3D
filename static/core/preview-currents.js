// Preview: the major currents as ribbons, the textbook "conveyor belt" picture drawn from
// data. The lines are streamlines traced through the fastest water of a current field by
// scripts/preview_currents.py, each point [lon, lat, speed m/s, temperature anomaly C]. A
// ribbon is widest where the current is fastest and ends in an arrowhead, with more heads
// along long lines; coloured by speed, or warm against cold by the water's temperature
// minus the ocean mean at its latitude (the atlas's warm and cold currents). A dark rim
// under each ribbon keeps it readable over the sea's blues.
import * as THREE from 'three';

const SPEED = ['#cc4778', '#f89540', '#f0f921'];            // plasma, slow to fast
const ANOMALY = ['#3a8fd9', '#9ecae1', '#f7f7f7', '#f4a582', '#d6273b'];   // -4..+4 C

function ramp(stops, t) {
  const x = THREE.MathUtils.clamp(t, 0, 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  return new THREE.Color(stops[i]).lerp(new THREE.Color(stops[i + 1]), x - i);
}

export function colourOf(point, mode, reference) {
  return mode === 'temp' ? ramp(ANOMALY, (point[3] + 4) / 8) : ramp(SPEED, Math.sqrt(point[2] / reference));
}

// lines: the traced currents; place(lon, lat) -> Vector3 on the current projection;
// seam(...lons) -> true where a flat map's edge falls between the longitudes, so a triangle
// spanning it is left out rather than stretched across the whole map.
export function buildRibbons(lines, mode, place, seam) {
  const speeds = lines.flat().map(p => p[2]).sort((a, b) => a - b);
  const reference = speeds[Math.floor(speeds.length * 0.95)] || 1;
  const fill = { position: [], colour: [] };
  const rim = { position: [], colour: [] };
  const dark = new THREE.Color('#0d1620');
  const tri = (target, a, b, c, colours) => {
    if (seam(a[0], b[0], c[0])) return;
    for (const [lon, lat] of [a, b, c]) target.position.push(...place(lon, lat).toArray());
    for (const colour of colours) target.colour.push(colour.r, colour.g, colour.b);
  };
  const halfWidth = speed => 0.16 + 0.55 * Math.min(1, Math.sqrt(speed / reference));
  for (const line of lines) {
    // Sides of the ribbon at every point, in degrees, square on the ground.
    const sides = line.map((p, i) => {
      const a = line[Math.max(0, i - 1)], b = line[Math.min(line.length - 1, i + 1)];
      const c = Math.max(Math.cos(THREE.MathUtils.degToRad(p[1])), 0.1);
      let dx = (((b[0] - a[0] + 540) % 360) - 180) * c, dy = b[1] - a[1];
      const n = Math.hypot(dx, dy) || 1;
      dx /= n; dy /= n;
      return { dx, dy, c, p };
    });
    const edge = (s, w, k) => [s.p[0] - k * s.dy * w / s.c, s.p[1] + k * s.dx * w];
    for (let i = 0; i + 1 < sides.length; i++) {
      const s0 = sides[i], s1 = sides[i + 1];
      const w0 = halfWidth(s0.p[2]), w1 = halfWidth(s1.p[2]);
      const c0 = colourOf(s0.p, mode, reference), c1 = colourOf(s1.p, mode, reference);
      const [l0, r0, l1, r1] = [edge(s0, w0, 1), edge(s0, w0, -1), edge(s1, w1, 1), edge(s1, w1, -1)];
      tri(fill, l0, r0, l1, [c0, c0, c1]);
      tri(fill, r0, r1, l1, [c0, c1, c1]);
      const [L0, R0, L1, R1] = [edge(s0, w0 + 0.12, 1), edge(s0, w0 + 0.12, -1), edge(s1, w1 + 0.12, 1), edge(s1, w1 + 0.12, -1)];
      tri(rim, L0, R0, L1, [dark, dark, dark]);
      tri(rim, R0, R1, L1, [dark, dark, dark]);
    }
    // Arrowheads at the end and every 30 points (about 1800 km) along the way.
    for (let i = sides.length - 1; i > 3; i -= 30) {
      const s = sides[i];
      const w = halfWidth(s.p[2]) * 2.4, length = w * 1.6;
      const tip = [s.p[0] + s.dx * length / s.c, s.p[1] + s.dy * length];
      const colour = colourOf(s.p, mode, reference);
      tri(rim, edge(s, w + 0.2, 1), edge(s, w + 0.2, -1), [tip[0] + s.dx * 0.25 / s.c, tip[1] + s.dy * 0.25], [dark, dark, dark]);
      tri(fill, edge(s, w, 1), edge(s, w, -1), tip, [colour, colour, colour]);
    }
  }
  const group = new THREE.Group();
  for (const [part, order] of [[rim, 3], [fill, 4]]) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.position, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(part.colour, 3));
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide,
      transparent: true, opacity: part === rim ? 0.55 : 0.95, depthWrite: false }));
    mesh.renderOrder = order;
    group.add(mesh);
  }
  group.userData.reference = reference;
  return group;
}
