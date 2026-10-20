import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import { createRoot } from "react-dom/client";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from "@xyflow/react";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Bird,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Circle,
  CircleAlert,
  CircleCheck,
  Copy,
  CornerDownRight,
  Cpu,
  Download,
  FileCheck2,
  Fingerprint,
  FlaskConical,
  FolderOpen,
  GitBranch,
  Globe2,
  History,
  Info,
  ListFilter,
  LoaderCircle,
  LockKeyhole,
  Maximize2,
  Monitor,
  MousePointer2,
  Network,
  PanelsTopLeft,
  Play,
  RotateCcw,
  Save,
  ScanLine,
  ScanSearch,
  Search,
  ShieldX,
  SlidersHorizontal,
  Square,
  TextSearch,
  Unplug,
  Upload,
  Workflow,
  X,
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import {
  DEFINITIONS,
  defaultWorkflow,
  normalizeWorkflow,
  validConnection,
  workflowError,
  branchEnabled,
} from "./workflow.mjs";
import "./style.css";
import brandMark from "../assets/app-mark.png";

const api = window.chickadee;
const Icons = {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Bird,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Circle,
  CircleAlert,
  CircleCheck,
  Copy,
  CornerDownRight,
  Cpu,
  Download,
  FileCheck2,
  Fingerprint,
  FlaskConical,
  FolderOpen,
  GitBranch,
  Globe2,
  History,
  Info,
  ListFilter,
  LoaderCircle,
  LockKeyhole,
  Maximize2,
  Monitor,
  MousePointer2,
  Network,
  PanelsTopLeft,
  Play,
  RotateCcw,
  Save,
  ScanLine,
  ScanSearch,
  Search,
  ShieldX,
  SlidersHorizontal,
  Square,
  TextSearch,
  Unplug,
  Upload,
  Workflow,
  X,
};
const LABELS = {
  HOMOGLYPH: "닮은꼴 문자",
  JAMO: "자모 분해",
  TRANSPARENT: "투명 텍스트",
  OFFSCREEN: "화면 밖 은닉",
  GAMBLING: "도박 홍보 의심",
  ADULT: "성인 콘텐츠 의심",
  LOAN: "대출 모집 의심",
  INVESTMENT: "투자 모집 의심",
  COMMERCIAL: "구매·추천 유도",
};
const STATUS = {
  idle: "검사 준비",
  running: "검사 진행 중",
  stopping: "중단 처리 중",
  completed: "검사 완료",
  partial: "일부 결과",
  cancelled: "사용자 중단",
  failed: "검사 실패",
  imported: "불러온 결과",
};
const STAGE_NAMES = {
  target: "검사 대상",
  browser: "페이지 확인",
  collector: "콘텐츠 수집",
  techniques: "위장·은닉 분석",
  candidates: "광고 문맥 분석",
  report: "결과 저장",
};
function Icon({ name, size = 18, ...props }) {
  const Component = Icons[name] || Icons.Circle;
  return <Component size={size} strokeWidth={1.7} {...props} />;
}
function shortUrl(value) {
  try {
    const u = new URL(value);
    return u.host + (u.pathname === "/" ? "" : u.pathname);
  } catch {
    return value || "대상 URL을 입력하세요";
  }
}
function relativeUrl(value) {
  try {
    const u = new URL(value);
    return u.pathname + u.search;
  } catch {
    return value || "";
  }
}
function time(value) {
  return new Date(value).toLocaleTimeString("ko-KR", { hour12: false });
}
function formatElapsed(seconds) {
  return seconds < 60
    ? `${Math.floor(seconds)}초`
    : `${Math.floor(seconds / 60)}분 ${Math.floor(seconds % 60)}초`;
}
function Button({ icon, children, className = "", ...props }) {
  return (
    <button className={`button ${className}`} {...props}>
      {icon && <Icon name={icon} size={16} />}
      <span>{children}</span>
    </button>
  );
}
function FlowNode({ id, data, selected }) {
  const def = DEFINITIONS[id],
    position = {
      left: Position.Left,
      right: Position.Right,
      top: Position.Top,
      bottom: Position.Bottom,
    };
  return (
    <div
      className={`flow-node tone-${def.tone} ${data.state || ""} ${selected ? "selected" : ""}`}
    >
      {def.input && (
        <Handle
          id="in"
          type="target"
          position={position[def.input]}
          isConnectable={data.editable}
        />
      )}
      <div className="node-top">
        <span className="node-icon">
          <Icon name={def.icon} size={20} />
        </span>
        <span className="node-subtitle">{def.subtitle}</span>
        <span
          className={`node-state ${data.state}`}
          title={
            data.state === "active"
              ? "실행 중"
              : data.state === "done"
                ? "실행됨"
                : "대기"
          }
        />
      </div>
      <strong>{def.title}</strong>
      <p>{id === "target" ? shortUrl(data.url) : def.detail}</p>
      <div className="node-bottom">
        <span>{data.caption || "실행 대기"}</span>
        <Icon
          name={
            data.state === "done"
              ? "Check"
              : data.state === "active"
                ? "LoaderCircle"
                : "ArrowUpRight"
          }
          size={13}
          className={data.state === "active" ? "spin" : ""}
        />
      </div>
      {def.output && (
        <Handle
          id="out"
          type="source"
          position={position[def.output]}
          isConnectable={data.editable}
        />
      )}
    </div>
  );
}
const nodeTypes = { stage: FlowNode };

