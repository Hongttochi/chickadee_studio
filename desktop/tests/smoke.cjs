const { _electron: electron } = require("playwright");
const path = require("node:path");
const fs = require("node:fs/promises");
const assert = require("node:assert/strict");
const http = require("node:http");
const launch =
  process.env.CHICKADEE_SERVICE_UI === "1"
    ? require("./source-ui-harness.cjs").launch
    : (options) => electron.launch(options);
async function waitForHistory(page, count) {
  const deadline = Date.now() + 30000;
  let state;
  while (Date.now() < deadline) {
    state = await page.evaluate(() => window.chickadee.state());
    if (!state.running && state.history.length === count) return state;
    if (state.status === "failed")
      throw new Error("검사 실패: " + JSON.stringify(state));
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error("검사 완료 대기 실패: " + JSON.stringify(state));
}

(async () => {
  const root = path.resolve(__dirname, "../..");
  const artifacts = path.join(root, "artifacts");
  const data = path.join(artifacts, "electron-test-" + Date.now());
  const executable = process.env.CHICKADEE_PACKAGED_EXE || require("electron");
  const args = process.env.CHICKADEE_PACKAGED_EXE
    ? []
    : [path.join(root, "desktop")];
  const env = { ...process.env, CHICKADEE_TEST_DATA: data };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await launch({
    executablePath: executable,
    args,
    env,
    timeout: 45000,
  });
  let server;
  let passed = false;
  try {
    const page = await app.firstWindow();
    page.setDefaultTimeout(15000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page
      .locator(".target-bar button.primary:not(:disabled)")
      .waitFor({ timeout: 30000 });
    assert.equal(
      await page
        .locator(
          ".engine-indicator,.heading .eyebrow,.canvas-footer,.flow-caption,.statusbar",
        )
        .count(),
      0,
    );
    assert.equal(await page.locator(".react-flow__node").count(), 6);
    assert.ok(
      await page.evaluate(() => document.fonts.check("600 14px Pretendard")),
    );
    assert.equal(await page.locator(".brand-mark img").count(), 1);
    await page.screenshot({
      path: path.join(artifacts, "electron-workflow-empty.png"),
    });
    await page.keyboard.press("Control+k");
    await page.getByRole("dialog", { name: "빠른 명령" }).waitFor();
    await page.getByRole("textbox", { name: "명령 검색" }).fill("설정");
    await page.keyboard.press("Enter");
    await page.getByLabel("최대 페이지", { exact: true }).fill("20");
    await page.getByRole("button", { name: "완료", exact: true }).click();
    await page.getByRole("button", { name: "검사 옵션", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "데모 검사", exact: true })
      .click();
    await page.getByRole("button", { name: "일시정지", exact: true }).click();
    await page
      .getByRole("button", { name: "검사 재개", exact: true })
      .waitFor({ timeout: 30000 });
    await page.screenshot({
      path: path.join(artifacts, "electron-paused.png"),
    });
    await page.getByRole("button", { name: "검사 재개", exact: true }).click();
    await page
      .locator(".scan-status strong")
      .filter({ hasText: "검사 완료" })
      .waitFor({ timeout: 90000 });
    await page.locator(".preview-image img").waitFor();
    const firstPreview = await page
      .locator(".preview-image img")
      .getAttribute("src");
    const firstPreviewUrl = await page
      .locator(".browser-chrome span[title]")
      .getAttribute("title");
    const firstRun = await page.evaluate(() => window.chickadee.state());
    const firstResultPath = firstRun.history[0].path;
    await page.getByRole("button", { name: "화면 확대" }).click();
    await page.getByRole("dialog", { name: "검사 화면" }).waitFor();
    assert.equal(
      await page.getByAltText("검사 화면 확대").getAttribute("src"),
      firstPreview,
    );
    assert.ok(
      (await page.locator(".preview-modal").innerText()).includes(
        firstPreviewUrl,
      ),
    );
    await page.getByRole("button", { name: "미리보기 닫기" }).click();
    assert.equal(
      await page
        .locator(".summary-numbers")
        .innerText()
        .then((text) => text.includes("14")),
      true,
    );
    await page.screenshot({
      path: path.join(artifacts, "electron-workflow.png"),
    });
    await page.getByRole("button", { name: /^탐지 내역/ }).click();
    assert.equal(await page.locator("tbody tr").count(), 14);
    await page.locator("tbody tr").first().click();
    await page
      .getByRole("textbox", { name: "검토 메모" })
      .fill("문자 변형과 원문 확인 · 통합 검사");
    await page.getByRole("button", { name: "검토 확인", exact: true }).click();
    await page
      .getByRole("status")
      .filter({ hasText: "1건 검토 저장" })
      .waitFor();
    await page
      .getByRole("combobox", { name: "검토 상태 필터" })
      .selectOption("unreviewed");
    assert.equal(await page.locator("tbody tr").count(), 13);
    await page.getByRole("checkbox", { name: "표시 항목 전체 선택" }).check();
    await page
      .locator(".bulk-toolbar")
      .getByRole("button", { name: "검토 제외", exact: true })
      .click();
    await page
      .getByRole("status")
      .filter({ hasText: "13건 검토 저장" })
      .waitFor();
    assert.equal(await page.locator("tbody tr").count(), 0);
    await page
      .getByRole("combobox", { name: "검토 상태 필터" })
      .selectOption("all");
    await page.getByRole("button", { name: "검사 기록", exact: true }).click();
    await page.locator("tbody tr").first().click();
    await page.locator("tbody tr .review-confirmed").first().waitFor();
    assert.equal(await page.locator("tbody tr .review-confirmed").count(), 1);
    assert.equal(await page.locator("tbody tr .review-dismissed").count(), 13);
    await page.locator("tbody tr").first().click();
    assert.equal(
      await page.getByRole("textbox", { name: "검토 메모" }).inputValue(),
      "문자 변형과 원문 확인 · 통합 검사",
    );
    await page.screenshot({
      path: path.join(artifacts, "electron-results.png"),
    });
    const csv = path.join(data, "export-test.csv");
    await app.evaluate(({ dialog }, filePath) => {
      dialog.showSaveDialog = async () => ({ canceled: false, filePath });
    }, csv);
    await page.getByRole("button", { name: "CSV 저장", exact: true }).click();
    await page
      .getByRole("status")
      .filter({ hasText: "CSV를 저장했습니다" })
      .waitFor();
    const bytes = await fs.readFile(csv);
    assert.ok(bytes.subarray(0, 3).equals(Buffer.from([239, 187, 191])));
    await page.getByRole("button", { name: "탐색 경로", exact: true }).click();
    assert.equal(await page.locator("tbody tr").count(), 4);
    await page.getByRole("button", { name: "진행 기록", exact: true }).click();
    await page.screenshot({
      path: path.join(artifacts, "electron-activity.png"),
    });
    assert.ok(
      (await page.locator(".full-timeline").innerText()).includes("DOM"),
    );
    await page.getByRole("button", { name: "검사 구성", exact: true }).click();
    const edge = page.locator('[data-testid="rf__edge-techniques-report"]');
    await edge.dispatchEvent("click");
    await page.keyboard.press("Delete");
    await page.waitForFunction(
      () => document.querySelectorAll(".react-flow__edge").length === 5,
    );
    assert.equal(
      await page
        .locator('.react-flow__node[data-id="techniques"] .flow-node.disabled')
        .count(),
      1,
    );
    const source = await page
      .locator(
        '.react-flow__node[data-id="techniques"] .react-flow__handle-right',
      )
      .boundingBox();
    const target = await page
      .locator('.react-flow__node[data-id="report"] .react-flow__handle-left')
      .boundingBox();
    await page.mouse.move(
      source.x + source.width / 2,
      source.y + source.height / 2,
    );
    await page.mouse.down();
    await page.waitForTimeout(100);
    await page.mouse.move(
      target.x + target.width / 2,
      target.y + target.height / 2,
      { steps: 20 },
    );
    await page.waitForTimeout(150);
    await page.screenshot({
      path: path.join(artifacts, "electron-connecting.png"),
    });
    await page.mouse.up();
    await page.waitForFunction(
      () => document.querySelectorAll(".react-flow__edge").length === 6,
    );
    await page.getByRole("button", { name: "구성 저장", exact: true }).click();
    await page
      .getByRole("status")
      .filter({ hasText: "구성 저장 완료" })
      .waitFor();
    assert.equal(errors.length, 0, errors.join("\n"));
    // Owned loopback fixture: verify the real single-page action and recheck.
    server = http.createServer((_request, response) => {
      response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      response.end(
        '<!doctype html><html lang="ko"><title>단일 페이지 검사</title><body><p style="opacity:0">카지노 가입 보너스 지급</p><a href="/other">다음 글</a></body></html>',
      );
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const fixtureUrl = `http://127.0.0.1:${server.address().port}/first`;
    await page.getByRole("textbox", { name: "검사 대상 URL" }).fill(fixtureUrl);
    await page.getByRole("button", { name: "검사 옵션", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "이 페이지만 검사", exact: true })
      .click();
    await waitForHistory(page, 2);
    const onePage = await page.evaluate(() => window.chickadee.state());
    const oneReport = JSON.parse(
      await fs.readFile(
        path.join(path.dirname(onePage.history[0].path), "scan-report.json"),
        "utf8",
      ),
    );
    assert.equal(oneReport.pages_scanned.length, 1);
    assert.equal(oneReport.enabled_stages.follow_links, false);
    await page.getByRole("button", { name: /^탐지 내역/ }).click();
    await page.locator("tbody tr").first().click();
    await page.getByRole("button", { name: "항목 작업", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "이 페이지만 재검사", exact: true })
      .click();
    await waitForHistory(page, 3);
    const rechecked = await page.evaluate(() => window.chickadee.state());
    assert.equal(rechecked.history[0].url, fixtureUrl);
    assert.equal(rechecked.history[0].pages, 1);
    const preferences = JSON.parse(
      await fs.readFile(path.join(data, "preferences.json"), "utf8"),
    );
    assert.equal(preferences.maxPages, 20);
    assert.equal(preferences.url, fixtureUrl);
    // A run without preview must not inherit the preceding run's image.
    await page.getByRole("button", { name: "검사 설정", exact: true }).click();
    await page.getByLabel("실시간 브라우저 화면", { exact: false }).uncheck();
    await page.getByRole("button", { name: "완료", exact: true }).click();
    await page.getByRole("button", { name: "검사 옵션", exact: true }).click();
    await page
      .getByRole("menuitem", { name: "데모 검사", exact: true })
      .click();
    await waitForHistory(page, 4);
    assert.equal(await page.locator(".preview-image img").count(), 0);
    // Reopen an older run and restore its exact screenshot, URL and review.
    await page.getByRole("button", { name: "검사 기록", exact: true }).click();
    await page.locator("tbody tr").last().click();
    await page.locator("tbody tr .review-confirmed").first().waitFor();
    await page
      .getByRole("textbox", { name: "결과 검색" })
      .fill("없는 검색어 · filter reset");
    await page.getByRole("button", { name: "검사 구성", exact: true }).click();
    await page.locator('.react-flow__node[data-id="collector"]').click();
    await page.locator(".node-config").waitFor();
    await app.evaluate(({ dialog }, resultPath) => {
      dialog.showOpenDialog = async () => ({
        canceled: false,
        filePaths: [resultPath],
      });
    }, firstResultPath);
    await page
      .getByRole("button", { name: "결과 불러오기", exact: true })
      .click();
    await page.locator("tbody tr").first().waitFor();
    assert.equal(
      await page.getByRole("textbox", { name: "결과 검색" }).inputValue(),
      "",
    );
    assert.equal(await page.locator("tbody tr").count(), 14);
    await page.getByRole("button", { name: "검사 구성", exact: true }).click();
    await page.locator(".preview-image img").waitFor();
    assert.equal(await page.locator(".node-config").count(), 0);
    assert.equal(
      await page.locator(".preview-image img").getAttribute("src"),
      firstPreview,
    );
    assert.equal(
      await page.locator(".browser-chrome span[title]").getAttribute("title"),
      firstPreviewUrl,
    );
    await page.screenshot({
      path: path.join(artifacts, "studio-clean-workflow.png"),
    });
    await page.getByRole("button", { name: "진행 기록", exact: true }).click();
    await page.getByRole("button", { name: "HTTP 통신", exact: true }).click();
    assert.ok((await page.locator(".full-timeline .event-row").count()) > 0);
    await page.locator(".full-timeline .event-row").first().click();
    await page.locator(".event-modal").waitFor();
    assert.ok(
      (await page.locator(".event-modal pre").innerText()).includes(
        "http_response",
      ),
    );
    await page.locator(".event-modal .modal-heading > button").click();
    assert.equal(errors.length, 0, errors.join("\n"));
    passed = true;
    console.log(
      JSON.stringify({
        status: "passed",
        findings: 14,
        pages: 4,
        preview: true,
        previewZoom: true,
        previewReloadExact: true,
        previewOffClearsImage: true,
        resultImportResetsFilters: true,
        savedNetworkEvents: true,
        csv: true,
        disconnectReconnect: true,
        pauseResume: true,
        reviewReload: true,
        bulkReview: true,
        commandPalette: true,
        singlePageRecheck: true,
        preferencesPersisted: true,
        mode:
          process.env.CHICKADEE_SERVICE_UI === "1"
            ? "source-ui-real-python"
            : "electron",
        data,
      }),
    );
  } finally {
    await app.close();
    if (server) {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
  }
  if (passed) {
    const restarted = await launch({
      executablePath: executable,
      args,
      env,
      timeout: 45000,
    });
    try {
      const page = await restarted.firstWindow();
      await page
        .locator(".target-bar button.primary:not(:disabled)")
        .waitFor({ timeout: 30000 });
      const prefs = JSON.parse(
        await fs.readFile(path.join(data, "preferences.json"), "utf8"),
      );
      assert.equal(
        await page.getByRole("textbox", { name: "검사 대상 URL" }).inputValue(),
        prefs.url,
      );
      console.log(JSON.stringify({ restartPreferences: "passed" }));
    } finally {
      await restarted.close();
    }
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
