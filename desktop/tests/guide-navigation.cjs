// Current guide navigation and layout against the real renderer; no scans or API calls.
const assert = require('node:assert/strict');
const path = require('node:path');
const { launch } = require('./source-ui-harness.cjs');
(async () => {
 const app = await launch({env:{...process.env,CHICKADEE_TEST_DATA:path.resolve(__dirname,'../../artifacts/guide-navigation-'+Date.now())}});
 try {
  const page=await app.firstWindow();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.emulateMedia({reducedMotion:'reduce'});
  const guide=page.getByRole('dialog',{name:'사용 가이드',exact:true});
  await guide.waitFor();
  const {guideSteps}=await import('../src/guide-content.mjs');
  for(const size of [{width:1280,height:800},{width:720,height:600},{width:390,height:650}]) {
   await page.setViewportSize(size);
   for(const [index,step] of guideSteps.entries()) {
    await guide.getByRole('button',{name:`${index+1}단계: ${step.label}`,exact:true}).click();
    await page.waitForFunction(()=>{const i=document.querySelector('.tutorial-screen img');return i?.complete && i.naturalWidth>0;});
    assert.equal(await guide.locator('h3').innerText(),step.title);
    assert.equal(await guide.locator('.tutorial-instructions > div').count(),step.instructions.length);
    const bounds=await guide.evaluate(el=>({scroll:el.scrollWidth,width:el.clientWidth,footer:el.querySelector('footer').getBoundingClientRect().bottom}));
    assert.ok(bounds.scroll<=bounds.width+1,'Guide must not overflow horizontally');
    assert.ok(bounds.footer<=size.height,'Footer remains reachable');
    assert.equal(await guide.locator('.tutorial-content').evaluate(el=>el.scrollTop),0);
   }
  }
  await page.setViewportSize({width:1280,height:800});
  await guide.getByRole('button',{name:'2단계: 구성·OCR',exact:true}).click();
  await guide.getByRole('button',{name:'화면 크게 보기',exact:true}).click();
  await page.getByRole('dialog',{name:'가이드 화면 확대',exact:true}).waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.tutorial-image-dialog').count(),0);
  assert.equal(await guide.count(),1);
  await page.screenshot({path:path.resolve(__dirname,'../../artifacts/guide-desktop.png')});
  await page.setViewportSize({width:390,height:650});
  await page.screenshot({path:path.resolve(__dirname,'../../artifacts/guide-small.png')});
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.tutorial-dialog').count(),0);
  await page.setViewportSize({width:1280,height:800});
  await page.getByRole('button',{name:'설정',exact:true}).click();
  await page.getByRole('button',{name:'사용 가이드',exact:true}).click();
  await guide.waitFor();
  assert.equal(await guide.getByRole('button',{name:'1단계: 검사 시작',exact:true}).getAttribute('aria-current'),'step');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({guideTopics:guideSteps.length,viewports:3,screenshots:true,zoomEscape:true,reopen:true,status:'passed'}));
 } finally {await app.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
