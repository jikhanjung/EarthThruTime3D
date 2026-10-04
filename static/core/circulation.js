// The present-day circulation schematic (wwolf P02 step 5): the textbook conveyor belt as
// ribbons, one colour per layer, the deeper ones underneath, with triangles where water sinks
// (pointing down) and where a drawn deep limb ends and rises (pointing up); and the overturning
// sections behind it, drawn on a canvas in the legend. The data is
// scripts/build_circulation.py's.
//
// createCirculation owns all of it: when it is available (the present, for now), loading,
// the meshes, the legend and the note. The page tells it the stop and hands it the view each
// frame; flux's currents select only says whether it is chosen.
import * as THREE from 'three';

export const BELT_COLOURS = { surface: '#f07b3f', deep: '#3d7fe0', bottom: '#9b6ad8' };
export const MARK_COLOURS = { sink: '#1f4fa8', rise: BELT_COLOURS.surface, rim: '#f4f7f8' };
const LAYERS = { bottom: { width: 0.38, order: 3 }, deep: { width: 0.5, order: 5 }, surface: { width: 0.7, order: 7 } };
const RIM = new THREE.Color('#0d1620');
const LIFT = 0.0025;
// A bottom-water line fades out over its last 25 points (about 1500 km at the build's 60 km
// spacing): it mixes upward as it spreads, with no single end.
const FADE_POINTS = 25;
// Arrowheads along a line every 30 points (about 1800 km), none at its end.
const ARROW_POINTS = 30;
const MARK_SIZE = 2.3, MARK_RIM = 1;

// Opacity along a line: 1, or falling to 0 over the last FADE_POINTS points of a fading one.
export function fadeOf(line) {
  const last = line.points.length - 1;
  return line.points.map((_, i) => (line.fade ? Math.min(1, (last - i) / FADE_POINTS) : 1));
}

// A flat map's edge: the longitudes of a triangle that straddles it span most of the map once
// measured from the centre, as the overlay lines test it (sheetLongitude in globe.js).
export function seamOf(projection, meridian) {
  if (projection === 'globe') return () => false;
  const sheet = (lon) => ((((lon - meridian) % 360) + 540) % 360) - 180;
  return (...lons) => Math.max(...lons.map(sheet)) - Math.min(...lons.map(sheet)) > 180;
}

// The ribbons as triangles in degrees, built once: for each layer a rim and a fill part, each
// { order, corners: [lon, lat] per vertex, colours: RGBA per vertex }.
export function ribbonParts(lines) {
  const parts = [];
  for (const [kind, style] of Object.entries(LAYERS)) {
    const rim = { order: style.order, corners: [], colours: [] };
    const fill = { order: style.order + 1, corners: [], colours: [] };
    const colour = new THREE.Color(BELT_COLOURS[kind]);
    const push = (part, corners, tint, alphas) => {
      for (const corner of corners) part.corners.push(...corner);
      for (const alpha of alphas) part.colours.push(tint.r, tint.g, tint.b, alpha);
    };
    for (const line of lines.filter((l) => l.kind === kind)) {
      const alpha = fadeOf(line);
      // Each point's direction, in degrees square on the ground.
      const sides = line.points.map((p, i) => {
        const a = line.points[Math.max(0, i - 1)], b = line.points[Math.min(line.points.length - 1, i + 1)];
        const cosLat = Math.max(Math.cos(THREE.MathUtils.degToRad(p[1])), 0.1);
        let dx = (((b[0] - a[0] + 540) % 360) - 180) * cosLat, dy = b[1] - a[1];
        const n = Math.hypot(dx, dy) || 1;
        dx /= n; dy /= n;
        return { dx, dy, cosLat, p };
      });
      const edge = (s, w, k) => [s.p[0] - k * s.dy * w / s.cosLat, s.p[1] + k * s.dx * w];
      for (let i = 0; i + 1 < sides.length; i++) {
        const [s0, s1, a0, a1] = [sides[i], sides[i + 1], alpha[i], alpha[i + 1]];
        for (const [part, w, tint] of [[rim, style.width + 0.12, RIM], [fill, style.width, colour]]) {
          const [l0, r0, l1, r1] = [edge(s0, w, 1), edge(s0, w, -1), edge(s1, w, 1), edge(s1, w, -1)];
          push(part, [l0, r0, l1], tint, [a0, a0, a1]);
          push(part, [r0, r1, l1], tint, [a0, a1, a1]);
        }
      }
      // A line ends at a mark or on another line, where its water carries on in another layer.
      for (let i = sides.length - 1 - ARROW_POINTS / 2; i > 3; i -= ARROW_POINTS) {
        const s = sides[i];
        const w = style.width * 2.4, length = w * 1.6;
        const tip = [s.p[0] + s.dx * length / s.cosLat, s.p[1] + s.dy * length];
        const a = [alpha[i], alpha[i], alpha[i]];
        push(rim, [edge(s, w + 0.2, 1), edge(s, w + 0.2, -1), [tip[0] + s.dx * 0.25 / s.cosLat, tip[1] + s.dy * 0.25]], RIM, a);
        push(fill, [edge(s, w, 1), edge(s, w, -1), tip], colour, a);
      }
    }
    parts.push(rim, fill);
  }
  return parts;
}