function App() {
  const [flow, setFlow] = useState(defaultWorkflow),
    [url, setUrl] = useState("http://113.198.66.73:18244/"),
    [view, setView] = useState("workflow");
  const [status, setStatus] = useState("idle"),
    [active, setActive] = useState(null),
    [visited, setVisited] = useState(new Set());
  const [events, setEvents] = useState([]),
    [records, setRecords] = useState([]),
    [pages, setPages] = useState([]),
    [history, setHistory] = useState([]);
  const [preview, setPreview] = useState(null),
    [currentUrl, setCurrentUrl] = useState(""),
    [queue, setQueue] = useState(0),
    [discovered, setDiscovered] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null),
    [selectedRecord, setSelectedRecord] = useState(null),
    [selectedEvent, setSelectedEvent] = useState(null);
  const [pending, setPending] = useState([]),
    [pageFilter, setPageFilter] = useState("visited");
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all"),
    [eventFilter, setEventFilter] = useState("all"),
    [notice, setNotice] = useState(null);
  const [settings, setSettings] = useState(false),
    [profile, setProfile] = useState("default"),
    [maxPages, setMaxPages] = useState(100),
    [timeout, setTimeoutValue] = useState(300);
  const [livePreview, setLivePreview] = useState(true),
    [outputRoot, setOutputRoot] = useState(""),
    [outcome, setOutcome] = useState(null),
    [zoomPreview, setZoomPreview] = useState(false);
  const [startTime, setStartTime] = useState(null),
    [elapsed, setElapsed] = useState(0),
    [booted, setBooted] = useState(false);
  const timelineRef = useRef(null),
    autoScroll = useRef(true);
  const running = ["running", "stopping"].includes(status);
  const tell = (message, type = "info") =>
    setNotice({ message, type, key: Date.now() });
  const action = async (fn) => {
    try {
      return await fn();
    } catch (error) {
      tell(error.message, "error");
      return null;
    }
  };
  useEffect(() => {
    if (!notice) return;
    const id = window.setTimeout(() => setNotice(null), 6000);
    return () => window.clearTimeout(id);
  }, [notice]);
  const appendEvent = useCallback((event) => {
    setEvents((items) => [
      ...items.slice(-1999),
      { ...event, key: crypto.randomUUID() },
    ]);
  }, []);
  const applyOutcome = useCallback((value) => {
    setOutcome(value);
    setRecords([
      ...value.result.findings,
      ...(value.report.ad_candidates || []),
    ]);
    setPages(
      value.report.page_diagnostics ||
        value.report.pages_scanned.map((url) => ({ url, status: "scanned" })),
    );
    setPending(value.report.pending_urls || []);
    if (value.report.workflow?.version === 1) {
      try {
        setFlow(normalizeWorkflow(value.report.workflow));
      } catch {}
    }
    if (value.events)
      setVisited(
        new Set(
          value.events.filter((e) => e.kind === "phase").map((e) => e.stage),
        ),
      );
    setStatus(value.report.status);
    setElapsed(value.result.meta.elapsed_sec || 0);
    setCurrentUrl(
      (previous) =>
        value.preview?.url ||
        (value.events
          ? value.result.meta.entry_url
          : previous || value.result.meta.entry_url),
    );
    setUrl(value.result.meta.entry_url);
    setDiscovered(
      value.report.crawl_summary?.discovered_urls ||
        value.report.pages_scanned.length,
    );
    setQueue(value.report.pages_remaining || 0);
    setActive(null);
    if (value.history) setHistory(value.history);
    if (value.events)
      setEvents(
        value.events
          .slice(-2000)
          .map((event) => ({ ...event, key: crypto.randomUUID() })),
      );
    if (Object.hasOwn(value, "preview")) setPreview(value.preview);
  }, []);
  useEffect(() => {
    if (!api) {
      tell("데스크톱 앱에서 실행하세요.", "error");
      return;
    }
    api
      .state()
      .then((state) => {
        setHistory(state.history);
        setOutputRoot(state.outputRoot);
        if (state.workflow) {
          try {
            setFlow(normalizeWorkflow(state.workflow));
          } catch {}
        }
        setBooted(true);
      })
      .catch((error) => tell(error.message, "error"));
    return api.onEvent((event) => {
      if (event.kind === "preview") {
        if (/^data:image\/jpeg;base64,[a-zA-Z0-9+/=]+$/.test(event.data_url))
          setPreview(event);
        return;
      }
      appendEvent(event);
      if (
        event.url &&
        ["phase", "started", "page_complete"].includes(event.kind)
      )
        setCurrentUrl(event.url);
      if (event.kind === "started") {
        setStartTime(Date.now());
        setStatus("running");
        setCurrentUrl(event.url);
        setVisited(new Set(["target"]));
      }
      if (event.kind === "phase") {
        setActive(event.stage);
        setVisited((previous) => new Set([...previous, event.stage]));
      }
      if (event.kind === "progress") {
        setQueue(event.queue_remaining);
      }
      if (event.kind === "url_discovered")
        setPending((items) => [...items, event]);
      if (event.kind === "phase" && event.action === "navigate")
        setPending((items) => items.filter((item) => item.url !== event.url));
      if (event.kind === "page_complete") {
        setPages((items) => [...items, event.page]);
        setQueue(event.queue_remaining);
        setDiscovered(event.discovered_urls);
      }
      if (event.kind === "finding")
        setRecords((items) => [
          ...items,
          { ...event.finding, _detail: event.detail },
        ]);
      if (event.kind === "candidate")
        setRecords((items) => [...items, event.candidate]);
      if (event.kind === "done") {
        applyOutcome(event);
        tell("검사 결과와 진행 기록을 저장했습니다.", "success");
      }
      if (event.kind === "error") {
        setStatus("failed");
        tell(event.message, "error");
      }
    });
  }, [appendEvent, applyOutcome]);
  useEffect(() => {
    if (!running || !startTime) return;
    const id = window.setInterval(
      () => setElapsed((Date.now() - startTime) / 1000),
      500,
    );
    return () => window.clearInterval(id);
  }, [running, startTime]);
  useEffect(() => {
    if (autoScroll.current && timelineRef.current)
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
  }, [events]);
  const findings = records.filter((r) => r.technique),
    candidates = records.filter((r) => r.category),
    error = workflowError(flow);
  const flowNodes = useMemo(
    () =>
      flow.nodes.map((node) => {
        const enabled =
          !["techniques", "candidates"].includes(node.id) ||
          branchEnabled(flow, node.id);
        const state = !enabled
          ? "disabled"
          : active === node.id
            ? status === "failed"
              ? "error"
              : "active"
            : visited.has(node.id)
              ? "done"
              : "";
        let caption =
          node.id === "browser"
            ? `${pages.length}페이지 방문`
            : node.id === "collector"
              ? `${discovered}개 URL 발견`
              : node.id === "techniques"
                ? `${findings.length}건 발견`
                : node.id === "candidates"
                  ? `${candidates.length}건 광고 의심`
                  : node.id === "target"
                    ? "HTTP / HTTPS"
                    : outcome
                      ? "JSON · CSV 저장 완료"
                      : "실행 종료 후 저장";
        if (!enabled) caption = "분석 경로 연결 안 됨";
        return {
          ...node,
          type: "stage",
          deletable: false,
          data: { state, caption, url, editable: !running },
        };
      }),
    [
      flow,
      active,
      visited,
      pages.length,
      discovered,
      findings.length,
      candidates.length,
      outcome,
      url,
      running,
      status,
    ],
  );
  const flowEdges = useMemo(
    () =>
      flow.edges.map((edge) => ({
        ...edge,
        type: "default",
        animated: running && (edge.target === active || edge.source === active),
        style: {
          stroke: edge.target === active ? "#c4ff1a" : "#66788e",
          strokeWidth: edge.target === active ? 2.8 : 1.8,
        },
      })),
    [flow.edges, running, active],
  );
  const onNodesChange = useCallback(
    (changes) =>
      setFlow((value) => ({
        ...value,
        nodes: applyNodeChanges(changes, value.nodes),
      })),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => {
      if (!running)
        setFlow((value) => ({
          ...value,
          edges: applyEdgeChanges(changes, value.edges),
        }));
    },
    [running],
  );
  const onConnect = useCallback(
    (connection) => {
      if (!running && validConnection(connection))
        setFlow((value) => ({
          ...value,
          edges: addEdge({ ...connection, type: "default" }, value.edges),
        }));
    },
    [running],
  );
  const start = async (demo = false) => {
    if (error) {
      tell(error, "error");
      return;
    }
    if (
      !Number.isInteger(Number(maxPages)) ||
      Number(maxPages) < 1 ||
      Number(maxPages) > 10000
    ) {
      tell("최대 페이지는 1~10000 사이의 정수로 지정하세요.", "error");
      return;
    }
    if (
      !Number.isFinite(Number(timeout)) ||
      Number(timeout) <= 0 ||
      Number(timeout) > 1800
    ) {
      tell("제한시간은 1~1800초로 지정하세요.", "error");
      return;
    }
    let entry = url.trim();
    if (!entry.includes("://"))
      entry = /^(?:\d{1,3}\.){3}|^localhost/.test(entry)
        ? "http://" + entry
        : "https://" + entry;
    setStatus("running");
    setRecords([]);
    setPages([]);
    setPending([]);
    setEvents([]);
    setPreview(null);
    setOutcome(null);
    setActive("target");
    setVisited(new Set(["target"]));
    setDiscovered(0);
    setQueue(0);
    setElapsed(0);
    setStartTime(Date.now());
    setView("workflow");
    setSelectedNode(null);
    setSelectedRecord(null);
    try {
      await api.start({
        url: demo ? "http://127.0.0.1/" : entry,
        max_pages: Number(maxPages),
        timeout_sec: Number(timeout),
        profile,
        preview: livePreview,
        demo,
        workflow: flow,
      });
    } catch (error) {
      setStatus("failed");
      tell(error.message, "error");
    }
  };
  const load = async () => {
    const value = await action(() => api.load());
    if (value) {
      applyOutcome(value);
      setView("results");
      setSelectedRecord(null);
    }
  };
  const saveFlow = () =>
    action(async () => {
      await api.saveWorkflow(flow);
      tell("구성 저장 완료", "success");
    });
  const loadFlow = () =>
    action(async () => {
      const value = await api.loadWorkflow();
      if (value) {
        setFlow(normalizeWorkflow(value));
        tell("구성 불러오기 완료", "success");
      }
    });
  const filteredRecords = records.filter(
    (record) =>
      (filter === "all" ||
        (filter === "required" && record.technique) ||
        (filter === "candidates" && record.category) ||
        record.technique === filter) &&
      [
        record.url,
        record.evidence_text,
        record.location,
        LABELS[record.technique || record.category],
      ]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const filteredEvents = events.filter(
    (event) =>
      eventFilter === "all" ||
      (eventFilter === "phase" &&
        ["phase", "page_complete", "started", "done"].includes(event.kind)) ||
      (eventFilter === "network" &&
        ["http_response", "request_blocked"].includes(event.kind)) ||
      (eventFilter === "findings" &&
        ["finding", "candidate", "warning", "error"].includes(event.kind)),
  );
  const phaseTitle = active ? STAGE_NAMES[active] : STATUS[status];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <img src={brandMark} alt="돋보기를 든 박새 로고" />
          </span>
          <span>
            chickadee<span className="brand-dot">.</span>
          </span>
        </div>
        <button className="workspace-switch" onClick={() => setSettings(true)}>
          <span className="workspace-avatar">C</span>
          <div>
            <strong>웹사이트 검사</strong>
            <small>{profile === "test" ? "게시판 구성" : "표준 구성"}</small>
          </div>
          <Icon name="ChevronsUpDown" size={14} />
        </button>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {[
            ["workflow", "Workflow", "검사 구성"],
            ["results", "ListFilter", "탐지 내역"],
            ["pages", "Network", "탐색 경로"],
            ["activity", "Activity", "진행 기록"],
            ["history", "History", "검사 기록"],
          ].map(([id, icon, label]) => (
            <button
              key={id}
              className={`nav-item ${view === id ? "active" : ""}`}
              onClick={() => setView(id)}
            >
              <Icon name={icon} />
              <span>{label}</span>
              {id === "results" && records.length > 0 && (
                <b>{records.length}</b>
              )}
              {id === "activity" && running && <span className="live-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" disabled={running} onClick={load}>
            <Icon name="FolderOpen" />
            <span>결과 불러오기</span>
          </button>
          <button className="nav-item" onClick={() => setSettings(true)}>
            <Icon name="SlidersHorizontal" />
            <span>검사 설정</span>
          </button>
          <button
            className="engine-indicator"
            onClick={() => setSettings(true)}
          >
            <span className={booted ? "ready-dot" : "muted-dot"} />
            <div>
              <strong>{booted ? "검사 준비" : "환경 확인"}</strong>
              <small>Desktop · v0.5.0</small>
            </div>
            <Icon name="ChevronRight" size={15} />
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span>워크스페이스</span>
          <Icon name="ChevronRight" size={13} />
          <strong>웹사이트 점검</strong>
          <div className="topbar-right">
            <span className="local-label">
              <Icon name="Monitor" size={13} /> LOCAL
            </span>
          </div>
        </header>
        <section className="heading">
          <div>
            <div className="eyebrow">CHICKADEE STUDIO</div>
            <h1>
              {view === "history"
                ? "검사 기록"
                : view === "results"
                  ? "탐지 내역"
                  : view === "pages"
                    ? "탐색 경로"
                    : view === "activity"
                      ? "진행 기록"
                      : "검사 구성"}
            </h1>
            <p>
              {view === "workflow"
                ? "노드를 연결하고, 검사의 모든 단계를 직접 확인하세요."
                : "관측한 데이터와 탐지 근거를 한곳에서 검토하세요."}
            </p>
          </div>
          <div className="heading-actions">
            <Button
              icon="FlaskConical"
              disabled={running || !booted}
              onClick={() => start(true)}
            >
              데모 검사
            </Button>
            <Button
              icon="FolderOpen"
              onClick={() => action(() => api.openFolder())}
            >
              결과 폴더
            </Button>
          </div>
        </section>
        <section className="target-bar">
          <span className="target-icon">
            <Icon name="Globe2" size={20} />
          </span>
          <input
            aria-label="검사 대상 URL"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={running}
            placeholder="https://example.go.kr"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !running) start();
            }}
          />
          <button
            className="profile-selector"
            onClick={() => setSettings(true)}
          >
            <span>
              {profile === "test"
                ? "모의 게시판"
                : profile === "public"
                  ? "공공 사이트"
                  : "기본 탐색"}
            </span>
            <Icon name="ChevronDown" size={14} />
          </button>
          <span className="separator" />
          {running ? (
            <Button
              icon="Square"
              className="stop-button"
              onClick={() =>
                action(async () => {
                  setStatus("stopping");
                  await api.stop();
                })
              }
              disabled={status === "stopping"}
            >
              검사 중단
            </Button>
          ) : (
            <Button
              icon="Play"
              className="primary"
              disabled={!booted}
              onClick={() => start()}
            >
              검사 실행
            </Button>
          )}
        </section>
        <section className="summary-strip">
          <div className="scan-status">
            <span
              className={
                running
                  ? "pulse-dot"
                  : status === "failed"
                    ? "error-dot"
                    : "ready-dot"
              }
            />
            <strong>{phaseTitle}</strong>
            {elapsed > 0 && <span>{formatElapsed(elapsed)}</span>}
          </div>
          <div className="summary-numbers">
            <button
              className={
                view === "pages" && pageFilter === "visited" ? "active" : ""
              }
              onClick={() => {
                setView("pages");
                setPageFilter("visited");
                setSearch("");
              }}
            >
              <Icon name="Network" size={13} />
              <span>방문</span>
              <b>{pages.length}</b>
            </button>
            <button
              className={
                view === "results" && filter === "required" ? "active" : ""
              }
              onClick={() => {
                setView("results");
                setFilter("required");
                setSearch("");
              }}
            >
              <Icon name="Fingerprint" size={13} />
              <span>필수 탐지</span>
              <b>{findings.length}</b>
            </button>
            <button
              className={
                view === "results" && filter === "candidates" ? "active" : ""
              }
              onClick={() => {
                setView("results");
                setFilter("candidates");
                setSearch("");
              }}
            >
              <Icon name="TextSearch" size={13} />
              <span>광고 의심</span>
              <b className="amber-text">{candidates.length}</b>
            </button>
            <button
              className={
                view === "pages" && pageFilter === "pending" ? "active" : ""
              }
              onClick={() => {
                setView("pages");
                setPageFilter("pending");
                setSearch("");
              }}
            >
              <Icon name="LoaderCircle" size={13} />
              <span>대기</span>
              <b>{queue}</b>
            </button>
          </div>
        </section>
        <div className="content-area">
          {view === "workflow" && (
            <div className="studio">
              <section className="canvas-shell">
                <div className="canvas-toolbar">
                  <span>
                    <Icon name="Workflow" size={16} />
                    <strong>검사 흐름</strong>
                    <small>
                      {flow.nodes.length} nodes · {flow.edges.length}{" "}
                      connections
                    </small>
                  </span>
                  <div>
                    <button
                      title="기본 구성"
                      disabled={running}
                      onClick={() => {
                        setFlow(defaultWorkflow());
                        setSelectedNode(null);
                      }}
                    >
                      <Icon name="RotateCcw" size={15} />
                    </button>
                    <button
                      title="구성 불러오기"
                      disabled={running}
                      onClick={loadFlow}
                    >
                      <Icon name="Upload" size={15} />
                    </button>
                    <button
                      title="구성 내보내기"
                      onClick={() => action(() => api.exportWorkflow(flow))}
                    >
                      <Icon name="Download" size={15} />
                    </button>
                    <Button icon="Save" onClick={saveFlow}>
                      구성 저장
                    </Button>
                  </div>
                </div>
                <div className="flow-area">
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    nodeTypes={nodeTypes}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    isValidConnection={validConnection}
                    deleteKeyCode={["Backspace", "Delete"]}
                    nodesDraggable={!running}
                    nodesConnectable={!running}
                    edgesReconnectable={false}
                    onNodeClick={(_event, node) => setSelectedNode(node.id)}
                    onPaneClick={() => setSelectedNode(null)}
                    fitView
                    fitViewOptions={{ padding: 0.12 }}
                    minZoom={0.35}
                    maxZoom={1.5}
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background color="#303947" gap={20} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap
                      nodeColor={(node) =>
                        ({
                          blue: "#3182f6",
                          teal: "#00d38b",
                          purple: "#a57aff",
                          amber: "#ff934f",
                        })[DEFINITIONS[node.id].tone]
                      }
                      maskColor="rgba(16,20,28,.8)"
                      style={{ width: 120, height: 74 }}
                      pannable
                      zoomable
                    />
                  </ReactFlow>
                  {error && (
                    <div className="flow-warning">
                      <Icon name="Unplug" size={15} />
                      {error}
                    </div>
                  )}
                  <div className="flow-caption">
                    <span>
                      <i className="legend-dot" /> 실행 단계
                    </span>
                    <span>
                      포트를 드래그해 연결 · 연결 선택 후 Delete로 제거
                    </span>
                  </div>
                </div>
                <div className="canvas-footer">
                  <Icon name="GitBranch" size={14} />
                  <span>
                    {flow.follow_links
                      ? "하위 링크 탐색 켜짐"
                      : "입력 페이지 한정"}
                  </span>
                  <span>
                    필수 탐지 {branchEnabled(flow, "techniques") ? "ON" : "OFF"}{" "}
                    · 광고 문맥{" "}
                    {branchEnabled(flow, "candidates") ? "ON" : "OFF"}
                  </span>
                  <button onClick={() => setSelectedNode("collector")}>
                    구성 설정 <Icon name="ArrowUpRight" size={12} />
                  </button>
                </div>
              </section>
              <aside className="monitor-panel">
                {selectedNode ? (
                  <NodeSettings
                    id={selectedNode}
                    flow={flow}
                    setFlow={setFlow}
                    url={url}
                    setUrl={setUrl}
                    running={running}
                    onClose={() => setSelectedNode(null)}
                  />
                ) : (
                  <>
                    <div className="panel-heading">
                      <span>
                        <i className={running ? "live-dot" : "muted-dot"} />
                        <strong>실시간 화면</strong>
                      </span>
                      <small>{running ? "LIVE" : "STANDBY"}</small>
                    </div>
                    <div className="browser-preview">
                      <div className="browser-chrome">
                        <span className="browser-dots">
                          <i />
                          <i />
                          <i />
                        </span>
                        <span title={currentUrl || url}>
                          <Icon name="LockKeyhole" size={11} />
                          {shortUrl(currentUrl || url)}
                        </span>
                        <button
                          title="화면 확대"
                          disabled={!preview}
                          onClick={() => setZoomPreview(true)}
                        >
                          <Icon name="Maximize2" size={13} />
                        </button>
                      </div>
                      {preview ? (
                        <button
                          className="preview-image"
                          onClick={() => setZoomPreview(true)}
                        >
                          <img
                            src={preview.data_url}
                            alt="실제 검사 브라우저의 현재 화면"
                          />
                        </button>
                      ) : (
                        <div className="preview-placeholder">
                          <Icon name="PanelsTopLeft" size={34} />
                          <strong>
                            {livePreview ? "화면 대기" : "화면 미리보기 꺼짐"}
                          </strong>
                          <span>검사를 시작하면 실제 화면이 표시됩니다.</span>
                        </div>
                      )}
                      <div className="preview-caption">
                        <span>
                          {preview
                            ? "실제 Chromium 화면"
                            : "아직 관측한 화면이 없습니다"}
                        </span>
                        <span>
                          {preview?.timestamp ? time(preview.timestamp) : "—"}
                        </span>
                      </div>
                    </div>
                    <div className="current-location">
                      <span>검사 위치</span>
                      <strong title={currentUrl}>
                        {currentUrl
                          ? relativeUrl(currentUrl)
                          : "검사를 시작해 주세요."}
                      </strong>
                    </div>
                    <div className="activity-heading">
                      <strong>진행 기록</strong>
                      <button onClick={() => setView("activity")}>
                        전체 기록 <Icon name="ArrowUpRight" size={13} />
                      </button>
                    </div>
                    <div
                      className="mini-timeline"
                      ref={timelineRef}
                      onScroll={(event) => {
                        autoScroll.current =
                          event.target.scrollHeight -
                            event.target.scrollTop -
                            event.target.clientHeight <
                          90;
                      }}
                    >
                      {events
                        .filter((event) =>
                          [
                            "phase",
                            "finding",
                            "candidate",
                            "page_complete",
                            "warning",
                            "error",
                            "done",
                            "started",
                          ].includes(event.kind),
                        )
                        .slice(-100)
                        .map((event) => (
                          <EventRow
                            key={event.key}
                            event={event}
                            onClick={() => setSelectedEvent(event)}
                            compact
                          />
                        ))}
                      {events.length === 0 && (
                        <div className="timeline-empty">
                          <span className="timeline-empty-line" />
                          <p>진행 단계가 여기에 기록됩니다.</p>
                          <small>이동, 수집, 분석, 저장까지</small>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </aside>
            </div>
          )}
          {view === "results" && (
            <div className="results-layout">
              <section className="table-section">
                <div className="list-toolbar">
                  <div className="segmented">
                    {[
                      ["all", "전체"],
                      ["required", "필수 탐지"],
                      ["candidates", "광고 의심"],
                    ].map(([id, label]) => (
                      <button
                        className={filter === id ? "active" : ""}
                        key={id}
                        onClick={() => setFilter(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="search">
                    <Icon name="Search" size={15} />
                    <input
                      aria-label="결과 검색"
                      placeholder="원문, URL 검색"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                  <Button
                    icon="Download"
                    disabled={!outcome || running}
                    onClick={() =>
                      action(async () => {
                        const result = await api.exportCSV();
                        if (result) tell("CSV를 저장했습니다.", "success");
                      })
                    }
                  >
                    CSV 저장
                  </Button>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>유형</th>
                        <th>탐지 원문</th>
                        <th>페이지</th>
                        <th>검토</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRecords.map((record) => (
                        <tr
                          key={record.id}
                          className={
                            selectedRecord?.id === record.id ? "selected" : ""
                          }
                          onClick={() => setSelectedRecord(record)}
                        >
                          <td>
                            <button
                              className={`type-badge type-filter ${record.technique ? "purple" : "amber"}`}
                              onClick={(event) => {
                                event.stopPropagation();
                                setFilter(record.technique || "candidates");
                              }}
                            >
                              {LABELS[record.technique || record.category]}
                            </button>
                          </td>
                          <td className="evidence-cell">
                            {record.evidence_text}
                          </td>
                          <td className="url-cell" title={record.url}>
                            {shortUrl(record.url)}
                          </td>
                          <td>
                            <span className="review-label">확인 필요</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filteredRecords.length === 0 && (
                    <Empty
                      icon="ScanSearch"
                      title={running ? "분석 진행" : "탐지 내역 없음"}
                      text="검사를 시작하거나 저장된 result.json을 불러오세요."
                    />
                  )}
                </div>
                <div className="table-footer">
                  {filteredRecords.length}개 항목{" "}
                  <span>일반 광고 후보는 법적 불법성 판정이 아닙니다.</span>
                </div>
              </section>
              <RecordDetail
                record={selectedRecord}
                outcome={outcome}
                onCopy={(text) => action(() => api.copy(text))}
              />
            </div>
          )}
          {view === "pages" && (
            <section className="table-section">
              <div className="list-toolbar">
                <div className="segmented">
                  <button
                    className={pageFilter === "visited" ? "active" : ""}
                    onClick={() => setPageFilter("visited")}
                  >
                    방문 {pages.length}
                  </button>
                  <button
                    className={pageFilter === "pending" ? "active" : ""}
                    onClick={() => setPageFilter("pending")}
                  >
                    대기 {queue}
                  </button>
                </div>
                <span className="subtle">발견 {discovered}</span>
                <div className="search">
                  <Icon name="Search" size={15} />
                  <input
                    placeholder="경로 검색"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>응답</th>
                      <th>검사한 경로</th>
                      <th>발견 링크</th>
                      <th>분석 요소</th>
                      <th>후보</th>
                      <th>소요</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(pageFilter === "pending" ? pending : pages)
                      .filter((page) =>
                        page.url.toLowerCase().includes(search.toLowerCase()),
                      )
                      .map((page, index) => (
                        <tr
                          key={index}
                          onClick={() =>
                            setSelectedEvent(
                              pageFilter === "pending"
                                ? { kind: "url_discovered", ...page }
                                : { kind: "page_complete", page },
                            )
                          }
                        >
                          <td>
                            <span
                              className={`http-badge ${page.http_status >= 400 ? "bad" : ""}`}
                            >
                              {page.http_status || "—"}
                            </span>
                          </td>
                          <td className="path-cell">
                            <Icon name="CornerDownRight" size={14} />
                            <span title={page.url}>
                              {relativeUrl(page.url)}
                            </span>
                            {page.discovered_from && (
                              <small title={page.discovered_from}>
                                ↳ {relativeUrl(page.discovered_from)}
                              </small>
                            )}
                          </td>
                          <td>{page.links_discovered ?? "—"}</td>
                          <td>{page.elements_examined ?? "—"}</td>
                          <td>{page.candidates_added ?? "—"}</td>
                          <td>
                            {page.elapsed_sec
                              ? `${page.elapsed_sec.toFixed(1)}s`
                              : "—"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
                {!(pageFilter === "pending" ? pending : pages).length && (
                  <Empty
                    icon="Network"
                    title={
                      pageFilter === "pending"
                        ? "대기 주소 없음"
                        : "탐색 경로 없음"
                    }
                    text="발견한 실제 링크와 방문한 페이지를 확인할 수 있습니다."
                  />
                )}
              </div>
              <div className="table-footer">
                페이지를 선택하면 수집 수치와 응답 내역을 확인할 수 있습니다.
              </div>
            </section>
          )}
          {view === "activity" && (
            <section className="activity-section">
              <div className="list-toolbar">
                <div className="segmented">
                  {[
                    ["all", "전체"],
                    ["phase", "진행 단계"],
                    ["network", "HTTP 통신"],
                    ["findings", "탐지·오류"],
                  ].map(([id, label]) => (
                    <button
                      key={id}
                      className={eventFilter === id ? "active" : ""}
                      onClick={() => setEventFilter(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <span className="subtle">
                  최근 {events.length}개 · 전체 기록 저장
                </span>
              </div>
              <div className="full-timeline">
                {filteredEvents.map((event) => (
                  <EventRow
                    key={event.key}
                    event={event}
                    onClick={() => setSelectedEvent(event)}
                  />
                ))}
                {!filteredEvents.length && (
                  <Empty
                    icon="Activity"
                    title="검사 과정을 기다리고 있습니다"
                    text="실제 수행한 작업만 시간순으로 기록합니다."
                  />
                )}
              </div>
            </section>
          )}
          {view === "history" && (
            <section className="table-section">
              <div className="list-toolbar">
                <strong>최근 검사</strong>
                <Button icon="FolderOpen" disabled={running} onClick={load}>
                  결과 불러오기
                </Button>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>대상</th>
                      <th>상태</th>
                      <th>방문 페이지</th>
                      <th>필수 / 후보</th>
                      <th>완료 시각</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr
                        key={item.id}
                        onClick={() =>
                          !running &&
                          action(async () => {
                            const value = await api.history(item.id);
                            applyOutcome(value);
                            setView("results");
                          })
                        }
                      >
                        <td>{shortUrl(item.url)}</td>
                        <td>
                          <span className="type-badge">
                            {STATUS[item.status]}
                          </span>
                        </td>
                        <td>{item.pages}</td>
                        <td>
                          {item.findings} / {item.candidates}
                        </td>
                        <td>
                          {new Date(item.finished_at).toLocaleString("ko-KR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!history.length && (
                  <Empty
                    icon="History"
                    title="첫 검사를 시작해 보세요"
                    text="검사마다 별도 폴더에 결과와 진행 기록을 보관합니다."
                  />
                )}
              </div>
            </section>
          )}
        </div>
        <footer className="statusbar">
          <span>
            <span className={running ? "pulse-dot" : "ready-dot"} />
            {STATUS[status]}
          </span>
          <span>
            {running
              ? "실제 페이지 검사 중"
              : outcome
                ? `${pages.length}페이지 · ${STATUS[status]}`
                : "URL 입력 · 구성 선택"}
          </span>
          <span>
            로컬 검사 <i /> JSON · CSV
          </span>
        </footer>
      </main>
      {notice && (
        <div className={`toast ${notice.type}`} role="status">
          <Icon
            name={
              notice.type === "error"
                ? "CircleAlert"
                : notice.type === "success"
                  ? "CircleCheck"
                  : "Info"
            }
          />
          <span>{notice.message}</span>
          <button onClick={() => setNotice(null)}>
            <Icon name="X" size={15} />
          </button>
        </div>
      )}
      {settings && (
        <div className="modal-backdrop" onClick={() => setSettings(false)}>
          <section
            className="modal settings-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">SCAN SETTINGS</span>
                <h2>검사 설정</h2>
              </div>
              <button onClick={() => setSettings(false)}>
                <Icon name="X" />
              </button>
            </div>
            <label>
              사이트 탐색 설정
              <select
                value={profile}
                disabled={running}
                onChange={(event) => setProfile(event.target.value)}
              >
                <option value="default">기본 탐색 · 같은 사이트 전체</option>
                <option value="test">
                  사용자 모의 게시판 · .post-detail 본문
                </option>
                <option value="public">공공 사이트 기본 설정</option>
              </select>
            </label>
            <div className="form-row">
              <label>
                최대 페이지
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={maxPages}
                  disabled={running}
                  onChange={(event) => setMaxPages(event.target.value)}
                />
              </label>
              <label>
                전체 제한시간 (초)
                <input
                  type="number"
                  min="1"
                  max="1800"
                  value={timeout}
                  disabled={running}
                  onChange={(event) => setTimeoutValue(event.target.value)}
                />
              </label>
            </div>
            <label className="toggle-label">
              <div>
                <strong>실시간 브라우저 화면</strong>
                <small>실제 Chromium 화면을 검사 중 표시합니다.</small>
              </div>
              <input
                type="checkbox"
                checked={livePreview}
                disabled={running}
                onChange={(event) => setLivePreview(event.target.checked)}
              />
            </label>
            <label>
              결과 저장 위치
              <div className="folder-input">
                <span title={outputRoot}>{outputRoot}</span>
                <Button
                  icon="FolderOpen"
                  disabled={running}
                  onClick={() =>
                    action(async () => setOutputRoot(await api.chooseFolder()))
                  }
                >
                  변경
                </Button>
              </div>
            </label>
            <div className="modal-footer">
              <span>각 검사는 별도 폴더에 저장됩니다.</span>
              <Button className="primary" onClick={() => setSettings(false)}>
                완료
              </Button>
            </div>
          </section>
        </div>
      )}
      {selectedEvent && (
        <div className="modal-backdrop" onClick={() => setSelectedEvent(null)}>
          <section
            className="modal event-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">OBSERVED EVENT</span>
                <h2>실행 내역</h2>
              </div>
              <button onClick={() => setSelectedEvent(null)}>
                <Icon name="X" />
              </button>
            </div>
            <p className="event-summary">{eventLabel(selectedEvent).title}</p>
            <pre>
              {JSON.stringify(
                selectedEvent,
                (key, value) => (key === "key" ? undefined : value),
                2,
              )}
            </pre>
          </section>
        </div>
      )}
      {zoomPreview && preview && (
        <div
          className="modal-backdrop preview-backdrop"
          onClick={() => setZoomPreview(false)}
        >
          <section
            className="preview-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div>
              <strong>실제 검사 브라우저</strong>
              <span>{preview.url}</span>
              <button onClick={() => setZoomPreview(false)}>
                <Icon name="X" />
              </button>
            </div>
            <img src={preview.data_url} alt="검사 화면 확대" />
          </section>
        </div>
      )}
    </div>
  );
}
function Empty({ icon, title, text }) {
  return (
    <div className="empty-state">
      <span>
        <Icon name={icon} size={28} />
      </span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}
function NodeSettings({ id, flow, setFlow, url, setUrl, running, onClose }) {
  const def = DEFINITIONS[id];
  return (
    <>
      <div className="panel-heading">
        <strong>단계 설정</strong>
        <button onClick={onClose}>
          <Icon name="X" size={16} />
        </button>
      </div>
      <div className={`node-config tone-${def.tone}`}>
        <span className="config-icon">
          <Icon name={def.icon} size={27} />
        </span>
        <small>{def.subtitle}</small>
        <h2>{def.title}</h2>
        <p>{def.detail}</p>
        {id === "target" && (
          <label>
            시작 URL
            <input
              value={url}
              disabled={running}
              onChange={(event) => setUrl(event.target.value)}
            />
          </label>
        )}
        {id === "collector" && (
          <label className="toggle-label">
            <div>
              <strong>하위 링크 탐색</strong>
              <small>끄면 입력한 페이지만 검사합니다.</small>
            </div>
            <input
              type="checkbox"
              checked={flow.follow_links}
              disabled={running}
              onChange={(event) =>
                setFlow((value) => ({
                  ...value,
                  follow_links: event.target.checked,
                }))
              }
            />
          </label>
        )}
        {["techniques", "candidates"].includes(id) && (
          <div className="connection-state">
            <span
              className={branchEnabled(flow, id) ? "ready-dot" : "muted-dot"}
            />
            {branchEnabled(flow, id)
              ? "분석과 결과 저장이 연결되어 있습니다."
              : "실행하려면 수집 → 분석 → 결과를 연결하세요."}
          </div>
        )}
        <dl>
          <dt>입력</dt>
          <dd>
            {id === "target"
              ? "사용자가 입력한 HTTP(S) 주소"
              : id === "browser"
                ? "대상 URL"
                : id === "collector"
                  ? "렌더링된 페이지"
                  : id === "report"
                    ? "분석 결과"
                    : "본문·CSS·요소 위치"}
          </dd>
          <dt>출력</dt>
          <dd>
            {id === "report"
              ? "result.json · result.csv · scan-report.json · events.jsonl"
              : id === "target"
                ? "시작 URL"
                : id === "browser"
                  ? "Chromium 페이지"
                  : id === "collector"
                    ? "DOM·스타일·링크"
                    : "원문과 탐지 근거"}
          </dd>
        </dl>
        <div className="config-note">
          <Icon name="Info" size={16} />
          <span>
            노드 연결은 실제 실행 단계에 적용됩니다. 연결을 변경하려면 검사를
            종료하세요.
          </span>
        </div>
      </div>
    </>
  );
}
function eventLabel(event) {
  if (event.kind === "url_discovered")
    return {
      icon: "Network",
      title: "주소 발견",
      detail: event.url,
      tone: "blue",
    };
  if (event.kind === "phase")
    return {
      icon:
        event.action === "scroll"
          ? "MousePointer2"
          : DEFINITIONS[event.stage]?.icon || "Activity",
      title: event.message,
      detail: event.selector || relativeUrl(event.url),
      tone: "teal",
    };
  if (event.kind === "http_response")
    return {
      icon: "ArrowDownLeft",
      title: `${event.http_status} ${event.method} · ${event.resource_type}`,
      detail: event.url,
      tone: "blue",
    };
  if (event.kind === "request_blocked")
    return {
      icon: "ShieldX",
      title: event.reason,
      detail: event.url,
      tone: "amber",
    };
  if (event.kind === "finding" || event.kind === "candidate") {
    const record = event.finding || event.candidate;
    return {
      icon: "ScanSearch",
      title: LABELS[record.technique || record.category] + " 발견",
      detail: record.evidence_text,
      tone: "purple",
    };
  }
  if (event.kind === "page_complete")
    return {
      icon: "CheckCheck",
      title: `페이지 검사 완료 · 링크 ${event.page.links_discovered}개`,
      detail: event.page.url,
      tone: "teal",
    };
  if (event.kind === "done")
    return {
      icon: "FileCheck2",
      title: `${STATUS[event.report.status]} · 결과 저장됨`,
      detail: event.path,
      tone: "teal",
    };
  if (event.kind === "started")
    return {
      icon: "Play",
      title: "검사를 시작했습니다",
      detail: event.url,
      tone: "teal",
    };
  return {
    icon: ["error", "warning"].includes(event.kind)
      ? "CircleAlert"
      : "Activity",
    title: event.message || event.kind,
    detail: event.url,
    tone: ["error", "warning"].includes(event.kind) ? "amber" : "gray",
  };
}
function EventRow({ event, onClick, compact = false }) {
  const label = eventLabel(event);
  return (
    <button
      className={`event-row ${compact ? "compact" : ""}`}
      onClick={onClick}
    >
      <span className={`event-icon ${label.tone}`}>
        <Icon name={label.icon} size={compact ? 13 : 17} />
      </span>
      <div>
        <strong>{label.title}</strong>
        {label.detail && <p title={label.detail}>{label.detail}</p>}
      </div>
      <time>{event.timestamp ? time(event.timestamp) : ""}</time>
    </button>
  );
}
function RecordDetail({ record, outcome, onCopy }) {
  if (!record)
    return (
      <aside className="record-panel">
        <Empty
          icon="MousePointer2"
          title="항목을 선택하세요"
          text="원문·검출 위치·탐지 근거를 확인할 수 있습니다."
        />
      </aside>
    );
  const detail = record.technique
    ? record._detail || outcome?.report.evidence_details?.[record.id] || {}
    : record;
  const keywords = detail.matched_keywords || [
    ...new Set((detail.analysis?.matches || []).map((match) => match.keyword)),
  ];
  return (
    <aside className="record-panel">
      <div className="panel-heading">
        <strong>탐지 근거</strong>
        <span className="mono">{record.id}</span>
      </div>
      <div className="record-body">
        <span className={`type-badge ${record.technique ? "purple" : "amber"}`}>
          {LABELS[record.technique || record.category]}
        </span>
        <h2>{record.technique ? "위장·은닉 의심 항목" : "광고 의심"}</h2>
        <label>탐지 원문</label>
        <blockquote>{record.evidence_text}</blockquote>
        <label>탐지 키워드</label>
        <div className="keyword-list">
          {keywords.map((term) => (
            <span key={term}>{term}</span>
          ))}
        </div>
        <label>탐지 사유</label>
        <ul>
          {(detail.style_reasons || detail.reasons || []).map(
            (reason, index) => (
              <li key={index}>{reason}</li>
            ),
          )}
        </ul>
        <label>
          페이지 URL{" "}
          <button onClick={() => onCopy(record.url)} title="URL 복사">
            <Icon name="Copy" size={13} />
          </button>
        </label>
        <pre className="detail-url">{record.url}</pre>
        <label>
          DOM 위치{" "}
          <button onClick={() => onCopy(record.location)} title="위치 복사">
            <Icon name="Copy" size={13} />
          </button>
        </label>
        <pre>{record.location}</pre>
        <details>
          <summary>원시 데이터</summary>
          <pre>{JSON.stringify({ record, detail }, null, 2)}</pre>
        </details>
      </div>
    </aside>
  );
}
createRoot(document.getElementById("root")).render(
  <ReactFlowProvider>
    <App />
  </ReactFlowProvider>,
);
