// The present-day circulation schematic (wwolf P02 step 5): the textbook conveyor belt as
// ribbons, one colour per layer, the deeper ones underneath, with triangles where water sinks
// (pointing down) and where a drawn deep limb ends and rises (pointing up); and the overturning
// sections behind it, drawn on a canvas. The data is scripts/build_circulation.py's.
import * as THREE from 'three';

export const BELT_COLOURS = { surface: '#f07b3f', deep: '#3d7fe0', bottom: '#9b6ad8' };
const LAYERS = { bottom: { width: 0.38, order: 3 }, deep: { width: 0.5, order: 5 }, surface: { width: 0.7, order: 7 } };
const MARKS = { sink: { fill: '#1f4fa8', down: true }, rise: { fill: '#f07b3f', down: false } };
const RIM = new THREE.Color('#0d1620');
// A bottom-water line fades out over its last 25 points (about 1500 km): it mixes upward as it
// spreads, with no single end.
const FADE_POINTS = 25;

// Opacity along a line: 1, or falling to 0 over the last FADE_POINTS points of a fading one.
export function fadeOf(line) {
  const last = line.points.length - 1;
  return line.points.map((_, i) => (line.fade ? Math.min(1, (last - i) / FADE_POINTS) : 1));
}

function meshOf(part, order, size) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(part.position, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(part.colour, size));
  const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide,
    transparent: true, opacity: 0.95, depthWrite: false }));
  mesh.renderOrder = order;
  return mesh;
}

// place(lon, lat) -> Vector3 on the current projection; seam(...lons) -> true where a flat
// map's edge falls between the longitudes, so a triangle spanning it is left out rather than
// stretched across the whole map.
export function buildBelt(data, place, seam) {
  const group = new THREE.Group();
  for (const [kind, style] of Object.entries(LAYERS)) {
    const fill = { position: [], colour: [] }, rim = { position: [], colour: [] };
    const colour = new THREE.Color(BELT_COLOURS[kind]);
    const tri = (target, corners, tint, alphas) => {
      if (seam(...corners.map((c) => c[0]))) return;
      for (const [lon, lat] of corners) target.position.push(...place(lon, lat).toArray());
      for (const alpha of alphas) target.colour.push(tint.r, tint.g, tint.b, alpha);
    };
    for (const line of data.lines.filter((l) => l.kind === kind)) {
      const alpha = fadeOf(line);
      // Each point's direction, in degrees square on the ground.
      const sides = line.points.map((p, i) => {
        const a = line.points[Math.max(0, i - 1)], b = line.points[Math.min(line.points.length - 1, i + 1)];
        const c = Math.max(Math.cos(THREE.MathUtils.degToRad(p[1])), 0.1);
        let dx = (((b[0] - a[0] + 540) % 360) - 180) * c, dy = b[1] - a[1];
        const n = Math.hypot(dx, dy) || 1;
        dx /= n; dy /= n;
        return { dx, dy, c, p };
      });
      const edge = (s, w, k) => [s.p[0] - k * s.dy * w / s.c, s.p[1] + k * s.dx * w];
      for (let i = 0; i + 1 < sides.length; i++) {
        const [s0, s1, a0, a1] = [sides[i], sides[i + 1], alpha[i], alpha[i + 1]];
        for (const [target, w, tint] of [[rim, style.width + 0.12, RIM], [fill, style.width, colour]]) {
          const [l0, r0, l1, r1] = [edge(s0, w, 1), edge(s0, w, -1), edge(s1, w, 1), edge(s1, w, -1)];
          tri(target, [l0, r0, l1], tint, [a0, a0, a1]);
          tri(target, [r0, r1, l1], tint, [a0, a1, a1]);
        }
      }
      // Arrowheads along the line every 30 points (about 1800 km), none at its end: a line ends
      // at a mark or on another line, where its water carries on in another layer.
      for (let i = sides.length - 16; i > 3; i -= 30) {
        const s = sides[i];
        const w = style.width * 2.4, length = w * 1.6;
        const tip = [s.p[0] + s.dx * length / s.c, s.p[1] + s.dy * length];
        tri(rim, [edge(s, w + 0.2, 1), edge(s, w + 0.2, -1), [tip[0] + s.dx * 0.25 / s.c, tip[1] + s.dy * 0.25]],
          RIM, [alpha[i], alpha[i], alpha[i]]);
        tri(fill, [edge(s, w, 1), edge(s, w, -1), tip], colour, [alpha[i], alpha[i], alpha[i]]);
      }
    }
    group.add(meshOf(rim, style.order, 4), meshOf(fill, style.order + 1, 4));
  }
  const fill = { position: [], colour: [] }, rim = { position: [], colour: [] };
  const push = (target, corners, tint) => {
    if (seam(...corners.map((c) => c[0]))) return;
    for (const [lon, lat] of corners) target.position.push(...place(lon, lat).toArray());
    for (let i = 0; i < 3; i++) target.colour.push(tint.r, tint.g, tint.b);
  };
  for (const [kind, lon, lat] of data.marks) {
    const style = MARKS[kind];
    const c = Math.max(Math.cos(THREE.MathUtils.degToRad(lat)), 0.25);
    const sign = style.down ? 1 : -1;
    const tri = (size) => [[lon - size / c, lat + sign * size * 0.7], [lon + size / c, lat + sign * size * 0.7],
      [lon, lat - sign * size]];
    push(rim, tri(3.3), new THREE.Color('#f4f7f8'));
    push(fill, tri(2.3), new THREE.Color(style.fill));
  }
  group.add(meshOf(rim, 9, 3), meshOf(fill, 10, 3));
  return group;
}

// An overturning section: latitude across (north to the right), depth down, the streamfunction
// as colour (red: clockwise, water north near the surface and sinking in the north; blue: the
// opposite), contours every 4 Sv with an arrowhead along the flow.
const OVERTURN = ['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b'];
function ramp(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1) * (OVERTURN.length - 1);
  const i = Math.min(Math.floor(x), OVERTURN.length - 2);
  return new THREE.Color(OVERTURN[i]).lerp(new THREE.Color(OVERTURN[i + 1]), x - i);
}
export function drawSection(canvas, section, title, limit = 20) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 256, height = canvas.clientHeight || 110;
  canvas.width = width * ratio; canvas.height = height * ratio;
  const g = canvas.getContext('2d');
  g.scale(ratio, ratio);
  const left = 30, right = 4, top = 14, bottom = 15;
  const { lat, depth, psi } = section;
  const deepest = Math.ceil(depth[depth.length - 1] / 1000) * 1000;
  const x = (la) => left + (la - lat[0]) / (lat[lat.length - 1] - lat[0]) * (width - left - right);
  const y = (d) => top + d / deepest * (height - top - bottom);
  g.fillStyle = '#3a3f44';
  g.fillRect(left, top, width - left - right, height - top - bottom);
  for (let k = 0; k < depth.length; k++) {
    const d0 = k ? depth[k - 1] : 0;
    for (let i = 0; i < lat.length; i++) {
      const value = psi[k][i];
      if (value === null) continue;
      const a = x(i ? (lat[i - 1] + lat[i]) / 2 : lat[0]), b = x(i + 1 < lat.length ? (lat[i] + lat[i + 1]) / 2 : lat[i]);
      g.fillStyle = `#${ramp((value / limit + 1) / 2).getHexString()}`;
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
  g.fillText(title, left, 10);
}
