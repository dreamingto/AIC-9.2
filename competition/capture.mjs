// Real Chrome artifact rendering and optional narrated live browser recording.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('@playwright/test');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'output/competition');
const videoMode = process.argv.includes('--video');
const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8088';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const context = await browser.newContext({ viewport: { width:1280, height:720 }, ...(videoMode ? { recordVideo: {dir:path.join(out,'recording'),size:{width:1280,height:720}} } : {}) });
const page = await context.newPage();
const deckURL = pathToFileURL(path.join(out,'答辩幻灯片.html')).href;
const errors = [];
page.on('pageerror', error => errors.push(error.message));
if (!videoMode) {
  await page.goto(deckURL);
  await page.waitForFunction(() => document.querySelector('.deck > .slide.is-active'));
  fs.mkdirSync(path.join(out,'frames'),{recursive:true});
  for(let i=0;i<8;i++) {
    await page.goto(deckURL+'#/'+(i+1));
    await page.waitForTimeout(650);
    const bounds = await page.locator('.deck > .slide.is-active').evaluate(el=>({width:el.scrollWidth,height:el.scrollHeight}));
    if(bounds.width>1280 || bounds.height>720) throw new Error(`slide overflow: ${i+1}`);
    await page.screenshot({path:path.join(out,'frames',`slide-${i+1}.png`)});
  }
  await page.emulateMedia({media:'print'});
  await page.pdf({path:path.join(out,'机图索隐_答辩幻灯片.pdf'),preferCSSPageSize:true,printBackground:true});
  await page.emulateMedia({media:'screen'});
  await page.goto(baseURL+'/demo');
  await page.getByRole('heading',{name:'国内古籍固定演示案例'}).waitFor();
  await page.screenshot({path:path.join(out,'frames','app-demo.png'),fullPage:true});
  const article=page.getByRole('article').filter({hasText:'《天工开物》：水碓与水磨'});
  const response=page.waitForResponse(r=>r.url().endsWith('/search')&&r.request().method()==='POST');
  await article.getByRole('button',{name:'运行区域检索'}).click();
  const actual=await response;
  if(!actual.ok()) throw new Error(await actual.text());
  const result=await actual.json();
  fs.writeFileSync(path.join(out,'live-demo-response.json'),JSON.stringify(result,null,2));
  await page.getByRole('region',{name:'真实检索结果'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,'frames','app-results.png')});
  await page.goto(baseURL+'/compare/'+result.results[0].candidate_id);
  await page.getByRole('heading').first().waitFor();
  await page.waitForTimeout(900);
  await page.screenshot({path:path.join(out,'frames','app-compare.png'),fullPage:true});
} else {
  const durations=JSON.parse(fs.readFileSync(path.join(out,'audio','durations.json'),'utf8'));
  for(let i=0;i<8;i++) {
    const start=Date.now();
    await page.goto(deckURL+'#/'+(i+1));
    if(i===4 || i===5) {
      await page.waitForTimeout(2500);
      await page.goto(baseURL+'/demo');
      const article=page.getByRole('article').filter({hasText:i===4?'《耕织图》：织机与经线':'《天工开物》：水碓与水磨'});
      await article.scrollIntoViewIfNeeded();
      await page.waitForTimeout(3500);
      const response=page.waitForResponse(r=>r.url().endsWith('/search')&&r.request().method()==='POST');
      await article.getByRole('button',{name:i===4?'运行文本检索':'运行区域检索'}).click();
      const actual=await response;
      if(!actual.ok()) throw new Error(await actual.text());
      const data=await actual.json();
      await page.getByRole('region',{name:'真实检索结果'}).scrollIntoViewIfNeeded();
      await page.waitForTimeout(5000);
      await page.goto(baseURL+'/compare/'+data.results[0].candidate_id);
      await page.waitForTimeout(1000);
      await page.waitForTimeout(4000);
      await page.getByRole('heading',{name:/匹配得分与组件贡献/}).scrollIntoViewIfNeeded();
    }
    const remaining=durations[i]*1000-(Date.now()-start);
    if(remaining<0) throw new Error('live demonstration took longer than narration slot');
    await page.waitForTimeout(remaining);
    console.log(`recorded slide ${i+1}/8`);
  }
}
if(errors.length) throw new Error(errors.join('\n'));
await context.close();
if(videoMode) console.log('recording='+await page.video().path());
await browser.close();
