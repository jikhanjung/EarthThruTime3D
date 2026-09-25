import {chromium, expect} from '@playwright/test';
const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL, args: ['--enable-unsafe-swiftshader']});
const base = process.env.VIEWER_URL || 'http://127.0.0.1:8153/';
try {
  const page = await browser.newPage({locale: 'en-US', viewport: {width: 1280, height: 900}});
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
  const globe = page.locator('#globe');
  const params = () => new URL(page.url()).searchParams;
  const view = async () => ({
    projection: await page.locator('#projection').inputValue(), surface: await globe.getAttribute('data-surface'),
    shading: await page.locator('#shading').inputValue(), grid: await page.locator('#grid').getAttribute('aria-pressed'),
  });
  // A link sets the view before the first stop is drawn.
  await page.goto(new URL('/?masks=paleodem2018&age=300&view=equalearth&surface=temp&shading=5&grid=0', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  expect(await view()).toEqual({projection: 'equalearth', surface: 'temp', shading: '5', grid: 'false'});
  await expect(page.locator('#globe-age')).toContainText('300 Ma');
  // A default page writes nothing of its own; the controls write what differs.
  await page.goto(new URL('/?masks=paleodem2018', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  expect([...params().keys()]).toEqual(['masks']);
  await page.selectOption('#projection', 'mollweide');
  await page.locator('#settings-toggle').click();
  await page.locator('#rivers').click();
  // Each control resets the 0.4 s debounce, so the projection can land in one write and
  // the switch in the next: poll for both rather than reading straight after the first.
  await expect.poll(() => params().get('view')).toBe('mollweide');
  await expect.poll(() => params().get('rivers')).toBe('0');
  expect(params().has('shading')).toBe(false);
  // Reloading the written address gives the same view.
  const written = page.url();
  await page.goto(written);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#projection')).toHaveValue('mollweide');
  await expect(page.locator('#rivers')).toHaveAttribute('aria-pressed', 'false');
  // Values outside the lists are ignored.
  await page.goto(new URL('/?masks=paleodem2018&view=cube&surface=lava&shading=3', base).href);
  await expect(globe).toHaveAttribute('aria-busy', 'false');
  expect(await view()).toEqual({projection: 'globe', surface: 'relief', shading: '1', grid: 'true'});
  expect(errors).toEqual([]);
  console.log('View from the address, written back, reloaded and invalid values ignored passed');
} finally {
  await browser.close();
}