// A mark's triangle in degrees, pointing down where water sinks and up where it rises.
export function markCorners([kind, lon, lat], size) {
  const cosLat = Math.max(Math.cos(THREE.MathUtils.degToRad(lat)), 0.25);
  const sign = kind === 'sink' ? 1 : -1;
  return [[lon - size / cosLat, lat + sign * size * 0.7], [lon + size / cosLat, lat + sign * size * 0.7],
    [lon, lat - sign * size]];
}

// How far east a mark must move so its rim triangle keeps to one side of a flat map's edge:
// 0 when it does not straddle it, else the nearest whole-degree shift that clears it.
export function markShift(mark, seam) {
  const lons = (shift) => markCorners([mark[0], mark[1] + shift, mark[2]], MARK_SIZE + MARK_RIM).map((c) => c[0]);
  if (!seam(...lons(0))) return 0;
  for (let step = 1; step <= 40; step++) {
    for (const shift of [step, -step]) if (!seam(...lons(shift))) return shift;
  }
  return 0;
}

export function createCirculation({ url, earth, stage, L, fmt }) {
  const $ = (id) => document.getElementById(id);
  let data = null, load = null, failed = false;
  let present = false, chosen = false;
  let group = null, meshes = [], parts = [], viewKey = '';
  const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide,
    transparent: true, opacity: 0.95, depthWrite: false });
  const legend = document.createElement('figure');
  legend.className = 'flux-legend circulation-legend';
  legend.id = 'circulation-legend';
  legend.hidden = true;

  const drawn = () => Boolean(chosen && present && data);

  function fetchData() {
    load ??= fetch(url)
      .then((response) => {
        if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
        return response.json();
      })
      .then((json) => {
        const { schematic, sections } = json ?? {};
        if (!Array.isArray(schematic?.lines) || !Array.isArray(schematic?.marks) || !Array.isArray(sections?.basins)) {
          throw new Error(`${url}: not a circulation file`);
        }
        data = json;
        build();
      })
      .catch((error) => {
        console.error(error);
        failed = true;
        load = null;
      })
      .finally(update);
  }

  // The meshes, once: the triangles in degrees and their colours are fixed; only the positions
  // follow the view. Every part shares one material, so one shader program.
  function build() {
    const marks = data.schematic.marks;
    const markPart = (size, tint) => ({ order: size > MARK_SIZE ? 9 : 10, marks: true, size,
      corners: marks.flatMap((m) => markCorners(m, size).flat()),
      colours: marks.flatMap((m) => {
        const colour = new THREE.Color(tint ?? MARK_COLOURS[m[0]]);
        return [0, 1, 2].flatMap(() => [colour.r, colour.g, colour.b, 1]);
      }) });
    parts = [...ribbonParts(data.schematic.lines), markPart(MARK_SIZE + MARK_RIM, MARK_COLOURS.rim), markPart(MARK_SIZE)];
    group = new THREE.Group();
    meshes = parts.map((part) => {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(part.corners.length / 2 * 3), 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(part.colours, 4));
      const mesh = new THREE.Mesh(geometry, material);
      mesh.renderOrder = part.order;
      mesh.frustumCulled = false;
      group.add(mesh);
      return mesh;
    });
    group.visible = false;
    earth.add(group);
  }

  // Positions for the view: each triangle placed, or folded to a point where it would
  // straddle a flat map's edge; a mark straddling it moves whole to one side instead.
  function place(view) {
    const seam = seamOf(view.projection, view.meridian);
    const shifts = data.schematic.marks.map((mark) => markShift(mark, seam));
    let marksShown = 0;
    parts.forEach((part, index) => {
      const positions = meshes[index].geometry.attributes.position.array;
      const c = part.corners;
      for (let t = 0; t < c.length / 6; t++) {
        const shift = part.marks ? shifts[t] : 0;
        const lons = [c[t * 6] + shift, c[t * 6 + 2] + shift, c[t * 6 + 4] + shift];
        const fold = seam(...lons);
        if (part.marks && part.size === MARK_SIZE && !fold) marksShown++;
        for (let k = 0; k < 3; k++) {
          const vertex = fold ? 0 : k;
          const point = view.place(lons[vertex], c[t * 6 + vertex * 2 + 1], LIFT);
          positions.set([point.x, point.y, point.z], (t * 3 + k) * 3);
        }
      }
      meshes[index].geometry.attributes.position.needsUpdate = true;
    });
    stage.dataset.circulationMarks = String(marksShown);
  }

  function showLegend() {
    const dock = $('map-legend') || stage.parentElement;
    if (legend.parentElement !== dock) {
      const head = dock.querySelector('.legend-head');
      if (head) head.after(legend); else dock.prepend(legend);
    }
    const wanted = chosen && present;
    legend.hidden = !(wanted && (data || failed));
    if (legend.hidden) return;
    if (!data) {
      legend.innerHTML = `<figcaption>${L.circulationLegend}</figcaption><p class="belt-note">${L.circulationFailed}</p>`;
      delete legend.dataset.built;
      return;
    }
    if (legend.dataset.built) return;
    const line = (colour, text) => `<li><span style="background:${colour}"></span>${text}</li>`;
    const mark = (glyph, colour, text) => `<li><b class="belt-mark" style="color:${colour}">${glyph}</b>${text}</li>`;
    const basins = data.sections.basins;
    legend.innerHTML = `<figcaption>${L.circulationLegend}</figcaption><ul>`
      + line(BELT_COLOURS.surface, L.beltSurface) + line(BELT_COLOURS.deep, L.beltDeep)
      + line(BELT_COLOURS.bottom, L.beltBottom) + mark('▼', MARK_COLOURS.sink, L.beltSink)
      + mark('▲', MARK_COLOURS.rise, L.beltRise)
      + line(`linear-gradient(90deg,${BELT_COLOURS.bottom},transparent)`, L.beltFade)
      + `</ul><p class="belt-note">${L.beltCross}</p><details><summary>${L.sectionsHead}</summary>`
      + basins.map((_, index) => `<canvas data-section="${index}"></canvas>`).join('')
      + `<p class="belt-note">${L.sectionsCaption}</p></details>`;
    // The sections are drawn once opened, when the canvas has its width.
    const details = legend.querySelector('details');
    details.addEventListener('toggle', () => {
      if (!details.open) return;
      for (const canvas of details.querySelectorAll('canvas')) {
        const basin = basins[canvas.dataset.section];
        drawSection(canvas, basin, sectionTitle(basin, L, fmt));
      }
    });
    legend.dataset.built = 'true';
  }

  function update() {
    if (chosen && present && !data && !load && !failed) fetchData();
    const note = $('circulation-note');
    if (note) note.hidden = !drawn();
    if (group) group.visible = drawn();
    viewKey = '';
    stage.dataset.circulation = failed && chosen && present ? 'error' : drawn() ? String(data.schematic.lines.length) : '';
    showLegend();
  }

  return {
    // Whether this stop has a schematic: the present only, for now.
    setStop(isPresent) {
      present = isPresent;
      update();
    },
    available: () => present,
    // Whether the currents select is on the schematic.
    show(on) {
      if (on !== chosen) failed = false;
      chosen = on;
      update();
    },
    // Each animation frame: view = { key, projection, meridian, place(lon, lat, lift), hidden }.
    // `hidden` while the globe's surface is cut away or see-through, where the belt would show
    // through from the far side.
    frame(view) {
      if (!group) return;
      group.visible = drawn() && !view.hidden;
      if (stage.dataset.circulationShown !== String(group.visible)) stage.dataset.circulationShown = String(group.visible);
      if (!group.visible || view.key === viewKey) return;
      viewKey = view.key;
      place(view);
    },
  };
}

