import { chromium, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const errors = [];
// The long-standing checks below are written against the 2002 web-map masks, whose
// names and frame ids they know; the 2016 atlas, now the default, gets its own pass.
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8000/';
const legacy = new URL('?masks=scotese2002', base).href;
try {
  const page = await browser.newPage({viewport: {width:1440, height:1100}});
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(legacy);
  const globe = page.locator('#globe');
  await expect(globe).toHaveAttribute('data-frame', 'scotese-000');
  await mkdir('data/screenshots', {recursive:true});
  await page.screenshot({path:'data/screenshots/globe-desktop.png',fullPage:true});
  const frames = await page.locator('#globe-frames').textContent().then(JSON.parse);
  for (let index = 0; index < frames.length; index++) {
    await page.locator('#era').selectOption(String(index));
    await expect(globe).toHaveAttribute('data-frame', frames[index].id);
    await expect(globe).toHaveAttribute('aria-busy', 'false');
  }
  console.log(`All ${frames.length} 2002 frames rendered`);
  const before = await page.locator('#globe canvas').screenshot();
  await globe.focus();
  await page.keyboard.press('ArrowRight');
  const after = await page.locator('#globe canvas').screenshot();
  expect(Buffer.compare(before,after)).not.toBe(0);
  const canvas = await page.locator('#globe canvas').boundingBox();
  await page.mouse.move(canvas.x + canvas.width/2, canvas.y + canvas.height/2);
  await page.mouse.down();
  await page.mouse.move(canvas.x + canvas.width/2 + 130, canvas.y + canvas.height/2 + 25, {steps:8});
  await page.mouse.up();
  await page.mouse.wheel(0,-150);
  await page.locator('#grid').click();
  await expect(page.locator('#grid')).toHaveAttribute('aria-pressed','true');
  await page.locator('#rotate').click();
  await expect(page.locator('#rotate')).toHaveAttribute('aria-pressed','true');
  await page.locator('#rotate').click();
  await page.locator('#play').click();
  await expect(globe).toHaveAttribute('data-frame', 'scotese-650');
  await expect(globe).toHaveAttribute('data-frame', 'scotese-514', {timeout:8000});
  await page.locator('#era').selectOption('13');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(globe).toHaveAttribute('data-frame','scotese-050');
  // Dispatch rapid changes in one browser task: the latest selection must win.
  await page.evaluate(() => {
    const select = document.querySelector('#era');
    for (const value of ['2','6','15','16']) {select.value=value;select.dispatchEvent(new Event('change'));}
  });
  await expect(globe).toHaveAttribute('data-frame','scotese-000');
  // Derived surface: the mask globe must differ from the source-map globe, keep
  // working across frames, and leave the source preview untouched.
  await page.locator('#era').selectOption('16');
  await expect(globe).toHaveAttribute('data-frame','scotese-000');
  const sourceGlobe = await page.locator('#globe canvas').screenshot();
  const panelBefore = await page.locator('.globe-panel').boundingBox();
  await page.locator('#surface').click();
  await expect(page.locator('#surface')).toHaveAttribute('aria-pressed','true');
  await expect(globe).toHaveAttribute('aria-busy','false');
  await expect(page.locator('#surface-note')).toBeVisible();
  const maskGlobe = await page.locator('#globe canvas').screenshot();
  const panelMasked = await page.locator('.globe-panel').boundingBox();
  expect(panelMasked.height).toBe(panelBefore.height);
  expect(Buffer.compare(sourceGlobe,maskGlobe)).not.toBe(0);
  expect(await page.locator('#source-preview').getAttribute('src')).toContain('/globe/maps/');
  // Names are drawn on the sphere, so assert on the count the viewer reports.
  await expect(globe).toHaveAttribute('data-names', '7');
  // Sub-steps: each interpolated stop must render a different sphere, and the page
  // must say it is interpolated rather than observed.
  const stops = [];
  for (const value of [102, 103, 104, 105, 106]) {
    await page.locator('#timeline').fill(String(value));
    await page.locator('#timeline').dispatchEvent('input');
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    stops.push(await page.locator('#globe canvas').screenshot());
  }
  for (let index = 1; index < stops.length; index++) {
    expect(Buffer.compare(stops[index - 1], stops[index])).not.toBe(0);
  }
  await page.locator('#timeline').fill('104');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  await expect(page.locator('#between-note')).toBeVisible();
  // A stop inside a gap with matched landmasses carries them; a stop on a source map
  // has nothing to carry.
  await page.locator('#timeline').fill('100');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  expect(Number(await globe.getAttribute('data-motions'))).toBeGreaterThan(0);
  await page.locator('#timeline').fill('98');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-motions', '0');
  await page.locator('#timeline').fill('104');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  // The notes about the derived surface and the interpolated stop must not resize the
  // globe: the inspector scrolls instead of growing the row.
  const panelWithNotes = await page.locator('.globe-panel').boundingBox();
  expect(panelWithNotes.height).toBe(panelBefore.height);
  expect(panelWithNotes.width).toBe(panelBefore.width);
  expect(await page.locator('.inspector').evaluate((node) =>
    node.scrollHeight > node.clientHeight)).toBe(true);
  expect(await page.locator('#globe-age').textContent()).toContain('보간');
  await page.locator('#timeline').fill('106');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.00');
  await expect(page.locator('#between-note')).toBeHidden();
  // Both ends of the map range land on a source map, never on an interpolated stop.
  for (const [value, id] of [['46', 'scotese-650'], ['110', 'scotese-000']]) {
    await page.locator('#timeline').fill(value);
    await page.locator('#timeline').dispatchEvent('input');
    await expect(globe).toHaveAttribute('data-frame', id);
    await expect(globe).toHaveAttribute('data-blend', '0.00');
  }
  expect(await page.locator('#timeline').getAttribute('max')).toBe('110');
  // Older than any map: bare ocean, no surface claim, no stale preview, and the model
  // says whether it reaches that far.
  await page.locator('#timeline').fill('0');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-mapless', 'true');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#mapless-note')).toBeVisible();
  await expect(page.locator('#source-figure')).toBeHidden();
  expect(await page.locator('#globe-age').textContent()).toContain('지도 없음');
  await page.locator('#timeline').fill('46');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-mapless', 'false');
  await expect(page.locator('#mapless-note')).toBeHidden();
  console.log('Deep-time stops passed');
  console.log('Interpolated sub-steps passed');
  const painted = await page.evaluate(() => {
    const canvas = document.querySelector('#globe canvas');
    const context = canvas.getContext('webgl2') || canvas.getContext('webgl');
    return Boolean(context);
  });
  expect(painted).toBe(true);
  await page.screenshot({path:'data/screenshots/globe-mask.png',fullPage:true});
  // Projections: each draws a different picture of the same stop, the flat ones have
  // nothing to spin, and the globe gets its rotation back.
  const drawn = new Map();
  for (const name of ['globe', 'mollweide', 'equirect']) {
    await page.locator('#projection').selectOption(name);
    await expect(globe).toHaveAttribute('data-projection', name);
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    // Every projection can turn: the globe orbits, a sheet shifts its centre meridian.
    await expect(page.locator('#rotate')).toBeEnabled();
    drawn.set(name, await page.locator('#globe canvas').screenshot());
  }
  const pictures = [...drawn.values()];
  for (let first = 0; first < pictures.length; first++) {
    for (let second = first + 1; second < pictures.length; second++) {
      expect(Buffer.compare(pictures[first], pictures[second])).not.toBe(0);
    }
  }
  await page.locator('#projection').selectOption('mollweide');
  await page.locator('#era').selectOption('16');
  await expect(globe).toHaveAttribute('data-frame', 'scotese-000');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-names', '7');
  await page.screenshot({path:'data/screenshots/globe-mollweide.png',fullPage:true});
  await page.locator('#projection').selectOption('globe');
  await expect(page.locator('#rotate')).toBeEnabled();
  // The plate model is a second dataset drawn over the first. It must reconstruct at
  // the stop's own age, say whose data it is, and leave when switched off.
  const beforePlates = await page.locator('#globe canvas').screenshot();
  // The overlay is chosen from a dropdown whose default is the Scotese surface alone,
  // and a line in the inspector points at it until a model is picked.
  expect(await page.locator('#plate-overlay').inputValue()).toBe('');
  await expect(page.locator('#plate-hint')).toBeVisible();
  await page.locator('#plate-overlay').selectOption('merdith2021');
  await expect(page.locator('#plate-hint')).toBeHidden();
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#plate-note')).toBeVisible();
  expect(await page.locator('#plate-note').textContent()).toContain('Merdith');
  const withPlates = await page.locator('#globe canvas').screenshot();
  expect(Buffer.compare(beforePlates, withPlates)).not.toBe(0);
  const atPresent = Number(await globe.getAttribute('data-plates'));
  expect(atPresent).toBeGreaterThan(500);
  await page.locator('#era').selectOption('0');
  await expect(globe).toHaveAttribute('data-frame', 'scotese-650');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  // Fewer blocks exist at 650 Ma than today, so the count has to fall.
  expect(Number(await globe.getAttribute('data-plates'))).toBeLessThan(atPresent);
  await page.locator('#era').selectOption('8');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  // Two models, same shapes, different absolute reference frame: switching has to
  // redraw and to re-credit.
  await expect(globe).toHaveAttribute('data-plate-model', 'merdith2021');
  const firstFrame = await page.locator('#globe canvas').screenshot();
  await page.locator('#plate-overlay').selectOption('muller2022');
  await expect(globe).toHaveAttribute('data-plate-model', 'muller2022');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  const secondFrame = await page.locator('#globe canvas').screenshot();
  expect(Buffer.compare(firstFrame, secondFrame)).not.toBe(0);
  expect(await page.locator('#plate-cite').textContent()).toContain('Müller');
  await page.locator('#plate-overlay').selectOption('merdith2021');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  expect(await page.locator('#plate-cite').textContent()).toContain('Merdith');
  // Every model states how it relates to the others, because two of the three nearly
  // coincide inside this timeline and a reader should not have to discover that.
  await page.locator('#plate-overlay').selectOption('cao2024');
  await expect(globe).toHaveAttribute('data-plate-model', 'cao2024');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  expect(await page.locator('#plate-note-model').textContent()).toContain('1 Ga');
  await page.locator('#plate-overlay').selectOption('merdith2021');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await page.locator('#era').selectOption('16');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  // Every model the page declares, plus the option of none. The count varies with the
  // deployment: a model whose licence forbids publication is listed only where a key
  // exists to unlock it.
  const declaredModels = await page.locator('#globe-plates').textContent().then(JSON.parse);
  expect(await page.locator('#plate-overlay option').count()).toBe(declaredModels.length + 1);
  expect(declaredModels.length).toBeGreaterThanOrEqual(4);
  // A model whose licence forbids publication is listed but locked, and unlocking
  // happens in place so the reader keeps the age and the view they had.
  const restricted = declaredModels.find((model) => model.locked);
  if (restricted && process.env.VIEWER_KEY) {
    await page.locator('#plate-overlay').selectOption(restricted.id);
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    await expect(page.locator('#plate-unlock')).toBeVisible();
    await expect(globe).toHaveAttribute('data-plates', '0');
    await page.fill('#plate-key', 'not-the-key');
    await page.click('#plate-unlock button');
    await expect(page.locator('#unlock-wrong')).toBeVisible();
    await page.fill('#plate-key', process.env.VIEWER_KEY);
    await page.click('#plate-unlock button');
    await expect(page.locator('#plate-unlock')).toBeHidden();
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    expect(Number(await globe.getAttribute('data-plates'))).toBeGreaterThan(0);
    console.log('Locked-model unlock passed');
  }
  await page.locator('#plate-overlay').selectOption('');
  await expect(globe).toHaveAttribute('data-plates', '0');
  await expect(page.locator('#plate-note')).toBeHidden();
  await expect(page.locator('#plate-hint')).toBeVisible();
  console.log('Plate reconstruction overlay passed');
  await page.locator('#era').selectOption('8');
  await expect(globe).toHaveAttribute('data-frame','scotese-237');
  await expect(globe).toHaveAttribute('aria-busy','false');
  await expect(globe).toHaveAttribute('data-names', '2');
  await page.locator('#surface').click();
  await expect(globe).toHaveAttribute('data-names', '0');
  await expect(page.locator('#surface')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#surface-note')).toBeHidden();
  await expect(globe).toHaveAttribute('aria-busy','false');
  console.log('Land-mask surface toggle passed');
  await page.locator('#era').selectOption('16');
  await expect(globe).toHaveAttribute('data-frame','scotese-000');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#reset').click();
  await page.screenshot({path:'data/screenshots/globe-mobile.png',fullPage:true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  // A phone leads with the instrument: the globe and the slider share the first screen
  // and the inspector follows them rather than sitting between them.
  const phone = async (selector) => page.locator(selector).boundingBox();
  const panel = await phone('.globe-panel');
  const timeline = await phone('.timeline');
  const inspector = await phone('.inspector');
  expect(timeline.y).toBeGreaterThan(panel.y);
  expect(inspector.y).toBeGreaterThan(timeline.y);
  expect(timeline.y + timeline.height).toBeLessThanOrEqual(844);
  expect(panel.height).toBeGreaterThan(300);
  // The controls stay on one row; a second row would cover the sphere.
  expect((await phone('.globe-toolbar')).height).toBeLessThan(52);
  // Sideways on the same phone the slider must still be reachable without scrolling.
  await page.setViewportSize({width:844,height:390});
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  const short = await phone('.timeline');
  expect(short.y + short.height).toBeLessThanOrEqual(390);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'data/screenshots/globe-landscape.png',fullPage:true});
  console.log('Phone layout passed');
  await page.setViewportSize({width:390,height:844});
  // Force a missing source in a fresh page and verify retry restores the globe.
  const broken = await browser.newPage();
  await broken.route('**/globe/maps/scotese-000.jpg', route => route.fulfill({status:404}));
  await broken.goto(legacy);
  await expect(broken.locator('#retry')).toBeVisible();
  await broken.unroute('**/globe/maps/scotese-000.jpg');
  await broken.locator('#retry').click();
  await expect(broken.locator('#globe')).toHaveAttribute('data-frame','scotese-000');
  // The default page shows the 2016 atlas: 90 maps, no originals, no names yet, and a
  // way back to the 2002 masks for comparison.
  const atlas = await browser.newPage({viewport: {width:1440, height:1100}});
  atlas.on('pageerror', error => errors.push(error.message));
  await atlas.goto(base);
  const atlasGlobe = atlas.locator('#globe');
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-000');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  const atlasFrames = await atlas.locator('#globe-frames').textContent().then(JSON.parse);
  expect(atlasFrames.length).toBe(90);
  expect(atlasFrames.every(frame => frame.url === null && frame.field)).toBe(true);
  await expect(atlas.locator('#surface')).toHaveCount(0);
  await expect(atlas.locator('#source-preview')).toHaveCount(0);
  await expect(atlas.locator('#frame-number')).toHaveText('90 / 90');
  await expect(atlas.locator('#timeline-oldest')).toContainText('Ma');
  for (const id of ['paleoatlas-255', 'paleoatlas-510', 'paleoatlas-750']) {
    await atlas.locator('#era').selectOption(String(atlasFrames.findIndex(frame => frame.id === id)));
    await expect(atlasGlobe).toHaveAttribute('data-frame', id);
    await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  }
  await expect(atlas.locator('#period')).toHaveText('토니아기');
  // Names come from the plate groups under each piece, and an in-between stop carries
  // control points computed from the PALEOMAP rotations.
  await atlas.locator('#era').selectOption(String(atlasFrames.findIndex(frame => frame.id === 'paleoatlas-255')));
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(Number(await atlasGlobe.getAttribute('data-names'))).toBeGreaterThan(3);
  const atlasStops = await atlas.locator('#globe-stops').textContent().then(JSON.parse);
  const between = atlasStops.findIndex(([from, , blend]) => from >= 0 && blend > 0.4 && blend < 0.6);
  await atlas.locator('#timeline').fill(String(between));
  await atlas.locator('#timeline').dispatchEvent('input');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(Number(await atlasGlobe.getAttribute('data-motions'))).toBeGreaterThan(0);
  await expect(atlas.locator('#between-note')).toContainText('PALEOMAP');
  // Fossil-checked coastlines: drawn at the reader's age, and said to be missing where
  // the dataset stops (535 Ma), rather than borrowed from the nearest distant age.
  const frameIndex = (id) => String(atlasFrames.findIndex(frame => frame.id === id));
  await atlas.locator('#era').selectOption(frameIndex('paleoatlas-255'));
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await atlas.locator('#coastline').check();
  await expect(atlasGlobe).toHaveAttribute('data-coastline-age', '255');
  expect(Number(await atlasGlobe.getAttribute('data-coastlines'))).toBeGreaterThan(0);
  await expect(atlas.locator('#coastline-note')).toBeVisible();
  await atlas.locator('#era').selectOption(frameIndex('paleoatlas-750'));
  await expect(atlasGlobe).toHaveAttribute('data-coastlines', '0');
  await expect(atlas.locator('#coastline-age')).toContainText('535');
  await atlas.locator('#era').selectOption(frameIndex('paleoatlas-255'));
  await expect(atlasGlobe).toHaveAttribute('data-coastline-age', '255');
  await atlas.locator('#projection').selectOption('mollweide');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await atlas.locator('#globe canvas').screenshot({path:'data/screenshots/globe-atlas-coastlines-255.png'});
  await atlas.locator('#coastline').uncheck();
  await expect(atlasGlobe).toHaveAttribute('data-coastlines', '0');
  await expect(atlas.locator('#coastline-note')).toBeHidden();
  console.log('Fossil coastline layer passed');
  await atlas.screenshot({path:'data/screenshots/globe-atlas-750.png', fullPage:true});
  await expect(atlas.locator('a[href="?masks=scotese2002"]')).toHaveCount(1);
  // The overlay dropdown starts at "경계선 없음" whatever the browser remembers, and any
  // model draws its boundaries over the mask rather than instead of it.
  await expect(atlas.locator('#plate-overlay option[value=""]')).toHaveText('경계선 없음');
  await atlas.locator('#plate-overlay').selectOption('paleomap2016');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(Number(await atlasGlobe.getAttribute('data-plates'))).toBeGreaterThan(0);
  await atlas.reload();
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-000');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(await atlas.locator('#plate-overlay').inputValue()).toBe('');
  await expect(atlasGlobe).toHaveAttribute('data-plates', '0');
  for (const model of ['paleomap2016', 'merdith2021']) {
    await atlas.locator('#plate-overlay').selectOption(model);
    await expect(atlasGlobe).toHaveAttribute('data-plate-model', model);
    await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
    expect(Number(await atlasGlobe.getAttribute('data-plates'))).toBeGreaterThan(0);
    await expect(atlas.locator('#globe-age')).toContainText('대륙 마스크');
  }
  await atlas.locator('#plate-overlay').selectOption('');
  await expect(atlasGlobe).toHaveAttribute('data-plates', '0');
  // A flat sheet turns about the pole: a drag or the arrow keys move the centre meridian,
  // and the grid and the boundaries turn with the map.
  await atlas.locator('#projection').selectOption('mollweide');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await expect(atlasGlobe).toHaveAttribute('data-meridian', '0.0');
  await atlas.locator('#plate-overlay').selectOption('paleomap2016');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await atlas.locator('#grid').click();
  await atlas.waitForTimeout(200);
  const unturned = await atlas.locator('#globe canvas').screenshot();
  const sheet = await atlas.locator('#globe canvas').boundingBox();
  await atlas.mouse.move(sheet.x + sheet.width / 2, sheet.y + sheet.height / 2);
  await atlas.mouse.down();
  await atlas.mouse.move(sheet.x + sheet.width / 2 + 160, sheet.y + sheet.height / 2, {steps: 8});
  await atlas.mouse.up();
  const turned = Number(await atlasGlobe.getAttribute('data-meridian'));
  expect(Math.abs(turned)).toBeGreaterThan(5);
  await atlas.waitForTimeout(200);
  expect(Buffer.compare(unturned, await atlas.locator('#globe canvas').screenshot())).not.toBe(0);
  expect(Number(await atlasGlobe.getAttribute('data-plates'))).toBeGreaterThan(0);
  await atlasGlobe.focus();
  await atlas.keyboard.press('ArrowRight');
  expect(Number(await atlasGlobe.getAttribute('data-meridian'))).toBeCloseTo((((turned + 10) % 360) + 540) % 360 - 180, 1);
  await atlas.screenshot({path:'data/screenshots/globe-mollweide-turned.png', fullPage:true});
  await atlas.locator('#reset').click();
  await expect(atlasGlobe).toHaveAttribute('data-meridian', '0.0');
  await atlas.locator('#grid').click();
  await atlas.locator('#plate-overlay').selectOption('');
  await atlas.locator('#projection').selectOption('globe');
  console.log('Turning a flat sheet passed');
  // A 1 Myr spacing is chosen beside the slider; the page comes back at the same age and
  // each step moves one million years.
  await atlas.locator('#era').selectOption(frameIndex('paleoatlas-255'));
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-255');
  await Promise.all([atlas.waitForURL(/interval=1/), atlas.locator('#sampling').selectOption('interval:1')]);
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-255');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(await atlas.locator('#sampling').inputValue()).toBe('interval:1');
  const perMyr = await atlas.locator('#globe-stops').textContent().then(JSON.parse);
  const at = Number(await atlas.locator('#timeline').inputValue());
  expect(perMyr[at][3]).toBe(255);
  await atlas.locator('#timeline').fill(String(at + 1));
  await atlas.locator('#timeline').dispatchEvent('input');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  expect(perMyr[at + 1][3]).toBe(254);
  await expect(atlas.locator('#age')).toContainText('254');
  console.log('One million year spacing passed');
  console.log('2016 atlas default passed');
  expect(errors).toEqual([]);
  console.log('Rotation, zoom, playback, rapid switching, mobile layout and failed-load recovery passed');
} finally { await browser.close(); }
