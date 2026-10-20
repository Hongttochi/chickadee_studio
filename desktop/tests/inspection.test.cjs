const test = require("node:test");
const assert = require("node:assert/strict");
test("exploration shows observed edges, bounds large graphs and terminates on cycles", async () => {
  const { explorationFlow } = await import("../src/inspection-model.mjs");
  const nodes = ["a", "b", "c"].map((id) => ({ id, kind: "page", url: `https://example.invalid/${id}`, status: "scanned" }));
  const edges = [{ id: "ab", source: "a", target: "b" }, { id: "bc", source: "b", target: "c" }, { id: "cb", source: "c", target: "b" }];
  const flow = explorationFlow({ nodes, edges });
  assert.equal(flow.nodes[1].position.x, 270);
  assert.equal(flow.edges.length, 3);
  const limited = explorationFlow({ nodes, edges }, 2);
  assert.equal(limited.omitted, 1);
  assert.equal(limited.edges.length, 1);
  assert.deepEqual(explorationFlow(null).nodes, []);
});
