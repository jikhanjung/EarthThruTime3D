import {chromium, expect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8153/';
try {
  const page = await browser.newPage({locale: 'en-US', viewport: {width: 1280, height: 900}});
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  const globe = page.locator('#globe');
  const items = page.locator('#pin-list li');
  const openMenu = async () => {
    // The menu remembers being open, so only a closed one is pressed.
    if (await page.locator('#settings-toggle').getAttribute('aria-expanded') !== 'true') await page.locator('#settings-toggle').click();
  };
  // Without pins in the address the layer is off: nothing drawn, nothing in the panel.
  await page.goto(new URL('/?masks=paleodem2018&age=200', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#pin')).toHaveAttribute('aria-pressed', 'false');
  await expect(globe).toHaveAttribute('data-pins', '0');
  await expect(page.locator('#pin-panel')).toBeHidden();
  // Switched on, a click that does not drag drops a pin and a second click on it takes it
  // away; a drag turns the globe and drops none. The middle of the view at 200 Ma is Africa.
  await openMenu();
  await page.locator('#pin').click();
  await expect(page.locator('#pin-panel')).toBeVisible();
  const box = await page.locator('#globe canvas').first().boundingBox();
  const [x, y] = [box.x + box.width / 2, box.y + box.height / 2];
  await page.mouse.click(x, y);
  await expect(globe).toHaveAttribute('data-pins', '1');
  await expect(items.nth(0)).toContainText('plate 701');
  expect(new URL(page.url()).searchParams.get('pin')).toMatch(/^-?\d+\.\d\d,-?\d+\.\d\d$/);
  await page.mouse.click(x, y);
  await expect(globe).toHaveAttribute('data-pins', '0');
  await page.mouse.move(x - 40, y);
  await page.mouse.down();
  await page.mouse.move(x + 40, y, {steps: 6});
  await page.mouse.up();
  await expect(globe).toHaveAttribute('data-pins', '0');
  // Pins in the address switch it on. Seoul and Chicago at 200 Ma, as scripts/assess_pin.py
  // places them with the PALEOMAP rotations.
  await page.goto(new URL('/?masks=paleodem2018&age=200&pin=126.98,37.57;-87.63,41.88', base).href);
  await expect(globe).toHaveAttribute('data-pins', '2');
  await expect(page.locator('#pin')).toHaveAttribute('aria-pressed', 'true');
  await expect(items.nth(0)).toContainText('plate 604');
  await expect(items.nth(0)).toContainText('here 46.2°N 133.9°E');
  await expect(items.nth(1)).toContainText('here 21.4°N 31.5°W');
  await expect(page.locator('#pin-distances')).toHaveText('1–2 12,355 km (10,509 km today)');
  // "here" turns the globe to the pin; the × takes a pin away, and one pin has no distance.
  await items.nth(0).locator('.pin-here').click();
  await items.nth(1).locator('.pin-remove').click();
  await expect(globe).toHaveAttribute('data-pins', '1');
  await expect(page.locator('#pin-distances')).toHaveText('');
  expect(new URL(page.url()).searchParams.get('pin')).toBe('126.98,37.57');
  // Switched off, the pins leave the map, the panel and the address; on again they are back.
  await openMenu();
  await page.locator('#pin').click();
  await expect(globe).toHaveAttribute('data-pins', '0');
  await expect(page.locator('#pin-panel')).toBeHidden();
  expect(new URL(page.url()).searchParams.has('pin')).toBe(false);
  await page.locator('#pin').click();
  await expect(globe).toHaveAttribute('data-pins', '1');
  // Land the model does not carry that far back says so; Astana's polygon begins at 420 Ma.
  await page.goto(new URL('/?masks=paleodem2018&age=450&pin=71.43,51.13;-87.63,41.88', base).href);
  await expect(globe).toHaveAttribute('data-pins', '1');
  await expect(items.nth(0)).toContainText('back only to 420 Ma');
  // The 2002 maps part from the PALEOMAP rotations before 300 Ma, so pins are not drawn there.
  await page.goto(new URL('/?masks=scotese2002&age=425&pin=-87.63,41.88', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(items.nth(0)).toContainText('not drawn on these maps before 300 Ma');
  await expect(globe).toHaveAttribute('data-pins', '0');
  // On a flat map "here" brings the pin's longitude to the middle, and a click still drops.
  await page.goto(new URL('/?masks=paleodem2018&age=200&pin=126.98,37.57', base).href);
  await expect(globe).toHaveAttribute('data-pins', '1');
  await page.selectOption('#projection', 'mollweide');
  await expect(globe).toHaveAttribute('data-projection', 'mollweide');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await items.nth(0).locator('.pin-here').click();
  await expect(globe).toHaveAttribute('data-meridian', '133.9');
  await mkdir('test-results', {recursive: true});
  await page.screenshot({path: 'test-results/pin-reviewed.png'});
  // In a time window the plates have not moved by a pixel: the pin stays on today's place.
  await page.goto(new URL('/?masks=paleodem2018&window=lastcycle&pin=126.98,37.57', base).href);
  await expect(globe).toHaveAttribute('data-pins', '1');
  await page.locator('#timeline').fill('0');
  await page.locator('#timeline').dispatchEvent('input');
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(items.nth(0)).toContainText('here 37.6°N 127.0°E');
  await page.goto(new URL('/lang/ko/?next=/?masks=paleodem2018', base).href);
  await expect(page.locator('#pin')).toHaveText('위치 핀');
  expect(errors).toEqual([]);
  console.log('Click against drag, pins from the address, here and ×, the switch, vanished land, the 2002 maps, a flat map, a time window and languages passed');
} finally {await browser.close();}
