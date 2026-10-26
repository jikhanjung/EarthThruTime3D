// The present-day Earth in motion (jikhanjung P10): wind and surface currents as particles
// on 2D canvases over the globe, clouds as a white shell. Ported from GSM's "움직이는 지구"
// (koprifossillab 007·014·016·018), whose Cesium/OpenLayers projection is replaced by the
// globe's own: a particle moves in longitude and latitude, and the page places it.
//
// None of it is live. Wind and clouds are one moment pinned when the release was built, the
// currents a 1992–2018 mean; the caption under the age says which, whenever a layer is on.
// On a past stop of the elevation series the currents are FOAM's nearest run (wwolf P02),
// in the same baked form; wind and clouds stay with the present.
import * as THREE from 'three';

const EARTH_RADIUS = 6371000;
const M_PER_LAT = Math.PI * EARTH_RADIUS / 180;
// Speed bins follow GSM: bin i covers ref·i/3 to ref·(i+1)/3; a particle at `ref` moves `px`
// screen pixels a frame. Wind warm, thin and quick; currents teal, thick, slow, long tails.
export const WIND = {
  ref: { '10m': 12, '250hPa': 45 }, px: 1.4, life: 80, fade: 0.93, width: 1.0,
  colours: ['#bfbfbf', '#e3e3e3', '#ffffff', '#fff2a8', '#ffd65c', '#ffab40', '#ff7a33', '#ff3d3d'],
};
// The mean is slower than any one day's flow (median 0.07 m/s, 90th percentile 0.2), so the
// reference is 0.3 m/s rather than GSM's 0.5 for its three-day snapshots.
export const OCEAN = {
  ref: 0.3, px: 0.75, life: 170, fade: 0.965, width: 1.8,
  colours: ['#2a8a8f', '#2c9d97', '#30b0a2', '#3ac3ae', '#4fd5bb', '#6fe4c9', '#97f0da', '#c4f9ec'],
};

// A baked field: R = u, G = v over the ranges given beside it, B = sea (currents only).
// Wind cells are grid nodes from -180°, 90°; current cells are 0.25° cell centres.
export function decodeField(rgba, width, height, range, centred) {
  const size = width * height;
  const u = new Float32Array(size), v = new Float32Array(size);
  const sea = centred ? new Uint8Array(size) : null;
  const [u0, u1] = range.u, [v0, v1] = range.v;
  for (let i = 0; i < size; i++) {
    u[i] = u0 + rgba[i * 4] * (u1 - u0) / 255;
    v[i] = v0 + rgba[i * 4 + 1] * (v1 - v0) / 255;
    if (sea) sea[i] = rgba[i * 4 + 2] > 127 ? 1 : 0;
  }
  return { u, v, sea, width, height, centred };
}

// [u, v] in m/s at a longitude and latitude, bilinear, wrapping in longitude; null on land.
export function sampleField(field, lon, lat) {
  const { width, height, centred } = field;
  const cells = width / 360;
  const x = ((lon + 180 - (centred ? 0.5 / cells : 0)) * cells % width + width) % width;
  const y = (90 - (centred ? 0.5 / cells : 0) - lat) * cells;
  if (y < 0 || y > height - 1) return null;
  const x0 = Math.floor(x), y0 = Math.floor(y);
  const x1 = (x0 + 1) % width, y1 = Math.min(y0 + 1, height - 1);
  if (field.sea && !field.sea[Math.round(y) * width + (Math.round(x) % width)]) return null;
  const fx = x - x0, fy = y - y0;
  const at = (grid) => (grid[y0 * width + x0] * (1 - fx) + grid[y0 * width + x1] * fx) * (1 - fy)
    + (grid[y1 * width + x0] * (1 - fx) + grid[y1 * width + x1] * fx) * fy;
  return [at(field.u), at(field.v)];
}

