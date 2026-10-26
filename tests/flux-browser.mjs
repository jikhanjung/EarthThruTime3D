// The present-day Earth (jikhanjung P10): satellite base at 0 Ma, wind, currents and clouds,
// the moment of the data on screen, the address, gating away from 0 Ma, flat maps, no
// third-party requests and a phone. Needs a server whose bundle has data/derived/present-earth.
import {chromium, expect as baseExpect} from '@playwright/test';
const expect = baseExpect.configure({timeout: 30000});

const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8150/';
const origin = new URL(base).origin;
try {
  const page = await browser.newPage({viewport: {width: 1400, height: 900}});
  const errors = [], external = [];
  page.on('pageerror', e => errors.push(e.message));
  // A navigation cuts off the previous page's downloads; that is not this layer's error.
  page.on('console', m => { if (m.type() === 'error' && !/Failed to fetch|ERR_ABORTED/.test(m.text())) errors.push(m.text()); });
  page.on('request', r => { if (!r.url().startsWith(origin) && !r.url().startsWith('data:')) external.push(r.url()); });
  const globe = page.locator('#globe');
  const menu = async () => { if (await page.locator('#settings-menu').isHidden()) await page.locator('#settings-toggle').click(); };

  await page.goto(new URL('/?masks=paleodem2018', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  // The present is the photograph; the computed rivers and the ice overlay step aside.
  await expect(globe).toHaveAttribute('data-surface', 'sat');
  await expect(globe).toHaveAttribute('data-rivers', 'false');
  await expect(page.locator('#globe-age')).toContainText('0 Ma');
  await expect(page.locator('#flux-when')).toContainText('Blue Marble');
  await expect(globe).toHaveAttribute('data-flux', 'ready');
  await expect(page.locator('.flux-canvas')).toHaveCount(2);
  await expect(page.locator('#globe canvas')).toHaveCount(1);

  // Each layer on: the moment comes from the catalogue, never typed by hand.
  const present = JSON.parse(await page.locator('#globe-present').textContent());
  const moment = `${present.weather.t.slice(0, 10)} ${present.weather.t.slice(11, 16)} UTC`;
  await menu();
  await page.selectOption('#wind-layer', '250hPa');
  await page.selectOption('#currents', 'flow');
  await page.selectOption('#cloud-layer', 'sat');
  await expect(globe).toHaveAttribute('data-wind', '250hPa');
  await expect(globe).toHaveAttribute('data-currents', 'true');
  await expect(globe).toHaveAttribute('data-clouds', 'sat');
  await expect(page.locator('#flux-when')).toContainText(moment);
  await expect(page.locator('#flux-when')).toContainText(`${present.ocean.period[0]}–${present.ocean.period[1]}`);
  await expect(page.locator('#flux-legend')).toContainText('250 hPa');
  await expect(page.locator('#flux-legend')).toContainText(moment);
  await expect(page.locator('#flux-note')).toBeVisible();
  await expect.poll(() => new URL(page.url()).searchParams.get('wind')).toBe('250hPa');
  await expect.poll(() => new URL(page.url()).searchParams.get('currents')).toBe('flow');
  await expect.poll(() => new URL(page.url()).searchParams.get('clouds')).toBe('sat');
  await page.waitForTimeout(2500);
  // Particles are drawn: the wind canvas is not blank.
  const inked = await page.evaluate(() => {
    const canvas = document.querySelector('.flux-canvas[data-layer="wind"]');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let count = 0;
    for (let i = 3; i < data.length; i += 4 * 16) if (data[i] > 0) count++;
    return count;
  });
  expect(inked).toBeGreaterThan(50);
  await page.screenshot({path: 'test-results/flux-globe.png'});

  // One layer off: its moment leaves the caption.
  await page.selectOption('#cloud-layer', '');
  await page.selectOption('#currents', '');
  await expect(page.locator('#flux-when')).not.toContainText('–');
  await expect(globe).toHaveAttribute('data-clouds', '');

  // Away from the present everything stands down, and comes back. Where the bundle has the
  // past current fields the stop offers its own currents (data-flux="past"), switched off here.
  await page.locator('#older').click();
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-flux', /^(unavailable|past)$/);
  await expect(globe).toHaveAttribute('data-currents', 'false');
  await expect(globe).not.toHaveAttribute('data-surface', 'sat');
  await expect(page.locator('#flux-when')).toBeHidden();
  await expect(page.locator('#wind-layer')).toBeDisabled();
  await expect(page.locator('.flux-canvas[data-layer="wind"]')).toBeHidden();
  await page.locator('#newer').click();
  await expect(globe).toHaveAttribute('data-surface', 'sat');
  await expect(globe).toHaveAttribute('data-wind', '250hPa');

  // Flat maps carry the clouds and particles too.
  await page.selectOption('#cloud-layer', 'model');
  await page.selectOption('#projection', 'mollweide');
  await expect(globe).toHaveAttribute('data-projection', 'mollweide');
  await expect(globe).toHaveAttribute('data-clouds', 'model');
  await page.waitForTimeout(1500);
  await page.screenshot({path: 'test-results/flux-mollweide.png'});

  // The satellite switch gives the elevation colours back, with their rivers.
  await menu();
  await page.locator('#satellite').click();
  await expect(globe).toHaveAttribute('data-surface', 'relief');
  await expect(globe).toHaveAttribute('data-rivers', 'true');
  await expect.poll(() => new URL(page.url()).searchParams.get('sat')).toBe('0');

  // The default atlas, whose plain surface is the mask: the present is still the photograph,
  // and the mask's note stays hidden. A drag leaves no blank frame while the camera settles.
  await page.goto(new URL('/?wind=10m', base).href);
  await expect(globe).toHaveAttribute('data-wind', '10m');
  await expect(globe).toHaveAttribute('data-surface', 'sat');
  await expect(page.locator('#surface-note')).toBeHidden();
  await page.waitForTimeout(1000);
  const box = await globe.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 20, {steps: 6});
  await page.mouse.up();
  for (let i = 0; i < 8; i++) {
    const ink = await page.evaluate(() => {
      const canvas = document.querySelector('.flux-canvas[data-layer="wind"]');
      const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
      let count = 0;
      for (let j = 3; j < data.length; j += 64) if (data[j]) count++;
      return count;
    });
    expect(ink).toBeGreaterThan(50);
    await page.waitForTimeout(120);
  }

  // The address reopens the same view.
  await page.goto(new URL('/?masks=paleodem2018&wind=10m&currents=flow&clouds=model', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(globe).toHaveAttribute('data-wind', '10m');
  await expect(globe).toHaveAttribute('data-currents', 'true');
  await expect(globe).toHaveAttribute('data-clouds', 'model');
  await expect(page.locator('#wind-layer')).toHaveValue('10m');

  // English, with the same moment.
  await page.goto(new URL('/lang/en/?next=/%3Fmasks%3Dpaleodem2018%26wind%3D10m', base).href);
  await page.goto(new URL('/?masks=paleodem2018&wind=10m', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#flux-when')).toContainText(`Wind ${moment}`);

  // A phone: the caption and legend fit, the canvases follow the stage.
  const phone = await browser.newPage({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
  phone.on('pageerror', e => errors.push(e.message));
  await phone.goto(new URL('/?masks=paleodem2018&wind=10m&clouds=sat', base).href);
  await expect(phone.locator('#globe')).toHaveAttribute('data-wind', '10m');
  await expect(phone.locator('#globe')).toHaveAttribute('data-satellite-size', '4096');
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await phone.waitForTimeout(1500);
  await phone.screenshot({path: 'test-results/flux-phone.png'});

  expect(external).toEqual([]);
  expect(errors).toEqual([]);
  console.log('Present-day Earth: satellite base, wind, currents, clouds, moment, gating, flat map, address, English and phone passed');
} finally {
  await browser.close();
}
