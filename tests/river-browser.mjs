import {chromium, expect as baseExpect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
// setDefaultTimeout covers actions; an assertion keeps Playwright's own 5 s unless it is
// configured too, and a first draw that is merely slow then fails on a loaded machine.
const expect = baseExpect.configure({timeout: 20000});
const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8153/';
try {
  const page = await browser.newPage({locale: 'en-US', viewport: {width: 1280, height: 900}});
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  const river = page.waitForResponse(response => response.url().includes('/globe/rivers/paleodem-0000.png'));
  await page.goto(new URL('/?masks=paleodem2018', base).href);
  expect((await river).status()).toBe(200);
  const globe = page.locator('#globe');
  await expect(globe).toHaveAttribute('data-rivers', 'true');
  await expect(page.locator('#river-note')).toContainText('Grid spacing is not reconstruction accuracy');
  await page.locator('#settings-toggle').click();
  await page.locator('#rivers').click();
  await expect(globe).toHaveAttribute('data-rivers', 'false');
  await expect(page.locator('#river-note')).toBeHidden();
  await page.locator('#rivers').click();
  await expect(globe).toHaveAttribute('data-rivers', 'true');
  await page.locator('#settings-toggle').click();
  await page.locator('#sealevel').fill('-130');
  await expect(globe).toHaveAttribute('data-river-low', '1.00');
  await page.locator('#sealevel').fill('0');
  await expect(globe).toHaveAttribute('data-river-low', '0.00');
  await mkdir('test-results', {recursive: true});
  await page.screenshot({path: 'test-results/rivers-reviewed.png'});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto(new URL('/lang/ko/?next=/?masks=paleodem2018', base).href);
  await expect(globe).toHaveAttribute('data-rivers', 'true');
  await page.locator('#info-toggle').click();
  await expect(page.locator('#river-note')).toContainText('격자 간격과 복원 정확도는 다릅니다');
  for (const [window, age] of [['deglacial', 21], ['lastcycle', 70]]) {
    await page.goto(new URL(`/?masks=paleodem2018&window=${window}`, base).href);
    const frames = JSON.parse(await page.locator('#globe-frames').textContent());
    await page.selectOption('#era', String(frames.findIndex(frame => frame.deglacial?.age_ka === age)));
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    expect(Number(await globe.getAttribute('data-river-low'))).toBeGreaterThan(0);
  }
  expect(errors).toEqual([]);
  console.log('River PNG, shader, toggle, resolution wording, lowstand/time windows, mobile and languages passed');
} finally {await browser.close();}
