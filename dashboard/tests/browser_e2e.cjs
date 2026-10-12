/* Run against a local server or the published dashboard:
   BIST_E2E_URL=http://127.0.0.1:8766/ node dashboard/tests/browser_e2e.cjs
   Needs Playwright + Chromium. No fake data or successful skip on missing browser. */
'use strict';
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const ctx=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const page=await ctx.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.BIST_E2E_URL||'http://127.0.0.1:8766/');
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Hazır'));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'mobile page must not overflow');
  assert.equal(await page.locator('#installApp').isVisible(),true);
  await page.locator('#quickRun').click();
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Run sunucu'));
  const count=await page.locator('.research-card').count();
  const published=await page.evaluate(async()=>{const r=await fetch('data/latest.json',{cache:'no-store'});return r.json()});
  const api=require('../research.js');
  assert.equal(count,api.scan(published,{mode:'value',margin:20}).length);
  await page.locator('#quickMode').selectOption('all');
  await page.locator('#quickRun').click();
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Tüm doğrulanmış hisseler:'));
  assert.equal(await page.locator('.research-card').count(),api.scan(published,{mode:'all',margin:20}).length);
  await page.evaluate(()=>navigator.serviceWorker.ready);
  await page.reload();
  await page.waitForFunction(()=>navigator.serviceWorker.controller!==null);
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Hazır'));
  const cache=await page.evaluate(async()=>{const all=[];for(const name of await caches.keys())for(const req of await(await caches.open(name)).keys())all.push(req.url);return all});
  assert(cache.length>0,'static assets should be installed');
  assert(!cache.some(x=>x.includes('/data/')),'financial data must never be cached');
  await ctx.setOffline(true);
  await page.waitForFunction(()=>document.querySelector('#banner').textContent.includes('ÇEVRİMDIŞI'));
  await page.locator('#quickRun').click();
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Tarama yapılamadı'));
  assert.equal(await page.locator('.research-card').count(),0);
  await page.reload();
  assert.match(await page.locator('body').innerText(),/İnternet bağlantısı gerekli/);
  await ctx.setOffline(false);
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#quickStatus').textContent.includes('Hazır'));
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'PASS',mobile_width:390,value_matches:count,cache_assets:cache.length,offline_navigation:true,online_recovery:true}));
 } finally { await browser.close() }
})().catch(error=>{console.error(error);process.exitCode=1});
