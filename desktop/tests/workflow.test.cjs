const { test } = require("node:test");
const assert = require("node:assert/strict");
test("saved disconnected workflows restore the fixed pipeline", async () => {
  const { defaultWorkflow, normalizeWorkflow, branchEnabled } = await import("../src/workflow.mjs");
  const flow = defaultWorkflow();
  flow.edges = [];
  flow.ocr_enabled = false;
  const restored = normalizeWorkflow(flow);
  assert.deepEqual(restored.edges, defaultWorkflow().edges);
  assert.equal(branchEnabled(restored, "techniques"), true);
  assert.equal(branchEnabled(restored, "candidates"), true);
  assert.equal(branchEnabled(restored, "ocr"), false);
});
test("unknown and duplicated nodes or connections cannot become executable workflows", async () => {
  const { defaultWorkflow, normalizeWorkflow } =
    await import("../src/workflow.mjs");
  const bad = defaultWorkflow();
  bad.edges.push({ source: "target", target: "report" });
  assert.throws(() => normalizeWorkflow(bad));
  const duplicate = defaultWorkflow();
  duplicate.nodes[1].id = "target";
  assert.throws(() => normalizeWorkflow(duplicate));
});
test("OCR migrates legacy workflows and follows only its switch", async () => {
  const { defaultWorkflow, normalizeWorkflow, branchEnabled } = await import('../src/workflow.mjs');
  const legacy = defaultWorkflow();
  legacy.version = 1;
  legacy.nodes = legacy.nodes.filter(n => n.id !== "dedup");
  legacy.edges = legacy.edges.filter(e => e.source !== "dedup" && !(e.source === "ocr" && e.target === "techniques")).map(e => e.target === "dedup" ? { ...e, target: "report" } : e);
  legacy.nodes = legacy.nodes.filter(n => n.id !== 'ocr');
  legacy.edges = legacy.edges.filter(e => e.source !== 'ocr' && e.target !== 'ocr');
  delete legacy.ocr_enabled;
  const flow = normalizeWorkflow(legacy);
  assert.equal(flow.nodes.length, 8);
  assert.equal(branchEnabled(flow, 'ocr'), true);
  flow.ocr_enabled = false;
  assert.equal(branchEnabled(normalizeWorkflow(flow), 'ocr'), false);
  flow.ocr_enabled = true;
  flow.edges = flow.edges.filter(e => e.source !== 'ocr');
  assert.equal(branchEnabled(flow, 'ocr'), true);
});
