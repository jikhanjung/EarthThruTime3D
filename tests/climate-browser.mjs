import {chromium, expect as baseExpect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
// setDefaultTimeout covers actions; an assertion keeps Playwright's own 5 s unless it is
// configured too, and a first draw that is merely slow then fails on a loaded machine.
const expect = baseExpect.configure({timeout: 20000});
const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8153/';
try {
  const page = await browser.newPage({locale: 'en-US', viewport: {width: 1280, height: 900}});
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  const globe = page.locator('#globe');
  // The whole timeline has no modelled climate to offer.
  await page.goto(new URL('/?masks=paleodem2018', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#vegetation')).toHaveCount(0);
  for (const [window, age] of [['deglacial', 21], ['lastcycle', 125]]) {
    await page.goto(new URL(`/?masks=paleodem2018&window=${window}`, base).href);
    const frames = JSON.parse(await page.locator('#globe-frames').textContent());
    expect(frames.every(frame => frame.climate)).toBe(true);
    const texture = page.waitForResponse(response => response.url().includes(`/globe/climate/paleodem-0000/${age}.png`));
    // The menu remembers being open, so only a closed one is pressed.
    if (await page.locator('#settings-toggle').getAttribute('aria-expanded') !== 'true') await page.locator('#settings-toggle').click();
    await page.locator('#vegetation').click();
    await page.selectOption('#era', String(frames.findIndex(frame => frame.deglacial?.age_ka === age)));
    expect((await texture).status()).toBe(200);
    await expect(globe).toHaveAttribute('data-surface', 'veg');
    await expect(page.locator('#vegetation')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#veg-legend')).toBeVisible();
    await expect(page.locator('#rain-legend')).toBeHidden();
    await expect(page.locator('#climate-note')).toContainText('does not reproduce the ‘Green Sahara’');
    // The two modes are one surface choice: rainfall takes over, and a second press gives the relief back.
    await page.locator('#rainfall').click();
    await expect(globe).toHaveAttribute('data-surface', 'rain');
    await expect(page.locator('#vegetation')).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator('#rain-legend')).toBeVisible();
    await expect(page.locator('#veg-legend')).toBeHidden();
    // The mode holds from one stop to the next, each with its own texture.
    const older = page.waitForResponse(response => response.url().includes(`/globe/climate/paleodem-0000/${age + 1}.png`));
    await page.locator('#older').click();
    expect((await older).status()).toBe(200);
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    await expect(globe).toHaveAttribute('data-surface', 'rain');
    await page.locator('#rainfall').click();
    await expect(globe).toHaveAttribute('data-surface', 'relief');
    await expect(page.locator('#climate-note')).toBeHidden();
  }
  await page.locator('#vegetation').click();
  await expect(globe).toHaveAttribute('data-surface', 'veg');
  await mkdir('test-results', {recursive: true});
  await page.screenshot({path: 'test-results/climate-reviewed.png'});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto(new URL('/lang/ko/?next=/?masks=paleodem2018%26window=deglacial', base).href);
  await expect(page.locator('#vegetation')).toHaveText('모형 식생');
  expect(errors).toEqual([]);
  console.log('Climate textures, both modes, legends, the Sahara note, stop to stop, mobile and languages passed');
} finally {await browser.close();}
