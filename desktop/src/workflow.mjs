export const DEFINITIONS = {
  target: {
    title: "검사 대상",
    subtitle: "검사 범위",
    icon: "Globe2",
    tone: "blue",
    detail: "시작 URL과 검사 범위를 지정합니다.",
    input: null,
    output: "bottom",
  },
  browser: {
    title: "브라우저",
    subtitle: "페이지 렌더링",
    icon: "PanelsTopLeft",
    tone: "blue",
    detail: "페이지 이동 · 렌더링 · 응답 확인",
    input: "top",
    output: "right",
  },
  collector: {
    title: "콘텐츠 수집",
    subtitle: "본문 · 링크",
    icon: "ScanLine",
    tone: "teal",
    detail: "본문 · 링크 · 계산된 스타일 추출",
    input: "left",
    output: "right",
  },
  techniques: {
    title: "필수 탐지",
    subtitle: "4개 유형",
    icon: "Fingerprint",
    tone: "purple",
    detail: "닮은꼴 · 자모 · 투명 · 화면 밖",
    input: "left",
    output: "right",
  },
  candidates: {
    title: "광고 분류",
    subtitle: "5개 분류",
    icon: "TextSearch",
    tone: "amber",
    detail: "권유 문맥과 일반 광고 후보 검토",
    input: "left",
    output: "right",
  },
  report: {
    title: "결과 출력",
    subtitle: "JSON · CSV",
    icon: "FileCheck2",
    tone: "teal",
    detail: "JSON · CSV · 실행 기록 저장",
    input: "left",
    output: null,
  },
};
export const PAIRS = [
  ["target", "browser"],
  ["browser", "collector"],
  ["collector", "techniques"],
  ["collector", "candidates"],
  ["techniques", "report"],
  ["candidates", "report"],
];
export const edgeFor = (source, target) => ({
  id: source + "-" + target,
  source,
  target,
  type: "default",
  sourceHandle: "out",
  targetHandle: "in",
});
export const defaultWorkflow = () => ({
  version: 1,
  follow_links: true,
  nodes: [
    { id: "target", position: { x: 0, y: 12 } },
    { id: "browser", position: { x: 0, y: 208 } },
    { id: "collector", position: { x: 260, y: 208 } },
    { id: "techniques", position: { x: 520, y: 72 } },
    { id: "candidates", position: { x: 520, y: 342 } },
    { id: "report", position: { x: 800, y: 208 } },
  ],
  edges: PAIRS.map(([a, b]) => edgeFor(a, b)),
});
export function validConnection(connection) {
  return PAIRS.some(
    ([a, b]) => a === connection.source && b === connection.target,
  );
}
export function normalizeWorkflow(value) {
  if (
    !value ||
    value.version !== 1 ||
    !Array.isArray(value.nodes) ||
    value.nodes.length !== 6 ||
    !Array.isArray(value.edges) ||
    value.edges.length > 6
  )
    throw new Error("지원하는 워크플로 JSON이 아닙니다.");
  const ids = new Set();
  const nodes = value.nodes.map((node) => {
    if (
      !DEFINITIONS[node.id] ||
      ids.has(node.id) ||
      ![node.position?.x, node.position?.y].every(
        (n) => Number.isFinite(n) && Math.abs(n) < 10000,
      )
    )
      throw new Error("노드 정보가 올바르지 않습니다.");
    ids.add(node.id);
    return { id: node.id, position: node.position };
  });
  const keys = new Set();
  const edges = value.edges.map((edge) => {
    if (!validConnection(edge) || keys.has(edge.source + "-" + edge.target))
      throw new Error("지원하지 않거나 중복된 연결입니다.");
    keys.add(edge.source + "-" + edge.target);
    return edgeFor(edge.source, edge.target);
  });
  return {
    version: 1,
    nodes,
    edges,
    follow_links: value.follow_links !== false,
  };
}
export function workflowError(flow) {
  const has = (a, b) =>
    flow.edges.some((e) => e.source === a && e.target === b);
  if (!has("target", "browser") || !has("browser", "collector"))
    return "검사 대상 → 브라우저 → 콘텐츠 수집을 연결해 주세요.";
  if (
    !(has("collector", "techniques") && has("techniques", "report")) &&
    !(has("collector", "candidates") && has("candidates", "report"))
  )
    return "분석 노드 하나 이상을 결과 저장까지 연결해 주세요.";
  return "";
}
export function branchEnabled(flow, id) {
  return (
    flow.edges.some((e) => e.source === "collector" && e.target === id) &&
    flow.edges.some((e) => e.source === id && e.target === "report")
  );
}
