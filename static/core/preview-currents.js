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
// style (optional): { colour, width (half-width in degrees), order, endArrow } for one fixed
// colour and width, as the conveyor's layers use; endArrow false puts the arrowheads along the
// line only. A point's fifth value, when given, is its opacity (a ribbon fading out).
export function buildRibbons(lines, mode, place, seam, style = {}) {
  const speeds = lines.flat().map(p => p[2]).sort((a, b) => a - b);
  const reference = speeds[Math.floor(speeds.length * 0.95)] || 1;
  const fill = { position: [], colour: [] };
  const rim = { position: [], colour: [] };
  const dark = new THREE.Color('#0d1620');
  const tri = (target, a, b, c, colours, alphas) => {
    if (seam(a[0], b[0], c[0])) return;
    for (const [lon, lat] of [a, b, c]) target.position.push(...place(lon, lat).toArray());
    colours.forEach((colour, i) => target.colour.push(colour.r, colour.g, colour.b, alphas[i]));
  };
  const alphaOf = p => p[4] ?? 1;
  const halfWidth = speed => style.width ?? 0.16 + 0.55 * Math.min(1, Math.sqrt(speed / reference));
  const fixed = style.colour && new THREE.Color(style.colour);
  const colourAt = p => fixed || colourOf(p, mode, reference);
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
      const c0 = colourAt(s0.p), c1 = colourAt(s1.p);
      const [l0, r0, l1, r1] = [edge(s0, w0, 1), edge(s0, w0, -1), edge(s1, w1, 1), edge(s1, w1, -1)];
      const [a0, a1] = [alphaOf(s0.p), alphaOf(s1.p)];
      tri(fill, l0, r0, l1, [c0, c0, c1], [a0, a0, a1]);
      tri(fill, r0, r1, l1, [c0, c1, c1], [a0, a1, a1]);
      const [L0, R0, L1, R1] = [edge(s0, w0 + 0.12, 1), edge(s0, w0 + 0.12, -1), edge(s1, w1 + 0.12, 1), edge(s1, w1 + 0.12, -1)];
      tri(rim, L0, R0, L1, [dark, dark, dark], [a0, a0, a1]);
      tri(rim, R0, R1, L1, [dark, dark, dark], [a0, a1, a1]);
    }
    // Arrowheads every 30 points (about 1800 km), from the end or, with endArrow false, from
    // half a spacing before it.
    for (let i = sides.length - 1 - (style.endArrow === false ? 15 : 0); i > 3; i -= 30) {
      const s = sides[i];
      const w = halfWidth(s.p[2]) * 2.4, length = w * 1.6;
      const tip = [s.p[0] + s.dx * length / s.c, s.p[1] + s.dy * length];
      const colour = colourAt(s.p);
      const a = [alphaOf(s.p), alphaOf(s.p), alphaOf(s.p)];
      tri(rim, edge(s, w + 0.2, 1), edge(s, w + 0.2, -1), [tip[0] + s.dx * 0.25 / s.c, tip[1] + s.dy * 0.25], [dark, dark, dark], a);
      tri(fill, edge(s, w, 1), edge(s, w, -1), tip, [colour, colour, colour], a);
    }
  }
  const group = new THREE.Group();
  for (const [part, order] of [[rim, style.order ?? 3], [fill, (style.order ?? 3) + 1]]) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.position, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(part.colour, 4));
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide,
      transparent: true, opacity: part === rim ? 0.55 : 0.95, depthWrite: false }));
    mesh.renderOrder = order;
    group.add(mesh);
  }
  group.userData.reference = reference;
  return group;
}

// The conveyor belt: the warm surface limb, North Atlantic Deep Water and Antarctic Bottom
// Water as ribbons of one colour each, the deeper ones underneath; triangles where water
// sinks (pointing down) and where a drawn deep limb ends and rises (pointing up).
export const CONVEYOR_COLOURS = { surface: '#f07b3f', deep: '#3d7fe0', bottom: '#9b6ad8' };
export function buildConveyor(data, place, seam) {
  const group = new THREE.Group();
  const layers = { bottom: { width: 0.38, order: 3 }, deep: { width: 0.5, order: 5 }, surface: { width: 0.7, order: 7 } };
  // A line marked "fade" fades out over its last 25 points (about 1500 km): the bottom
  // water mixing upward as it spreads, where no single end exists.
  const faded = line => line.points.map(([lon, lat], i) =>
    [lon, lat, 1, 0, line.fade ? Math.min(1, (line.points.length - 1 - i) / 25) : 1]);
  for (const [kind, style] of Object.entries(layers)) {
    const lines = data.lines.filter(line => line.kind === kind).map(faded);
    if (lines.length) group.add(buildRibbons(lines, 'speed', place, seam, { ...style, colour: CONVEYOR_COLOURS[kind], endArrow: false }));
  }
  const fill = { position: [], colour: [] }, rim = { position: [], colour: [] };
  const push = (target, points, colour) => {
    if (seam(...points.map(p => p[0]))) return;
    for (const [lon, lat] of points) target.position.push(...place(lon, lat).toArray());
    for (let i = 0; i < 3; i++) target.colour.push(colour.r, colour.g, colour.b);
  };
  for (const [kind, lon, lat] of data.marks) {
    const c = Math.max(Math.cos(THREE.MathUtils.degToRad(lat)), 0.25);
    const tri = size => {
      const s = kind === 'sink' ? 1 : -1;   // sink: point down (south on the map), rise: up
      return [[lon - size / c, lat + s * size * 0.7], [lon + size / c, lat + s * size * 0.7], [lon, lat - s * size]];
    };
    push(rim, tri(3.3), new THREE.Color('#f4f7f8'));
    push(fill, tri(2.3), new THREE.Color(kind === 'sink' ? '#1f4fa8' : '#f07b3f'));
  }
  for (const [part, order] of [[rim, 9], [fill, 10]]) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.position, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(part.colour, 3));
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide,
      transparent: true, opacity: 0.95, depthWrite: false }));
    mesh.renderOrder = order;
    group.add(mesh);
  }
  return group;
}

