const { _electron: electron } = require("playwright");
const path = require("node:path");
const fs = require("node:fs/promises");
const assert = require("node:assert/strict");

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
  const app = await electron.launch({
    executablePath: executable,
    args,
    env,
    timeout: 45000,
  });
  try {
    const page = await app.firstWindow();
    page.setDefaultTimeout(15000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page
      .locator(".engine-indicator strong")
      .filter({ hasText: "검사 준비" })
      .waitFor({ timeout: 30000 });
    assert.equal(await page.locator(".react-flow__node").count(), 6);
    assert.ok(
      await page.evaluate(() => document.fonts.check("600 14px Pretendard")),
    );
    assert.equal(await page.locator(".brand-mark img").count(), 1);
    await page.screenshot({
      path: path.join(artifacts, "electron-workflow-empty.png"),
    });
    await page.getByRole("button", { name: "데모 검사", exact: true }).click();
    await page
      .locator(".statusbar>span:first-child")
      .filter({ hasText: "검사 완료" })
      .waitFor({ timeout: 90000 });
    await page.locator(".preview-image img").waitFor();
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
    assert.ok(
      (await page.locator(".canvas-footer").innerText()).includes(
        "필수 탐지 OFF",
      ),
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
    console.log(
      JSON.stringify({
        status: "passed",
        findings: 14,
        pages: 4,
        preview: true,
        csv: true,
        disconnectReconnect: true,
        data,
      }),
    );
  } finally {
    await app.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
