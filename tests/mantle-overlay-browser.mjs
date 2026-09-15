import {chromium,expect} from '@playwright/test';
const browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
const base=process.env.VIEWER_URL || 'http://127.0.0.1:8142/';
try {
 const page=await browser.newPage({locale:'ko-KR',viewport:{width:1440,height:1100}});
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',msg=>{if(msg.type()==='error'&& /THREE|Shader|WebGL/.test(msg.text()))errors.push(msg.text())});
 page.on('request',r=>{if(r.url().includes('/mantle/assets/'))requests.push(r.url())});
 await page.goto(base);
 const globe=page.locator('#globe'),toggle=page.locator('#mantle-overlay');
 await expect(globe).toHaveAttribute('aria-busy','false');
 expect(requests).toEqual([]);
 if(await page.locator('#inspector').evaluate(n=>n.classList.contains('closed')))await page.locator('#info-toggle').click();
 // Entering from a flat map must not cancel the mode during its internal switch.
 await page.locator('#projection').selectOption('equirect');
 await expect(globe).toHaveAttribute('data-projection','equirect');
 const initial=await page.locator('#timeline').inputValue();
 await toggle.check();
 await expect(globe).toHaveAttribute('data-mantle-overlay','ready',{timeout:20000});
 await expect(page.locator('#age')).toContainText('80');
 await expect(globe).toHaveAttribute('data-mantle-cutaway','true');
 expect(requests.length).toBe(2);
 await page.screenshot({path:'test-results/mantle-overlay-desktop.png',fullPage:true});
 const cut=await page.locator('#globe canvas').screenshot();
 await page.locator('#mantle-cutaway').uncheck();
 await expect(globe).toHaveAttribute('data-mantle-cutaway','false');
 const closed=await page.locator('#globe canvas').screenshot();
 expect(Buffer.compare(cut,closed)).not.toBe(0);
 await page.locator('#mantle-cutaway').check();
 await page.locator('#overlay-slabs').uncheck();await page.locator('#overlay-slabs').check();
 expect(requests.length).toBe(2);
 await toggle.uncheck();
 await expect(globe).toHaveAttribute('data-mantle-overlay','off');
 await expect(page.locator('#timeline')).toHaveValue(initial);
 await expect(globe).toHaveAttribute('data-projection','equirect');
 await expect(globe).toHaveAttribute('aria-busy','false');
 // Re-enter and leave through an explicit time change.
 await toggle.check();await expect(globe).toHaveAttribute('data-mantle-overlay','ready');
 await page.locator('#timeline').fill(initial);await expect(globe).toHaveAttribute('data-mantle-overlay','off');
 await expect(toggle).not.toBeChecked();
 // Leaving through a projection change restores a complete surface.
 await toggle.check();await expect(globe).toHaveAttribute('data-mantle-overlay','ready');
 await page.locator('#projection').selectOption('mollweide');
 await expect(globe).toHaveAttribute('data-mantle-overlay','off');
 await expect(globe).toHaveAttribute('data-mantle-cutaway','false');
 // Network failure never opens the surface, and retry recovers.
 await page.route('**/mantle/assets/slabs-46-*',r=>r.fulfill({status:503}));
 await toggle.check();await expect(globe).toHaveAttribute('data-mantle-overlay','error');
 await expect(globe).toHaveAttribute('data-mantle-cutaway','false');
 await page.unroute('**/mantle/assets/slabs-46-*');
 await page.locator('#mantle-overlay-retry').click();
 await expect(globe).toHaveAttribute('data-mantle-overlay','ready');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('#info-toggle').click();
 await expect(page.locator('#mantle-overlay-caption')).toBeVisible();
 await page.screenshot({path:'test-results/mantle-overlay-mobile.png',fullPage:true});
 await page.locator('#info-toggle').click();
 // A cancelled load must not cut the restored surface after its response arrives.
 await toggle.uncheck();
 await page.route('**/mantle/assets/*',async r=>{await new Promise(resolve=>setTimeout(resolve,700));await r.continue().catch(()=>{});});
 await toggle.check();await expect(globe).toHaveAttribute('data-mantle-overlay','loading');
 await toggle.uncheck();await page.waitForTimeout(1000);
 await expect(globe).toHaveAttribute('data-mantle-overlay','off');
 await expect(globe).toHaveAttribute('data-mantle-cutaway','false');
 await page.unroute('**/mantle/assets/*');
 await page.goto(new URL('/lang/en/?next=/',base).href);
 await expect(page.locator('#mantle-overlay-panel')).toContainText('Approximate mantle overlay');
 // The elevation dataset uses the same cut and keeps its source metadata.
 await page.goto(new URL('/?masks=paleodem2018',base).href);
 if(await page.locator('#inspector').evaluate(n=>n.classList.contains('closed')))await page.locator('#info-toggle').click();
 await page.locator('#mantle-overlay').check();
 await expect(globe).toHaveAttribute('data-mantle-overlay','ready',{timeout:20000});
 await page.screenshot({path:'test-results/mantle-overlay-paleodem.png',fullPage:true});
 expect(errors).toEqual([]);
 console.log('Overlay: lazy 80 Ma meshes, cutaway, layers, restore, time exit, error/retry, mobile, English OK');
} finally {await browser.close()}
