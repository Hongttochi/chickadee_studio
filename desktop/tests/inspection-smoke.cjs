// Actual renderer + Python bridge + localhost fixture. No paid API requests.
const packaged = Boolean(process.env.CHICKADEE_PACKAGED_EXE);
const launch = packaged ? (options) => require("playwright")._electron.launch(options) : require("./source-ui-harness.cjs").launch;
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const http = require("node:http");

(async () => {
  const root = path.resolve(__dirname, "../..");
  const data = path.join(root, "artifacts", "inspection-ui-" + Date.now());
  let revision = 0;
  const server = http.createServer((request, response) => {
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    response.end(request.url === "/" ? '<a href="/post">게시글</a>' :
      `<article id="post" style="opacity:${revision ? 0 : 1}"><p>카지노 가입 보너스 ${revision}</p><a href="https://example.invalid/${revision}">주소</a></article>`);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const env = { ...process.env, CHICKADEE_TEST_DATA: data };
  let app;
  try {
    app = await launch({ env, ...(packaged ? { executablePath: process.env.CHICKADEE_PACKAGED_EXE, args: [] } : {}) });
    const page = await app.firstWindow();
    page.setDefaultTimeout(15000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.getByRole("dialog", { name: "사용 가이드" }).getByRole("button", { name: "사용 가이드 닫기", exact: true }).click();
    await page.locator(".header-run-controls button.primary:not(:disabled)").waitFor();
    await page.locator('.react-flow__node[data-id="target"]').click();
    await page.getByRole("textbox", { name: "검사 대상 URL" }).fill(`http://127.0.0.1:${server.address().port}/`);
    await page.getByRole("button", { name: "검사 분석", exact: true }).click();
    async function wait(count) {
      await page.waitForFunction(async (n) => {
        const state = await window.chickadee.state();
        return !state.running && state.history.length === n;
      }, count);
      await page.waitForFunction(() => document.querySelectorAll('.inspection-graph .react-flow__node').length >= 4);
      return page.evaluate(() => window.chickadee.state());
    }
    await page.locator(".header-run-controls button.primary").click();
    await wait(1);
    const firstGraph = await page.locator('.inspection-graph .react-flow__node').count();
    assert.ok(firstGraph >= 4);
    revision = 1;
    await page.locator(".header-run-controls button.primary").click();
    let current = await wait(2);
    await page.getByRole('tab', { name: '변경 비교', exact: true }).click();
    await page.locator('.inspection-changes article').first().waitFor();
    assert.ok((await page.locator('.inspection-changes').innerText()).includes('카지노 가입 보너스 0'));
    assert.ok((await page.locator('.inspection-changes').innerText()).includes('카지노 가입 보너스 1'));
    current = await page.evaluate(() => window.chickadee.state());
    assert.equal(current.history.length, 2);
    await page.getByLabel('비교 기준', { exact: true }).selectOption(current.history[1].id);
    await page.getByRole('button', { name: '비교', exact: true }).click();
    const result = current.history[0].path;
    const raw = await fs.readFile(result);
    const comparison = JSON.parse(await fs.readFile(path.join(path.dirname(result), 'comparison.json'), 'utf8'));
    assert.ok(comparison.counts.changed >= 1);
    await page.screenshot({ path: path.join(root, 'artifacts/inspection-comparison.png') });
    await page.getByRole('tab', { name: 'Groq 검토', exact: true }).click();
    await page.getByLabel('Groq API 키', { exact: true }).fill('test_key_not_real');
    await page.getByLabel('Groq 토큰 한도', { exact: true }).fill('1000');
    await page.getByRole('button', { name: '설정 적용', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('input[aria-label="Groq API 키"]').value === '');
    const insight = await page.evaluate(async () => {
      const state = await window.chickadee.state();
      return window.chickadee.inspection({ run_id: state.run_id });
    });
    await page.getByLabel('검토 영역', { exact: true }).selectOption(insight.packets.find((p) => p.text.includes('카지노')).id);
    await page.getByRole('button', { name: 'Groq 분석', exact: true }).click();
    await page.getByRole('status').filter({ hasText: '한도' }).waitFor();
    const stored = await fs.readFile(path.join(path.dirname(result), 'agent.json'), 'utf8');
    assert.ok(!stored.includes('test_key_not_real'));
    assert.equal(JSON.parse(stored).ledger.calls, 0);
    assert.deepEqual(await fs.readFile(result), raw);
    await page.getByRole('button', { name: '검사 기록', exact: true }).click();
    await page.locator('tbody tr').first().click();
    await page.getByRole('button', { name: '검사 분석', exact: true }).click();
    await page.getByRole('tab', { name: '변경 비교', exact: true }).click();
    await page.locator('.inspection-changes article').first().waitFor();
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log(JSON.stringify({ status: 'passed', mode: packaged ? 'electron-packaged' : 'source-ui-real-python', explorationGraph: true,
      textStyleLinkComparison: true, comparisonReload: true, groqConfiguration: true,
      budgetBlockedBeforeNetwork: true, immutableResult: true, secretNotPersisted: true, data }));
  } finally {
    if (app) await app.close();
    server.closeAllConnections(); await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
