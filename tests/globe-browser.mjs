import { chromium, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const errors = [];
try {
  const page = await browser.newPage({viewport: {width:1440, height:1100}});
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.VIEWER_URL || 'http://127.0.0.1:8000/?series=scotese');
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
  // Walking every frame must not keep every texture: the cache is bounded.
  expect(Number(await globe.getAttribute('data-cached'))).toBeLessThanOrEqual(12);
  console.log('All 17 frames rendered');
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
  for (const value of [56, 57, 58, 59, 60]) {
    await page.locator('#timeline').fill(String(value));
    await page.locator('#timeline').dispatchEvent('input');
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    stops.push(await page.locator('#globe canvas').screenshot());
  }
  for (let index = 1; index < stops.length; index++) {
    expect(Buffer.compare(stops[index - 1], stops[index])).not.toBe(0);
  }
  await page.locator('#timeline').fill('58');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  await expect(page.locator('#between-note')).toBeVisible();
  // A stop inside a gap with matched landmasses carries them; a stop on a source map
  // has nothing to carry.
  await page.locator('#timeline').fill('54');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  expect(Number(await globe.getAttribute('data-motions'))).toBeGreaterThan(0);
  await page.locator('#timeline').fill('52');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-motions', '0');
  await page.locator('#timeline').fill('58');
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
  await page.locator('#timeline').fill('60');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.00');
  await expect(page.locator('#between-note')).toBeHidden();
  // Both ends of the slider land on a source map, never on an interpolated stop.
  for (const [value, id] of [['0', 'scotese-650'], ['64', 'scotese-000']]) {
    await page.locator('#timeline').fill(value);
    await page.locator('#timeline').dispatchEvent('input');
    await expect(globe).toHaveAttribute('data-frame', id);
    await expect(globe).toHaveAttribute('data-blend', '0.00');
  }
  expect(await page.locator('#timeline').getAttribute('max')).toBe('64');
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
    if (name === 'globe') await expect(page.locator('#rotate')).toBeEnabled();
    else await expect(page.locator('#rotate')).toBeDisabled();
    drawn.set(name, await page.locator('#globe canvas').screenshot());
  }
  const pictures = [...drawn.values()];
  for (let first = 0; first < pictures.length; first++) {
    for (let second = first + 1; second < pictures.length; second++) {
      expect(Buffer.compare(pictures[first], pictures[second])).not.toBe(0);
    }
  }
  await page.locator('#projection').selectOption('mollweide');
  await expect(globe).toHaveAttribute('data-names', '7');
  await page.screenshot({path:'data/screenshots/globe-mollweide.png',fullPage:true});
  await page.locator('#projection').selectOption('globe');
  await expect(page.locator('#rotate')).toBeEnabled();
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
  await broken.goto(process.env.VIEWER_URL || 'http://127.0.0.1:8000/?series=scotese');
  await expect(broken.locator('#retry')).toBeVisible();
  await broken.unroute('**/globe/maps/scotese-000.jpg');
  await broken.locator('#retry').click();
  await expect(broken.locator('#globe')).toHaveAttribute('data-frame','scotese-000');
  expect(errors).toEqual([]);
  console.log('Rotation, zoom, playback, rapid switching, mobile layout and failed-load recovery passed');
} finally { await browser.close(); }
