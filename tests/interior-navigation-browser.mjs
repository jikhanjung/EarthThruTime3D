import {chromium, expect as baseExpect} from '@playwright/test';
const expect = baseExpect.configure({timeout: 30000});
const browser = await chromium.launch({headless: true, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8150/';
// The Earth interior section starts folded to its heading; open it before using its controls.
const openInterior = async (target) => {
  if (await target.locator('#interior-panel.folded').count()) await target.locator('#interior-title').click();
};
try {
  for (const masks of ['paleoatlas2016', 'paleodem2018']) {
    const page = await browser.newPage({viewport: {width: 1400, height: 1000}, deviceScaleFactor: .75, reducedMotion: 'reduce'});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => {if (m.type() === 'error' && /THREE|Shader|WebGL/.test(m.text())) errors.push(m.text());});
    await page.goto(new URL(`/?masks=${masks}`, base).href);
    const globe = page.locator('#globe');
    await expect(globe).toHaveAttribute('aria-busy', 'false');
    const drag = async (button, dx, dy) => {
      await page.mouse.move(550, 360);
      await page.mouse.down({button});
      await page.mouse.move(550 + dx, 360 + dy, {steps: 3});
      await page.mouse.up({button});
    };
    // Tilt and pan work before zooming and without elevation or interior layers.
    await drag('middle', 40, -40);
    await expect.poll(async () => Number(await globe.getAttribute('data-tilt'))).toBeGreaterThan(5);
    await drag('right', 100, 50);
    await expect(globe).not.toHaveAttribute('data-pan', '0.0000,0.0000,0.0000');
    await page.locator('#reset').click();
    await expect(globe).toHaveAttribute('data-pan', '0.0000,0.0000,0.0000');
    await openInterior(page);
    await page.locator('#crust-enabled').check();
    await expect(globe).toHaveAttribute('data-crust', 'ready');
    await page.locator('#mantle-overlay').check();
    await expect(globe).toHaveAttribute('data-mantle-overlay', 'ready');
    await page.locator('#interior-cutaway').check();
    await page.locator('#interior-focus').click();
    await expect(globe).toHaveAttribute('data-interior-backfaces', 'true');
    // Crossing the opaque/transparent queue boundary must not recolour the globe.
    // UI steps are 5%; use 1% here to isolate the queue boundary.
    await page.locator('#mantle-opacity').evaluate(input => { input.step = '1'; });
    const capture = async opacity => {
      await page.locator('#mantle-opacity').fill(String(opacity));
      await expect(globe).toHaveAttribute('data-mantle-opacity', String(opacity / 100));
      const png = await page.screenshot({clip: {x: 300, y: 200, width: 500, height: 400}});
      return page.evaluate(async base64 => {
        const img = new Image(); img.src = 'data:image/png;base64,' + base64; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
        return Array.from(ctx.getImageData(0, 0, c.width, c.height).data);
      }, png.toString('base64'));
    };
    const opaque = await capture(100), almost = await capture(99);
    const difference = opaque.reduce((sum, value, i) => sum + (i % 4 === 3 ? 0 : Math.abs(value - almost[i])), 0) / (opaque.length * .75);
    console.log(`${masks}: 100%→99% mean RGB change ${difference.toFixed(2)}/255`);
    expect(difference).toBeLessThan(5);
    await page.screenshot({path: `test-results/interior-backfaces-${masks}.png`});
    await globe.focus();
    for (let i = 0; i < 9; i++) await page.keyboard.press('+');
    await expect.poll(async () => Number(await globe.getAttribute('data-zoom'))).toBeLessThan(.2);
    await drag('right', 100, 60);
    const pan = await globe.getAttribute('data-pan');
    expect(pan).not.toBe('0.0000,0.0000,0.0000');
    await page.keyboard.down('Shift');
    await drag('left', 40, -25);
    await page.keyboard.up('Shift');
    await expect(globe).toHaveAttribute('data-pan', pan); // tilt must not also pan
    await page.screenshot({path: `test-results/interior-navigation-${masks}.png`});
    await page.locator('#reset').click();
    await expect(globe).toHaveAttribute('data-pan', '0.0000,0.0000,0.0000');
    await expect(globe).toHaveAttribute('data-tilt', '50');
    await page.locator('#interior-cutaway').uncheck();
    await expect(globe).toHaveAttribute('data-interior-backfaces', 'false');
    await page.selectOption('#projection', 'equirect');
    await drag('right', 80, 20);
    await expect(globe).not.toHaveAttribute('data-pan', '0.0000,0.0000,0.0000');
    await page.selectOption('#projection', 'globe');
    await expect(globe).toHaveAttribute('data-pan', '0.0000,0.0000,0.0000');
    expect(errors).toEqual([]);
    console.log(`${masks}: pan, zoom, tilt, shared cut backfaces, reset and projection passed`);
    await page.close();
  }
} finally {await browser.close();}
