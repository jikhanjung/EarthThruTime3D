import { chromium, expect as baseExpect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
// setDefaultTimeout covers actions; an assertion keeps Playwright's own 5 s unless it is
// configured too, and a first draw that is merely slow then fails on a loaded machine.
const expect = baseExpect.configure({timeout: 20000});
// BROWSER_CHANNEL=chrome runs on the installed Google Chrome when the bundled Chromium is absent.
const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL, args: ['--enable-unsafe-swiftshader']});
const errors = [];
// The long-standing checks below are written against the 2002 web-map masks, whose
// names and frame ids they know; the 2016 atlas, now the default, gets its own pass.
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8000/';
const legacy = new URL('?masks=scotese2002', base).href;
try {
  const page = await browser.newPage({locale: 'ko-KR', viewport: {width:1440, height:1100}});
  page.setDefaultTimeout(20000);
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(legacy);
  const globe = page.locator('#globe');
  await expect(globe).toHaveAttribute('data-frame', 'scotese-000');
  // Only the essentials sit in the toolbar, which fits without scrolling; the rest opens
  // from the menu, which Escape closes and this browser remembers.
  expect(await page.locator('.globe-toolbar').evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
  await expect(page.locator('#settings-menu')).toBeHidden();
  await expect(page.locator('#settings-menu #grid')).toHaveCount(1);
  await page.locator('#settings-toggle').click();
  await expect(page.locator('#settings-menu')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#settings-menu')).toBeHidden();
  await page.locator('#settings-toggle').click();
  await expect(page.locator('#settings-toggle')).toHaveAttribute('aria-expanded', 'true');
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
  // Zoom goes close enough to read a coastline, and the view still turns there.
  await globe.focus();
  for (let press = 0; press < 30; press++) await page.keyboard.press('+');
  await expect.poll(async () => Number(await globe.getAttribute('data-zoom'))).toBeLessThan(0.05);
  // Exercise close-up keyboard movement, but do not require different pixels over
  // a featureless ocean. The full-globe screenshot above checks visible rotation.
  for (let press = 0; press < 5; press++) await page.keyboard.press('ArrowLeft');
  await page.screenshot({path:'data/screenshots/globe-zoomed.png'});
  await page.locator('#reset').click();
  // The grid starts on; the button turns it off and on again.
  await expect(page.locator('#grid')).toHaveAttribute('aria-pressed','true');
  await page.locator('#grid').click();
  await expect(page.locator('#grid')).toHaveAttribute('aria-pressed','false');
  await page.locator('#grid').click();
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
  // The blend was already 0.50 at the previous stop, so wait on the frame, which changes.
  await expect(globe).toHaveAttribute('data-frame', 'scotese-050');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  expect(Number(await globe.getAttribute('data-motions'))).toBeGreaterThan(0);
  await page.locator('#timeline').fill('98');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-motions', '0');
  await page.locator('#timeline').fill('104');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('data-blend', '0.50');
  // The map is the page, and the notes about the derived surface and the interpolated
  // stop must not resize it: the inspector floats over it, scrolls inside, and stops
  // above the control panel.
  expect(panelBefore.height).toBeGreaterThan(900);
  const panelWithNotes = await page.locator('.globe-panel').boundingBox();
  expect(panelWithNotes.height).toBe(panelBefore.height);
  expect(panelWithNotes.width).toBe(panelBefore.width);
  const inspectorBox = await page.locator('.inspector').boundingBox();
  const controlsBox = await page.locator('.controls').boundingBox();
  expect(inspectorBox.y + inspectorBox.height).toBeLessThanOrEqual(controlsBox.y);
  expect(controlsBox.y + controlsBox.height).toBeLessThanOrEqual(panelBefore.y + panelBefore.height);
  // The inspector folds away and comes back without touching the map.
  await page.locator('#info-toggle').click();
  await expect(page.locator('.inspector')).toBeHidden();
  await expect(page.locator('#info-toggle')).toHaveAttribute('aria-expanded', 'false');
  expect((await page.locator('.globe-panel').boundingBox()).width).toBe(panelBefore.width);
  await page.locator('#info-toggle').click();
  await expect(page.locator('.inspector')).toBeVisible();
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
  // Equal Earth is a second equal-area sheet, taller than the 2:1 box and with a pole
  // line: the names still land and the picture differs from Mollweide's.
  const onMollweide = await page.locator('#globe canvas').screenshot();
  await page.locator('#projection').selectOption('equalearth');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-names', '7');
  const onEqualEarth = await page.locator('#globe canvas').screenshot();
  expect(Buffer.compare(onMollweide, onEqualEarth)).not.toBe(0);
  await page.screenshot({path:'data/screenshots/globe-equalearth.png',fullPage:true});
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
  // A phone is all map: the panel fills the screen under the header, the control panel
  // floats at its foot inside the screen, and the inspector folds out of the way.
  const phone = async (selector) => page.locator(selector).boundingBox();
  const panel = await phone('.globe-panel');
  const controlsPanel = await phone('.controls');
  expect(panel.height).toBeGreaterThan(700);
  expect(controlsPanel.y).toBeGreaterThan(panel.y + panel.height / 2);
  expect(controlsPanel.y + controlsPanel.height).toBeLessThanOrEqual(844);
  expect(controlsPanel.x + controlsPanel.width).toBeLessThanOrEqual(390);
  if (await page.locator('#info-toggle').getAttribute('aria-expanded') === 'true') {
    await page.locator('#info-toggle').click();
  }
  await expect(page.locator('.inspector')).toBeHidden();
  // The controls stay on one row; a second row would cover the sphere.
  expect((await phone('.globe-toolbar')).height).toBeLessThan(52);
  expect(await page.locator('.globe-toolbar').evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
  // Sideways on the same phone the slider must still be reachable without scrolling.
  await page.setViewportSize({width:844,height:390});
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  const short = await phone('.timeline');
  expect(short.y + short.height).toBeLessThanOrEqual(390);
  // There the open menu takes the toolbar's row inside the panel rather than covering the sphere.
  await expect(page.locator('#settings-menu')).toBeVisible();
  const shortMenu = await phone('#settings-menu');
  const shortControls = await phone('.controls');
  expect(shortMenu.y).toBeGreaterThanOrEqual(shortControls.y);
  expect(shortMenu.y + shortMenu.height).toBeLessThanOrEqual(shortControls.y + shortControls.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'data/screenshots/globe-landscape.png',fullPage:true});
  console.log('Phone layout passed');
  await page.setViewportSize({width:390,height:844});
  // Force a missing source in a fresh page and verify retry restores the globe.
  const broken = await browser.newPage({locale: 'ko-KR'});
  broken.setDefaultTimeout(20000);
  await broken.route('**/globe/maps/scotese-000.jpg', route => route.fulfill({status:404}));
  await broken.goto(legacy);
  await expect(broken.locator('#retry')).toBeVisible();
  await broken.unroute('**/globe/maps/scotese-000.jpg');
  await broken.locator('#retry').click();
  await expect(broken.locator('#globe')).toHaveAttribute('data-frame','scotese-000');
  // The default page shows the 2016 atlas: 90 maps, no originals, no names yet, and a
  // way back to the 2002 masks for comparison.
  const atlas = await browser.newPage({locale: 'ko-KR', viewport: {width:1440, height:1100}});
  atlas.setDefaultTimeout(20000);
  atlas.on('pageerror', error => errors.push(error.message));
  await atlas.goto(base);
  await atlas.locator('#settings-toggle').click();
  const atlasGlobe = atlas.locator('#globe');
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-000');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  const atlasFrames = await atlas.locator('#globe-frames').textContent().then(JSON.parse);
  const frameIndex = (id) => String(atlasFrames.findIndex(frame => frame.id === id));
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
  // An in-between stop names the period at its own age rather than "A → B", and the
  // present reads as 0 Ma.
  const halfway = (await atlas.locator('#globe-stops').textContent().then(JSON.parse))
    .findIndex(([from, , blend, age]) => from >= 0 && blend > 0.4 && blend < 0.6 && age > 251.902 && age < 259.51);
  await atlas.locator('#timeline').fill(String(halfway));
  await atlas.locator('#timeline').dispatchEvent('input');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await expect(atlas.locator('#period')).toHaveText('후기 페름기');
  await atlas.locator('#era').selectOption(String(atlasFrames.length - 1));
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-000');
  await expect(atlas.locator('#age')).toHaveText('0 Ma');
  await expect(atlas.locator('#period')).toHaveText('현재');
  // The header is one line: brand and a small title, no menu link or tag.
  await expect(atlas.locator('header nav:not(.lang)')).toHaveCount(0);
  await expect(atlas.locator('.tag')).toHaveCount(0);
  expect((await atlas.locator('header').boundingBox()).height).toBeLessThan(80);
  // KO|EN in the header: English swaps every label, the continent names included, and
  // comes back to the same address.
  await expect(atlas.locator('.lang a[aria-current="true"]')).toHaveText('KO');
  await atlas.locator('.lang a[hreflang="en"]').click();
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-000');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  await expect(atlas.locator('html')).toHaveAttribute('lang', 'en');
  await expect(atlas.locator('.lang a[aria-current="true"]')).toHaveText('EN');
  await expect(atlas.locator('#period')).toHaveText('Present');
  await expect(atlas.locator('#play')).toContainText('Play');
  const englishFrames = await atlas.locator('#globe-frames').textContent().then(JSON.parse);
  expect(englishFrames[englishFrames.length - 1].names.map(n => n.name)).toContain('Africa');
  expect(await atlas.locator('body').textContent()).not.toMatch(/[가-힣]/);
  await atlas.locator('#era').selectOption(frameIndex('paleoatlas-750'));
  await expect(atlas.locator('#period')).toHaveText('Tonian');
  await atlas.screenshot({path:'data/screenshots/globe-english.png', fullPage:true});
  await atlas.locator('.lang a[hreflang="ko"]').click();
  await expect(atlas.locator('html')).toHaveAttribute('lang', 'ko');
  await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false');
  console.log('Language switch passed');
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
  // The address carries the stop and the view, so the reload comes back at 255 Ma.
  await atlas.reload();
  await expect(atlasGlobe).toHaveAttribute('data-frame', 'paleoatlas-255');
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
  // The panel's dataset picker opens the elevation series at the same age and spacing.
  if (await atlas.locator('#dataset option[value="paleodem2018"]').count()) {
    await atlas.locator('#dataset').selectOption('paleodem2018');
    await atlas.waitForURL(/masks=paleodem2018/);
    await expect(atlasGlobe).toHaveAttribute('aria-busy', 'false', {timeout: 15000});
    await expect(atlas.locator('#dataset')).toHaveValue('paleodem2018');
    await expect(atlas.locator('#age')).toContainText('254');
    expect(new URL(atlas.url()).searchParams.get('interval')).toBe('1');
    console.log('Dataset picker passed');
  }
  console.log('2016 atlas default passed');
  // The elevation series, where this checkout has built it: relief at 0 Ma with the
  // present-day ice, the surface and layer controls where they now live, the fossil
  // coastlines over the grids, the atlas prelude as a mask, a deep stop, and the English
  // page with nothing left in Korean. A checkout without the textures is sent back to
  // the atlas, and the pass is skipped rather than failed.
  // Earlier pages keep their render loops running; close them so the software renderer
  // gives the elevation pass its whole budget.
  await Promise.all([page.close(), broken.close(), atlas.close()]);
  const dem = await browser.newPage({locale: 'ko-KR', viewport: {width:1280, height:1000}});
  dem.setDefaultTimeout(20000);
  dem.on('pageerror', error => errors.push(error.message));
  await dem.goto(new URL('?masks=paleodem2018', base).href);
  // The elevation series has the most controls, and its toolbar still fits.
  expect(await dem.locator('.globe-toolbar').evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
  await dem.locator('#settings-toggle').click();
  const demGlobe = dem.locator('#globe');
  const demFrames = await dem.locator('#globe-frames').textContent().then(JSON.parse);
  if (!demFrames.some(frame => frame.relief)) {
    console.log('Elevation series not built here; skipped');
  } else {
    // The map now fills the window, so the software renderer draws a larger canvas and
    // the first texture of a fresh page can outlast the default wait.
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-0000', {timeout: 15000});
    await expect(demGlobe).toHaveAttribute('data-surface', 'relief');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    await expect(demGlobe).toHaveAttribute('data-ice', 'true');
    expect(demFrames.length).toBe(112);
    // Names and motion are borrowed from the atlas where computed: at a stop halfway
    // between two grids the morph carries landmasses, and the names ride the relief.
    if (demFrames.every(frame => frame.names.length)) {
      const demStops = await dem.locator('#globe-stops').textContent().then(JSON.parse);
      const halfway = demStops.findIndex(([from, , blend]) => demFrames[from]?.id === 'paleodem-0600' && blend === 0.5);
      expect(halfway).toBeGreaterThan(0);
      await dem.locator('#timeline').fill(String(halfway));
      await dem.locator('#timeline').dispatchEvent('input');
      await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-0600');
      await expect(demGlobe).toHaveAttribute('data-blend', '0.50');
      await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
      expect(Number(await demGlobe.getAttribute('data-motions'))).toBeGreaterThan(0);
      await expect(demGlobe).toHaveAttribute('data-surface', 'relief');
      // The coastline of the gap's older end rides the same motion field as the surface.
      await dem.locator('#coastline').check();
      await expect.poll(async () => await demGlobe.getAttribute('data-coastline-carried')).toBe('true');
      await expect(dem.locator('#coastline-age')).toContainText('옮겨');
      await dem.locator('#coastline').uncheck();
      await dem.screenshot({path:'data/screenshots/globe-elevation-halfway.png', fullPage:false});
      await dem.locator('#era').selectOption(String(demFrames.length - 1));
      await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-0000');
      console.log('Elevation names and motion passed');
    }
    // Settings of the surface sit in the inspector; the toolbar keeps the view controls.
    await expect(dem.locator('.globe-toolbar #shading')).toHaveCount(0);
    await expect(dem.locator('.inspector #shading')).toHaveCount(1);
    await expect(dem.locator('.inspector #sealevel')).toHaveCount(1);
    await dem.locator('#shading').selectOption('5');
    await expect(demGlobe).toHaveAttribute('data-shading', '5');
    await dem.locator('#sealevel').fill('-120');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '-120');
    await expect(dem.locator('#sealevel-value')).toHaveText('−120 m');
    await expect(dem.locator('#sea-note')).toBeVisible();
    await dem.locator('#sealevel').fill('0');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '0');
    // The long-term curve is an overlay opened from the toolbar, above the control panel.
    await expect(dem.locator('#sea-overlay')).toBeHidden();
    await dem.locator('#sea-chart').click();
    await expect(dem.locator('#sea-chart')).toHaveAttribute('aria-pressed', 'true');
    await expect(dem.locator('#sea-overlay')).toBeVisible();
    const seaBox = await dem.locator('#sea-overlay').boundingBox();
    const demControls = await dem.locator('.controls').boundingBox();
    expect(seaBox.y + seaBox.height).toBeLessThanOrEqual(demControls.y);
    await dem.screenshot({path:'data/screenshots/globe-elevation-sea-curve.png'});
    // With the menu open too, the curve stacks above it rather than under it.
    const menuBox = await dem.locator('#settings-menu').boundingBox();
    expect(seaBox.y + seaBox.height).toBeLessThanOrEqual(menuBox.y + 1);
    // On a laptop-width window the curve and the open inspector do not overlap.
    await dem.setViewportSize({width: 1000, height: 800});
    if (await dem.locator('#info-toggle').getAttribute('aria-expanded') !== 'true') await dem.locator('#info-toggle').click();
    const seaNarrow = await dem.locator('#sea-overlay').boundingBox();
    const inspectorNarrow = await dem.locator('.inspector').boundingBox();
    expect(seaNarrow.x + seaNarrow.width).toBeLessThanOrEqual(inspectorNarrow.x);
    await dem.setViewportSize({width: 1280, height: 1000});
    await dem.locator('#sea-chart').click();
    await expect(dem.locator('#sea-overlay')).toBeHidden();
    // The curve departure is a box on top of the slider; at a grid stop it adds nothing.
    await dem.locator('#sealevel-curve').check();
    await expect(demGlobe).toHaveAttribute('data-sealevel', '0');
    await dem.locator('#sealevel-curve').uncheck();
    // Close in, the elevation series stands up in 3D and the view tilts; the toolbar
    // button lays it flat again, and zooming back out does too.
    await expect(demGlobe).toHaveAttribute('data-relief', '0.00');
    await demGlobe.focus();
    for (let press = 0; press < 12; press++) await dem.keyboard.press('+');
    await expect.poll(async () => Number(await demGlobe.getAttribute('data-relief'))).toBeGreaterThan(0.9);
    await expect(dem.locator('#relief-note')).toBeVisible();
    await dem.screenshot({path:'data/screenshots/globe-elevation-3d.png'});
    // While the terrain stands, a middle drag tilts and turns the view; reset puts it back.
    await expect(demGlobe).toHaveAttribute('data-tilt', '50');
    const demCanvas = await dem.locator('#globe canvas').boundingBox();
    await dem.mouse.move(demCanvas.x + demCanvas.width / 2, demCanvas.y + demCanvas.height / 2);
    await dem.mouse.down({button: 'middle'});
    await dem.mouse.move(demCanvas.x + demCanvas.width / 2 + 60, demCanvas.y + demCanvas.height / 2 - 40, {steps: 6});
    await dem.mouse.up({button: 'middle'});
    expect(Number(await demGlobe.getAttribute('data-tilt'))).toBeGreaterThan(55);
    expect(Number(await demGlobe.getAttribute('data-heading'))).toBeGreaterThan(5);
    // Two fingers moved up together tilt it further on a touch screen.
    const tiltBefore = Number(await demGlobe.getAttribute('data-tilt'));
    const cdp = await dem.context().newCDPSession(dem);
    await cdp.send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 2});
    const cx = demCanvas.x + demCanvas.width / 2;
    const cy = demCanvas.y + demCanvas.height / 2;
    const fingers = (dy) => [{x: cx - 60, y: cy + dy, id: 0}, {x: cx + 60, y: cy + dy, id: 1}];
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: fingers(0)});
    for (let step = 1; step <= 8; step++) {
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: fingers(-8 * step)});
    }
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
    await cdp.send('Emulation.setTouchEmulationEnabled', {enabled: false});
    expect(Number(await demGlobe.getAttribute('data-tilt'))).toBeGreaterThan(tiltBefore + 5);
    await dem.screenshot({path:'data/screenshots/globe-elevation-3d-tilted.png'});
    await dem.locator('#reset').click();
    await expect(demGlobe).toHaveAttribute('data-tilt', '50');
    await expect(demGlobe).toHaveAttribute('data-heading', '0');
    await demGlobe.focus();
    for (let press = 0; press < 12; press++) await dem.keyboard.press('+');
    await expect.poll(async () => Number(await demGlobe.getAttribute('data-relief'))).toBeGreaterThan(0.9);
    // Lines drawn on the surface ride the lifted ground: the boundaries still draw there.
    await dem.locator('#plate-overlay').selectOption('paleomap2016');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    expect(Number(await demGlobe.getAttribute('data-plates'))).toBeGreaterThan(0);
    await dem.screenshot({path:'data/screenshots/globe-elevation-3d-plates.png'});
    await dem.locator('#plate-overlay').selectOption('');
    await dem.locator('#relief3d').click();
    await expect(dem.locator('#relief3d')).toHaveAttribute('aria-pressed', 'false');
    await expect(demGlobe).toHaveAttribute('data-relief', '0.00');
    await expect(dem.locator('#relief-note')).toBeHidden();
    await dem.locator('#relief3d').click();
    await expect.poll(async () => Number(await demGlobe.getAttribute('data-relief'))).toBeGreaterThan(0.9);
    await dem.locator('#reset').click();
    await expect(demGlobe).toHaveAttribute('data-relief', '0.00');
    await dem.locator('#temperature').click();
    await expect(demGlobe).toHaveAttribute('data-surface', 'temp');
    // The colour key shows with the temperature surface, with the stop's distance from
    // today's mean filled in; the present stop is 0.0 from itself.
    await expect(dem.locator('#temp-legend')).toBeVisible();
    await expect(dem.locator('#temp-legend')).toHaveAttribute('data-delta', /^-?\d+\.\d$/);
    await dem.locator('#temperature').click();
    await expect(demGlobe).toHaveAttribute('data-surface', 'relief');
    await expect(dem.locator('#temp-legend')).toBeHidden();
    await dem.locator('#surface').click();
    await expect(demGlobe).toHaveAttribute('data-surface', 'mask');
    await dem.locator('#surface').click();
    await expect(demGlobe).toHaveAttribute('data-surface', 'relief');
    await dem.locator('#ice').click();
    await expect(demGlobe).toHaveAttribute('data-ice', 'false');
    await dem.locator('#ice').click();
    // Rivers are routed over every grid of the series, so the present has them; the
    // toggle hides the lines and shows them again without a reload.
    await expect(demGlobe).toHaveAttribute('data-rivers', 'true');
    await expect(dem.locator('#river-note')).toBeVisible();
    await dem.locator('#rivers').click();
    await expect(demGlobe).toHaveAttribute('data-rivers', 'false');
    await expect(dem.locator('#river-note')).toBeHidden();
    await dem.locator('#rivers').click();
    await expect(demGlobe).toHaveAttribute('data-rivers', 'true');
    // Lowering the sea mixes in the field routed at the slider's lowest level, fully at
    // the bottom of the range; back at the datum none of it shows.
    await expect(demGlobe).toHaveAttribute('data-river-low', '0.00');
    await dem.locator('#sealevel').fill('-130');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-river-low', '1.00');
    await dem.locator('#sealevel').fill('-60');
    await dem.locator('#sealevel').dispatchEvent('input');
    // With the fields routed over the ice built, the present brackets −60 m between the two
    // steps around it and names the age; without them it is the share of the −130 m field.
    const presentFrame = (await dem.locator('#globe-frames').textContent().then(JSON.parse)).find(frame => frame.age === 0);
    const iceSlices = presentFrame.rivers_ice || [];
    if (iceSlices.length) {
      const index = iceSlices.findIndex(slice => slice.level_m <= -60);
      const upper = index ? iceSlices[index - 1] : {level_m: 0};
      const share = (-60 - upper.level_m) / (iceSlices[index].level_m - upper.level_m);
      await expect(demGlobe).toHaveAttribute('data-river-low', share.toFixed(2));
      await expect(demGlobe).not.toHaveAttribute('data-river-ice', '');
    } else {
      await expect(demGlobe).toHaveAttribute('data-river-low', '0.46');
      await expect(demGlobe).toHaveAttribute('data-river-ice', '');
    }
    await dem.locator('#sealevel').fill('0');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-river-low', '0.00');
    await expect(demGlobe).toHaveAttribute('data-river-ice', '');
    // Past ice: the 300 Ma grid carries the sheet the atlas paints there, the 200 Ma grid none.
    await dem.locator('#era').selectOption(String(demFrames.findIndex(frame => frame.id === 'paleodem-3000')));
    // A freshly built texture's first load can take longer than the default wait.
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-3000', {timeout: 15000});
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    await expect(demGlobe).toHaveAttribute('data-ice', 'true');
    await expect(demGlobe).toHaveAttribute('data-ice-kind', 'drawn');
    await expect(dem.locator('#ice-note')).toBeVisible();
    await expect(dem.locator('#ice-limit-note')).toBeHidden();
    // The slider's range is the ice this stop has: half the late Palaeozoic apex swing
    // below, the whole volume melted above. A lower sea cuts the field below its edge; the
    // top of the range cuts it above everything; the readout says how much ice that is.
    await expect(demGlobe).toHaveAttribute('data-ice-cut', '0.500');
    await expect(dem.locator('#sealevel')).toHaveAttribute('min', '-50');
    await expect(dem.locator('#sealevel')).toHaveAttribute('max', '80');
    await expect(dem.locator('#sealevel-notes')).toContainText('−50 m');
    await dem.locator('#sealevel').fill('-50');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '-50');
    expect(Number(await demGlobe.getAttribute('data-ice-cut'))).toBeLessThan(0.5);
    await expect(dem.locator('#sea-level')).toContainText('km³');
    await dem.locator('#sealevel').fill('80');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '80');
    expect(Number(await demGlobe.getAttribute('data-ice-cut'))).toBeGreaterThan(1);
    await dem.locator('#sealevel').fill('0');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '0');
    // Where the atlas paints nothing but the paper's ice volume is above the strip's cut,
    // a cap at the modelled limit, flagged as such.
    await dem.locator('#era').selectOption(String(demFrames.findIndex(frame => frame.id === 'paleodem-1400')));
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-1400');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    await expect(demGlobe).toHaveAttribute('data-ice-kind', 'limit');
    await expect(dem.locator('#ice-limit-note')).toBeVisible();
    await dem.locator('#era').selectOption(String(demFrames.findIndex(frame => frame.id === 'paleodem-2000')));
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-2000');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    await expect(demGlobe).toHaveAttribute('data-ice', 'false');
    // No ice here, so the slider has no range and rests.
    await expect(dem.locator('#sealevel')).toBeDisabled();
    await dem.locator('#era').selectOption(String(demFrames.length - 1));
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleodem-0000');
    // The present has dated lowstand slices, the last deglaciation: at -130 m the page
    // shows the 24 ka slice, and the slider marks both ends of the ice.
    await expect(dem.locator('#sealevel-notes')).toContainText('−130 m');
    await expect(dem.locator('#sealevel')).toHaveAttribute('min', '-130');
    await expect(dem.locator('#sealevel')).toHaveAttribute('max', '60');
    await dem.locator('#sealevel').fill('-130');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-sealevel', '-130');
    await expect(demGlobe).toHaveAttribute('data-ice-low', '24.0');
    await dem.locator('#sealevel').fill('0');
    await dem.locator('#sealevel').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-ice-low', '');
    // The fossil coastlines are offered over the grids as over the atlas.
    await dem.locator('#coastline').check();
    await expect.poll(async () => Number(await demGlobe.getAttribute('data-coastlines'))).toBeGreaterThan(0);
    await dem.locator('#coastline').uncheck();
    // Before 540 Ma the series is the atlas masks; before 750 Ma nothing but a model.
    await dem.locator('#era').selectOption(String(demFrames.findIndex(frame => frame.id === 'paleoatlas-600')));
    await expect(demGlobe).toHaveAttribute('data-frame', 'paleoatlas-600');
    await expect(demGlobe).toHaveAttribute('data-surface', 'mask');
    await expect(dem.locator('#period')).toHaveText('에디아카라기');
    await dem.locator('#timeline').fill('0');
    await dem.locator('#timeline').dispatchEvent('input');
    await expect(demGlobe).toHaveAttribute('data-mapless', 'true');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    await dem.locator('.lang a[hreflang="en"]').click();
    await expect(dem.locator('html')).toHaveAttribute('lang', 'en');
    await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
    expect(await dem.locator('body').textContent()).not.toMatch(/[가-힣]/);
    await dem.screenshot({path:'data/screenshots/globe-elevation-english.png', fullPage:true});
    console.log('Elevation series passed');
    // The time window: the last 25,000 years a thousand years at a stop, each age with its
    // dated ice slice and the stack's sea level, the slider locked to it.
    await dem.goto(new URL('?masks=paleodem2018&window=deglacial', base).href);
    const windowFrames = await dem.locator('#globe-frames').textContent().then(JSON.parse);
    if (!windowFrames[0].deglacial) {
      console.log('Deglacial slices not built here; time window skipped');
    } else {
      await expect(demGlobe).toHaveAttribute('aria-busy', 'false', {timeout: 15000});
      expect(windowFrames.length).toBe(26);
      await expect(dem.locator('#window')).toHaveValue('deglacial');
      await expect(dem.locator('#sampling')).toHaveCount(0);
      await expect(dem.locator('#timeline')).toHaveAttribute('max', '25');
      await expect(demGlobe).toHaveAttribute('data-ice-age', '0');
      await expect(demGlobe).toHaveAttribute('data-sealevel', '0');
      await expect(dem.locator('#sealevel')).toBeDisabled();
      await dem.locator('#era').selectOption(String(windowFrames.findIndex(frame => frame.deglacial.age_ka === 21)));
      await expect(demGlobe).toHaveAttribute('data-ice-age', '21');
      await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
      expect(Number(await demGlobe.getAttribute('data-sealevel'))).toBeLessThan(-100);
      await expect(dem.locator('#sealevel')).toBeDisabled();
      await expect(dem.locator('#age')).toContainText('21,000');
      await dem.screenshot({path:'data/screenshots/globe-deglacial-21ka.png'});
      // Back to the whole series: the stops return and the slider moves again.
      await dem.locator('#window').selectOption('');
      await dem.waitForURL((url) => !url.searchParams.has('window'));
      await expect(demGlobe).toHaveAttribute('aria-busy', 'false', {timeout: 15000});
      await expect(dem.locator('#sampling')).toHaveCount(1);
      await expect(dem.locator('#sealevel')).toBeEnabled();
      console.log('Time window passed');
      // The last glacial cycle: dated slices to 25 ka, PaleoMIST's modelled ice to 80 ka
      // where built, and before them the retreat's shape at the stack's own level, named as
      // assumed ice.
      await dem.goto(new URL('?masks=paleodem2018&window=lastcycle', base).href);
      await expect(demGlobe).toHaveAttribute('aria-busy', 'false', {timeout: 15000});
      const cycleFrames = await dem.locator('#globe-frames').textContent().then(JSON.parse);
      expect(cycleFrames.length).toBe(131);
      await expect(dem.locator('#timeline')).toHaveAttribute('max', '130');
      const at = async (ka) => {
        await dem.locator('#era').selectOption(String(cycleFrames.findIndex(frame => frame.deglacial.age_ka === ka)));
        await expect(demGlobe).toHaveAttribute('data-ice-age', String(ka));
        await expect(demGlobe).toHaveAttribute('aria-busy', 'false');
      };
      await at(21);
      await expect(demGlobe).toHaveAttribute('data-ice-kind', 'drawn');
      await expect(dem.locator('#ice-analogue-note')).toBeHidden();
      await dem.locator('#projection').selectOption('equirect');
      await dem.screenshot({path:'data/screenshots/globe-cycle-21ka.png'});
      const modelled = cycleFrames.some(frame => frame.ice_kind === 'reconstructed');
      await at(40);
      if (modelled) {
        // Modelled ice at the stack's level, the rivers the 40 ka field, and the strip
        // carrying PaleoMIST's own curve beside the stack's.
        await expect(demGlobe).toHaveAttribute('data-ice-kind', 'reconstructed');
        await expect(dem.locator('#ice-model-note')).toBeVisible();
        await expect(dem.locator('#ice-analogue-note')).toBeHidden();
        await expect(demGlobe).toHaveAttribute('data-ice-low', '');
        await expect(demGlobe).toHaveAttribute('data-river-ice', '40.0');
        await expect(dem.locator('#sea-strip .sea-model')).toHaveCount(1);
        await dem.screenshot({path:'data/screenshots/globe-cycle-40ka.png'});
      } else {
        await expect(demGlobe).toHaveAttribute('data-ice-kind', 'analogue');
      }
      await expect(demGlobe).toHaveAttribute('data-sealevel', String(Math.round(cycleFrames.find(frame => frame.deglacial.age_ka === 40).deglacial.level_m)));
      await expect(dem.locator('#sealevel')).toBeDisabled();
      await at(100);
      await expect(demGlobe).toHaveAttribute('data-ice-kind', 'analogue');
      await expect(dem.locator('#ice-analogue-note')).toBeVisible();
      if (modelled) await expect(dem.locator('#ice-model-note')).toBeHidden();
      await expect(demGlobe).not.toHaveAttribute('data-ice-low', '');
      await expect(demGlobe).toHaveAttribute('data-sealevel', String(Math.round(cycleFrames.find(frame => frame.deglacial.age_ka === 100).deglacial.level_m)));
      await at(121);
      await expect(demGlobe).toHaveAttribute('data-ice-low', '');
      await dem.screenshot({path:'data/screenshots/globe-cycle-121ka.png'});
      await dem.locator('#projection').selectOption('globe');
      console.log('Last glacial cycle passed');
    }
  }
  expect(errors).toEqual([]);
  console.log('Rotation, zoom, playback, rapid switching, mobile layout and failed-load recovery passed');
} finally { await browser.close(); }
