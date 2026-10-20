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
  Pause,
  Command,
  MoreHorizontal,
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
import "./theme.css";
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
  Pause,
  Command,
  MoreHorizontal,
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
  idle: "",
  running: "검사 진행 중",
  stopping: "중단 처리 중",
  pausing: "일시정지 요청",
  paused: "일시정지",
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
    return u.host + (u.pathname === "/" ? "" : u.pathname) + u.search;
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
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleTimeString("ko-KR", { hour12: false });
}
function formatElapsed(seconds) {
  return seconds < 60
    ? `${Math.floor(seconds)}초`
    : `${Math.floor(seconds / 60)}분 ${Math.floor(seconds % 60)}초`;
}
function Button({
  icon,
  children,
  className = "",
  variant = "secondary",
  ...props
}) {
  return (
    <button className={`button button-${variant} ${className}`} {...props}>
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

        <span
          className={`node-state ${data.state}`}
          title={
            data.state === "active"
              ? "실행 중"
              : data.state === "paused"
                ? "일시정지"
                : data.state === "done"
                  ? "실행됨"
                  : "대기"
          }
        />
      </div>
      <strong>{def.title}</strong>
      {id === "target" && <p title={data.url}>{shortUrl(data.url)}</p>}
      <div className="node-bottom">
        <span>{data.state ? data.caption : ""}</span>
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
const REVIEW_LABELS = {
  unreviewed: "미검토",
  confirmed: "검토 확인",
  dismissed: "제외",
};

function ActionMenu({ label, items, className = "" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    ref.current.querySelector('[role="menuitem"]:not(:disabled)')?.focus();
    const dismiss = (event) => {
      if (!ref.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);
  return (
    <div className={`action-menu ${className}`} ref={ref}>
      <button
        className="menu-trigger"
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Icon name="ChevronDown" size={16} />
      </button>
      {open && (
        <div
          className="action-menu-panel"
          role="menu"
          aria-label={label}
          onKeyDown={(event) => {
            const buttons = [
              ...event.currentTarget.querySelectorAll("button:not(:disabled)"),
            ];
            const index = buttons.indexOf(document.activeElement);
            if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
              event.preventDefault();
              const next =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? buttons.length - 1
                    : (index +
                        (event.key === "ArrowDown" ? 1 : -1) +
                        buttons.length) %
                      buttons.length;
              buttons[next]?.focus();
            }
            if (event.key === "Escape") {
              setOpen(false);
              ref.current.querySelector(".menu-trigger").focus();
            }
          }}
        >
          {items.map((item) => (
            <button
              role="menuitem"
              key={item.label}
              disabled={item.disabled}
              className={item.danger ? "danger-text" : ""}
              onClick={() => {
                setOpen(false);
                item.action();
              }}
            >
              <Icon name={item.icon} size={16} />
              <span>{item.label}</span>
              {item.shortcut && <kbd>{item.shortcut}</kbd>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CommandPalette({ commands, onClose }) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const choices = commands.filter(
    (command) =>
      command.label.includes(query) ||
      command.keywords?.includes(query.toLowerCase()),
  );
  const run = (command) => {
    if (command && !command.disabled) {
      onClose();
      command.action();
    }
  };
  return (
    <div className="modal-backdrop command-backdrop" onClick={onClose}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="빠른 명령"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Escape") onClose();
          if (["ArrowDown", "ArrowUp"].includes(event.key)) {
            event.preventDefault();
            setIndex(
              (value) =>
                (value +
                  (event.key === "ArrowDown" ? 1 : -1) +
                  choices.length) %
                Math.max(1, choices.length),
            );
          }
          if (event.key === "Enter") {
            event.preventDefault();
            run(choices[index]);
          }
        }}
      >
        <div className="command-search">
          <Icon name="Search" />
          <input
            autoFocus
            aria-label="명령 검색"
            placeholder="무엇을 할까요?"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setIndex(0);
            }}
          />
          <kbd>ESC</kbd>
        </div>
        <div className="command-results" role="listbox" aria-label="명령 목록">
          {choices.map((command, i) => (
            <button
              role="option"
              aria-selected={i === index}
              key={command.label}
              disabled={command.disabled}
              onMouseEnter={() => setIndex(i)}
              onClick={() => run(command)}
            >
              <Icon name={command.icon} size={17} />
              <span>
                {command.label}
                <small>{command.description}</small>
              </span>
              {command.shortcut && <kbd>{command.shortcut}</kbd>}
            </button>
          ))}
          {!choices.length && <p>일치하는 명령 없음</p>}
        </div>
        <footer>
          ↑↓ 이동 <span>Enter 실행</span>
          <span>Ctrl K 열기</span>
        </footer>
      </section>
    </div>
  );
}

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
  const [reviewData, setReviewData] = useState({ revision: 0, items: {} });
  const [reviewFilter, setReviewFilter] = useState("all");
  const [pageSearch, setPageSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [reviewSaving, setReviewSaving] = useState(false);
  const [palette, setPalette] = useState(false);
  const [capabilities, setCapabilities] = useState(null);
  const [visualPreview, setVisualPreview] = useState(false);
  const [runTarget, setRunTarget] = useState("");
  const timelineRef = useRef(null),
    autoScroll = useRef(true);
  const running = ["running", "pausing", "paused", "stopping"].includes(status);
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
    setSelectedNode(null);
    setZoomPreview(false);
    if (value.events) {
      setSearch("");
      setFilter("all");
      setReviewFilter("all");
      setPageSearch("");
      setPageFilter("visited");
      setEventFilter("all");
    }
    setRunTarget(value.result.meta.entry_url);
    setSelectedRecord(null);
    setReviewData(value.reviews || { revision: 0, items: {} });
    setSelectedIds(new Set());
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
          value.events
            .filter((e) => e.kind === "phase" || e.kind === "started")
            .map((e) => (e.kind === "started" ? "target" : e.stage)),
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
    if (!value.report.desktop_options?.demo)
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
        setVisualPreview(Boolean(state.preview_only));
        const prefs = state.preferences || {};
        if (typeof prefs.url === "string") setUrl(prefs.url);
        if (Number.isInteger(prefs.maxPages)) setMaxPages(prefs.maxPages);
        if (Number.isFinite(prefs.timeout)) setTimeoutValue(prefs.timeout);
        if (["default", "test", "public"].includes(prefs.profile))
          setProfile(prefs.profile);
        if (typeof prefs.livePreview === "boolean")
          setLivePreview(prefs.livePreview);
        api
          .capabilities()
          .then(setCapabilities)
          .catch(() => {});
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
      if (event.kind === "control")
        setStatus((previous) =>
          previous === "stopping" ? previous : event.state,
        );
      if (
        event.url &&
        ["phase", "started", "page_complete"].includes(event.kind)
      )
        setCurrentUrl(event.url);
      if (event.kind === "started") {
        setRunTarget(event.url);
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
      }
      if (event.kind === "error") {
        setStatus("failed");
        tell(event.message, "error");
      }
    });
  }, [appendEvent, applyOutcome]);
  useEffect(() => {
    if (
      !booted ||
      !Number.isInteger(Number(maxPages)) ||
      Number(maxPages) < 1 ||
      Number(maxPages) > 10000 ||
      !Number.isFinite(Number(timeout)) ||
      Number(timeout) <= 0 ||
      Number(timeout) > 1800
    )
      return;
    const id = window.setTimeout(
      () =>
        api
          .preferences({
            url,
            maxPages: Number(maxPages),
            timeout: Number(timeout),
            profile,
            livePreview,
          })
          .catch((error) => tell(error.message, "error")),
      450,
    );
    return () => window.clearTimeout(id);
  }, [booted, url, maxPages, timeout, profile, livePreview]);
  useEffect(() => {
    setSelectedIds(new Set());
  }, [filter, reviewFilter, search]);
  useEffect(() => {
    const keydown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPalette((value) => !value);
      }
      if (event.key === "Escape") {
        setPalette(false);
        setSettings(false);
        setSelectedEvent(null);
        setZoomPreview(false);
      }
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, []);
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
              : status === "paused"
                ? "paused"
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
                    ? ""
                    : outcome
                      ? "JSON · CSV 저장 완료"
                      : "실행 종료 후 저장";
        if (!enabled) caption = "분석 경로 연결 안 됨";
        return {
          ...node,
          type: "stage",
          deletable: false,
          data: {
            state,
            caption,
            url:
              outcome?.result.meta.entry_url ||
              (running ? runTarget || url : url),
            editable: !running,
          },
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
      runTarget,
    ],
  );
  const flowEdges = useMemo(
    () =>
      flow.edges.map((edge) => ({
        ...edge,
        type: "default",
        animated:
          status === "running" &&
          (edge.target === active || edge.source === active),
        style: {
          stroke:
            edge.target === active
              ? "#53f0bc"
              : visited.has(edge.source)
                ? {
                    blue: "#438dff",
                    teal: "#00d99a",
                    purple: "#a780ff",
                    amber: "#57a5cf",
                  }[DEFINITIONS[edge.source].tone]
                : "#61738e",
          strokeWidth: edge.target === active ? 2.8 : 1.8,
        },
      })),
    [flow.edges, status, active, visited],
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
  const start = async (demo = false, overrides = {}) => {
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
    let entry = (overrides.url || url).trim();
    if (!entry && !demo) {
      tell("검사할 URL을 입력하세요.", "error");
      return;
    }
    if (!entry.includes("://"))
      entry = /^(?:\d{1,3}\.){3}|^localhost/.test(entry)
        ? "http://" + entry
        : "https://" + entry;
    if (!demo) {
      try {
        const target = new URL(entry);
        if (
          !["http:", "https:"].includes(target.protocol) ||
          target.username ||
          target.password
        )
          throw new Error();
      } catch {
        tell("http 또는 https 웹사이트 주소를 입력하세요.", "error");
        return;
      }
    }
    const nextFlow = overrides.singlePage
      ? { ...flow, follow_links: false }
      : flow;
    if (!demo) setUrl(entry);
    if (overrides.singlePage) setFlow(nextFlow);
    setStatus("running");
    setRunTarget(demo ? "" : entry);
    setRecords([]);
    setSearch("");
    setFilter("all");
    setReviewFilter("all");
    setPages([]);
    setPending([]);
    setEvents([]);
    setPreview(null);
    setOutcome(null);
    setReviewData({ revision: 0, items: {} });
    setSelectedIds(new Set());
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
        workflow: nextFlow,
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
  const pause = () =>
    action(async () => {
      const resuming = status === "paused" || status === "pausing";
      setStatus(resuming ? "running" : "pausing");
      try {
        await (resuming ? api.resume() : api.pause());
      } catch (error) {
        const value = await api.state();
        setStatus(value.status);
        throw error;
      }
    });
  const stop = () =>
    action(async () => {
      setStatus("stopping");
      await api.stop();
    });
  const updateReview = (ids, status, note) =>
    action(async () => {
      setReviewSaving(true);
      try {
        const value = await api.review({
          ids,
          status,
          ...(note === undefined ? {} : { note }),
          expected_revision: reviewData.revision,
        });
        setReviewData(value);
        setSelectedIds(new Set());
        tell(`${ids.length}건 검토 저장`, "success");
      } finally {
        setReviewSaving(false);
      }
    });
  const commands = [
    {
      label: "검사 실행",
      keywords: "run scan",
      description: "현재 URL과 구성으로 검사",
      icon: "Play",
      disabled: running || !booted,
      action: () => start(),
    },
    {
      label: "데모 검사",
      keywords: "demo",
      description: "로컬 예제 · 필수 탐지 14건",
      icon: "FlaskConical",
      disabled: running || !booted,
      action: () => start(true),
    },
    {
      label:
        status === "paused" || status === "pausing" ? "검사 재개" : "일시정지",
      icon: "Pause",
      disabled: !running || status === "stopping",
      action: pause,
    },
    {
      label: "검사 중단",
      icon: "Square",
      disabled: !running || status === "stopping",
      action: stop,
    },
    ...[
      ["workflow", "검사 구성", "Workflow"],
      ["results", "탐지 내역", "ListFilter"],
      ["pages", "탐색 경로", "Network"],
      ["activity", "진행 기록", "Activity"],
      ["history", "검사 기록", "History"],
    ].map(([id, label, icon]) => ({ label, icon, action: () => setView(id) })),
    {
      label: "결과 불러오기",
      icon: "FolderOpen",
      disabled: running,
      action: load,
    },
    {
      label: "CSV 저장",
      icon: "Download",
      disabled: !outcome || running,
      action: () =>
        action(async () => {
          const value = await api.exportCSV();
          if (value) tell("CSV를 저장했습니다.", "success");
        }),
    },
    {
      label: "검사 설정",
      icon: "SlidersHorizontal",
      action: () => setSettings(true),
    },
  ];
  const filteredRecords = records.filter(
    (record) =>
      (reviewFilter === "all" ||
        (reviewData.items[record.id]?.status || "unreviewed") ===
          reviewFilter) &&
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
  const phaseTitle = ["paused", "pausing", "stopping"].includes(status)
    ? STATUS[status]
    : active
      ? STAGE_NAMES[active]
      : STATUS[status];
  const displayedPreviewUrl = preview
    ? typeof preview.url === "string"
      ? preview.url
      : ""
    : currentUrl || url;
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
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="topbar-right">
            <button
              className="command-launcher"
              onClick={() => setPalette(true)}
              aria-label="빠른 명령"
            >
              <Icon name="Search" size={14} />
              <span>빠른 명령</span>
              <kbd>Ctrl K</kbd>
            </button>
            {visualPreview && (
              <span className="local-label">디자인 미리보기 · 저장된 데모</span>
            )}
          </div>
        </header>
        <section className="heading">
          <div>
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
          </div>
          <div className="heading-actions">
            <Button
              icon="FolderOpen"
              variant="ghost"
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
          <div className="target-field">
            <label htmlFor="target-url">
              {outcome ? "다음 검사 대상" : "검사 대상"}{" "}
            </label>
            <input
              id="target-url"
              aria-label="검사 대상 URL"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              disabled={running}
              placeholder="https://example.go.kr"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !running) start();
              }}
            />
          </div>
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
          <div className="run-actions">
            {running ? (
              <>
                <Button
                  icon={
                    status === "paused" || status === "pausing"
                      ? "Play"
                      : "Pause"
                  }
                  variant="secondary"
                  disabled={status === "stopping"}
                  onClick={pause}
                  title="현재 페이지 검사가 끝나면 일시정지합니다."
                >
                  {status === "paused"
                    ? "검사 재개"
                    : status === "pausing"
                      ? "정지 요청 취소"
                      : "일시정지"}
                </Button>
                <Button
                  icon="Square"
                  variant="danger"
                  className="stop-button"
                  onClick={stop}
                  disabled={status === "stopping"}
                >
                  검사 중단
                </Button>
              </>
            ) : (
              <>
                <Button
                  icon="Play"
                  className="primary"
                  disabled={!booted}
                  onClick={() => start()}
                >
                  검사 실행
                </Button>
                <ActionMenu
                  label="검사 옵션"
                  items={[
                    {
                      label: "데모 검사",
                      icon: "FlaskConical",
                      disabled: !booted,
                      action: () => start(true),
                    },
                    {
                      label: "이 페이지만 검사",
                      icon: "ScanLine",
                      disabled: !booted,
                      action: () => start(false, { singlePage: true }),
                    },
                    {
                      label: "검사 설정",
                      icon: "SlidersHorizontal",
                      action: () => setSettings(true),
                    },
                  ]}
                />
              </>
            )}
          </div>
        </section>
        <section
          className="summary-strip"
          hidden={!running && !outcome && status !== "failed"}
        >
          <div className="scan-status">
            <span
              className={
                running
                  ? status === "paused"
                    ? "warning-dot"
                    : "pulse-dot"
                  : status === "failed"
                    ? "error-dot"
                    : "ready-dot"
              }
            />
            <strong>{phaseTitle}</strong>
            {elapsed > 0 && <span>{formatElapsed(elapsed)}</span>}
            {outcome && (
              <span
                className="outcome-target"
                title={outcome.result.meta.entry_url}
              >
                {outcome.report.desktop_options?.demo
                  ? "로컬 데모 결과"
                  : shortUrl(outcome.result.meta.entry_url)}
              </span>
            )}
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
                  <button
                    className="follow-toggle"
                    aria-pressed={flow.follow_links}
                    disabled={running}
                    title="하위 링크 탐색"
                    onClick={() =>
                      setFlow((value) => ({
                        ...value,
                        follow_links: !value.follow_links,
                      }))
                    }
                  >
                    <Icon name="GitBranch" size={14} />
                    <span>하위 링크</span>
                  </button>
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
                    <Background color="#34425c" gap={24} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap
                      nodeColor={(node) =>
                        ({
                          blue: "#3182f6",
                          teal: "#00d38b",
                          purple: "#a57aff",
                          amber: "#57a5cf",
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
                        <strong>미리보기</strong>
                      </span>
                    </div>
                    <div className="browser-preview">
                      <div className="browser-chrome">
                        <span className="browser-dots">
                          <i />
                          <i />
                          <i />
                        </span>
                        <span title={displayedPreviewUrl}>
                          <Icon
                            name={
                              displayedPreviewUrl.startsWith("https:")
                                ? "LockKeyhole"
                                : "Globe2"
                            }
                            size={11}
                          />
                          {displayedPreviewUrl
                            ? shortUrl(displayedPreviewUrl)
                            : "캡처 주소 없음"}
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
                            {livePreview ? "검사 화면 없음" : "미리보기 꺼짐"}
                          </strong>
                        </div>
                      )}
                      <div className="preview-caption">
                        <span>
                          {preview?.timestamp ? time(preview.timestamp) : "—"}
                        </span>
                      </div>
                    </div>
                    {currentUrl && currentUrl !== preview?.url && (
                      <div className="current-location">
                        <span>검사 위치</span>
                        <strong title={currentUrl}>
                          {currentUrl
                            ? relativeUrl(currentUrl)
                            : "검사를 시작해 주세요."}
                        </strong>
                      </div>
                    )}
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
                  <select
                    className="review-select"
                    aria-label="검토 상태 필터"
                    value={reviewFilter}
                    onChange={(event) => setReviewFilter(event.target.value)}
                  >
                    <option value="all">검토 전체</option>
                    {Object.entries(REVIEW_LABELS).map(([id, label]) => (
                      <option value={id} key={id}>
                        {label}
                      </option>
                    ))}
                  </select>
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
                {selectedIds.size > 0 && (
                  <div className="bulk-toolbar">
                    <strong>{selectedIds.size}개 선택</strong>
                    <Button
                      icon="CheckCheck"
                      variant="ghost"
                      disabled={reviewSaving || running}
                      onClick={() =>
                        updateReview([...selectedIds], "confirmed")
                      }
                    >
                      검토 확인
                    </Button>
                    <Button
                      icon="X"
                      variant="ghost"
                      disabled={reviewSaving || running}
                      onClick={() =>
                        updateReview([...selectedIds], "dismissed")
                      }
                    >
                      검토 제외
                    </Button>
                    <Button
                      icon="RotateCcw"
                      variant="ghost"
                      disabled={reviewSaving || running}
                      onClick={() =>
                        updateReview([...selectedIds], "unreviewed")
                      }
                    >
                      미검토
                    </Button>
                    <button
                      aria-label="선택 해제"
                      className="bulk-clear"
                      onClick={() => setSelectedIds(new Set())}
                    >
                      <Icon name="X" size={15} />
                    </button>
                  </div>
                )}
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th className="selection-cell">
                          <input
                            type="checkbox"
                            aria-label="표시 항목 전체 선택"
                            disabled={
                              running || !outcome || !filteredRecords.length
                            }
                            checked={
                              filteredRecords.length > 0 &&
                              filteredRecords
                                .slice(0, 500)
                                .every((record) => selectedIds.has(record.id))
                            }
                            onChange={(event) =>
                              setSelectedIds(
                                event.target.checked
                                  ? new Set(
                                      filteredRecords
                                        .slice(0, 500)
                                        .map((record) => record.id),
                                    )
                                  : new Set(),
                              )
                            }
                          />
                        </th>
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
                          <td
                            className="selection-cell"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              aria-label={`${record.id} 선택`}
                              disabled={running || !outcome || reviewSaving}
                              checked={selectedIds.has(record.id)}
                              onChange={(event) =>
                                setSelectedIds((previous) => {
                                  const next = new Set(previous);
                                  if (event.target.checked) {
                                    if (next.size < 500) next.add(record.id);
                                  } else next.delete(record.id);
                                  return next;
                                })
                              }
                            />
                          </td>
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
                            <span
                              className={`review-label review-${reviewData.items[record.id]?.status || "unreviewed"}`}
                            >
                              {
                                REVIEW_LABELS[
                                  reviewData.items[record.id]?.status ||
                                    "unreviewed"
                                ]
                              }
                            </span>
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
                </div>
              </section>
              <RecordDetail
                key={selectedRecord?.id || "empty"}
                record={selectedRecord}
                outcome={outcome}
                review={
                  selectedRecord ? reviewData.items[selectedRecord.id] : null
                }
                onReview={(status, note) =>
                  updateReview([selectedRecord.id], status, note)
                }
                reviewDisabled={running || !outcome || reviewSaving}
                onRecheck={() =>
                  start(false, { url: selectedRecord.url, singlePage: true })
                }
                recheckDisabled={
                  running || !booted || outcome?.report.desktop_options?.demo
                }
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
                    value={pageSearch}
                    onChange={(event) => setPageSearch(event.target.value)}
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
                        page.url
                          .toLowerCase()
                          .includes(pageSearch.toLowerCase()),
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
      {palette && (
        <CommandPalette commands={commands} onClose={() => setPalette(false)} />
      )}
      {settings && (
        <div className="modal-backdrop" onClick={() => setSettings(false)}>
          <section
            className="modal settings-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
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
            <details className="automation-info">
              <summary>에이전트 확장 규격</summary>
              <p>
                로컬 도구 {capabilities?.tools?.length || 0}개 · 규격 v
                {capabilities?.protocol_version || 1}. 실행 ID와 입력 형식을
                검증하며, 검사 제어·근거 조회·검토 기록에 같은 기능을
                사용합니다.
              </p>
              <small>
                현재 AI 제공자는 연결하지 않았습니다. 페이지 본문과 광고 문구는
                분석 대상 데이터로 취급합니다.
              </small>
            </details>
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
            role="dialog"
            aria-modal="true"
            aria-label="검사 화면"
            onClick={(event) => event.stopPropagation()}
          >
            <div>
              <strong>검사 화면</strong>
              <span>{preview.url}</span>
              <button
                aria-label="미리보기 닫기"
                onClick={() => setZoomPreview(false)}
              >
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
function RecordDetail({
  record,
  outcome,
  onCopy,
  review,
  onReview,
  reviewDisabled,
  onRecheck,
  recheckDisabled,
}) {
  const [note, setNote] = useState(review?.note || "");
  useEffect(() => setNote(review?.note || ""), [record?.id, review?.note]);
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
  const reasons = [...(detail.style_reasons || detail.reasons || [])];
  for (const match of detail.analysis?.matches || []) {
    if (
      (record.technique === "HOMOGLYPH" && match.homoglyph) ||
      (record.technique === "JAMO" && match.jamo)
    ) {
      const span = record.evidence_text.slice(...match.source_span);
      reasons.push(
        `원문 ‘${span}’에서 ${record.technique === "JAMO" ? "분리된 자모" : "닮은꼴 문자"}를 확인했습니다. 광고 키워드: ${match.keyword}`,
      );
    }
  }
  if (record.technique === "HOMOGLYPH")
    for (const match of detail.analysis?.contextual_homoglyphs || [])
      reasons.push(`${match.reason}: ${match.original} → ${match.canonical}`);
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
        <div className="review-control">
          <span
            className={`review-label review-${review?.status || "unreviewed"}`}
          >
            {REVIEW_LABELS[review?.status || "unreviewed"]}
          </span>
          <ActionMenu
            label="항목 작업"
            items={[
              {
                label: outcome?.report.desktop_options?.demo
                  ? "데모 재실행은 검사 옵션에서"
                  : "이 페이지만 재검사",
                icon: "RotateCcw",
                disabled: recheckDisabled,
                action: onRecheck,
              },
              {
                label: "원문 복사",
                icon: "Copy",
                action: () => onCopy(record.evidence_text),
              },
              {
                label: "URL 복사",
                icon: "Globe2",
                action: () => onCopy(record.url),
              },
            ]}
          />
        </div>
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
          {(reasons.length
            ? [...new Set(reasons)]
            : [
                "광고 키워드와 해당 기법의 분석 결과를 근거로 검출했습니다. 상세 값은 원시 데이터에서 확인할 수 있습니다.",
              ]
          ).map((reason, index) => (
            <li key={index}>{reason}</li>
          ))}
        </ul>
        <div className="review-editor">
          <label htmlFor="review-note">
            검토 메모 <small>{note.length}/2000</small>
          </label>
          <textarea
            id="review-note"
            aria-label="검토 메모"
            maxLength={2000}
            disabled={reviewDisabled}
            placeholder="판단 근거, 확인할 사항"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <div className="review-actions">
            <Button
              icon="CheckCheck"
              disabled={reviewDisabled}
              onClick={() => onReview("confirmed", note)}
            >
              검토 확인
            </Button>
            <Button
              icon="X"
              variant="ghost"
              disabled={reviewDisabled}
              onClick={() => onReview("dismissed", note)}
            >
              제외
            </Button>
            <ActionMenu
              label="검토 작업"
              items={[
                {
                  label: "메모 저장",
                  icon: "Save",
                  disabled: reviewDisabled,
                  action: () => onReview(review?.status || "unreviewed", note),
                },
                {
                  label: "미검토로 변경",
                  icon: "RotateCcw",
                  disabled: reviewDisabled,
                  action: () => onReview("unreviewed", note),
                },
              ]}
            />
          </div>
          {review?.updated_at && (
            <small>
              {review.actor === "agent" ? "에이전트" : "사용자"} ·{" "}
              {new Date(review.updated_at).toLocaleString("ko-KR")}
            </small>
          )}
        </div>
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
