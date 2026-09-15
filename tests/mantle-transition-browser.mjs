import {chromium,expect} from '@playwright/test';
const browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
const gates=[];
const base=process.env.VIEWER_URL||'http://127.0.0.1:8151/';
try {
  const page=await browser.newPage({viewport:{width:1000,height:750},reducedMotion:'reduce'});
  page.setDefaultTimeout(30000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(new URL('/?masks=paleodem2018',base).href);
  const globe=page.locator('#globe'),canvas=page.locator('#globe canvas');
  // Sample the globe itself, clear of the loading caption and inspector overlays.
  const capture=async()=>{
    const box=await canvas.boundingBox();
    return page.screenshot({style:'#status { visibility: hidden !important; }',clip:{x:box.x+box.width*.42,y:box.y+box.height*.3,width:250,height:200}});
  };
  const ready=async age=>{
    await expect(globe).toHaveAttribute('data-mantle-overlay','ready',{timeout:30000});
    await expect(globe).toHaveAttribute('data-mantle-age',String(age));
  };
  await page.locator('#mantle-overlay').check();await ready(80);console.log('Initial overlay ready');
  await page.locator('#mantle-cutaway').focus();await page.keyboard.press('Space');
  await page.locator('#mantle-opacity').fill('35');
  for(const [button,from,to,index] of [['newer',80,60,'47'],['older',60,80,'46']]) {
    let releaseMesh,releaseSurface;
    const meshGate=new Promise(resolve=>{releaseMesh=resolve});
    const surfaceGate=new Promise(resolve=>{releaseSurface=resolve});
    await page.route(`**/mantle/assets/*-${index}-*`,async route=>{await meshGate;await route.continue().catch(()=>{})});
    const field=`**/globe/fields/paleodem-${String(to*10).padStart(4,'0')}.png`;
    await page.route(field,async route=>{await surfaceGate;await route.continue().catch(()=>{})});
    gates.push(releaseMesh,releaseSurface);
    const oldLabel=await page.locator('#globe-age').textContent();
    const before=await capture();console.log(button,'captured current globe');
    await page.locator(`#${button}`).click();
    await expect(globe).toHaveAttribute('data-mantle-overlay','loading');
    await expect(globe).toHaveAttribute('data-mantle-age',String(from));
    await expect(globe).toHaveAttribute('data-mantle-opacity','0.35');
    await expect(page.locator('#globe-age')).toHaveText(oldLabel);
    await page.waitForTimeout(300);
    expect((await capture()).equals(before)).toBe(true);console.log(button,'current globe retained');
    releaseSurface();
    await page.waitForTimeout(300);
    // Even when the surface is ready first, the previous complete globe remains.
    await expect(globe).toHaveAttribute('data-mantle-age',String(from));
    expect((await capture()).equals(before)).toBe(true);console.log(button,'current globe retained');
    releaseMesh();await ready(to);
    await expect(globe).toHaveAttribute('data-frame',`paleodem-${String(to*10).padStart(4,'0')}`);
    await expect(globe).toHaveAttribute('data-mantle-opacity','0.35');
    expect((await capture()).equals(before)).toBe(false);
    await page.unroute(`**/mantle/assets/*-${index}-*`);await page.unroute(field);
  }
  expect(errors).toEqual([]);
  console.log('Younger/Older retain identical rendered globe while loading, then replace surface and mantle together');
} catch(error) {console.error(error);throw error;} finally {for(const release of gates)release();await browser.close()}
