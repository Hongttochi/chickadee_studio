// Component integration driver: Chromium renders local UI, Python performs
// real scans over stdio. Native Electron dialogs/window launch are not tested.
const { chromium } = require("playwright");
const { Backend } = require("../electron/backend.cjs");
const fs = require("node:fs/promises");
const path = require("node:path");
const http = require("node:http");

exports.launch = async ({ env }) => {
  const root = path.resolve(__dirname, "../..");
  const data = env.CHICKADEE_TEST_DATA;
  const dist = path.join(root, "desktop/dist");
  await fs.mkdir(data, { recursive: true });
  let preferences = await fs
    .readFile(path.join(data, "preferences.json"), "utf8")
    .then(JSON.parse)
    .catch(() => ({}));
  let page,
    browser,
    closing = false,
    delivery = Promise.resolve();
  const outputRoot = path.join(data, "results");
  const dialog = {
    showSaveDialog: async () => ({ canceled: true }),
    showOpenDialog: async () => ({ canceled: true }),
  };
  const backend = new Backend(
    path.join(root, ".venv/Scripts/python.exe"),
    ["-m", "chickadee.bridge", "--data-dir", data],
    { cwd: root, env: { ...env, PYTHONIOENCODING: "utf-8" } },
    (event) => {
      if (!closing && page)
        delivery = delivery
          .then(() =>
            page.evaluate((value) => window.__sourceEvent?.(value), event),
          )
          .catch(() => {});
    },
  );
  const server = http.createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(
        new URL(request.url, "http://localhost").pathname,
      );
      const file = path.resolve(
        dist,
        "." + (pathname === "/" ? "/index.html" : pathname),
      );
      if (!file.startsWith(dist + path.sep)) throw new Error("outside root");
      const mime = {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".png": "image/png",
        ".woff2": "font/woff2",
      };
      response.writeHead(200, {
        "Content-Type": mime[path.extname(file)] || "application/octet-stream",
      });
      response.end(await fs.readFile(file));
    } catch {
      response.writeHead(404);
      response.end();
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  async function invoke(method, value) {
    if (method === "state")
      return {
        ...(await backend.request("state")),
        outputRoot,
        preferences,
        workflow: await fs
          .readFile(path.join(data, "workflow.json"), "utf8")
          .then(JSON.parse)
          .catch(() => null),
      };
    if (method === "start")
      return backend.request("start", { ...value, output_root: outputRoot });
    if (["stop", "pause", "resume", "capabilities"].includes(method))
      return backend.request(method);
    if (method === "history") {
      const state = await backend.request("state");
      const item = state.history.find((record) => record.id === value);
      if (!item) throw new Error("검사 기록이 없습니다.");
      return backend.request("load", { path: item.path });
    }
    if (method === "load") {
      const selected = await dialog.showOpenDialog();
      return selected.canceled
        ? null
        : backend.request("load", { path: selected.filePaths[0] });
    }
    if (method === "exportCSV") {
      const selected = await dialog.showSaveDialog();
      return selected.canceled
        ? null
        : backend.request("export", { path: selected.filePath });
    }
    if (method === "review")
      return backend.request("review", { ...value, actor: "human" });
    if (method === "preferences") {
      preferences = { ...preferences, ...value };
      await fs.writeFile(
        path.join(data, "preferences.json"),
        JSON.stringify(preferences),
      );
      return preferences;
    }
    if (method === "saveWorkflow") {
      await fs.writeFile(
        path.join(data, "workflow.json"),
        JSON.stringify(value),
      );
      return true;
    }
    throw new Error("통합 검사에서 지원하지 않는 네이티브 동작: " + method);
  }
  async function close() {
    closing = true;
    await backend.close();
    await delivery;
    if (browser) await browser.close();
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  }
  try {
    browser = await chromium.launch({
      executablePath: env.CHICKADEE_PREVIEW_CHROMIUM,
      headless: true,
    });
    page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    await page.route("**/*", (route) =>
      route
        .request()
        .url()
        .startsWith(origin + "/")
        ? route.continue()
        : route.abort(),
    );
    await page.exposeBinding("__sourceInvoke", (_source, method, value) =>
      invoke(method, value),
    );
    await page.addInitScript(() => {
      window.chickadee = Object.fromEntries(
        [
          "state",
          "start",
          "pause",
          "resume",
          "stop",
          "capabilities",
          "preferences",
          "history",
          "load",
          "exportCSV",
          "review",
          "saveWorkflow",
          "exportWorkflow",
          "loadWorkflow",
          "copy",
          "openFolder",
          "chooseFolder",
        ].map((method) => [
          method,
          (value) => window.__sourceInvoke(method, value),
        ]),
      );
      window.chickadee.onEvent = (callback) => {
        window.__sourceEvent = callback;
        return () => {
          window.__sourceEvent = null;
        };
      };
    });
    await page.goto(origin);
    return {
      firstWindow: async () => page,
      evaluate: async (callback, value) => callback({ dialog }, value),
      close,
    };
  } catch (error) {
    await close();
    throw error;
  }
};
