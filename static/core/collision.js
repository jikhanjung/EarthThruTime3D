import { crustState } from './collision-math.js';
import { createSurface } from './collision-surface.js';
const $ = id => document.getElementById(id);
const strings = JSON.parse($('collision-strings').textContent);
const slider = $('collision-time');
let data, timer, request;
const query=new URL(location.href).searchParams;
const linked=query.get('linked')==='1'&&window.parent!==window;
let desiredAge=[80,60,40,20,0].includes(Number(query.get('age')))&&query.has('age')?Number(query.get('age')):80;
let waiting=false, linkedError=false;
$('collision-linked-note').hidden=!linked;
let terrain;
try { terrain = createSurface($('collision-surface'), $('surface-ve'), $('surface-reset')); }
catch { $('surface-status').textContent = strings.surfaceError; }
if(linked)terrain?.setSectionVisible(false);

function canvas(id, height) {
  const element = $(id), width = element.clientWidth;
  const ratio = Math.min(devicePixelRatio || 1, 2);
  element.width = Math.round(width * ratio); element.height = Math.round(height * ratio);
  element.style.height = `${height}px`;
  const ctx = element.getContext('2d');
  ctx.scale(ratio, ratio);
  ctx.font = '12px system-ui'; ctx.fillStyle = '#c8dce4'; ctx.lineWidth = 1;
  return {ctx, width, height};
}
function line(ctx, x1, y1, x2, y2, color, weight = 1) {
  ctx.strokeStyle = color; ctx.lineWidth = weight;
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
}
function segments(ctx, values, x, y, color, weight) {
  ctx.strokeStyle = color; ctx.lineWidth = weight; ctx.beginPath();
  for (const [x1, y1, x2, y2] of values) { ctx.moveTo(x(x1), y(y1)); ctx.lineTo(x(x2), y(y2)); }
  ctx.stroke();
}
function map(frame) {
  if (!$('collision-overview').open) return;
  const {ctx, width, height} = canvas('collision-map', 320);
  const x = lon => 44 + (lon - 40) / 75 * (width - 62);
  const y = lat => 28 + (60 - lat) / 100 * (height - 60);
  for (const lat of [-40, -20, 0, 20, 40, 60]) {
    line(ctx, x(40), y(lat), x(115), y(lat), '#243e49');
    ctx.fillText(`${lat}°`, 3, y(lat) + 4);
  }
  for (const lon of [50, 70, 85, 100]) {
    line(ctx, x(lon), y(-40), x(lon), y(60), '#243e49');
    ctx.fillText(`${lon}°E`, x(lon) - 15, height - 12);
  }
  if ($('collision-continents').checked) {
    segments(ctx, frame.map.cratons, x, y, '#e8c984', 1.3);
    segments(ctx, frame.map.boundaries, x, y, '#afc2c9', .7);
  }
  line(ctx, x(data.longitude), y(-40), x(data.longitude), y(60), '#f18fae', 2);
  ctx.fillStyle = '#ffb9cf'; ctx.fillText('A′', x(data.longitude)+5, y(60)+13);
  ctx.fillText('A', x(data.longitude)+5, y(-40)-5);
  // Present-day geographic reference only; the outlines themselves move with age.
  ctx.fillStyle = '#c8dce4'; ctx.fillText(`${frame.age_ma} Ma · OPT1`, 48, 17);
}
function section(frame) {
  const flow = $('collision-flow').checked;
  const requestedVE = Number($('section-ve').value);
  const neededHeight = 32 + ($('collision-section').clientWidth-75)/(100*Math.PI/180*6371)*2900*requestedVE + (flow ? 105 : 45);
  const {ctx, width, height} = canvas('collision-section', neededHeight);
  const bottom = height - (flow ? 105 : 45);
  const x = lat => 53 + (lat + 40) / 100 * (width - 75);
  const y = depth => 32 + depth/2900 * (bottom - 32);
  for (const depth of [0, 1000, 2000, 2900]) {
    line(ctx, x(-40), y(depth), x(60), y(depth), '#243e49');
    ctx.fillText(`${depth}`, 3, y(depth)+4);
  }
  for (const lat of [-40, -20, 0, 20, 40, 60]) {
    line(ctx, x(lat), y(0), x(lat), y(2900), '#243e49');
    ctx.fillText(`${lat}°`, x(lat)-12, bottom+18);
  }
  ctx.fillText(`${strings.depth} (km)`, 5, 14);
  ctx.fillText('A', x(-40), 26); ctx.fillText('A′', x(60)-12, 26);
  if ($('collision-mantle').checked) {
    segments(ctx, frame.section.slabs, x, y, '#69b5ea', 1.3);
    segments(ctx, frame.section.piles, x, y, '#f5a051', 1.3);
  }
  const exaggeration = ((bottom-32)/2900) / ((width-75)/(100*Math.PI/180*6371));
  ctx.fillText(`${strings.exaggeration} ×${exaggeration.toFixed(1)}`, 55, bottom+36);
  if (flow) {
    // A separate strip prevents arrows from being read as a measured vector field.
    ctx.fillStyle = '#152f37'; ctx.fillRect(0, height-62, width, 62);
    ctx.fillStyle = '#d9baeb'; ctx.fillText(strings.flow, 10, height-45);
    for (let i = 0; i < 3; i++) {
      const cx = (i+.5)*width/3, cy = height-21, rx = width/9;
      ctx.strokeStyle = '#c4a2dc'; ctx.beginPath(); ctx.ellipse(cx, cy, rx, 10, 0, 0, 2*Math.PI); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx+7, cy-10); ctx.lineTo(cx-2, cy-15); ctx.lineTo(cx-2, cy-5); ctx.closePath(); ctx.fill();
    }
  }
}
function crust(frame) {
  $('crust-panel').hidden = !$('collision-crust').checked;
  if ($('crust-panel').hidden) return;
  const shortening = Number($('collision-shortening').value);
  $('shortening-value').textContent = `${shortening} km`;
  const state = crustState(frame.age_ma, Number($('collision-onset').value), shortening);
  const neededHeight = 75 + ($('collision-crust-view').clientWidth-70)/2000*120*Number($('crust-ve').value);
  const {ctx, width, height} = canvas('collision-crust-view', neededHeight);
  const x = distance => 50 + distance/2000*(width-70);
  const y = depth => 35 + (depth+15)/120*(height-75);
  for (const depth of [0, 35, 70, 100]) {
    line(ctx, x(0), y(depth), x(2000), y(depth), '#28434b');
    ctx.fillText(`${depth}`, 5, y(depth)+4);
  }
  for (const distance of [0, 1000, 2000]) ctx.fillText(`${distance} km`, Math.min(x(distance), width-61), height-12);
  ctx.fillStyle = '#e2bb75';
  ctx.fillRect(x(state.shortening), y(-state.uplift), x(2000)-x(state.shortening), y(state.thickness-state.uplift)-y(-state.uplift));
  // Material grid: the same columns shorten, with area conserved per unit strike length.
  for (let i=0; i<=10; i++) {
    const position = state.shortening + state.width*i/10;
    line(ctx, x(position), y(-state.uplift), x(position), y(state.thickness-state.uplift), '#71562e');
  }
  ctx.setLineDash([5, 4]);
  ctx.strokeStyle = '#adc2c9'; ctx.strokeRect(x(0), y(0), x(2000)-x(0), y(35)-y(0));
  ctx.setLineDash([]);
  ctx.fillStyle = '#c8dce4';
  ctx.fillText(`${strings.south} → ${strings.north} · ${strings.distance} (km)`, 50, 17);
  const exaggeration = ((height-75)/120)/((width-70)/2000);
  ctx.fillText(`${strings.exaggeration} ×${exaggeration.toFixed(1)}`, 50, 33);
  $('crust-values').textContent = `${strings.shortening}: ${state.shortening.toFixed(0)} km · ${strings.thickness}: ${state.thickness.toFixed(1)} km · ${strings.uplift}: ${state.uplift.toFixed(1)} km`;
  $('crust-panel').dataset.thickness = state.thickness.toFixed(1);
}
function draw() {
  if (!data || waiting) return;
  const frame = data.frames[Number(slider.value)];
  $('collision-age').textContent = `${frame.age_ma} Ma`;
  slider.setAttribute('aria-valuetext', `${frame.age_ma} Ma`);
  $('collision-status').textContent = `${strings.original} · ${frame.age_ma} Ma`;
  document.body.dataset.age = String(frame.age_ma);
  map(frame); section(frame); crust(frame);
  if (terrain && $('collision-surface').dataset.age !== String(frame.age_ma)) {
    try {
      terrain.update(frame.surface, frame.age_ma);
      $('surface-status').textContent = `PaleoDEM · ${frame.age_ma} Ma · PALEOMAP`;
    } catch { $('surface-status').textContent = strings.surfaceError; }
if(linked)terrain?.setSectionVisible(false);
  }
}
function stop() { clearInterval(timer); timer = null; $('collision-play').textContent = strings.play; }
$('collision-play').addEventListener('click', () => {
  if (timer) { stop(); return; }
  if (Number(slider.value) === 4) { slider.value = '0'; draw(); }
  $('collision-play').textContent = strings.pause;
  timer = setInterval(() => {
    slider.value = String(Math.min(4, Number(slider.value)+1)); draw();
    if (Number(slider.value) === 4) stop();
  }, 1600);
});
slider.addEventListener('input', () => {
  stop();
  if(linked){
    const age=data.frames[Number(slider.value)].age_ma;
    if(String(age)===document.body.dataset.age)return;
    setWaiting(true);window.parent.postMessage({type:'collision-age-change',age},location.origin);
  } else draw();
});
for (const id of ['continents', 'mantle', 'flow', 'crust', 'onset', 'shortening']) {
  $(`collision-${id}`).addEventListener('input', draw);
}
for (const id of ['section-ve', 'crust-ve']) $(id).addEventListener('change', draw);
$('collision-overview').addEventListener('toggle', draw);
const observer = new ResizeObserver(() => draw()); observer.observe(document.querySelector('main'));
async function load() {
  request?.abort(); request = new AbortController();
  $('collision-status').textContent = strings.loading; $('collision-retry').hidden = true;
  try {
    const response = await fetch($('collision-data').dataset.url, {signal: request.signal});
    if (!response.ok) throw new Error(response.status);
    const result = await response.json();
    if (result.schema_version !== 1 || result.frames.length !== 5 || result.frames.some((f, i) => f.age_ma !== 80-i*20)) throw new Error('Invalid section');
    data = result;slider.value=String(data.frames.findIndex(f=>f.age_ma===desiredAge));
    slider.disabled=waiting&&!linkedError;$('collision-play').disabled=linked;draw();
  } catch (error) {
    if (error.name !== 'AbortError') { $('collision-status').textContent = strings.error; $('collision-retry').hidden = false; }
  }
}
function setWaiting(value,error=false) {
  waiting=value;linkedError=error;slider.disabled=(value&&!error)||!data;
  document.querySelector('.plots').hidden=value;
  $('collision-overview').hidden=value;
  $('collision-linked-status').hidden=!value;
  $('collision-linked-status').textContent=error?strings.linkedError:strings.linkedLoading;
  $('collision-retry').hidden=!error;
  if(value){delete document.body.dataset.age;$('collision-age').textContent='…';}
}
window.addEventListener('message',event=>{
  if(!linked||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='collision-link-state')return;
  const state=event.data;if(![80,60,40,20,0].includes(state.age))return;
  stop();desiredAge=state.age;setWaiting(!state.ready,Boolean(state.error));
  if(data&&state.ready){slider.value=String(data.frames.findIndex(f=>f.age_ma===desiredAge));draw();}
});
$('collision-retry').addEventListener('click', () => {
  if(linked&&linkedError&&data) {
    setWaiting(true);
    window.parent.postMessage({type:'collision-age-change',age:desiredAge},location.origin);
  } else load();
});
document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
window.addEventListener('pagehide', () => { stop(); request?.abort(); observer.disconnect(); terrain?.dispose(); });
load();