// A field moved with the map between two stops: each cell takes the value the field holds
// where the map's travel brings it from, `shift(lon, lat)` degrees east and north (the share
// of the travel field the mountain marks move by), sea included, so the particles keep to the
// coast the page draws. Built once per place, not per particle.
export function warpField(field, shift) {
  const { width, height, centred } = field;
  const cells = width / 360;
  const half = centred ? 0.5 / cells : 0;
  const values = { ...field, sea: null };
  const u = new Float32Array(width * height), v = new Float32Array(width * height);
  const sea = field.sea ? new Uint8Array(width * height) : null;
  for (let row = 0; row < height; row++) {
    const lat = 90 - half - row / cells;
    for (let col = 0; col < width; col++) {
      const lon = -180 + half + col / cells;
      const [east, north] = shift(lon, lat);
      const fromLon = ((lon - east + 540) % 360) - 180;
      const fromLat = Math.max(-90 + half, Math.min(90 - half, lat - north));
      const index = row * width + col;
      const flow = sampleField(values, fromLon, fromLat);
      if (flow) [u[index], v[index]] = flow;
      if (sea) sea[index] = sampleField(field, fromLon, fromLat) ? 1 : 0;
    }
  }
  return { u, v, sea, width, height, centred };
}

// Beyond this view shift in one frame the old trails are wiped rather than faded.
export const WIPE_PX = 40;
// How much of a trail a frame keeps when the view shifted `moved` px: the layer's own fade
// at rest, falling continuously with the shift (0.4 px halves the exponent's headroom), so
// the trail length follows the camera's speed instead of jumping.
export function trailFade(fade, moved) {
  return Math.pow(fade, 1 + Math.max(0, moved) / 0.4);
}

// One step: `k` metres per frame for each m/s, east by u, north by v.
export function advance(lon, lat, u, v, k) {
  const shrink = Math.max(0.05, Math.cos(lat * Math.PI / 180));
  return [((lon + u * k / (M_PER_LAT * shrink) + 540) % 360) - 180, lat + v * k / M_PER_LAT];
}

export function speedBin(speed, ref) {
  return Math.max(0, Math.min(7, Math.floor(speed / ref * 3)));
}

// The legend's eight steps as [label, colour], in m/s.
export function legendSteps(style, ref) {
  const digits = ref < 2 ? 2 : 0;
  const at = (i) => (ref * i / 3).toFixed(digits);
  return style.colours.map((colour, i) => [i === 7 ? `> ${at(7)}` : `${at(i)}–${at(i + 1)}`, colour]);
}

