// Presentation adapter only: backend IDs and observed edges are never invented.
export function explorationFlow(graph, limit = 240) {
  const source = Array.isArray(graph?.nodes) ? graph.nodes.slice(0, limit) : [];
  const ids = new Set(source.map((node) => node.id));
  const edges = (Array.isArray(graph?.edges) ? graph.edges : []).filter(
    (edge) => ids.has(edge.source) && ids.has(edge.target),
  );
  const depth = new Map();
  for (const node of source) {
    if (!edges.some((edge) => edge.target === node.id)) depth.set(node.id, 0);
  }
  // Minimum observed path depth; bounded even when navigation contains cycles.
  for (let pass = 0; pass < source.length; pass++) {
    let changed = false;
    for (const edge of edges) {
      if (!depth.has(edge.source)) continue;
      const next = depth.get(edge.source) + 1;
      if (!depth.has(edge.target) || next < depth.get(edge.target)) {
        depth.set(edge.target, next);
        changed = true;
      }
    }
    if (!changed) break;
  }
  const rows = new Map();
  return {
    nodes: source.map((node) => {
      const column = depth.get(node.id) || 0;
      const row = rows.get(column) || 0;
      rows.set(column, row + 1);
      let page = node.url || "";
      try { page = new URL(page).pathname; } catch {}
      return { id: node.id, position: { x: column * 270, y: row * 100 },
        data: { label: node.kind === "page" ? `${page.slice(0, 45)} · ${node.status}` : `${node.label} · ${node.packet_ids?.length || 0}영역` } };
    }),
    edges: edges.map((edge) => ({ ...edge, type: "smoothstep" })),
    omitted: Math.max(0, (graph?.nodes?.length || 0) - source.length),
  };
}

export const CHANGE_LABELS = { newly_observed: "신규 관측", changed: "변경", not_observed: "미관측", unchanged: "동일" };
