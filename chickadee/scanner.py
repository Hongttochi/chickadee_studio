import asyncio
import heapq
from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import ipaddress
import itertools
import json
import os
import re
from pathlib import Path
import sys
import tempfile
from threading import Event
import time
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from . import __version__
from .detection import Rules, analyze, classify_elements
from .candidates import classify_candidates, CATEGORY_LABELS
from .exports import CSV_COLUMNS, csv_bytes, atomic_write
from .profiles import SiteProfile

# A browser installed with PLAYWRIGHT_BROWSERS_PATH=0 travels with the package.
# Honour an explicit developer setting; frozen builds always use their own copy.
if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
else:
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")


def normalize_url(value: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("http:// 또는 https://로 시작하는 웹사이트 URL을 입력하세요. 인증정보를 URL에 넣지 마세요.")
    _ = parts.port  # Validate malformed ports before launching the browser.
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def origin(url: str) -> tuple:
    parts = urlsplit(url)
    return parts.scheme.lower(), (parts.hostname or "").lower(), parts.port or (443 if parts.scheme == "https" else 80)


def visit_key(url: str) -> tuple:
    parts = urlsplit(url)
    return origin(url), parts.path or "/", tuple(sorted(parse_qsl(parts.query, keep_blank_values=True)))


def navigation_priority(url: str) -> int:
    """Visit content and pagination before global menus, without guessing URLs."""
    parts = urlsplit(url)
    path = parts.path.casefold()
    keys = {k.casefold() for k, value in parse_qsl(parts.query) if value}
    if re.search(r"/(?:login|logout|join|signup|admin|auth)(?:/|\.|$)", path):
        return 40
    if path.startswith('/api/'):
        return 50
    if keys & {'board_idx', 'post_id', 'postid', 'article_id', 'articleid', 'nttid', 'wr_id', 'document_srl'} or re.search(r"(?:^|/)(?:view|read|detail)(?:[./]|$)|/(?:posts|articles)/\d+", path):
        return 0
    if re.search(r"(?:board|bbs|forum|posts|articles)", path):
        return 10
    if keys & {'q', 'query', 'keyword', 'searchword'} or 'search' in path:
        return 30
    return 20


def is_loopback(url: str) -> bool:
    host = urlsplit(url).hostname
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def validate_result(result):
    from jsonschema import Draft202012Validator
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "result.schema.json"
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(result)
    ids, keys = set(), set()
    for finding in result["findings"]:
        key = finding["url"], finding["location"], finding["technique"]
        if finding["id"] in ids or key in keys:
            raise ValueError("결과에 중복 ID 또는 중복 검출이 있습니다.")
        ids.add(finding["id"])
        keys.add(key)


def output_directory() -> Path:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    return base / "results"


@dataclass(frozen=True)
class ScanConfig:
    entry_url: str
    max_pages: int = 50
    timeout_sec: float = 300
    page_timeout_sec: float = 15
    settle_ms: int = 500
    allow_network: bool = False
    rules_path: Path | None = None
    profile_path: Path | None = None
    retries: int = 1
    interval_sec: float = 1.0

    def __post_init__(self):
        normalize_url(self.entry_url)
        if not self.allow_network and not is_loopback(self.entry_url):
            raise ValueError("로컬 전용 모드입니다. 외부 사이트를 검사하려면 --local-only 옵션 없이 실행하세요.")
        if not 1 <= self.max_pages <= 10000:
            raise ValueError("최대 페이지 수는 1~10000 사이여야 합니다.")
        if not 0 < self.timeout_sec <= 1800 or not 0 < self.page_timeout_sec <= 120:
            raise ValueError("전체 제한시간은 0초 초과~1800초, 페이지 제한은 0초 초과~120초여야 합니다.")
        if not 0 <= self.settle_ms <= 5000:
            raise ValueError("렌더링 대기는 0~5000ms 사이여야 합니다.")
        if type(self.retries) is not int or not 0 <= self.retries <= 3 or not 0 <= self.interval_sec <= 30:
            raise ValueError("재시도는 0~3회, 요청 간격은 0~30초여야 합니다.")
        Rules.load(self.rules_path)
        SiteProfile.load(self.profile_path)


@dataclass
class ScanOutcome:
    result: dict
    report: dict

    def save(self, folder: Path) -> Path:
        validate_result(self.result)
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(self.result, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        csv_payload = csv_bytes(self.result, self.report)
        report = {**self.report, "result_sha256": hashlib.sha256(payload).hexdigest(), "output_path": str(folder / "result.json"),
                  "csv_sha256": hashlib.sha256(csv_payload).hexdigest(), "csv_columns": list(CSV_COLUMNS), "csv_schema_version": "1.0"}
        # Each file replaces atomically. A matching SHA-256 in the sidecar lets
        # consumers detect an interrupted write between the two replacements.
        for name, content in (("result.json", payload), ("result.csv", csv_payload),
                              ("scan-report.json", (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))):
            atomic_write(folder / name, content)
        self.report.update(report)
        return folder / "result.json"

    def save_csv(self, path):
        validate_result(self.result)
        atomic_write(path, csv_bytes(self.result, self.report))
        return Path(path)

    @classmethod
    def load(cls, path: Path):
        path = Path(path)
        if path.stat().st_size > 20_000_000:
            raise ValueError("결과 파일은 20MB 이하여야 합니다.")
        payload = path.read_bytes()
        result = json.loads(payload.decode("utf-8-sig"))
        validate_result(result)
        report_path = path.with_name("scan-report.json")
        report = {"status": "imported", "pages_scanned": [], "errors": [], "evidence_details": {}}
        if report_path.exists():
            if report_path.stat().st_size > 20_000_000:
                raise ValueError("실행 보고서는 20MB 이하여야 합니다.")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(report, dict) or report.get("result_sha256") != hashlib.sha256(payload).hexdigest():
                raise ValueError("결과와 보고서의 해시가 일치하지 않습니다. 같은 실행의 파일 쌍을 가져오세요.")
            if report.get("status") not in ("completed", "partial", "failed", "cancelled") or not isinstance(report.get("pages_scanned"), list) or not isinstance(report.get("errors"), list) or not isinstance(report.get("evidence_details", {}), dict):
                raise ValueError("실행 보고서 형식이 올바르지 않습니다.")
            candidates = report.get("ad_candidates", [])
            ids = {f["id"] for f in result["findings"]}
            if not isinstance(candidates, list) or len(candidates) > 20000:
                raise ValueError("광고 후보 목록 형식이 올바르지 않습니다.")
            for candidate in candidates:
                if not isinstance(candidate, dict) or not all(isinstance(candidate.get(k), str) and candidate[k] for k in ("id", "url", "location", "evidence_text", "category")):
                    raise ValueError("광고 후보 필수 필드가 올바르지 않습니다.")
                normalize_url(candidate["url"])
                if candidate["id"] in ids or candidate["category"] not in CATEGORY_LABELS:
                    raise ValueError("광고 후보 ID 또는 분류가 올바르지 않습니다.")
                ids.add(candidate["id"])
                for key in ("matched_keywords", "reasons"):
                    if not isinstance(candidate.get(key, []), list) or not all(isinstance(s, str) for s in candidate.get(key, [])):
                        raise ValueError("광고 후보 근거는 문자열 배열이어야 합니다.")
        return cls(result, report)


@dataclass
class _State:
    findings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    seen_findings: set = field(default_factory=set)
    remaining: int = 0
    evidence_details: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    blocked_requests: list = field(default_factory=list)
    retry_count: int = 0
    states_scanned: int = 0
    stopped_origins: dict = field(default_factory=dict)
    ad_candidates: list = field(default_factory=list)
    candidate_keys: dict = field(default_factory=dict)
    finding_scopes: set = field(default_factory=set)
    page_diagnostics: list = field(default_factory=list)
    discovered_urls: int = 1


async def scan(config: ScanConfig, stop: Event | None = None, emit=None) -> ScanOutcome:
    stop = stop or Event()
    emit = emit or (lambda event: None)
    started = datetime.now().astimezone()
    clock = time.monotonic()
    state = _State()
    rules = Rules.load(config.rules_path)
    profile = SiteProfile.load(config.profile_path)
    status = "completed"
    emit({"kind": "status", "message": "브라우저를 준비하고 있습니다."})
    worker = asyncio.create_task(_crawl(config, state, emit, rules, profile))
    try:
        while not worker.done():
            if stop.is_set():
                status = "cancelled"
                worker.cancel()
                break
            if time.monotonic() - clock >= config.timeout_sec:
                status = "partial"
                state.errors.append({"url": config.entry_url, "message": "전체 제한시간에 도달했습니다. 일부 결과입니다."})
                worker.cancel()
                break
            await asyncio.wait({worker}, timeout=0.1)
        try:
            await worker
        except asyncio.CancelledError:
            if status == "completed":
                raise
        except Exception as exc:
            status = "failed"
            state.errors.append({"url": config.entry_url, "message": str(exc)})
    finally:
        if not worker.done():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
    if status == "completed" and (state.errors or state.remaining):
        status = "partial" if state.pages else "failed"
    finished = datetime.now().astimezone()
    result = {
        "meta": {"topic": "TOPIC", "entry_url": config.entry_url,
                 "started_at": started.isoformat(), "finished_at": finished.isoformat(),
                 "elapsed_sec": round(time.monotonic() - clock, 3), "tool_version": __version__},
        "findings": state.findings,
    }
    report = {"status": status, "pages_scanned": state.pages, "pages_remaining": state.remaining,
              "page_diagnostics": state.page_diagnostics,
              "crawl_summary": {"discovered_urls": state.discovered_urls, "pages_scanned": len(state.pages),
                                "queue_remaining": state.remaining, "scheduling": "content-first"},
              "errors": state.errors, "finding_count": len(state.findings),
              "states_scanned": state.states_scanned, "retry_count": state.retry_count,
              "evidence_details": state.evidence_details, "actions": state.actions,
              "ad_candidates": _final_candidates(state),
              "blocked_requests": state.blocked_requests,
              "stopped_origins": {v["origin"]: v for v in state.stopped_origins.values()},
              "rules_version": rules.version, "profile": asdict(profile),
              "execution_mode": "network-explicit" if config.allow_network else "loopback-only",
              "limits": {"max_pages": config.max_pages, "timeout_sec": config.timeout_sec,
                         "page_timeout_sec": config.page_timeout_sec, "settle_ms": config.settle_ms,
                         "retries": config.retries, "interval_sec": config.interval_sec}}
    report["candidate_count"] = len(report["ad_candidates"])
    report["csv_schema_version"] = "1.0"
    return ScanOutcome(result, report)


def _final_candidates(state):
    candidates = [dict(c) for c in state.ad_candidates if (c['url'], c['scope_location']) not in state.finding_scopes]
    detail_hits = {}
    for candidate in candidates:
        if not candidate.get('related_content_url'):
            detail_hits.setdefault((candidate['url'], candidate['category']), candidate)
    result = []
    for candidate in candidates:
        detail = detail_hits.get((candidate.get('related_content_url'), candidate['category']))
        if detail is None:
            result.append(candidate)
        else:
            detail.setdefault('summary_observations', []).append({k: candidate[k] for k in ('url', 'location', 'evidence_text')})
    return result


async def _crawl(config: ScanConfig, state: _State, emit, rules: Rules, profile: SiteProfile):
    from playwright.async_api import async_playwright

    script = Path(__file__).with_name("extract.js").read_text(encoding="utf-8")
    # Cancelling Playwright's __aenter__ can orphan its transport task. Finish
    # startup under a shield, then explicitly stop it before propagating cancel.
    starter = asyncio.create_task(async_playwright().start())
    try:
        pw = await asyncio.shield(starter)
    except asyncio.CancelledError:
        pw = await starter
        await pw.stop()
        raise
    browser = None
    try:
        try:
            browser = await pw.chromium.launch(headless=True, chromium_sandbox=True)
        except Exception as exc:
            raise RuntimeError("Chromium을 시작하지 못했습니다. 소스 실행 시 python -m playwright install chromium을 PLAYWRIGHT_BROWSERS_PATH=0 설정 후 실행하세요. " + str(exc)) from exc
        try:
            context = await browser.new_context(viewport={"width": 1366, "height": 900},
                                                accept_downloads=False, service_workers="block")
            allowed = {origin(config.entry_url), *(origin(url) for url in profile.allowed_resource_origins)}
            async def guard(route):
                request = route.request
                reason = None
                essential = request.resource_type in ("document", "stylesheet", "script")
                if request.method not in ("GET", "HEAD"):
                    reason = "GET/HEAD 외 요청 차단"
                    essential = False
                elif request.resource_type in ("image", "media", "font"):
                    await route.abort()
                    return
                else:
                    try:
                        target = normalize_url(request.url)
                        if not config.allow_network and not is_loopback(target):
                            reason = "로컬 전용 모드: 외부 자원 차단"
                        elif origin(target) in state.stopped_origins:
                            reason = "HTTP 429 수신으로 해당 origin 추가 요청 중단"
                        elif origin(target) not in allowed:
                            reason = "허용되지 않은 origin 차단"
                    except ValueError:
                        reason = "HTTP(S) 외 자원 차단"
                if reason:
                    entry = {"url": request.url, "method": request.method, "type": request.resource_type, "reason": reason}
                    if len(state.blocked_requests) < 200:
                        state.blocked_requests.append(entry)
                    if essential and not any(e["url"] == request.url for e in state.errors):
                        state.errors.append({"url": request.url, "message": reason + ": 콘텐츠가 누락될 수 있습니다."})
                    await route.abort()
                else:
                    await route.continue_()
            await context.route("**/*", guard)
            def observe_response(response):
                if response.status != 429:
                    return
                source = origin(response.url)
                if source not in state.stopped_origins:
                    parts = urlsplit(response.url)
                    state.stopped_origins[source] = {"origin": urlunsplit((parts.scheme, parts.netloc, "", "", "")),
                        "status": 429, "url": response.url,
                        "retry_after": response.headers.get("retry-after"), "policy": "stop-origin"}
                    state.errors.append({"url": response.url, "message": "HTTP 429: 같은 origin의 새 요청과 재시도를 중단했습니다."})
                    emit({"kind": "warning", "message": "HTTP 429: 해당 사이트 요청을 중단합니다."})
            context.on("response", observe_response)
            async def block_socket(socket):
                await socket.close(reason="Chickadee: WebSocket connections are disabled")
            await context.route_web_socket("**/*", block_socket)
            sequence = itertools.count()
            entry = normalize_url(config.entry_url)
            queue = [(0, next(sequence), entry)]
            queued = {visit_key(entry)}
            visited = set()
            site = origin(entry)
            attempts = 0
            while queue and attempts < config.max_pages:
                if site in state.stopped_origins:
                    break
                _, _, url = heapq.heappop(queue)
                key = visit_key(url)
                if key in visited:
                    continue
                visited.add(key)
                attempts += 1
                if attempts > 1:
                    await asyncio.sleep(config.interval_sec)
                state.remaining = len(queue) + 1
                emit({"kind": "status", "message": f"{attempts}/{config.max_pages} 페이지 점검 중: {url}"})
                emit({"kind": "progress", "pages_scanned": len(state.pages), "attempts": attempts,
                      "queue_remaining": len(queue), "max_pages": config.max_pages})
                page = await context.new_page()
                page_started = time.monotonic()
                diagnostic = {"url": url, "priority": navigation_priority(url), "status": "inspecting",
                              "links_discovered": 0, "links_queued": 0, "elements_examined": 0}
                state.page_diagnostics.append(diagnostic)
                findings_before, candidates_before = len(state.findings), len(state.ad_candidates)
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.on("popup", lambda popup: popup.close())
                try:
                    async def inspect():
                        nonlocal site
                        response = await _navigate(page, url, config, state, emit)
                        diagnostic["final_url"] = page.url
                        diagnostic["http_status"] = response.status if response else None
                        diagnostic["title"] = await page.title()
                        if response and response.status >= 400:
                            raise RuntimeError(f"HTTP {response.status}")
                        if response and "html" not in response.headers.get("content-type", "text/html"):
                            raise RuntimeError("HTML 문서가 아니어서 점검하지 않았습니다.")
                        if attempts == 1:
                            site = origin(page.url)
                        elif origin(page.url) != site:
                            raise RuntimeError("다른 사이트로 이동되어 점검하지 않았습니다.")
                        final_key = visit_key(page.url)
                        if final_key in visited and final_key != key:
                            return []
                        visited.add(final_key)
                        return await _inspect_dynamic(page, config, profile, rules, site, script, state, emit)
                    links = await asyncio.wait_for(inspect(), timeout=config.page_timeout_sec)
                    diagnostic["links_discovered"] = len(links)
                    diagnostic["status"] = "scanned"
                    if page.url not in state.pages:
                        state.pages.append(page.url)
                    for link in links:
                        try:
                            candidate = normalize_url(link)
                            candidate_key = visit_key(candidate)
                        except ValueError:
                            continue
                        if origin(candidate) == site and urlsplit(candidate).path.startswith(profile.path_prefix) and candidate_key not in queued and candidate_key not in visited:
                            if Path(urlsplit(candidate).path).suffix.lower() in {".pdf", ".zip", ".exe", ".hwp", ".hwpx", ".docx", ".xlsx", ".png", ".jpg", ".mp4"}:
                                continue
                            if len(queued) >= 20000:
                                raise RuntimeError("탐색 URL 안전 한도 20000개에 도달했습니다.")
                            heapq.heappush(queue, (navigation_priority(candidate), next(sequence), candidate))
                            queued.add(candidate_key)
                            diagnostic["links_queued"] += 1
                            state.discovered_urls = len(queued)
                except Exception as exc:
                    diagnostic["status"] = "error"
                    diagnostic["error"] = str(exc) or "페이지 제한시간 초과"
                    state.errors.append({"url": url, "message": str(exc) or "페이지 제한시간을 초과했습니다."})
                    emit({"kind": "warning", "message": f"점검 누락: {url} - {exc or '페이지 제한시간 초과'}"})
                finally:
                    diagnostic["elapsed_sec"] = round(time.monotonic() - page_started, 3)
                    diagnostic["findings_added"] = len(state.findings) - findings_before
                    diagnostic["candidates_added"] = len(state.ad_candidates) - candidates_before
                    emit({"kind": "page_complete", "page": diagnostic, "pages_scanned": len(state.pages),
                          "queue_remaining": len(queue), "discovered_urls": state.discovered_urls})
                    await page.close()
                state.remaining = len(queue)
            if queue and site not in state.stopped_origins:
                state.errors.append({"url": config.entry_url, "message": "최대 페이지 수에 도달했습니다. 일부 결과입니다."})
        finally:
            await browser.close()
    finally:
        await pw.stop()


async def _navigate(page, url, config, state, emit):
    for attempt in range(config.retries + 1):
        if origin(url) in state.stopped_origins:
            raise RuntimeError("HTTP 429 수신으로 해당 origin 재시도를 중단했습니다.")
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=int(config.page_timeout_sec * 1000))
            # Rate limiting ends collection for the origin; never retry 429.
            retryable = response and response.status >= 500
            if not retryable or attempt == config.retries:
                return response
            try:
                delay = min(5, max(0.5, float(response.headers.get("retry-after", "1"))))
            except ValueError:
                delay = 1
        except Exception:
            if attempt == config.retries or origin(url) in state.stopped_origins or any(r["url"] == url for r in state.blocked_requests):
                raise
            delay = min(5, 1 + attempt)
        state.retry_count += 1
        emit({"kind": "status", "message": f"일시 오류 재시도 {attempt + 1}/{config.retries}: {url}"})
        await asyncio.sleep(delay)


_FINGERPRINT = """() => {
    const html = document.body?.innerHTML || '';
    let hash = 2166136261;
    const limit = 4000000;
    for (let i=0; i<Math.min(html.length, limit); i++) hash = Math.imul(hash ^ html.charCodeAt(i), 16777619);
    return {signature: JSON.stringify([location.href, html.length, hash >>> 0,
      scrollX, scrollY, innerWidth, innerHeight]), truncated: html.length > limit};
}"""


async def _inspect_dynamic(page, config, profile, rules, site, script, state, emit):
    links, seen = [], set()
    async def snapshot():
        if site in state.stopped_origins:
            raise RuntimeError("HTTP 429 수신으로 해당 origin 수집을 중단했습니다.")
        if origin(page.url) != site:
            raise RuntimeError("설정된 동작이 다른 사이트로 이동하여 점검을 중단했습니다.")
        fingerprint = await page.evaluate(_FINGERPRINT)
        if fingerprint['truncated'] and not any('DOM 상태 비교 한도' in e['message'] for e in state.errors):
            state.errors.append({"url": page.url, "message": "DOM 상태 비교 한도(4MB) 초과: 일부 변경을 놓칠 수 있습니다."})
        if fingerprint['signature'] not in seen:
            seen.add(fingerprint['signature'])
            state.states_scanned += 1
            links.extend(await _inspect_frame(page.main_frame, "", {}, page.url, script, state, emit, rules, profile.content_selector))
            if page.url not in state.pages:
                state.pages.append(page.url)
        return fingerprint
    await page.wait_for_timeout(config.settle_ms)
    await page.evaluate("document.querySelectorAll('details').forEach(el => el.open = true)")
    await page.wait_for_timeout(config.settle_ms)
    previous = await snapshot()
    quiet = 0
    for step in range(profile.scroll_steps):
        await page.evaluate("window.scrollTo(0, document.body?.scrollHeight || 0)")
        await page.wait_for_timeout(config.settle_ms)
        current = await snapshot()
        quiet = quiet + 1 if current == previous else 0
        if quiet >= 2:
            break
        if step == profile.scroll_steps - 1 and current != previous:
            state.errors.append({"url": page.url, "message": "스크롤 수집 한도에서 콘텐츠가 계속 변경되었습니다. 일부 결과입니다."})
        previous = current
    await page.evaluate("window.scrollTo(0, 0)")
    for action_index in range(profile.max_actions if profile.controls else 0):
        chosen = None
        for selector in profile.controls:
            control = page.locator(selector)
            count = await control.count()
            if count > 1:
                raise ValueError(f"읽기용 선택자가 여러 요소와 일치합니다: {selector}")
            if count == 1 and await control.is_visible() and await control.is_enabled():
                chosen = selector, control
                break
        if chosen is None:
            break
        selector, control = chosen
        allowed = await control.evaluate("""el => {
            const tag = el.tagName.toLowerCase();
            if (tag === 'button') return el.type === 'button' || !el.closest('form');
            if (tag === 'summary') return true;
            if (tag === 'a') return !el.getAttribute('href') || /^(#|javascript:)/i.test(el.getAttribute('href'));
            return el.getAttribute('role') === 'button' && !el.closest('form');
        }""")
        if not allowed:
            raise ValueError(f"폼 제출 또는 일반 링크는 읽기용 클릭 대상이 아닙니다: {selector}")
        before = await page.evaluate(_FINGERPRINT)
        state.actions.append({"url": page.url, "selector": selector, "index": action_index + 1})
        await control.click(timeout=min(3000, int(config.page_timeout_sec * 1000)), no_wait_after=True)
        await page.wait_for_timeout(config.settle_ms)
        after = await snapshot()
        if after == before:
            state.errors.append({"url": page.url, "message": f"설정한 읽기 동작의 콘텐츠 변경을 확인하지 못했습니다: {selector}"})
            break
        if action_index == profile.max_actions - 1:
            if any([await page.locator(s).count() == 1 and await page.locator(s).is_visible() and await page.locator(s).is_enabled() for s in profile.controls]):
                state.errors.append({"url": page.url, "message": "읽기 동작 한도에 도달했습니다. 일부 결과일 수 있습니다."})
    return list(dict.fromkeys(links))


async def _inspect_frame(frame, prefix, inherited, page_url, script, state, emit, rules=None, content_selector=None):
    data = await frame.evaluate(script, {"contentSelector": content_selector})
    if state.page_diagnostics:
        diagnostic = state.page_diagnostics[-1]
        diagnostic["elements_examined"] += len(data["elements"])
        if content_selector:
            diagnostic["content_selector"] = content_selector
            diagnostic["content_roots_matched"] = data.get("content_roots_matched", 0)
    if data["truncated"] or data["links_truncated"]:
        state.errors.append({"url": page_url, "message": "요소·텍스트·링크 수집 한도 초과: 일부 콘텐츠가 누락되었습니다."})
    links = data["links"]
    for hit in classify_elements(data["elements"], inherited, rules):
        location = prefix + hit["location"]
        scope = prefix + (hit.get("content_scope") or hit["location"])
        state.finding_scopes.add((page_url, scope))
        key = page_url, location, hit["technique"]
        if key in state.seen_findings:
            continue
        state.seen_findings.add(key)
        finding = {"id": f"f_{len(state.findings) + 1:05d}", "url": page_url, "is_violation": True,
                   "location": location, "evidence_text": hit["text"], "technique": hit["technique"]}
        state.findings.append(finding)
        state.evidence_details[finding["id"]] = {"analysis": hit["analysis"],
            "style_reasons": hit.get("reasons", []), "computed_style": hit.get("computed_style", {}),
            "frame_flags": inherited, "action_sequence": list(state.actions),
            "scope_location": scope, "observed_at": datetime.now().astimezone().isoformat()}
        emit({"kind": "finding", "finding": finding})
    for hit in classify_candidates(data["elements"], rules):
        scope = prefix + (hit.get("content_scope") or hit["location"])
        key = page_url, scope, hit["category"]
        if (page_url, scope) in state.finding_scopes or key in state.candidate_keys:
            continue
        candidate = {"id": f"c_{len(state.ad_candidates) + 1:05d}", "url": page_url,
                     "location": prefix + hit["location"], "scope_location": scope,
                     "evidence_text": hit["text"], "category": hit["category"], "review_required": True,
                     "matched_keywords": hit["matched_keywords"], "reasons": hit["reasons"],
                     "observed_at": datetime.now().astimezone().isoformat(), "analysis": hit.get("analysis", {})}
        if hit.get('related_content_url'):
            candidate['related_content_url'] = hit['related_content_url']
        state.candidate_keys[key] = candidate["id"]
        state.ad_candidates.append(candidate)
        emit({"kind": "candidate", "candidate": candidate})
    for child in frame.child_frames:
        try:
            element = await child.frame_element()
            if content_selector and not await element.evaluate("(el, selector) => !!el.closest(selector)", content_selector):
                continue
            # Frame DOM elements appear in extract.js whenever they own fallback
            # text. Use a dedicated selector/style probe even for empty frames.
            probe = await element.evaluate(_FRAME_PROBE)
            flags = {key: inherited.get(key, False) or probe[key] for key in ("transparent", "offscreen")}
            frame_selector = probe["selector"]
            if probe["src"] is not None:
                frame_selector += "[src=" + json.dumps(probe["src"], ensure_ascii=False) + "]"
            await child.wait_for_load_state("domcontentloaded", timeout=1500)
            links.extend(await _inspect_frame(child, prefix + frame_selector + " >>> ", flags, page_url, script, state, emit, rules))
        except Exception as exc:
            state.errors.append({"url": page_url, "message": f"iframe 점검 실패 ({child.url}): {exc}"})
    return links


_FRAME_PROBE = """el => {
    const parts = [];
    for (let node = el; node; node = node.parentElement) {
        const tag = node.tagName.toLowerCase();
        const siblings = node.parentElement ? [...node.parentElement.children].filter(n => n.tagName === node.tagName) : [node];
        parts.unshift(tag + ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')');
        if (document.querySelectorAll(parts.join(' > ')).length === 1) break;
    }
    let opacity = 1, hidden = false, clipped = false, fixed = false;
    for (let node = el; node; node = node.parentElement) {
        const s = getComputedStyle(node);
        opacity *= Number(s.opacity);
        hidden ||= s.display === 'none';
        fixed ||= s.position === 'fixed';
        const box = node.getBoundingClientRect();
        clipped ||= (['hidden', 'clip'].includes(s.overflowX) && box.width <= 1) ||
            (['hidden', 'clip'].includes(s.overflowY) && box.height <= 1);
    }
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return {selector: parts.join(' > '), src: el.hasAttribute('src') ? el.src : null, transparent: opacity <= 0.01,
        offscreen: hidden || clipped || ['hidden', 'collapse'].includes(s.visibility) ||
        ((r.width > 0 || r.height > 0) && (r.right + (fixed ? 0 : scrollX) <= 0 ||
            r.bottom + (fixed ? 0 : scrollY) <= 0 ||
            (['absolute','fixed'].includes(s.position) && r.left + (fixed ? 0 : scrollX) > innerWidth + 2000) ||
            (fixed && r.top > innerHeight + 2000)))};
}"""
