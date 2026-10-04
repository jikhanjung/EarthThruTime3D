// Past surface currents (wwolf P02 step 3): FOAM's nearest run as the present-day particles,
// on the elevation series' past stops, the source named on screen, the field moved with the
// map between two stops, and none in the time windows. Needs a server whose bundle has the
// past current fields (scripts/build_past_currents.py); the present-day data is not needed.
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
  const goTo = (pick) => page.evaluate((source) => {
    const stops = JSON.parse(document.getElementById('globe-stops').textContent);
    const slider = document.getElementById('timeline');
    slider.value = String(stops.findIndex(new Function('s', `return ${source}`)));
    slider.dispatchEvent(new Event('input'));
  }, pick);

  // A stop with its own run: the field, the source under the age, the legend and the note.
  await page.goto(new URL('/?masks=paleodem2018&age=100&currents=flow', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-flux', 'past');
  await expect(globe).toHaveAttribute('data-currents', 'true');
  await expect(globe).toHaveAttribute('data-currents-run', '100');
  await expect(globe).toHaveAttribute('data-currents-warp', '');
  await expect(page.locator('#currents')).toBeEnabled();
  await expect(page.locator('#currents')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#flux-when')).toContainText('FOAM');
  await expect(page.locator('#flux-when')).toContainText('100');
  await expect(page.locator('#flux-legend')).toContainText('FOAM');
  await expect(page.locator('#foam-note')).toBeVisible();
  if (await page.locator('#wind-layer').count()) await expect(page.locator('#wind-layer')).toBeDisabled();
  await page.waitForTimeout(2500);
  const inked = await page.evaluate(() => {
    const canvas = document.querySelector('.flux-canvas[data-layer="ocean"]');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0;
    for (let i = 3; i < data.length; i += 4 * 16) if (data[i] > 0) count++;
    return count;
  });
  expect(inked).toBeGreaterThan(50);
  await page.screenshot({path: 'test-results/past-currents-100.png'});

  // A stop between two runs takes the nearest one, the younger on a tie.
  await goTo('s[3] === 110');
  await expect(globe).toHaveAttribute('data-currents-run', '100');
  await goTo('s[3] === 115');
  await expect(globe).toHaveAttribute('data-currents-run', '120');

  // Between two grids the nearer grid's field moves with the map.
  await goTo('s[3] > 100 && s[3] < 102.5');
  await expect(globe).not.toHaveAttribute('data-blend', '0.00');
  await expect(globe).toHaveAttribute('data-currents', 'true');
  await expect(globe).not.toHaveAttribute('data-currents-warp', '');
  await expect(globe).toHaveAttribute('data-currents-run', '100');

  // Flat maps draw the same particles.
  await page.selectOption('#projection', 'equalearth');
  await goTo('s[3] === 250');
  await expect(globe).toHaveAttribute('data-currents-run', '240');
  await page.waitForTimeout(2000);
  await page.screenshot({path: 'test-results/past-currents-250-equalearth.png'});

  // The address keeps currents=flow at every age.
  await expect.poll(() => new URL(page.url()).searchParams.get('currents')).toBe('flow');

  // The time windows have no past field. With the present-day data built the switch is
  // there but off; without it there is no currents layer in a window at all.
  await page.goto(new URL('/?masks=paleodem2018&window=lastcycle&currents=flow', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await goTo('s[3] > 0');
  await expect(globe).toHaveAttribute('data-blend', '0.00');
  expect(await globe.getAttribute('data-currents')).not.toBe('true');
  if (await page.locator('#currents').count()) await expect(page.locator('#currents')).toBeDisabled();

  if (external.length) throw new Error(`Third-party requests: ${external.join(', ')}`);
  if (errors.length) throw new Error(`Page errors: ${errors.join(' | ')}`);
  console.log('past currents: browser checks passed');
} finally {
  await browser.close();
}
