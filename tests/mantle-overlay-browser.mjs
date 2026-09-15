import {chromium,expect} from '@playwright/test';
const browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
const base=process.env.VIEWER_URL||'http://127.0.0.1:8150/';
try {
 const page=await browser.newPage({locale:'ko-KR',viewport:{width:1200,height:950},reducedMotion:'reduce'});
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error'&&/THREE|Shader|WebGL/.test(m.text()))errors.push(m.text())});
 page.on('request',r=>{if(r.url().includes('/mantle/assets/'))requests.push(r.url())});
 await page.goto(new URL('/?masks=paleodem2018',base).href);
 const globe=page.locator('#globe'),toggle=page.locator('#mantle-overlay');
 const ready=async age=>{await expect(globe).toHaveAttribute('data-mantle-overlay','ready',{timeout:30000});await expect(globe).toHaveAttribute('data-mantle-age',String(age));};
 await expect(globe).toHaveAttribute('aria-busy','false');expect(requests).toEqual([]);
 const initial=await page.locator('#timeline').inputValue();
 await page.selectOption('#projection','equirect');await toggle.check();await ready(80);
 expect(requests.length).toBe(2);
 await expect(page.locator('#overlay-core')).toBeChecked();
 await page.locator('#info-toggle').click();
 await page.screenshot({path:'test-results/mantle-global-core.png',fullPage:true});
 await page.locator('#info-toggle').click();
 await page.locator('#overlay-core').uncheck();await page.locator('#overlay-core').check();
 const before=requests.length;
 await page.locator('#mantle-longitude').fill('25');await page.locator('#mantle-latitude').fill('-15');await page.locator('#mantle-radius').fill('30');
 await page.locator('#mantle-opacity').fill('35');await expect(globe).toHaveAttribute('data-mantle-opacity','0.35');
 await page.locator('#mantle-cutaway').uncheck();await page.locator('#overlay-piles').uncheck();await page.locator('#overlay-piles').check();
 expect(requests.length).toBe(before);
 await page.locator('#info-toggle').click();
 await page.screenshot({path:'test-results/mantle-transparent.png',fullPage:true});
 await page.locator('#info-toggle').click();
 for(const age of [60,40,20,0]){await page.selectOption('#mantle-age',String(age));await ready(age);await expect(page.locator('#age')).toContainText(String(age));}
 console.log('Five source ages and transparency/cutaway controls passed');
 // Main timeline snaps to a source age, without loading crossed frames.
 const stops=JSON.parse(await page.locator('#globe-stops').textContent());
 const closest=age=>String(stops.reduce((best,s,i)=>Math.abs(s[3]-age)<Math.abs(stops[best][3]-age)?i:best,0));
 await page.locator('#timeline').fill(closest(31));await ready(40);
 await page.locator('#mantle-section-open').click();
 const popup=page.frameLocator('#collision-dialog iframe');
 await expect(popup.locator('body')).toHaveAttribute('data-age','40',{timeout:30000});
 await expect(popup.locator('#collision-linked-note')).toBeVisible();
 await expect(popup.locator('#collision-play')).toBeDisabled();
 await popup.locator('#collision-time').fill('3');await ready(20);
 await expect(popup.locator('body')).toHaveAttribute('data-age','20');
 await popup.locator('#collision-time').press('Escape');await expect(page.locator('#collision-dialog')).not.toBeVisible();
 console.log('Linked section and main age synchronization passed');
 await toggle.uncheck();await expect(page.locator('#timeline')).toHaveValue(initial);await expect(globe).toHaveAttribute('data-projection','equirect');
 await toggle.check();await ready(80);
 // Failed selected frame hides the old geometry, recovers without stale age.
 await page.route('**/mantle/assets/slabs-47-*',r=>r.fulfill({status:503}));
 await page.selectOption('#mantle-age','60');await expect(globe).toHaveAttribute('data-mantle-overlay','error');await expect(globe).toHaveAttribute('data-mantle-cutaway','false');
 await page.unroute('**/mantle/assets/slabs-47-*');await page.locator('#mantle-overlay-retry').click();await ready(60);
 const count=requests.length;
 await page.evaluate(()=>{const s=document.querySelector('#mantle-age');for(const a of ['0','20','80']){s.value=a;s.dispatchEvent(new Event('change'));}});
 await ready(80);expect(requests.length-count).toBe(2);
 await page.selectOption('#projection','mollweide');await expect(globe).toHaveAttribute('data-mantle-overlay','off');await expect(globe).toHaveAttribute('data-mantle-opacity','1');
 // Close while a request is pending; its eventual completion cannot restore a hole.
 await page.route('**/mantle/assets/*',async r=>{await new Promise(resolve=>setTimeout(resolve,700));await r.continue().catch(()=>{})});
 await toggle.check();await expect(globe).toHaveAttribute('data-mantle-overlay','loading');await toggle.uncheck();await page.waitForTimeout(900);
 await expect(globe).toHaveAttribute('data-mantle-overlay','off');await page.unroute('**/mantle/assets/*');
 await page.setViewportSize({width:390,height:844});await toggle.check();await ready(80);
 await expect(page.locator('#inspector')).toHaveClass(/closed/);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/mantle-multi-mobile.png',fullPage:true});
 await page.goto(new URL('/lang/en/?next=/',base).href);
 await expect(page.locator('#mantle-overlay-panel')).toContainText('Surface opacity');
 expect(errors).toEqual([]);
 console.log('Cancellation, failure/retry, projection restore, mobile and English passed');
} finally {await browser.close()}
