const { test } = require("node:test");
const assert = require("node:assert/strict");
test("workflow import preserves typed connections and disables a detached branch", async () => {
  const { defaultWorkflow, normalizeWorkflow, branchEnabled, workflowError } =
    await import("../src/workflow.mjs");
  const flow = normalizeWorkflow(defaultWorkflow());
  assert.equal(workflowError(flow), "");
  flow.edges = flow.edges.filter((e) => e.source !== "techniques");
  assert.equal(branchEnabled(flow, "techniques"), false);
  assert.equal(branchEnabled(flow, "candidates"), true);
  assert.equal(workflowError(flow), "");
  flow.edges = flow.edges.filter((e) => e.source !== "candidates");
  assert.ok(workflowError(flow));
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
