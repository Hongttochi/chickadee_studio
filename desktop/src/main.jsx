import UpdateSettings from "./UpdateSettings.jsx";
import React, {
  useState,
  useId,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import { createRoot } from "react-dom/client";
import EvidenceScreenshot from "./EvidenceScreenshot.jsx";
import ImageOCR from "./ImageOCR.jsx";
import LocalAIAnalysis from "./LocalAIAnalysis.jsx";
import RuntimeSettings from "./RuntimeSettings.jsx";
import ShortcutSettings from "./ShortcutSettings.jsx";
import { defaults as defaultShortcuts, validateShortcuts, fromEvent, keyLabel } from "./shortcuts.mjs";
import SettingsNav from "./SettingsNav.jsx";
import ScheduleSettings from "./ScheduleSettings.jsx";
import NotificationSettings from "./NotificationSettings.jsx";
import GrokSettings from "./GrokSettings.jsx";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  applyNodeChanges,
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
  Dice5,
  TrendingUp,
  Landmark,
  ShoppingCart,
  ShieldAlert,
  EyeOff,
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
  Settings,
  Bell,
  Sparkles,
  ArrowLeft,
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
  branchEnabled,
} from "./workflow.mjs";
import "./style.css";
import "./theme.css";
import brandMark from "../assets/app-mark.png";
import LoginPrompt from "./LoginPrompt.jsx";
import InspectionInsights from "./InspectionInsights.jsx";
import targetMap from "../assets/map.png";
import browserImage from "../assets/browser.png";
import collectionImage from "../assets/collection.png";
import duplicateRemoveImage from "../assets/duplicate_remove.png";
import paddleOCRImage from "../assets/paddle_ocr.png";
import searchImage from "../assets/search.png";
import hierarchyImage from "../assets/hierarchy.png";
import csvImage from "../assets/csv.png";
import diceImage from "../assets/dice.png";
import profitsImage from "../assets/profits.png";
import creditCardImage from "../assets/3d-credit-card.png";
import shoppingCartImage from "../assets/shopping-cart.png";
import warningImage from "../assets/image_warning.png";
import errorImage from "../assets/error.png";
import pauseImage from "../assets/pause.png";
import resumeImage from "../assets/resume.png";
import stopImage from "../assets/stop.png";
import checkImage from "../assets/check.png";
import deleteImage from "../assets/delete.png";
import saveImage from "../assets/save.png";
import refreshImage from "../assets/refresh.png";
import noFileImage from "../assets/no_file.png";
import noLocationImage from "../assets/no_location.png";
import waitDetectionImage from "../assets/wait_detection.png";
import noRecordImage from "../assets/no_record.png";
import Tutorial, { rememberTutorial, shouldShowTutorial } from "./Tutorial.jsx";

const nodeImages = {
  target: targetMap,
  browser: browserImage,
  collector: collectionImage,
  ocr: paddleOCRImage,
  dedup: duplicateRemoveImage,
  techniques: searchImage,
  candidates: hierarchyImage,
  report: csvImage,
};

const api = window.chickadee;
const NODE_LAYOUT_KEY = "chickadee.node-layout.v3";
function restoreNodeLayout(nodes) {
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(NODE_LAYOUT_KEY));
  } catch {}
  const defaults = defaultWorkflow().nodes;
  return nodes.map(node => {
    const position = saved?.[node.id];
    const valid = position && [position.x, position.y].every(value =>
      Number.isFinite(value) && Math.abs(value) < 10000);
    return { ...node, position: valid ? position : defaults.find(item => item.id === node.id).position };
  });
}
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
  Dice5,
  TrendingUp,
  Landmark,
  ShoppingCart,
  ShieldAlert,
  EyeOff,
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
  Settings,
  Bell,
  Sparkles,
  ArrowLeft,
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
  AI_CONTEXT: "AI 광고 문맥",
};
const TYPE_ICONS = {
  GAMBLING: "Dice5",
  INVESTMENT: "TrendingUp",
  LOAN: "Landmark",
  COMMERCIAL: "ShoppingCart",
  AI_CONTEXT: "Sparkles",
  ADULT: "ShieldAlert",
  HOMOGLYPH: "Fingerprint",
  JAMO: "TextSearch",
  TRANSPARENT: "EyeOff",
  OFFSCREEN: "PanelsTopLeft",
};
const TYPE_IMAGES = {
  GAMBLING: diceImage,
  INVESTMENT: profitsImage,
  LOAN: creditCardImage,
  COMMERCIAL: shoppingCartImage,
};
function TypeBadgeContent({ type }) {
  return <>
    {TYPE_IMAGES[type]
      ? <img className="type-badge-image" src={TYPE_IMAGES[type]} alt="" width={16} height={16} draggable={false} />
      : <Icon name={TYPE_ICONS[type] || "CircleAlert"} size={13} />}
    <span>{LABELS[type] || type}</span>
  </>;
}

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
  image,
  children,
  className = "",
  variant = "secondary",
  ...props
}) {
  return (
    <button className={`button button-${variant} ${className}`} {...props}>
      {image ? <img className="button-image" src={image} alt="" width={20} height={20} draggable={false} /> : icon && <Icon name={icon} size={16} />}
      <span>{children}</span>
    </button>
  );
}
function FlowNode({ id, data, selected }) {
  const def = DEFINITIONS[id];
  const positions = { left: Position.Left, right: Position.Right, top: Position.Top, bottom: Position.Bottom };
  const status = { active: "실행 중", paused: "일시정지", done: "실행됨", error: "오류", disabled: "사용 안 함" }[data.state] || "대기";
  const statusIcon = { active: "LoaderCircle", paused: "Pause", done: "Check", error: "X", disabled: "Unplug" }[data.state];
  const caption = id === "target" ? shortUrl(data.url) : data.state && data.caption ? data.caption : def.subtitle;
  return (
    <div className={`flow-node tone-${def.tone} ${data.state || ""} ${selected ? "selected" : ""}`}>
      <div className="node-tile">
        {def.input && <Handle id="in" type="target" position={positions[def.input]} isConnectable={false} />}
        <img src={nodeImages[id]} alt="" width={44} height={44} className={`node-symbol node-symbol-${id}`} draggable={false} />
        {statusIcon && (
          <span className="node-run-state" title={status} aria-label={status}>
            <Icon name={statusIcon} size={15} className={data.state === "active" ? "spin" : ""} />
          </span>
        )}
        {def.output && <Handle id="out" type="source" position={positions[def.output]} isConnectable={false} />}
      </div>
      <strong>{def.title}</strong>
      <p className="node-caption" title={caption}>{caption}</p>
      {["active", "paused", "error", "disabled"].includes(data.state) && <span className="node-state-text">{status}</span>}
    </div>
  );
}

