// The present-day circulation schematic (wwolf P02 step 5): the conveyor belt on the currents
// select's "conveyor", at the present only, with its legend, the GODAS sections drawn once
// opened, the note, and the address. Needs a server whose bundle has circulation.json
// (scripts/build_circulation.py); the present-day data is not needed.
import {chromium, expect as baseExpect} from '@playwright/test';
const expect = baseExpect.configure({timeout: 30000});

const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8150/';
const origin = new URL(base).origin;
try {
  const page = await browser.newPage({viewport: {width: 1400, height: 900}});
  const errors = [], external = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to fetch|ERR_ABORTED/.test(m.text())) errors.push(m.text()); });
  page.on('request', r => { if (!r.url().startsWith(origin) && !r.url().startsWith('data:')) external.push(r.url()); });
  const globe = page.locator('#globe');
  const legend = page.locator('#circulation-legend');
  const goTo = (pick) => page.evaluate((source) => {
    const stops = JSON.parse(document.getElementById('globe-stops').textContent);
    const slider = document.getElementById('timeline');
    slider.value = String(stops.findIndex(new Function('s', `return ${source}`)));
    slider.dispatchEvent(new Event('input'));
  }, pick);
  const inked = (selector) => page.evaluate((selector) => {
    const canvas = document.querySelector(selector);
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0;
    for (let i = 0; i < data.length; i += 4 * 16) if (data[i] + data[i + 1] + data[i + 2] > 0) count++;
    return count;
  }, selector);

  // The present: nine lines, the legend with its keys, the note; no particles.
  await page.goto(new URL('/?masks=paleodem2018&currents=conveyor', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-circulation', '9');
  await expect(page.locator('#currents')).toHaveValue('conveyor');
  await expect(globe).toHaveAttribute('data-currents', 'false');
  await expect(legend).toBeVisible();
  await expect(legend.locator('li')).toHaveCount(6);
  await expect(page.locator('#circulation-note')).not.toBeHidden();
  // The sections are drawn once opened.
  await legend.locator('summary').click();
  await expect(legend.locator('canvas')).toHaveCount(2);
  expect(await inked('#circulation-legend canvas[data-section="0"]')).toBeGreaterThan(500);
  expect(await inked('#circulation-legend canvas[data-section="1"]')).toBeGreaterThan(500);
  await page.screenshot({path: 'test-results/circulation-globe.png'});

  // A flat map draws the same lines, rebuilt for the projection.
  await page.selectOption('#projection', 'equalearth');
  await expect(globe).toHaveAttribute('data-circulation', '9');
  await page.waitForTimeout(500);
  await page.screenshot({path: 'test-results/circulation-equalearth.png'});
  await expect.poll(() => new URL(page.url()).searchParams.get('currents')).toBe('conveyor');

  // A past stop: the schematic is the present's, so it stands down, and the select keeps the
  // choice for the way back; the past stop's own particles are still there to pick.
  await goTo('s[3] === 100');
  await expect(globe).toHaveAttribute('data-circulation', '');
  await expect(legend).toBeHidden();
  await expect(page.locator('#circulation-note')).toBeHidden();
  await expect(page.locator('#currents option[value="conveyor"]')).toBeDisabled();
  await goTo('s[3] === 0');
  await expect(globe).toHaveAttribute('data-circulation', '9');
  await goTo('s[3] === 100');
  await page.selectOption('#currents', 'flow');
  await expect(globe).toHaveAttribute('data-currents', 'true');
  await expect(globe).toHaveAttribute('data-circulation', '');
  await expect.poll(() => new URL(page.url()).searchParams.get('currents')).toBe('flow');

  // The time windows end at the present, where the schematic is drawn too.
  await page.goto(new URL('/?masks=paleodem2018&window=lastcycle&currents=conveyor', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-circulation', '9');
  await goTo('s[3] > 0');
  await expect(globe).toHaveAttribute('data-circulation', '');

  // A value the select does not offer is ignored.
  await page.goto(new URL('/?masks=paleodem2018&currents=belt', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#currents')).toHaveValue('');
  expect(await globe.getAttribute('data-circulation')).not.toBe('9');

  if (external.length) throw new Error(`Third-party requests: ${external.join(', ')}`);
  if (errors.length) throw new Error(`Page errors: ${errors.join(' | ')}`);
  console.log('circulation: browser checks passed');
} finally {
  await browser.close();
}
