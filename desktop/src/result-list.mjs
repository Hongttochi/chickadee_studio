// Ordering and URL grouping affect presentation only; original records stay intact.
export function sortDetections(records, order = "newest") {
  return records.map((record, index) => ({ record, index,
    time: Date.parse(record.observed_at || record._detail?.observed_at || "") || 0,
  })).sort((a, b) => (order === "oldest" ? 1 : -1) * (a.time - b.time || a.index - b.index))
    .map(item => item.record);
}

export function pathTreeRows(pages, collapsed = new Set(), query = "") {
  const roots = new Map();
  const needle = query.trim().toLowerCase();
  for (const [index, page] of pages.entries()) {
    if (!page.url.toLowerCase().includes(needle)) continue;
    let parsed;
    try { parsed = new URL(page.url); } catch { continue; }
    if (!["http:", "https:"].includes(parsed.protocol)) continue;
    const origin = parsed.origin;
    if (!roots.has(origin)) roots.set(origin, { key: origin, label: origin, children: new Map(), pages: [], count: 0 });
    let node = roots.get(origin); node.count++;
    const parts = parsed.pathname.split('/').slice(1);
    const directories = parts.slice(0, -1).slice(0, 64);
    let prefix = origin;
    for (const segment of directories) {
      prefix += '/' + segment;
      if (!node.children.has(prefix)) node.children.set(prefix, { key: prefix, label: segment ? '/' + segment : '/', children: new Map(), pages: [], count: 0 });
      node = node.children.get(prefix); node.count++;
    }
    node.pages.push({ page, key: `page:${index}:${page.url}` });
  }
  const rows = [];
  function visit(node, depth) {
    const expanded = !!needle || !collapsed.has(node.key);
    rows.push({ kind: 'group', key: node.key, label: node.label, count: node.count, depth, expanded });
    if (!expanded) return;
    for (const item of node.pages) rows.push({ kind: 'page', ...item, depth: depth + 1 });
    for (const child of node.children.values()) visit(child, depth + 1);
  }
  for (const root of roots.values()) visit(root, 0);
  return rows;
}
