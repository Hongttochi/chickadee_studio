// Evaluated independently in every frame, including cross-origin frames.
({limit = 20000, textLimit = 20000} = {}) => {
  const ignored = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'HEAD', 'TITLE']);
  const all = [...document.querySelectorAll('body, body *')];
  const ids = new Map(all.map((e, i) => [e, i]));
  const styleCache = new WeakMap();
  const style = e => {
    if (!styleCache.has(e)) styleCache.set(e, getComputedStyle(e));
    return styleCache.get(e);
  };
  function selector(el, frame = false) {
    const parts = [];
    for (let node = el; node; node = node.parentElement) {
      let part = node.tagName.toLowerCase();
      const classes = [...node.classList].map(c => '.' + CSS.escape(c)).join('');
      part += classes;
      const siblings = node.parentElement ? [...node.parentElement.children].filter(n => n.tagName === node.tagName) : [node];
      if (!classes || siblings.filter(n => n.matches(part)).length > 1) {
        part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      const path = parts.join(' > ');
      if (document.querySelectorAll(path).length === 1) break;
    }
    let path = parts.join(' > ');
    if (frame && el.hasAttribute('src')) {
      // Absolute src is required by the contest; nth-of-type disambiguates
      // duplicate frames. Resolve relative attributes before replaying this.
      path += `[src=${JSON.stringify(el.src)}]`;
    }
    return path;
  }
  function rgba(value) {
    const match = value.match(/^rgba?\(([^)]+)\)$/);
    if (!match) return null;
    const values = match[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    return values.length === 3 ? [...values, 1] : values;
  }
  function appearance(el) {
    const cs = style(el);
    let alpha = 1, hidden = false;
    for (let parent = el; parent; parent = parent.parentElement) {
      const ps = style(parent);
      alpha *= Number(ps.opacity);
      hidden ||= ps.display === 'none';
    }
    const color = rgba(cs.color);
    let background = [255, 255, 255, 1];
    for (let parent = el; parent; parent = parent.parentElement) {
      const bg = rgba(style(parent).backgroundColor);
      if (bg && bg[3] >= 0.99) { background = bg; break; }
    }
    const sameColor = color && color[3] > 0.99 && color.slice(0, 3).every((v, i) => Math.abs(v - background[i]) < 1);
    const transparent = alpha <= 0.01 || (color && color[3] <= 0.01) || !!sameColor;
    const rect = el.getBoundingClientRect();
    const outside = (rect.width > 0 || rect.height > 0) && (rect.right <= 0 || rect.bottom <= 0 ||
      (['absolute', 'fixed'].includes(cs.position) && rect.left > innerWidth + 2000));
    const offscreen = hidden || ['hidden', 'collapse'].includes(cs.visibility) || parseFloat(cs.fontSize) <= 1 || outside;
    return {transparent: !!transparent, offscreen: !!offscreen};
  }
  const elements = [];
  // Build text from DOM text nodes, excluding executable/style source. Also
  // aggregate actual text-owner visibility: a white parent must not make a
  // black, explicitly styled child look like hidden text.
  const textInfo = new Map();
  for (const el of [...all].reverse()) {
    if (ignored.has(el.tagName)) { textInfo.set(el, {text: '', direct: '', owners: []}); continue; }
    let text = '', direct = '';
    const owners = [];
    for (const node of el.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) { text += node.textContent; direct += node.textContent; }
      else if (node.nodeType === Node.ELEMENT_NODE) {
        const child = textInfo.get(node);
        if (child) { text += child.text; owners.push(...child.owners); }
      }
    }
    if (direct.trim()) owners.push(appearance(el));
    textInfo.set(el, {text, direct, owners});
  }
  let truncated = false;
  for (const el of all) {
    if (ignored.has(el.tagName) || el.closest('script, style, noscript, template')) continue;
    const info = textInfo.get(el);
    const text = info.text;
    if (!text.trim()) continue;
    const direct = info.direct;
    if (text.length > textLimit) {
      if (direct.trim()) truncated = true;
      continue;
    }
    if (elements.length >= limit) { truncated = true; break; }
    const visibility = {transparent: info.owners.length > 0 && info.owners.every(o => o.transparent),
      offscreen: info.owners.length > 0 && info.owners.every(o => o.offscreen)};
    elements.push({node_id: ids.get(el), parent_id: ids.get(el.parentElement) ?? null,
      location: selector(el), text, direct_text: direct, ...visibility});
  }
  return {elements, truncated, links: [...document.querySelectorAll('a[href]')].slice(0, limit).map(a => a.href),
    links_truncated: document.querySelectorAll('a[href]').length > limit};
}