// A section's title: the basin and the numbers the build read at stated latitudes.
export function sectionTitle(basin, L, fmt) {
  const latitude = (lat) => `${Math.abs(lat)}°${lat >= 0 ? 'N' : 'S'}`;
  const parts = [basin.basin === 'atlantic' ? L.basinAtlantic : L.basinIndoPacific];
  if (basin.red) parts.push(fmt(L.sectionRed, { lat: latitude(basin.red.lat), sv: basin.red.sv.toFixed(1) }));
  if (basin.blue) parts.push(fmt(L.sectionBlue, { lat: latitude(basin.blue.lat), sv: basin.blue.sv.toFixed(1) }));
  return parts.join(' · ');
}

// An overturning section: latitude across (north to the right), depth down, the streamfunction
// as colour (red: clockwise, water north near the surface and sinking in the north; blue: the
// opposite), contours every 4 Sv with an arrowhead along the flow.
const OVERTURN = ['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b'];
export const SECTION_BACKGROUND = '#3a3f44';
function ramp(t) {
  const x = THREE.MathUtils.clamp(t, 0, 1) * (OVERTURN.length - 1);
  const i = Math.min(Math.floor(x), OVERTURN.length - 2);
  return new THREE.Color(OVERTURN[i]).lerp(new THREE.Color(OVERTURN[i + 1]), x - i);
}
export function drawSection(canvas, section, title, limit = 20) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 256, height = canvas.clientHeight || 110;
  canvas.width = width * ratio; canvas.height = height * ratio;
  const context = canvas.getContext('2d');
  context.scale(ratio, ratio);
  const left = 30, right = 4, top = 14, bottom = 15;
  const { lat, depth, psi } = section;
  const deepest = Math.ceil(depth[depth.length - 1] / 1000) * 1000;
  const x = (la) => left + (la - lat[0]) / (lat[lat.length - 1] - lat[0]) * (width - left - right);
  const y = (d) => top + d / deepest * (height - top - bottom);
  context.fillStyle = SECTION_BACKGROUND;
  context.fillRect(left, top, width - left - right, height - top - bottom);
  for (let k = 0; k < depth.length; k++) {
    const d0 = k ? depth[k - 1] : 0;
    for (let i = 0; i < lat.length; i++) {
      const value = psi[k][i];
      if (value === null) continue;
      const a = x(i ? (lat[i - 1] + lat[i]) / 2 : lat[0]), b = x(i + 1 < lat.length ? (lat[i] + lat[i + 1]) / 2 : lat[i]);
      context.fillStyle = `#${ramp((value / limit + 1) / 2).getHexString()}`;
      context.fillRect(a, y(d0), b - a + 0.6, y(depth[k]) - y(d0) + 0.6);
    }
  }
  context.strokeStyle = 'rgba(20,24,28,.7)';
  context.fillStyle = 'rgba(20,24,28,.85)';
  context.lineWidth = 0.8;
  for (const { points } of section.contours) {
    context.beginPath();
    points.forEach(([la, d], i) => (i ? context.lineTo(x(la), y(d)) : context.moveTo(x(la), y(d))));
    context.stroke();
    if (points.length < 8) continue;
    const m = Math.floor(points.length / 2), [a, b] = [points[m - 1], points[m + 1]];
    const angle = Math.atan2(y(b[1]) - y(a[1]), x(b[0]) - x(a[0]));
    const [px, py] = [x(points[m][0]), y(points[m][1])];
    context.beginPath();
    context.moveTo(px + 5 * Math.cos(angle), py + 5 * Math.sin(angle));
    context.lineTo(px + 4 * Math.cos(angle + 2.5), py + 4 * Math.sin(angle + 2.5));
    context.lineTo(px + 4 * Math.cos(angle - 2.5), py + 4 * Math.sin(angle - 2.5));
    context.fill();
  }
  context.fillStyle = '#b9c9d1';
  context.font = '9px system-ui, sans-serif';
  context.textBaseline = 'middle';
  for (let d = 0; d <= deepest; d += 2000) context.fillText(d ? `${d / 1000} km` : '0', 2, y(d));
  context.textAlign = 'center';
  context.textBaseline = 'alphabetic';
  for (let la = Math.ceil(lat[0] / 30) * 30; la <= lat[lat.length - 1]; la += 30) {
    context.fillText(la ? `${Math.abs(la)}°${la > 0 ? 'N' : 'S'}` : '0°', x(la), height - 3);
  }
  context.textAlign = 'left';
  context.fillStyle = '#dcebee';
  context.fillText(title, left, 10);
}