// "2026-10-01 18:00 UTC" and the visitor's own clock for the same moment.
export function momentText(iso, lang) {
  const date = new Date(iso.replace('Z', ':00Z'));
  const utc = `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
  let local = '';
  try {
    local = date.toLocaleString(lang, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
  } catch { /* an unknown locale keeps UTC alone */ }
  return local && !/UTC$/.test(local) ? `${utc} (${local})` : utc;
}

export function createFlux({ config: present, stage, L, fmt, lang, api }) {
  // `present` is the present-day bundle, or null where it is not built; the past currents
  // still need the particles then.
  if (!present && !api.pastCurrents) return null;
  const config = present ?? {};
  const $ = (id) => document.getElementById(id);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // `past`: the drawn stop's own currents when it is not the present, from the page.
  const state = { present: false, past: null, wind: null, currents: false, clouds: null };
  let warp = { key: '', base: null, field: null };
  const fields = new Map();
  const layers = {};
  let fluxTime = 0;
  const when = $('flux-when');

  // ── particles ─────────────────────────────────────────────────────
  function particleLayer(name, style) {
    const canvas = document.createElement('canvas');
    canvas.className = 'flux-canvas';
    canvas.dataset.layer = name;
    canvas.hidden = true;
    canvas.setAttribute('aria-hidden', 'true');
    // Beside the globe's own canvas, not inside it: the stage holds the WebGL canvas alone.
    stage.parentElement.insertBefore(canvas, stage.nextSibling);
    return { name, style, canvas, context: canvas.getContext('2d'), particles: [], field: null, ref: 1, key: '', drawn: 0 };
  }
  layers.ocean = particleLayer('ocean', OCEAN);
  layers.wind = particleLayer('wind', WIND);

  function loadField(key, url, range, centred) {
    if (!fields.has(key)) {
      fields.set(key, (async () => {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Download failed: ${url}`);
        const bitmap = await createImageBitmap(await response.blob(), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const context = canvas.getContext('2d', { willReadFrequently: true });
        context.drawImage(bitmap, 0, 0);
        bitmap.close();
        const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
        return decodeField(data, canvas.width, canvas.height, range, centred);
      })());
      fields.get(key).catch(() => fields.delete(key));
    }
    return fields.get(key);
  }

  function spawn(layer, width, height, box) {
    for (let tries = 0; tries < (layer.name === 'ocean' ? 30 : 12); tries++) {
      const x = Math.random() * width, y = Math.random() * height;
      const place = api.lonLatAt(box.left + x, box.top + y);
      if (!place) continue;
      if (layer.field && sampleField(layer.field, place[0], place[1]) === null) continue;
      return { lon: place[0], lat: place[1], age: Math.floor(Math.random() * layer.style.life), x: null, y: null };
    }
    return { lon: 0, lat: 0, age: layer.style.life, x: null, y: null };
  }

  // Metres under one screen pixel at the middle of the view, or near the globe's limb.
  let metresPerPixel = 20000;
  function measure(box) {
    for (const [fx, fy] of [[0.5, 0.5], [0.5, 0.4], [0.4, 0.5], [0.6, 0.5], [0.5, 0.6]]) {
      const a = api.lonLatAt(box.left + box.width * fx, box.top + box.height * fy);
      const b = api.lonLatAt(box.left + box.width * fx + 10, box.top + box.height * fy);
      if (!a || !b) continue;
      const shrink = Math.cos((a[1] + b[1]) / 2 * Math.PI / 180);
      const dx = ((b[0] - a[0] + 540) % 360 - 180) * shrink, dy = b[1] - a[1];
      const metres = Math.hypot(dx, dy) * M_PER_LAT / 10;
      if (metres > 0) { metresPerPixel = metres; return; }
    }
  }

  // Median screen shift, in px, that the new view gives a sample of placed particles before
  // they move; Infinity when none is placed.
  function viewShift(particles) {
    const shifts = [];
    const stride = Math.max(1, Math.floor(particles.length / 64));
    for (let i = 0; i < particles.length; i += stride) {
      const p = particles[i];
      if (p.x === null) continue;
      const screen = api.screenOf(p.lon, p.lat);
      if (screen) shifts.push(Math.hypot(screen[0] - p.x, screen[1] - p.y));
    }
    if (!shifts.length) return Infinity;
    shifts.sort((a, b) => a - b);
    return shifts[shifts.length >> 1];
  }

  function step(layer, width, height, box, viewKey, dpr) {
    const { context, style } = layer;
    let fade = style.fade;
    if (layer.key !== viewKey) {
      // The view moved, so the trails drawn in the old view sit a little off. How far is
      // measured, not assumed: the median screen shift of a sample of particles. The trails
      // then fade faster in proportion (trailFade), short while the view moves fast and
      // lengthening smoothly as a damped camera settles. Wiping on every change made a
      // settling camera alternate wiped and kept frames, short and long tails (jikhanjung 113).
      // A new projection or canvas size, or a jump, still wipes. Every particle is placed
      // again in the new view, so this frame draws its next step either way.
      layer.key = viewKey;
      const frame = `${api.projection()}|${width}x${height}`;
      const moved = viewShift(layer.particles);
      if (frame !== layer.frame || !(moved < WIPE_PX)) {
        layer.frame = frame;
        layer.clears = (layer.clears || 0) + 1;
        stage.dataset[`${layer.name}Clears`] = String(layer.clears);
        context.setTransform(1, 0, 0, 1, 0, 0);
        context.clearRect(0, 0, layer.canvas.width, layer.canvas.height);
      } else {
        fade = trailFade(style.fade, moved);
      }
      stage.dataset[`${layer.name}Shift`] = Number.isFinite(moved) ? moved.toFixed(2) : '';
      for (const p of layer.particles) {
        const screen = api.screenOf(p.lon, p.lat);
        p.x = screen ? screen[0] : null;
        p.y = screen ? screen[1] : null;
      }
      layer.drawn = 0;
    }
    if (reduced && layer.drawn > 60) return;
    layer.drawn++;
    const count = Math.round(Math.min(layer.name === 'ocean' ? 6000 : 5000,
      Math.max(600, width * height / (layer.name === 'ocean' ? 220 : 260))));
    while (layer.particles.length < count) layer.particles.push(spawn(layer, width, height, box));
    layer.particles.length = count;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.globalCompositeOperation = 'destination-in';
    context.fillStyle = `rgba(0,0,0,${fade})`;
    context.fillRect(0, 0, width, height);
    context.globalCompositeOperation = 'source-over';
    const k = metresPerPixel * style.px / layer.ref;
    const bins = Array.from({ length: 8 }, () => []);
    for (let i = 0; i < layer.particles.length; i++) {
      let p = layer.particles[i];
      const flow = p.age < style.life ? sampleField(layer.field, p.lon, p.lat) : null;
      if (!flow || Math.abs(p.lat) > 89.5) {
        layer.particles[i] = spawn(layer, width, height, box);
        continue;
      }
      const [lon, lat] = advance(p.lon, p.lat, flow[0], flow[1], k);
      const screen = api.screenOf(lon, lat);
      p.age++;
      if (!screen || screen[0] < -20 || screen[1] < -20 || screen[0] > width + 20 || screen[1] > height + 20) {
        layer.particles[i] = spawn(layer, width, height, box);
        continue;
      }
      if (p.x !== null && Math.hypot(screen[0] - p.x, screen[1] - p.y) < 60) {
        bins[speedBin(Math.hypot(flow[0], flow[1]), layer.ref)].push(p.x, p.y, screen[0], screen[1]);
      }
      p.lon = lon; p.lat = lat; p.x = screen[0]; p.y = screen[1];
    }
    context.lineWidth = style.width;
    context.lineCap = 'round';
    bins.forEach((segments, bin) => {
      if (!segments.length) return;
      context.strokeStyle = style.colours[bin];
      context.beginPath();
      for (let j = 0; j < segments.length; j += 4) {
        context.moveTo(segments[j], segments[j + 1]);
        context.lineTo(segments[j + 2], segments[j + 3]);
      }
      context.stroke();
    });
  }

  // ── clouds ────────────────────────────────────────────────────────
  const cloudUniforms = {
    cloudMap: { value: null }, cloudOpacity: { value: 0.85 },
    projection: api.uniforms.projection, meridian: api.uniforms.meridian,
  };
  const cloudMesh = new THREE.Mesh(api.surfaceMesh.geometry, new THREE.ShaderMaterial({
    uniforms: cloudUniforms, transparent: true, depthWrite: false,
    vertexShader: `
      uniform int projection;
      varying vec2 vUv;
      void main() {
        vUv = uv;
        // Just above the ground on the sphere, just in front of a flat sheet.
        vec3 lifted = projection == 0 ? position * 1.006 : position + vec3(0.0, 0.0, 0.0006);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(lifted, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D cloudMap;
      uniform float cloudOpacity;
      uniform int projection;
      uniform float meridian;
      varying vec2 vUv;
      const float PI = 3.141592653589793;
      ${api.locateGLSL}
      void main() {
        vec2 uv;
        if (!locate(uv)) discard;
        // Baked as opacity already (GSM's curves), so white at that opacity.
        float alpha = texture2D(cloudMap, uv).r * cloudOpacity;
        if (alpha < 0.004) discard;
        gl_FragColor = vec4(vec3(1.0), alpha);
        #include <colorspace_fragment>
      }`,
  }));
  cloudMesh.renderOrder = 1;
  cloudMesh.visible = false;
  cloudMesh.frustumCulled = false;
  api.earth.add(cloudMesh);

  // ── controls ──────────────────────────────────────────────────────
  const windSelect = $('wind-layer'), currentToggle = $('currents'), cloudSelect = $('cloud-layer');
  const legend = document.createElement('figure');
  legend.className = 'flux-legend';
  legend.id = 'flux-legend';
  legend.hidden = true;

  function legendBlock(title, style, ref) {
    const steps = legendSteps(style, ref).map(([label, colour]) =>
      `<li><span style="background:${colour}"></span>${label}</li>`).join('');
    return `<figcaption>${title}</figcaption><ol>${steps}</ol>`;
  }

  function moment() { return config.weather ? momentText(config.weather.t, lang) : ''; }
  // The legend heads keep UTC alone; the caption under the age carries the local clock too.
  function momentUtc() { const t = config.weather?.t ?? ''; return t && `${t.slice(0, 10)} ${t.slice(11, 16)} UTC`; }

  function describe(past) {
    if (past) return state.currents && layers.ocean.field ? fmt(L.fluxOceanPast, { run: past.run_ma }) : '';
    const parts = [];
    const time = moment();
    if (state.wind && state.clouds) parts.push(fmt(L.fluxWind, { time }));
    else if (state.wind) parts.push(fmt(L.fluxWindOnly, { time }));
    else if (state.clouds) parts.push(fmt(L.fluxCloudOnly, { time }));
    if (state.currents && config.ocean) parts.push(fmt(L.fluxOcean, { from: config.ocean.period[0], to: config.ocean.period[1] }));
    if (api.satelliteShown() && config.base) parts.push(fmt(L.fluxBase, { epoch: L.fluxEpoch2004 }));
    return parts.join(' · ');
  }

  function showLegend(past) {
    const blocks = [];
    if (past && state.currents && layers.ocean.field) {
      blocks.push(legendBlock(fmt(L.oceanLegendPast, { run: past.run_ma }), OCEAN, OCEAN.ref));
    }
    if (state.present && state.wind) {
      blocks.push(legendBlock(fmt(state.wind === '10m' ? L.windLegend10m : L.windLegend250hPa, { time: momentUtc() }),
        WIND, WIND.ref[state.wind]));
    }
    if (state.present && state.currents && config.ocean) {
      blocks.push(legendBlock(fmt(L.oceanLegend, { from: config.ocean.period[0], to: config.ocean.period[1] }), OCEAN, OCEAN.ref));
    }
    if (state.present && state.clouds) {
      blocks.push(`<figcaption>${fmt(state.clouds === 'sat' ? L.cloudLegendSat : L.cloudLegendModel, { time: momentUtc() })}</figcaption>`);
    }
    const speeds = (state.present && (state.wind || state.currents)) || (past && state.currents);
    legend.innerHTML = (speeds ? `<p class="flux-unit">${L.fluxSpeed}</p>` : '') + blocks.join('');
    legend.hidden = !blocks.length;
    const dock = $('map-legend') || stage.parentElement;
    if (legend.parentElement !== dock) {
      const head = dock.querySelector('.legend-head');
      if (head) head.after(legend); else dock.prepend(legend);
    }
  }

  async function sync() {
    // The present's own layers come only from the present-day bundle.
    const on = state.present && Boolean(present);
    const past = on ? null : state.past;
    for (const control of [windSelect, cloudSelect]) {
      if (!control) continue;
      control.disabled = !on;
      control.title = on ? '' : L.fluxPresentOnly;
    }
    if (currentToggle) {
      const ocean = Boolean((on && config.ocean) || past);
      currentToggle.disabled = !ocean;
      currentToggle.title = ocean ? '' : L.currentsUnavailable;
    }
    currentToggle?.setAttribute('aria-pressed', String(state.currents));
    // Wind
    const wind = on && state.wind && config.weather ? config.weather.wind[state.wind] : null;
    layers.wind.field = null;
    if (wind) {
      try {
        layers.wind.field = await loadField(`wind:${state.wind}`, wind.url, wind, false);
        layers.wind.ref = WIND.ref[state.wind];
      } catch (error) { console.error(error); }
    }
    // Currents
    layers.ocean.field = null;
    if (on && state.currents && config.ocean) {
      try {
        layers.ocean.field = await loadField('ocean', config.ocean.url, config.ocean, true);
        layers.ocean.ref = OCEAN.ref;
      } catch (error) { console.error(error); }
    } else if (past && state.currents) {
      // Same speed scale as the present, so a weak model current looks weak beside it.
      try {
        const base = await loadField(`ocean:${past.url}`, past.url, past, true);
        if (past.shift && (warp.key !== past.key || warp.base !== base)) {
          warp = { key: past.key, base, field: warpField(base, past.shift) };
        }
        layers.ocean.field = past.shift ? warp.field : base;
        layers.ocean.ref = OCEAN.ref;
      } catch (error) { console.error(error); }
    }
    for (const layer of Object.values(layers)) {
      const shown = Boolean(layer.field);
      if (!shown) layer.particles.length = 0;
      layer.canvas.hidden = !shown;
      layer.key = '';
    }
    // Clouds
    const cloudUrl = on && state.clouds && config.weather ? config.weather.clouds[state.clouds] : null;
    if (cloudUrl) {
      try {
        cloudUniforms.cloudMap.value = await api.loadTexture(`cloud:${state.clouds}`, cloudUrl);
      } catch (error) {
        console.error(error);
        cloudUniforms.cloudMap.value = null;
      }
    }
    cloudMesh.visible = Boolean(cloudUrl && cloudUniforms.cloudMap.value);
    stage.dataset.flux = on ? 'ready' : past ? 'past' : 'unavailable';
    stage.dataset.currentsRun = past && layers.ocean.field ? String(past.run_ma) : '';
    stage.dataset.currentsWarp = past && layers.ocean.field && past.shift ? past.key : '';
    stage.dataset.wind = layers.wind.field ? state.wind : '';
    stage.dataset.currents = String(Boolean(layers.ocean.field));
    stage.dataset.clouds = cloudMesh.visible ? state.clouds : '';
    showLegend(past);
    const text = on ? describe() : past ? describe(past) : '';
    if (when) {
      when.textContent = text;
      when.hidden = !text;
    }
    stage.dataset.fluxWhen = text;
    if ($('flux-note')) $('flux-note').hidden = !(on && (state.wind || state.currents || state.clouds || api.satelliteShown()));
    if ($('foam-note')) $('foam-note').hidden = !(past && state.currents && layers.ocean.field);
    api.changed();
  }

  windSelect?.addEventListener('change', () => { state.wind = windSelect.value || null; sync(); });
  currentToggle?.addEventListener('click', () => { state.currents = !state.currents; sync(); });
  cloudSelect?.addEventListener('change', () => { state.clouds = cloudSelect.value || null; sync(); });

  return {
    // Called from selectStop with whether the stop is the present itself, then refresh().
    setPresent(present) {
      state.present = present;
    },
    // The drawn stop's past currents, or null: { url, u, v, run_ma, key, shift }, where
    // `shift` moves the field with the map between two stops (null on a stop).
    setPast(past) {
      state.past = past;
    },
    refresh: sync,
    state: () => ({ wind: state.wind, currents: state.currents, clouds: state.clouds }),
    restore({ wind, currents, clouds }) {
      if (wind && config.weather?.wind[wind]) state.wind = wind;
      if (currents && (config.ocean || api.pastCurrents)) state.currents = true;
      if (clouds && config.weather?.clouds[clouds]) state.clouds = clouds;
      if (windSelect) windSelect.value = state.wind || '';
      if (cloudSelect) cloudSelect.value = state.clouds || '';
    },
    // Each animation frame, after the camera has settled.
    frame(viewKey) {
      if (cloudMesh.geometry !== api.surfaceMesh.geometry) cloudMesh.geometry = api.surfaceMesh.geometry;
      const active = Object.values(layers).filter((layer) => layer.field);
      if (!active.length) return;
      const box = stage.getBoundingClientRect();
      const width = Math.round(box.width), height = Math.round(box.height);
      const dpr = Math.min(devicePixelRatio || 1, 2);
      for (const layer of active) {
        if (layer.canvas.width !== Math.round(width * dpr) || layer.canvas.height !== Math.round(height * dpr)) {
          layer.canvas.width = Math.round(width * dpr);
          layer.canvas.height = Math.round(height * dpr);
          layer.key = '';
        }
      }
      if (++fluxTime % 15 === 1 || active.some((layer) => layer.key !== viewKey)) measure(box);
      for (const layer of active) step(layer, width, height, box, viewKey, dpr);
    },
  };
}
