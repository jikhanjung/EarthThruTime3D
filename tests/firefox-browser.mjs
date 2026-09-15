// The globe in desktop Firefox, driven through WebDriver BiDi rather than Playwright (whose
// bundled Firefox is not always installable). The binary named by FIREFOX_BIN (default the
// macOS app) runs headless with a throwaway profile, so no X display is needed. Checks: the
// globe reaches a frame with rivers on, the sea at -60 m brackets the ice-river slices when
// they are built, the deglacial window at 20 ka shows that slice and ice age, and no console
// error or failed request occurred. Screenshots go to gitignored test-results/.
//   VIEWER_URL=http://127.0.0.1:8153/ node tests/firefox-browser.mjs
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdirSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const base = process.env.VIEWER_URL || 'http://127.0.0.1:8153/';
const binary = process.env.FIREFOX_BIN || '/Applications/Firefox.app/Contents/MacOS/firefox';
const port = Number(process.env.FIREFOX_PORT || 9333);
const profile = mkdtempSync(join(tmpdir(), 'firefox-browser-'));
const firefox = spawn(binary, ['--headless', '--no-remote', '--profile', profile,
  '--remote-debugging-port', String(port), '--remote-allow-origins', `ws://127.0.0.1:${port}`,
  '--window-size=1280,900', 'about:blank'], {stdio: ['ignore', 'pipe', 'pipe']});
let said = '';
firefox.stdout.on('data', chunk => {said += chunk;});
firefox.stderr.on('data', chunk => {said += chunk;});
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

let socket = null;
for (let attempt = 0; attempt < 60 && !socket; attempt++) {
  await sleep(500);
  socket = await new Promise(resolve => {
    const candidate = new WebSocket(`ws://127.0.0.1:${port}/session`);
    candidate.onopen = () => resolve(candidate);
    candidate.onerror = () => resolve(null);
  });
}
if (!socket) {
  firefox.kill();
  rmSync(profile, {recursive: true, force: true});
  throw new Error(`Firefox did not open port ${port}: ${said.slice(0, 500)}`);
}

let counter = 0;
const pending = new Map();
const events = [];
socket.onmessage = message => {
  const data = JSON.parse(message.data);
  if (data.id && pending.has(data.id)) {pending.get(data.id)(data); pending.delete(data.id);}
  else if (data.method) events.push(data);
};
const send = (method, params = {}) => new Promise(resolve => {
  const id = ++counter;
  pending.set(id, resolve);
  socket.send(JSON.stringify({id, method, params}));
});
const evaluate = async (context, expression) => {
  const reply = await send('script.evaluate', {expression, target: {context}, awaitPromise: true, resultOwnership: 'none'});
  if (reply.result?.type === 'exception') throw new Error(reply.result.exceptionDetails?.text || 'page script failed');
  return reply.result?.result?.value;
};
const stage = async context => JSON.parse(await evaluate(context,
  `JSON.stringify({...document.getElementById('globe').dataset, busy: document.getElementById('globe').getAttribute('aria-busy')})`));
const until = async (context, what, ready, seconds = 30) => {
  for (let waited = 0; waited < seconds * 2; waited++) {
    const state = await stage(context);
    if (ready(state)) return state;
    await sleep(500);
  }
  throw new Error(`${what} did not happen within ${seconds} s`);
};
const shown = state => state.frame && state.frame !== 'none' && state.busy === 'false';
const screenshot = async (context, name) => {
  const shot = await send('browsingContext.captureScreenshot', {context});
  mkdirSync('test-results', {recursive: true});
  writeFileSync(join('test-results', name), Buffer.from(shot.result.data, 'base64'));
};

try {
  const session = await send('session.new', {capabilities: {}});
  console.log('Firefox', session.result.capabilities.browserVersion);
  await send('session.subscribe', {events: ['log.entryAdded', 'network.responseCompleted', 'network.fetchError']});
  const context = (await send('browsingContext.getTree')).result.contexts[0].context;

  await send('browsingContext.navigate', {context, url: new URL('/?masks=paleodem2018', base).href, wait: 'complete'});
  const loaded = await until(context, 'the globe', shown);
  assert.equal(loaded.rivers, 'true', 'rivers are on by default');
  const frames = JSON.parse(await evaluate(context, `document.getElementById('globe-frames').textContent`));
  const slices = frames.find(frame => frame.id === loaded.frame)?.rivers_ice?.length || 0;

  await evaluate(context, `(() => {const slider = document.getElementById('sealevel'); slider.value = '-60'; slider.dispatchEvent(new Event('input', {bubbles: true}));})()`);
  const lowered = await until(context, 'the -60 m lowstand', state => state.busy === 'false'
    && (slices ? state.riverIce !== '' : Number(state.riverLow) > 0));
  if (slices) assert.ok(Number(lowered.riverIce) > 0, `ice-river bracket at -60 m: ${lowered.riverIce}`);
  await screenshot(context, 'firefox-lowstand.png');

  await send('browsingContext.navigate', {context, url: new URL('/?masks=paleodem2018&window=deglacial', base).href, wait: 'complete'});
  await until(context, 'the deglacial window', shown);
  await evaluate(context, `(() => {const frames = JSON.parse(document.getElementById('globe-frames').textContent);
    const era = document.getElementById('era'); era.value = String(frames.findIndex(frame => frame.deglacial?.age_ka === 20));
    era.dispatchEvent(new Event('change', {bubbles: true}));})()`);
  const glacial = await until(context, '20 ka', state => state.iceAge === '20' && state.busy === 'false');
  if (slices) assert.equal(glacial.riverIce, '20.0', 'the 20 ka ice-river slice');
  await screenshot(context, 'firefox-deglacial-20ka.png');

  const errors = events.filter(event => event.method === 'log.entryAdded' && event.params.level === 'error')
    .map(event => `${event.params.type}: ${event.params.text}`);
  const failed = events.filter(event => event.method === 'network.responseCompleted' && event.params.response.status >= 400)
    .map(event => `${event.params.response.status} ${event.params.response.url}`)
    // A request the page abandons when it moves on (NS_BINDING_ABORTED) is not a failure.
    .concat(events.filter(event => event.method === 'network.fetchError' && !/ABORT/.test(event.params.errorText))
      .map(event => `${event.params.errorText} ${event.params.request.url}`));
  assert.deepEqual(errors, [], 'console errors');
  assert.deepEqual(failed, [], 'failed requests');
  console.log(`-60 m: river-low ${lowered.riverLow}, river-ice ${lowered.riverIce || '(no slices)'}; 20 ka: river-ice ${glacial.riverIce || '(no slices)'}, ice-age ${glacial.iceAge}`);
  console.log(`Firefox: globe, rivers, -60 m${slices ? ' ice bracket' : ' lowstand'}, deglacial 20 ka, console and network passed`);
} finally {
  socket.close();
  firefox.kill();  // this process only, never other Firefox windows
  rmSync(profile, {recursive: true, force: true});
}