const nodeTypes = { stage: FlowNode };
const REVIEW_LABELS = {
  unreviewed: "미검토",
  confirmed: "검토 확인",
  dismissed: "제외",
};

function AnimatedTabs({ value, children }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const tabs = ref.current;
    const measure = () => {
      const active = tabs.querySelector("button.active");
      if (!active) {
        tabs.style.setProperty("--tab-width", "0px");
        return;
      }
      tabs.style.setProperty("--tab-left", `${active.offsetLeft}px`);
      tabs.style.setProperty("--tab-top", `${active.offsetTop + active.offsetHeight - 2}px`);
      tabs.style.setProperty("--tab-width", `${active.offsetWidth}px`);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(tabs);
    for (const button of tabs.querySelectorAll("button")) observer.observe(button);
    return () => observer.disconnect();
  }, [value]);
  return <div className="segmented animated-tabs" ref={ref}>{children}<span className="tab-indicator" aria-hidden="true" /></div>;
}

function ActionMenu({ label, items, className = "", triggerImage, triggerIcon = "ChevronDown", triggerText, disabled = false }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    (ref.current.querySelector('[role="menuitemradio"][aria-checked="true"]') ||
      ref.current.querySelector('.action-menu-panel button:not(:disabled)'))?.focus();
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
        disabled={disabled}
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {triggerText && <span>{triggerText}</span>}
        {triggerImage ? <img className="button-image" src={triggerImage} alt="" width={20} height={20} draggable={false} /> : <Icon name={triggerIcon} size={16} />}
      </button>
        <div
          className="action-menu-panel"
          data-open={open}
          aria-hidden={!open}
          inert={!open}
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
              role={typeof item.selected === "boolean" ? "menuitemradio" : "menuitem"}
              aria-checked={typeof item.selected === "boolean" ? item.selected : undefined}
              key={item.label}
              disabled={item.disabled}
              className={item.danger ? "danger-text" : ""}
              onClick={() => {
                setOpen(false);
                ref.current.querySelector(".menu-trigger").focus();
                item.action();
              }}
            >
              {typeof item.selected === "boolean"
                ? <span className="menu-selection-mark" aria-hidden="true">{item.selected && <Icon name="Check" size={16} />}</span>
                : item.image
                ? <img className={`menu-item-image ${item.imageClassName || ""}`} src={item.image} alt="" width={20} height={20} draggable={false} />
                : <Icon name={item.icon} size={16} />}
              <span>{item.label}</span>
              {item.shortcut && <kbd>{item.shortcut}</kbd>}
            </button>
          ))}
        </div>
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
  const [liveScreenshots, setLiveScreenshots] = useState({});
  const [preview, setPreview] = useState(null),
    [currentUrl, setCurrentUrl] = useState(""),
    [queue, setQueue] = useState(0),
    [discovered, setDiscovered] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null),
    [selectedRecord, setSelectedRecord] = useState(null),
    [selectedEvent, setSelectedEvent] = useState(null);
  const [monitorOpen, setMonitorOpen] = useState(false);
  const [scanNotice, setScanNotice] = useState(false);
  const startRequest = useRef(false);
  const lastSelectedRecord = useRef(null);
  useEffect(() => {
    if (selectedRecord) lastSelectedRecord.current = selectedRecord;
  }, [selectedRecord]);
  const detailRecord = selectedRecord || lastSelectedRecord.current;
  const [pending, setPending] = useState([]),
    [pageFilter, setPageFilter] = useState("visited");
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all"),
    [eventFilter, setEventFilter] = useState("all"),
    [notice, setNotice] = useState(null);
  const [reviewNotice, setReviewNotice] = useState(null);
  const [agentConfig, setAgentConfig] = useState({ model: "openai/gpt-oss-20b", token_limit: 24000, call_limit: 6 });
  const [inspectionTab, setInspectionTab] = useState("graph");
  const [shortcuts, setShortcuts] = useState(defaultShortcuts);
  const [settingsTab, setSettingsTab] = useState("general");
  const settingsReturnView = useRef("workflow");
  const openSettings = (section = "general") => { setSettingsTab(typeof section === "string" ? section : "general"); settingsReturnView.current = view === "settings" ? settingsReturnView.current : view; setView("settings"); };
  const [profile, setProfile] = useState("default"),
    [maxPages, setMaxPages] = useState(100),
    [timeout, setTimeoutValue] = useState(300);
  const [scanInterval, setScanInterval] = useState(0.5);
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
  const [tutorial, setTutorial] = useState(shouldShowTutorial);
  useEffect(() => {
    if (!booted || flow.nodes.some(node => node.dragging)) return;
    try {
      localStorage.setItem(NODE_LAYOUT_KEY, JSON.stringify(Object.fromEntries(
        flow.nodes.map(node => [node.id, node.position]),
      )));
    } catch {
      // Keep the canvas usable if browser storage is unavailable.
    }
  }, [booted, flow.nodes]);
  const [canvasApi, setCanvasApi] = useState(null);
  useEffect(() => {
    const canvas = document.querySelector(".flow-area");
    if (!canvasApi || !canvas || view !== "workflow") return;
    let frame;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        canvasApi.fitView({ padding: 0.2, maxZoom: 0.75, minZoom: 0.2, duration: 0 });
      });
    });
    observer.observe(canvas);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [canvasApi, view]);
  const focusTargetAfterGuide = useRef(false);
  useEffect(() => {
    if (!tutorial && focusTargetAfterGuide.current) {
      focusTargetAfterGuide.current = false;
      document.getElementById("target-url")?.focus();
    }
  }, [tutorial]);
  const closeTutorial = () => {
    rememberTutorial();
    setTutorial(false);
  };
  const timelineRef = useRef(null),
    autoScroll = useRef(true);
  const [loginRequest, setLoginRequest] = useState(null);
  const running = ["running", "pausing", "paused", "stopping"].includes(status);
  const tell = (message, type = "info") => {
    if (message === "이미 검사 중입니다.") {
      setScanNotice(true);
      return;
    }
    setNotice({ message, type, key: Date.now() });
  };
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
    if ([1, 2].includes(value.report.workflow?.version)) {
      try {
        const restored = normalizeWorkflow(value.report.workflow);
        setFlow(current => ({
          ...restored,
          nodes: restored.nodes.map(node => ({
            ...current.nodes.find(item => item.id === node.id),
            ...node,
            position: current.nodes.find(item => item.id === node.id)?.position || node.position,
          })),
        }));
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
        try { if (prefs.shortcuts) setShortcuts(validateShortcuts(prefs.shortcuts)); } catch {}
        if (typeof prefs.url === "string") setUrl(prefs.url);
        if (Number.isFinite(prefs.scanInterval) && prefs.scanInterval >= 0 && prefs.scanInterval <= 30) setScanInterval(prefs.scanInterval);
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
            const restored = normalizeWorkflow(state.workflow);
            setFlow({ ...restored, nodes: restoreNodeLayout(restored.nodes) });
          } catch {
            setFlow(current => ({ ...current, nodes: restoreNodeLayout(current.nodes) }));
          }
        } else {
          setFlow(current => ({ ...current, nodes: restoreNodeLayout(current.nodes) }));
        }
        setLoginRequest(state.authentication || null);
        setBooted(true);
      })
      .catch((error) => tell(error.message, "error"));
    return api.onEvent((event) => {
      if (event.kind === "login_required") setLoginRequest(event);
      if (["login_finished", "done", "started"].includes(event.kind)) setLoginRequest(null);
      if (event.kind === "evidence_screenshot") {
        if (event.screenshot && event.screenshot_id) setLiveScreenshots(previous => ({ ...previous, [event.screenshot_id]: event.screenshot }));
        return;
      }
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
        setRecords([]); setPages([]); setPending([]); setEvents([{ ...event, key: crypto.randomUUID() }]); setPreview(null); setOutcome(null); setLiveScreenshots({});
        setReviewData({ revision: 0, items: {} }); setSelectedIds(new Set()); setSelectedRecord(null);
        setDiscovered(0); setQueue(0); setElapsed(0); setSearch(""); setFilter("all"); setReviewFilter("all");
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
          ...items.filter(item => item.id !== event.finding.id),
          { ...event.finding, _detail: event.detail },
        ]);
      if (event.kind === "candidate")
        setRecords((items) => [...items.filter(item => item.id !== event.candidate.id), event.candidate]);
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
            scanInterval,
          })
          .catch((error) => tell(error.message, "error")),
      450,
    );
    return () => window.clearTimeout(id);
  }, [booted, url, maxPages, timeout, profile, livePreview, scanInterval]);
  useEffect(() => {
    setSelectedIds(new Set());
  }, [filter, reviewFilter, search]);
  useEffect(() => {
    const keydown = (event) => {
      if (event.key === "Escape") {
        setPalette(false);
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
    candidates = records.filter((r) => r.category);
  const flowNodes = useMemo(
    () =>
      flow.nodes.map((node) => {
        const enabled =
          !["techniques", "candidates", "ocr", "dedup"].includes(node.id) ||
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
              : node.id === "dedup" ? "동일 문구 · 근거 보존" : node.id === "ocr" ? "PaddleOCR · 이미지 문자 인식" : node.id === "techniques"
                ? `${findings.length}건 발견`
                : node.id === "candidates"
                  ? `${candidates.length}건 광고 의심`
                  : node.id === "target"
                    ? ""
                    : outcome
                      ? "JSON · CSV 저장 완료"
                      : "실행 종료 후 저장";
        if (!enabled) caption = node.id === "ocr" && flow.ocr_enabled === false ? "사용 안 함" : "분석 경로 연결 안 됨";
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
        selectable: false,
        deletable: false,
        focusable: false,
        reconnectable: false,
        animated:
          status === "running" &&
          (edge.target === active || edge.source === active),
        style: {
          stroke:
            edge.target === active
              ? "#2563a6"
              : visited.has(edge.source)
                ? "#41765b"
                : "#62666b",
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
  const start = async (demo = false, overrides = {}) => {
    if (running || startRequest.current) {
      tell("이미 검사 중입니다.");
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
    startRequest.current = true;
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
    setView((previous) => previous === "inspection" ? "inspection" : "workflow");
    setSelectedNode(null);
    setSelectedRecord(null);
    try {
      await api.start({
        url: demo ? "http://127.0.0.1/" : entry,
        max_pages: Number(maxPages),
        timeout_sec: Number(timeout),
        profile,
        preview: livePreview,
        interval_sec: scanInterval,
        demo,
        workflow: nextFlow,
      });
    } catch (error) {
      setStatus("failed");
      tell(error.message, "error");
    } finally {
      startRequest.current = false;
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
        setReviewNotice(`${ids.length}건의 검토 내용을 저장했습니다.`);
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
      label: "설정",
      icon: "Settings",
      action: () => openSettings(),
    },
    {
      label: "사용 가이드",
      keywords: "tutorial help 도움말 튜토리얼",
      icon: "MousePointer2",
      action: () => setTutorial(true),
    },
  ];
  useEffect(() => {
    const handle = event => {
      if (event.defaultPrevented || event.repeat || event.isComposing || event.target.closest?.('[data-shortcut-recorder]')) return;
      const key = fromEvent(event);
      const id = key && Object.keys(shortcuts).find(id => shortcuts[id] === key);
      if (!id) return;
      if (event.target.closest?.('input, textarea, [contenteditable="true"], [role="dialog"]') && id !== 'palette') return;
      event.preventDefault();
      if (id === 'palette') setPalette(previous => !previous);
      else if (id === 'settings') openSettings();
      else if (id === 'guide') setTutorial(true);
      else if (id === 'load') { if (!running) load(); }
      else setView(id);
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [shortcuts, running, load, openSettings]);
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
      <div className="window-titlebar" aria-hidden="true" />
      <aside className={`sidebar ${view === "settings" ? "settings-sidebar" : ""}`}>
        {view === "settings" ? <>
          <SettingsNav selected={settingsTab} onSelect={setSettingsTab} onBack={() => setView(settingsReturnView.current)} onGuide={() => setTutorial(true)} />
        </> : <>

          <div className="brand sidebar-brand">
            <span className="brand-mark"><img src={brandMark} alt="Chickadee 로고" /></span>
            <span>chickadee<span className="brand-dot">.</span></span>
          </div>

        <nav>
          {[
            ["workflow", "Workflow", "검사 구성"],
            ["results", "ListFilter", "탐지 내역"],
            ["pages", "Network", "탐색 경로"],
            ["inspection", "GitBranch", "검사 분석"],
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
                <b className="detection-count">{records.length}</b>
              )}
              {id === "activity" && running && <span className="live-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom sidebar-tools">
          <SidebarTool label="설정" icon="Settings" shortcut={shortcuts.settings} onClick={openSettings} />
          <SidebarTool label="앱 재실행" icon="RotateCcw" disabled={running || !booted} onClick={() => action(() => api.restart())} />
          <SidebarTool label="결과 불러오기" icon="FolderOpen" shortcut={shortcuts.load} disabled={running} onClick={load} />
        </div>
        </>}
      </aside>
      <main className="main">
        <header className="topbar">
            <h1>
              {view === "settings" ? "설정" : view === "inspection" ? "검사 분석" : view === "history"
                ? "검사 기록"
                : view === "results"
                  ? "탐지 내역"
                  : view === "pages"
                    ? "탐색 경로"
                    : view === "activity"
                      ? "진행 기록"
                      : "검사 구성"}
            </h1>
          <div className="header-run-controls" aria-label="검사 실행 제어">
          <div className="run-actions" key={running ? status : "ready"}>
            {running ? (
              <>
                <Button
                  icon={
                    status === "paused" || status === "pausing"
                      ? "Play"
                      : "Pause"
                  }
                  variant="secondary"
                  disabled={status === "stopping" || Boolean(loginRequest)}
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
                      label: "설정",
                      icon: "Settings",
                      action: () => openSettings(),
                    },
                  ]}
                />
              </>
            )}
          </div>
          </div>
          <div className="topbar-right">
            <Button
              icon="FolderOpen"
              variant="ghost"
              onClick={() => action(() => api.openFolder())}
            >
              결과 폴더
            </Button>
            {visualPreview && (
              <span className="local-label">디자인 미리보기 · 저장된 데모</span>
            )}
          </div>
        </header>
        <section
          className="summary-strip"
          hidden={view === "settings" || (!running && !outcome && status !== "failed")}
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
        <div className="content-area" data-view={view} key={view}>
          {view === "settings" && <div className="settings-page" key={settingsTab}>
            <section className="settings-modal settings-page-content" aria-label="설정">
              <div className="settings-page-heading">
                <div><h2>{{ general: "일반", ai: "AI 연결", notifications: "알림", schedules: "예약 검사", shortcuts: "단축키", updates: "업데이트" }[settingsTab]}</h2><p>{{ general: "검사 방식과 결과 저장 위치를 관리합니다.", ai: "근거 검토에 사용할 AI 제공자와 사용 한도를 설정합니다.", notifications: "검사 완료 알림과 채널별 리포트를 설정합니다.", schedules: "정해진 시간에 저장된 구성으로 검사를 실행합니다.", shortcuts: "자주 쓰는 명령의 키보드 단축키를 설정합니다.", updates: "최신 릴리스를 확인하고 새 버전을 다운로드합니다." }[settingsTab]}</p></div>
              </div>
            {settingsTab === "general" && <>
            <RuntimeSettings disabled={running} />
            <div className="settings-field">
              <span>사이트 탐색 설정</span>
              <ActionMenu
                className="profile-menu"
                label="사이트 탐색 설정"
                disabled={running}
                triggerText={{
                  default: "기본 탐색 · 같은 사이트 전체",
                  test: "사용자 모의 게시판 · .post-detail 본문",
                  public: "공공 사이트 기본 설정",
                }[profile]}
                items={[
                  ["default", "기본 탐색 · 같은 사이트 전체"],
                  ["test", "사용자 모의 게시판 · .post-detail 본문"],
                  ["public", "공공 사이트 기본 설정"],
                ].map(([id, label]) => ({
                  label, selected: profile === id, disabled: running,
                  action: () => setProfile(id),
                }))}
              />
            </div>
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
            <div className="scan-pace">
              <div className="scan-pace-heading"><strong>탐색 속도</strong><span>{scanInterval}초 간격</span></div>
              <div className="scan-pace-options" role="group" aria-label="탐색 속도">{[[0, "빠르게", "대기 없이 탐색"], [0.5, "보통", "기본 속도"], [5, "천천히", "다른 작업과 함께"]].map(([value, label, hint]) => <button key={value} type="button" disabled={running} aria-pressed={scanInterval === value} onClick={() => setScanInterval(value)}><strong>{label}</strong><small>{hint}</small></button>)}</div>
              <label>페이지 사이 대기 시간<input aria-label="페이지 사이 대기 시간" type="range" min="0" max="30" step="0.5" value={scanInterval} disabled={running} onChange={event => setScanInterval(Number(event.target.value))} /></label>
              <p>다음 페이지로 이동하기 전 기다리는 시간입니다. 천천히 검사할 때는 전체 제한시간도 늘려 주세요. 검사 중인 페이지의 처리 속도는 유지됩니다.</p>
            </div>
            <label className="toggle-label">
              <div>
                <strong>실시간 브라우저 화면</strong>
                <small>검사 중인 페이지를 미리보기로 표시합니다.</small>
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
                <button
                  type="button"
                  className="folder-change-icon"
                  aria-label="결과 저장 위치 변경"
                  title="결과 저장 위치 변경"
                  disabled={running}
                  onClick={() =>
                    action(async () => setOutputRoot(await api.chooseFolder()))
                  }
                >
                  <Icon name="FolderOpen" size={18} />
                </button>
              </div>
            </label>
            <p className="settings-folder-hint">각 검사는 별도 폴더에 저장됩니다.</p>
            </>}
            {settingsTab === "ai" && <>
            <GrokSettings config={agentConfig} onConfigured={setAgentConfig} />
            <details className="automation-info">
              <summary>에이전트 확장 규격</summary>
              <p>
                로컬 도구 {capabilities?.tools?.length || 0}개 · 규격 v
                {capabilities?.protocol_version || 1}. 실행 ID와 입력 형식을
                검증하며, 검사 제어·근거 조회·검토 기록에 같은 기능을
                사용합니다.
              </p>
              <small>
                AI 검토는 사용자가 실행할 때만 호출합니다. 페이지 본문과 광고 문구는
                분석 대상 데이터로 취급합니다.
              </small>
            </details>
            </>}
            {settingsTab === "shortcuts" && <ShortcutSettings value={shortcuts} onChange={async value => { await api.preferences({ shortcuts: value }); setShortcuts(value); }} />}
            {settingsTab === "notifications" && <NotificationSettings />}
            {settingsTab === "updates" && <UpdateSettings />}
            {settingsTab === "schedules" && <ScheduleSettings options={{ url, max_pages: Number(maxPages), timeout_sec: Number(timeout), profile, preview: livePreview, interval_sec: scanInterval, workflow: flow }} />}
            </section>
          </div>}
          {view === "inspection" && <InspectionInsights onOpenHistory={() => setView("history")} tab={inspectionTab} setTab={setInspectionTab} runStatus={status} onOpenSettings={() => openSettings("ai")} agentConfig={agentConfig} />}
          {view === "workflow" && (
            <div className={`studio ${selectedNode || monitorOpen ? "panel-open" : "panel-closed"}`}>
              <section className="canvas-shell">
                <div className="canvas-toolbar">
                  <div>
                    <button title="노드 정렬" aria-label="노드 정렬" disabled={running} onClick={() => {
                      const positions = defaultWorkflow().nodes;
                      setFlow(value => ({ ...value, nodes: value.nodes.map(node => ({ ...node, position: positions.find(item => item.id === node.id).position })) }));
                      requestAnimationFrame(() => requestAnimationFrame(() => canvasApi?.fitView({ padding: 0.2, maxZoom: 0.75, duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 200 })));
                    }}><Icon name="Workflow" size={15} /></button>
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
                  </div>
                </div>
                <div className="flow-area">
                  {booted && <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    nodeTypes={nodeTypes}
                    onNodesChange={onNodesChange}
                    deleteKeyCode={null}
                    nodesDraggable={!running}
                    nodesConnectable={false}
                    edgesReconnectable={false}
                    edgesFocusable={false}
                    onNodeClick={(_event, node) => setSelectedNode(node.id)}
                    onPaneClick={() => setSelectedNode(null)}
                    onInit={setCanvasApi}
                    fitView
                    fitViewOptions={{ padding: 0.2, maxZoom: 0.75, minZoom: 0.2 }}
                    minZoom={0.2}
                    maxZoom={1.5}
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background color="#383838" gap={20} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap
                      nodeColor="#60646b"
                      maskColor="rgba(23,23,23,.65)"
                      style={{ width: 120, height: 74 }}
                      pannable
                      zoomable
                    />
                  </ReactFlow>}

                </div>
              </section>
              <aside
                className="monitor-panel"
                id="workflow-side-panel"
                aria-hidden={!selectedNode && !monitorOpen}
                inert={!selectedNode && !monitorOpen}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setSelectedNode(null);
                    setMonitorOpen(false);
                    document.querySelector(".workspace-rail button")?.focus();
                  }
                }}
              >
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
                      <button aria-label="미리보기·진행 기록 닫기" onClick={() => setMonitorOpen(false)}>
                        <Icon name="X" size={15} />
                      </button>
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
                          aria-label="미리보기 화면 확대"
                          disabled={!preview}
                          onClick={() => setZoomPreview(true)}
                        >
                          <Icon name="Maximize2" size={13} />
                        </button>
                      </div>
                      {preview ? (
                        <button
                          className="preview-image"
                          aria-label="검사 화면 크게 보기"
                          onClick={() => setZoomPreview(true)}
                        >
                          <img
                            src={preview.data_url}
                            alt="실제 검사 브라우저의 현재 화면"
                          />
                        </button>
                      ) : (
                        <div className="preview-placeholder">
                          <Icon name="PanelsTopLeft" size={28} />
                          <strong>
                            {livePreview
                              ? running ? "화면을 기다리는 중" : "검사 시작 전"
                              : "미리보기 꺼짐"}
                          </strong>
                          <span>
                            {livePreview
                              ? running ? "캡처가 도착하면 표시됩니다." : "실행하면 방문한 페이지가 표시됩니다."
                              : "설정에서 미리보기를 켤 수 있습니다."}
                          </span>
                        </div>
                      )}
                      <div className="preview-caption">
                        <span className="preview-status">
                          <i data-active={Boolean(preview && running && livePreview)} />
                          {!livePreview ? "꺼짐" : preview ? "최근 캡처" : running ? "캡처 대기" : "대기 중"}
                        </span>
                        <span>
                          {preview?.timestamp ? time(preview.timestamp) : ""}
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
                          <div className="timeline-waiting">
                            <span className="timeline-waiting-dot" />
                            <strong>아직 기록이 없습니다</strong>
                          </div>
                          <p>검사를 실행하면 아래 과정이 기록됩니다.</p>
                          <ol className="timeline-outline" aria-label="검사 과정 안내">
                            {[
                              ["Globe2", "페이지 이동", "방문한 주소와 응답 상태"],
                              ["ScanLine", "콘텐츠 수집", "페이지 본문과 하위 링크"],
                              ["Search", "탐지 · 분류", "발견한 항목과 판단 근거"],
                              ["FileCheck2", "결과 저장", "검사 요약과 출력 파일"],
                            ].map(([icon, title, description]) => (
                              <li key={title}>
                                <span className="timeline-outline-icon"><Icon name={icon} size={15} /></span>
                                <div><strong>{title}</strong><span>{description}</span></div>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </aside>
              <div className="workspace-rail">
                <button
                  aria-label="미리보기·진행 기록"
                  title="미리보기·진행 기록"
                  aria-expanded={Boolean(monitorOpen || selectedNode)}
                  aria-controls="workflow-side-panel"
                  onClick={() => {
                    setMonitorOpen(!(selectedNode || monitorOpen));
                    setSelectedNode(null);
                  }}
                >
                  <Icon name="ChevronRight" size={17} />
                </button>
              </div>
            </div>
          )}
          {view === "results" && (
            <div className={`results-layout ${selectedRecord ? "detail-open" : "detail-closed"}`}>
              <section className="table-section">
                <div className="list-toolbar">
                  <AnimatedTabs value={filter}>
                    {[
                      ["all", "전체", "ListFilter"],
                      ["required", "필수 탐지", "ScanSearch"],
                      ["candidates", "광고 의심", "ShieldAlert"],
                    ].map(([id, label, icon]) => (
                      <button
                        className={filter === id ? "active" : ""}
                        aria-pressed={filter === id}
                        key={id}
                        onClick={() => setFilter(id)}
                      >
                        <Icon name={icon} size={15} aria-hidden="true" />
                        {label}
                      </button>
                    ))}
                  </AnimatedTabs>
                  <div className="search">
                    <Icon name="Search" size={15} />
                    <input
                      aria-label="결과 검색"
                      placeholder="원문, URL 검색"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                  <ActionMenu
                    className="review-filter-menu"
                    label={`검토 상태 필터: ${reviewFilter === "all" ? "검토 전체" : REVIEW_LABELS[reviewFilter]}`}
                    triggerText={reviewFilter === "all" ? "검토 전체" : REVIEW_LABELS[reviewFilter]}
                    items={[["all", "검토 전체"], ...Object.entries(REVIEW_LABELS)].map(([id, label]) => ({
                      label,
                      selected: reviewFilter === id,
                      action: () => setReviewFilter(id),
                    }))}
                  />
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
              image={checkImage}
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
                              data-type={record.technique || record.category}
                              onClick={(event) => {
                                event.stopPropagation();
                                setFilter(record.technique || "candidates");
                              }}
                            >
                              <TypeBadgeContent type={record.technique || record.category} />
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
                  {outcome?.report.ocr_summary?.status === "partial" && <div className="ocr-coverage-notice" role="status"><Icon name="CircleAlert" size={17} /><div><strong>이미지 검사에 미확인 항목이 있습니다</strong><span>처리 실패 {outcome.report.ocr_summary.failed} · 판독 불가 {outcome.report.ocr_summary.unreadable || 0} · 생략 {outcome.report.ocr_summary.skipped || 0} — 탐지 내역이 없어도 정상으로 판단하지 마세요.</span></div></div>}
                  {filteredRecords.length === 0 && (
                    <Empty
                      icon="ScanSearch"
                      image={running ? undefined : noFileImage}
                      loading={running}
                      title={running ? "분석 진행" : "탐지 내역 없음"}
                      text="검사를 시작하거나 저장된 result.json을 불러오세요."
                    />
                  )}
                </div>
                <div className="table-footer">
                  {filteredRecords.length}개 항목{" "}
                </div>
              </section>
              <div className="record-drawer" aria-hidden={!selectedRecord} inert={!selectedRecord}>
              {detailRecord && <RecordDetail
                key={detailRecord.id}
                record={detailRecord}
                liveScreenshots={liveScreenshots}
                outcome={outcome}
                review={
                  reviewData.items[detailRecord.id]
                }
                onReview={(status, note) =>
                  updateReview([detailRecord.id], status, note)
                }
                reviewDisabled={running || !outcome || reviewSaving}
                onRecheck={() =>
                  start(false, { url: detailRecord.url, singlePage: true })
                }
                recheckDisabled={
                  running || !booted || outcome?.report.desktop_options?.demo
                }
                onCopy={(text) => action(async () => {
                  await api.copy(text);
                  tell("클립보드에 복사했습니다.", "success");
                })}
                onClose={() => setSelectedRecord(null)}
              />}
              </div>
            </div>
          )}
          {view === "pages" && (
            <section className="table-section">
              <div className="list-toolbar">
                <AnimatedTabs value={pageFilter}>
                  <button
                    className={pageFilter === "visited" ? "active" : ""}
                    aria-pressed={pageFilter === "visited"}
                    onClick={() => setPageFilter("visited")}
                  >
                    <Icon name="Globe2" size={15} aria-hidden="true" />
                    방문 <span className="path-tab-count">{pages.length}</span>
                  </button>
                  <button
                    className={pageFilter === "pending" ? "active" : ""}
                    aria-pressed={pageFilter === "pending"}
                    onClick={() => setPageFilter("pending")}
                  >
                    <Icon name="History" size={15} aria-hidden="true" />
                    대기 <span className="path-tab-count">{queue}</span>
                  </button>
                </AnimatedTabs>
                <span className="path-discovered">발견한 링크 <strong>{discovered}</strong></span>
                <div className="search">
                  <Icon name="Search" size={15} />
                  <input
                    placeholder="경로 검색"
                    aria-label="경로 검색"
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
                            {page.status === "authentication_required" && <small>로그인 필요 · 미수집</small>}
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
                    image={noLocationImage}
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
                <AnimatedTabs value={eventFilter}>
                  {[
                    ["all", "전체", "ListFilter"],
                    ["phase", "진행 단계", "Workflow"],
                    ["network", "HTTP 통신", "Network"],
                    ["findings", "탐지·오류", "CircleAlert"],
                  ].map(([id, label, icon]) => (
                    <button
                      key={id}
                      className={eventFilter === id ? "active" : ""}
                      aria-pressed={eventFilter === id}
                      onClick={() => setEventFilter(id)}
                    >
                      <Icon name={icon} size={15} aria-hidden="true" />
                      {label}
                    </button>
                  ))}
                </AnimatedTabs>
                <div className="activity-log-meta">
                  <span>최근 기록 <strong>{events.length}</strong></span>
                  <span className="activity-log-storage">전체 기록 저장</span>
                </div>
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
                    image={waitDetectionImage}
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
                          <span className="history-status-badge" data-status={item.status}>
                            {STATUS[item.status] || item.status || "상태 없음"}
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
                    image={noRecordImage}
                    title="첫 검사를 시작해 보세요"
                    text="검사마다 별도 폴더에 결과와 진행 기록을 보관합니다."
                  />
                )}
              </div>
            </section>
          )}
        </div>
      </main>
      {scanNotice && <ScanNotice onClose={() => setScanNotice(false)} />}
      {reviewNotice && <ReviewSavedNotice message={reviewNotice} onClose={() => setReviewNotice(null)} />}
      {notice && (
        <div className={`toast ${notice.type}`} role={notice.type === "error" ? "alert" : "status"}>
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
          <button aria-label="알림 닫기" onClick={() => setNotice(null)}>
            <Icon name="X" size={15} />
          </button>
        </div>
      )}
      {palette && (
        <CommandPalette commands={commands} onClose={() => setPalette(false)} />
      )}
      {loginRequest && <LoginPrompt key={loginRequest.request_id} request={loginRequest} onStop={() => api.stop()} />}
      {tutorial && (
        <Tutorial
          onClose={closeTutorial}
          canDemo={booted && !running}
          onDemo={() => {
            closeTutorial();
            start(true);
          }}
          onInspect={() => {
            focusTargetAfterGuide.current = true;
            closeTutorial();
            setView("workflow");
            setSelectedNode("target");
          }}
        />
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
function ReviewSavedNotice({ message, onClose }) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => {
      dialog.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialogRef}
      className="review-saved-dialog"
      aria-labelledby="review-saved-title"
      aria-describedby="review-saved-description"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <button className="review-saved-close" aria-label="닫기" onClick={onClose}><Icon name="X" size={18} /></button>
      <img className="review-saved-icon" src={checkImage} alt="" width={32} height={32} />
      <h2 id="review-saved-title">검토 저장 완료</h2>
      <p id="review-saved-description">{message}</p>
      <button className="review-saved-confirm" autoFocus onClick={onClose}>확인</button>
    </dialog>
  );
}

function ScanNotice({ onClose }) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => {
      dialog.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialogRef}
      className="scan-notice-dialog"
      aria-labelledby="scan-notice-title"
      aria-describedby="scan-notice-description"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <h2 id="scan-notice-title">이미 검사 중입니다</h2>
      <p id="scan-notice-description">현재 검사가 끝난 뒤 다시 실행해 주세요.<br />새 검사를 시작하려면 먼저 진행 중인 검사를 중단하세요.</p>
      <div><button autoFocus onClick={onClose}>확인</button></div>
    </dialog>
  );
}

function SidebarTool({ label, icon, shortcut, hint, disabled, onClick }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <div className="sidebar-tool-wrap" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={event => { if (event.key === "Escape") { setOpen(false); event.stopPropagation(); } }}>
    <button className="sidebar-tool" aria-label={label} aria-describedby={open ? id : undefined} disabled={disabled} onClick={onClick}><Icon name={icon} /></button>
    {open && <div className="sidebar-tool-tip" id={id} role="tooltip">
      <span>{label}</span>
      {shortcut && <kbd>{keyLabel(shortcut, /Mac/i.test(navigator.platform))}</kbd>}
      {hint && <small>{hint}</small>}
    </div>}
  </div>;
}

function Empty({ icon, image, title, text, loading = false }) {
  return (
    <div className={`empty-state${loading ? " empty-state-loading" : ""}`} role={loading ? "status" : undefined}>
      <span aria-hidden="true">
        {loading ? <Icon name="LoaderCircle" size={26} className="analysis-spinner" /> : image ? <img src={image} alt="" width={32} height={32} /> : <Icon name={icon} size={24} />}
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
        <button onClick={onClose} aria-label="단계 설정 닫기">
          <Icon name="X" size={16} />
        </button>
      </div>
      <div className={`node-config tone-${def.tone}`}>
        <span className={`config-icon config-icon-${id}`}>
          <img src={nodeImages[id]} alt="" width={28} height={28} draggable={false} />
        </span>
        <small>{def.subtitle}</small>
        <h2>{def.title}</h2>
        <p>{def.detail}</p>
        {id === "target" && (
          <label>
            검사 대상 URL
            <input
              id="target-url"
              type="url"
              placeholder="https://example.go.kr"
              value={url}
              readOnly={running}
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
        {id === "ocr" && <label className="toggle-label"><div><strong>이미지 OCR 사용</strong><small>이미지 속 글자도 필수 탐지와 광고 분류에 사용합니다.</small></div><input type="checkbox" checked={flow.ocr_enabled !== false} disabled={running} onChange={event => setFlow(value => ({ ...value, ocr_enabled: event.target.checked }))} /></label>}
        <dl>
          <dt>입력</dt>
          <dd>
            {id === "target"
              ? "사용자가 입력한 HTTP(S) 주소"
              : id === "browser"
                ? "대상 URL"
                : id === "collector"
                  ? "렌더링된 페이지"
                  : id === "ocr" ? "페이지에서 수집한 이미지" : id === "report"
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
            검사는 표시된 순서대로 진행됩니다. OCR 사용 여부는 이미지 OCR 단계에서 설정할 수 있습니다.
          </span>
        </div>
      </div>
    </>
  );
}
function eventLabel(event) {
  if (event.kind === "page_complete" && event.page.status === "authentication_required")
    return { icon: "LockKeyhole", title: "로그인 필요 · 미수집", detail: event.page.url, tone: "amber" };
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
  const eventImages = {
    url_discovered: hierarchyImage,
    http_response: browserImage,
    request_blocked: deleteImage,
    finding: searchImage,
    candidate: searchImage,
    page_complete: checkImage,
    done: saveImage,
    started: searchImage,
    error: errorImage,
    warning: warningImage,
  };
  const eventImage = event.kind === "control"
    ? (["paused", "pausing"].includes(event.state) ? pauseImage : event.state === "stopping" ? stopImage : resumeImage)
    : event.kind === "page_complete" && event.page?.status === "authentication_required" ? warningImage
    : event.kind === "done" && event.report?.status === "cancelled" ? stopImage
    : event.kind === "done" && event.report?.status === "failed" ? errorImage
    : event.kind === "phase"
    ? nodeImages[event.stage] || browserImage
    : eventImages[event.kind] || refreshImage;
  const imageScale = eventImage === browserImage ? 1.2
    : eventImage === hierarchyImage ? 1.8
    : eventImage === duplicateRemoveImage ? 1.5
    : eventImage === saveImage ? 1.15
    : eventImage === checkImage ? 1.5
    : eventImage === deleteImage ? 1.8
    : eventImage === searchImage ? .92 : 1;
  return (
    <button
      className={`event-row ${compact ? "compact" : ""}`}
      onClick={onClick}
    >
      <span className="event-icon event-asset">
        <img src={eventImage} alt="" width={compact ? 20 : 26} height={compact ? 20 : 26} style={{ transform: `scale(${imageScale})` }} draggable={false} />
      </span>
      <div>
        <strong>{event.kind === "http_response" ? <span className="http-event-title"><span className={`http-event-status status-${Math.floor(Number(event.http_status) / 100)}`} aria-label={`HTTP 상태 ${event.http_status}`}>{event.http_status}</span><span className={`http-event-method method-${String(event.method || "").toLowerCase()}`}>{event.method}</span><span className="http-event-resource">{event.resource_type}</span></span> : label.title}</strong>
        {label.detail && <p title={label.detail}>{label.detail}</p>}
      </div>
      <time>{event.timestamp ? time(event.timestamp) : ""}</time>
    </button>
  );
}
function RecordDetail({
  liveScreenshots = {},
  record,
  outcome,
  onCopy,
  review,
  onReview,
  reviewDisabled,
  onRecheck,
  recheckDisabled,
  onClose,
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
        <span>
          <span className="mono">{record.id}</span>
          <button aria-label="탐지 근거 닫기" onClick={onClose}><Icon name="X" size={16} /></button>
        </span>
      </div>
      <div className="record-body">
        <div className="record-overview">
        <span className={`type-badge ${record.technique ? "purple" : "amber"}`} data-type={record.technique || record.category}>
          <TypeBadgeContent type={record.technique || record.category} />
        </span>

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
        </div>
        <label>발견한 문구</label>
        <blockquote>{record.evidence_text}</blockquote>
        {keywords.length > 0 && (
          <p className="record-keywords"><span>탐지된 표현:</span> {keywords.join(", ")}</p>
        )}
        <label>탐지 이유</label>
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
        {(detail.evidence_sources?.length > 1) && <p className="evidence-capture-note">본문·이미지의 동일 문구를 합쳤습니다. 근거 {detail.evidence_sources.length}곳을 보존했습니다.</p>}
        {[...new Set([detail.image_id, ...(detail.evidence_sources || []).map(source => source.image_id)].filter(Boolean))].map(id => <ImageOCR key={id} image={outcome?.report.ocr_images?.find(image => image.id === id)} />)}
        <LocalAIAnalysis analysis={detail.local_ai} />
        <EvidenceScreenshot screenshot={outcome ? outcome.report.screenshots?.[detail.screenshot_id] : liveScreenshots[detail.screenshot_id]}

          hidden={record.technique === "TRANSPARENT" || record.technique === "OFFSCREEN"} />
        <div className="review-editor">
          <details className="review-note-details" open={note ? true : undefined}>
          <summary>검토 메모</summary>
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
          </details>
          <div className="review-actions">
            <Button
              icon="CheckCheck"
              image={checkImage}
              disabled={reviewDisabled}
              onClick={() => onReview("confirmed", note)}
            >
              검토 확인
            </Button>
            <Button
              icon="X"
              image={deleteImage}
              variant="ghost"
              disabled={reviewDisabled}
              onClick={() => onReview("dismissed", note)}
            >
              제외
            </Button>
            <ActionMenu
              label="검토 작업 더보기"
              className="review-more-menu"
              triggerIcon="MoreHorizontal"
              items={[
                {
                  label: "메모 저장",
                  icon: "Save",
                  image: saveImage,
                  imageClassName: "menu-image-save",
                  disabled: reviewDisabled,
                  action: () => onReview(review?.status || "unreviewed", note),
                },
                {
                  label: "미검토로 변경",
                  icon: "RotateCcw",
                  image: refreshImage,
                  disabled: reviewDisabled,
                  action: () => onReview("unreviewed", note),
                },
              ]}
            />
          </div>
        </div>
        {review?.updated_at && (
          <details className="review-metadata">
            <summary>최근 검토 정보</summary>
            <dl>
              <div><dt>검토자</dt><dd>{review.actor === "agent" ? "에이전트" : "사용자"}</dd></div>
              <div><dt>저장 시간</dt><dd><time dateTime={review.updated_at}>{new Date(review.updated_at).toLocaleString("ko-KR")}</time></dd></div>
            </dl>
          </details>
        )}
        <details className="record-technical">
        <summary>페이지 · 기술 정보</summary>
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