// An overturning cross-section on a canvas: latitude across (north to the right), depth
// down, the streamfunction as colour (red: clockwise, water north near the surface and
// sinking in the north; blue: the opposite), contours every 4 Sv with an arrowhead along
// the flow, as scripts/preview_currents.py oriented them.
const OVERTURN = ['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b'];
export function drawSection(canvas, section, limit = 20) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 256, height = canvas.clientHeight || 110;
  canvas.width = width * ratio; canvas.height = height * ratio;
  const g = canvas.getContext('2d');
  g.scale(ratio, ratio);
  const left = 30, right = 4, top = 14, bottom = 15;
  const { lat, depth, psi } = section;
  const deepest = Math.ceil(depth[depth.length - 1] / 1000) * 1000;
  const x = la => left + (la - lat[0]) / (lat[lat.length - 1] - lat[0]) * (width - left - right);
  const y = d => top + d / deepest * (height - top - bottom);
  g.fillStyle = '#3a3f44';
  g.fillRect(left, top, width - left - right, height - top - bottom);
  for (let k = 0; k < depth.length; k++) {
    const d0 = k ? depth[k - 1] : 0;
    for (let i = 0; i < lat.length; i++) {
      const value = psi[k][i];
      if (value === null) continue;
      const a = x(i ? (lat[i - 1] + lat[i]) / 2 : lat[0]), b = x(i + 1 < lat.length ? (lat[i] + lat[i + 1]) / 2 : lat[i]);
      g.fillStyle = '#' + ramp(OVERTURN, (value / limit + 1) / 2).getHexString();
      g.fillRect(a, y(d0), b - a + 0.6, y(depth[k]) - y(d0) + 0.6);
    }
  }
  g.strokeStyle = 'rgba(20,24,28,.7)';
  g.fillStyle = 'rgba(20,24,28,.85)';
  g.lineWidth = 0.8;
  for (const { points } of section.contours) {
    g.beginPath();
    points.forEach(([la, d], i) => (i ? g.lineTo(x(la), y(d)) : g.moveTo(x(la), y(d))));
    g.stroke();
    if (points.length < 8) continue;
    const m = Math.floor(points.length / 2), [a, b] = [points[m - 1], points[m + 1]];
    const angle = Math.atan2(y(b[1]) - y(a[1]), x(b[0]) - x(a[0]));
    const [px, py] = [x(points[m][0]), y(points[m][1])];
    g.beginPath();
    g.moveTo(px + 5 * Math.cos(angle), py + 5 * Math.sin(angle));
    g.lineTo(px + 4 * Math.cos(angle + 2.5), py + 4 * Math.sin(angle + 2.5));
    g.lineTo(px + 4 * Math.cos(angle - 2.5), py + 4 * Math.sin(angle - 2.5));
    g.fill();
  }
  g.fillStyle = '#b9c9d1';
  g.font = '9px system-ui, sans-serif';
  g.textBaseline = 'middle';
  for (let d = 0; d <= deepest; d += 2000) g.fillText(d ? `${d / 1000} km` : '0', 2, y(d));
  g.textAlign = 'center';
  g.textBaseline = 'alphabetic';
  for (let la = Math.ceil(lat[0] / 30) * 30; la <= lat[lat.length - 1]; la += 30) {
    g.fillText(la ? `${Math.abs(la)}°${la > 0 ? 'N' : 'S'}` : '0°', x(la), height - 3);
  }
  g.textAlign = 'left';
  g.fillStyle = '#dcebee';
  g.fillText(`${section.title}  빨강 최대 ${Math.round(section.red)} Sv · 파랑 최대 ${Math.round(section.blue)} Sv`, left, 10);
}
