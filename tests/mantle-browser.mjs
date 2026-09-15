import { chromium, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL,
  args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8137/';
const errors = [];
try {
  const page = await browser.newPage({locale: 'ko-KR', viewport: {width: 1280, height: 1000}});
  page.on('pageerror', (error) => errors.push(error.message));
  const firstMesh = page.waitForResponse(response => response.url().includes('/mantle/assets/slabs-50-'));
  await page.goto(new URL('/mantle/', base).href);
  expect((await firstMesh).headers()['content-encoding']).toBe('gzip');
  const stage = page.locator('#mantle-stage');
  await expect(stage).toHaveAttribute('data-frame', '50');
  await expect(page.locator('#mantle-age')).toHaveText('0 Ma');
  await page.locator('#mantle-time').fill('46');
  await expect(stage).toHaveAttribute('data-frame', '46');
  await expect(page.locator('#mantle-age')).toHaveText('80 Ma');
  await page.locator('#mantle-slabs').uncheck();
  await page.locator('#mantle-slabs').check();
  // Cancel pending loads repeatedly; only the last requested age may be displayed.
  const crossed = [];
  page.on('request', request => {
    if (/\/mantle\/assets\/\w+-(00|10|30)-/.test(request.url())) crossed.push(request.url());
  });
  await page.evaluate(() => {
    const slider = document.getElementById('mantle-time');
    for (const value of ['0', '10', '30', '50']) {
      slider.value = value; slider.dispatchEvent(new Event('input'));
    }
  });
  await expect(stage).toHaveAttribute('data-frame', '50');
  await expect(stage).toHaveAttribute('data-loading', 'false');
  expect(crossed).toEqual([]);
  await page.route('**/mantle/assets/*-49-*.bin', route => route.fulfill({status: 404}));
  await page.locator('#mantle-time').fill('49');
  await expect(page.locator('#mantle-status')).toContainText('불러오지 못했습니다');
  await expect(stage).not.toHaveAttribute('data-frame', /.+/);
  await page.locator('#mantle-time').fill('50');
  await expect(stage).toHaveAttribute('data-frame', '50');
  // A real context loss must recover without a page reload.
  await page.locator('#mantle-stage canvas').evaluate(canvas => {
    const extension=canvas.getContext('webgl2').getExtension('WEBGL_lose_context');
    window.restoreMantleContext=()=>extension.restoreContext();extension.loseContext();
  });
  await expect(page.locator('#mantle-time')).toBeDisabled();
  await page.evaluate(()=>window.restoreMantleContext());
  await expect(stage).toHaveAttribute('data-frame','50');
  await expect(page.locator('#mantle-time')).toBeEnabled();
  await mkdir('test-results', {recursive: true});
  await page.screenshot({path: 'test-results/mantle-desktop.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: 'test-results/mantle-mobile.png', fullPage: true});
  await page.goto(new URL('/lang/en/?next=/mantle/', base).href);
  await expect(page.locator('h1')).toHaveText('Mantle model experiment');
  await expect(stage).toHaveAttribute('data-frame', '50');
  expect(errors).toEqual([]);
  console.log('Mantle browser: ages, rapid loads, failure/recovery, layers, mobile and English OK');
} finally {
  await browser.close();
}
