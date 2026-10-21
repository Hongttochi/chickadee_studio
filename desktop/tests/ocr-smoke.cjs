// Real renderer, scanner and official Korean PaddleOCR model. No paid API.
const packaged = Boolean(process.env.CHICKADEE_PACKAGED_EXE);
const launch = packaged ? options => require('playwright')._electron.launch(options) : require('./source-ui-harness.cjs').launch;
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');

(async () => {
  const root = path.resolve(__dirname, '../..');
  const data = path.join(root, 'artifacts', 'ocr-ui-' + Date.now());
  const banner = await fs.readFile(path.join(root, 'tests/fixtures/ocr/promotion.png'));
  let requests = 0, app;
  const server = http.createServer((request, response) => {
    requests++;
    response.writeHead(200, { 'Content-Type': request.url === '/banner.png' ? 'image/png' : 'text/html; charset=utf-8' });
    response.end(request.url === '/banner.png' ? banner : '<!doctype html><meta charset="utf-8"><article><img src="/banner.png"></article>');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    app = await launch({ env: { ...process.env, CHICKADEE_TEST_DATA: data }, ...(packaged ? { executablePath: process.env.CHICKADEE_PACKAGED_EXE, args: [] } : {}) });
    const page = await app.firstWindow();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.setDefaultTimeout(20000);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('button', { name: '사용 가이드 닫기', exact: true }).click();
    await page.locator('.header-run-controls button.primary:not(:disabled)').waitFor();
    await page.locator('.react-flow__node[data-id="target"]').click();
    await page.getByRole('textbox', { name: '검사 대상 URL' }).fill(`http://127.0.0.1:${server.address().port}/`);
    await page.locator('.header-run-controls button.primary').click();
    let state;
    const deadline = Date.now() + 90000;
    do {
      state = await page.evaluate(() => window.chickadee.state());
      if (!state.running && state.history.length === 1) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    } while (Date.now() < deadline);
    assert.equal(state.history.length, 1, JSON.stringify(state));
    assert.equal(state.running, false);
    const resultPath = state.history[0].path;
    const report = JSON.parse(await fs.readFile(path.join(path.dirname(resultPath), 'scan-report.json'), 'utf8'));
    assert.equal(report.status, 'completed', JSON.stringify(report.errors));
    assert.equal(report.ocr_summary.completed, 1);
    assert.equal(report.ad_candidates[0].source_kind, 'image_ocr');
    assert.ok(report.ad_candidates[0].evidence_text.includes('카지노'));
    assert.equal(JSON.parse(await fs.readFile(resultPath, 'utf8')).findings.length, 0);
    const image = report.ocr_images[0];
    assert.equal(image.width, 900);
    assert.equal(image.lines.length, 2);
    await fs.access(path.join(path.dirname(resultPath), image.relative_path));
    await page.getByRole('button', { name: /^광고 의심/ }).first().click();
    await page.locator('tbody tr .evidence-cell').first().click();
    await page.getByAltText('OCR로 검사한 게시글 이미지', { exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('.image-ocr-preview img')?.naturalWidth > 0);
    // Load completion may replace the live selected row. Select the saved row.
    await page.locator('tbody tr .evidence-cell').first().click();
    await page.locator('.record-drawer[aria-hidden="false"]').waitFor();
    const section = page.getByRole('region', { name: '이미지 OCR 근거', exact: true });
    assert.equal(await section.locator('polygon').count(), 2);
    await section.locator('.image-ocr-lines button').first().click();
    assert.equal(await section.locator('polygon.selected').count(), 1);
    await page.screenshot({ path: path.join(root, 'artifacts/ocr-evidence-panel.png') });
    const count = requests;
    await page.getByRole('button', { name: '검사 기록', exact: true }).click();
    await page.locator('tbody tr').first().click();
    await page.getByRole('button', { name: /^광고 의심/ }).first().click();
    await page.locator('tbody tr .evidence-cell').first().click();
    await page.getByAltText('OCR로 검사한 게시글 이미지', { exact: true }).waitFor();
    assert.equal(requests, count, 'History reload must not revisit the site');
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log(JSON.stringify({ status: 'passed', mode: packaged ? 'electron-packaged' : 'source-ui-real-python', koreanImageText: true, boxes: true, historyReload: true, paidCalls: 0, resultPath }));
  } finally {
    if (app) await app.close();
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
