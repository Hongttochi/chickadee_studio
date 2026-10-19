import asyncio
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Event
import time
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from . import __version__
from .detection import Rules, analyze, classify_elements
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
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


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
            raise ValueError("이 실행은 로컬 전용입니다. 실제 사이트 검사는 별도 VM에서 --network 옵션으로 실행하고 이 PC에는 결과 JSON만 가져오세요. 이 옵션은 VM 격리를 검증하지 않습니다.")
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
        report = {**self.report, "result_sha256": hashlib.sha256(payload).hexdigest(), "output_path": str(folder / "result.json")}
        # Each file replaces atomically. A matching SHA-256 in the sidecar lets
        # consumers detect an interrupted write between the two replacements.
        for name, content in (("result.json", payload), ("scan-report.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))):
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(dir=folder, prefix=".chickadee-", delete=False) as stream:
                    temp_path = Path(stream.name)
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_path, folder / name)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        self.report.update(report)
        return folder / "result.json"

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
              "errors": state.errors, "finding_count": len(state.findings),
              "states_scanned": state.states_scanned, "retry_count": state.retry_count,
              "evidence_details": state.evidence_details, "actions": state.actions,
              "blocked_requests": state.blocked_requests,
              "stopped_origins": {v["origin"]: v for v in state.stopped_origins.values()},
              "rules_version": rules.version, "profile": asdict(profile),
              "execution_mode": "network-explicit" if config.allow_network else "loopback-only",
              "limits": {"max_pages": config.max_pages, "timeout_sec": config.timeout_sec,
                         "page_timeout_sec": config.page_timeout_sec, "settle_ms": config.settle_ms,
                         "retries": config.retries, "interval_sec": config.interval_sec}}
    return ScanOutcome(result, report)


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
            queue = deque([normalize_url(config.entry_url)])
            queued = {visit_key(queue[0])}
            visited = set()
            site = origin(queue[0])
            attempts = 0
            while queue and attempts < config.max_pages:
                if site in state.stopped_origins:
                    break
                url = queue.popleft()
                key = visit_key(url)
                if key in visited:
                    continue
                visited.add(key)
                attempts += 1
                if attempts > 1:
                    await asyncio.sleep(config.interval_sec)
                state.remaining = len(queue) + 1
                emit({"kind": "status", "message": f"{attempts}/{config.max_pages} 페이지 점검 중: {url}"})
                page = await context.new_page()
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.on("popup", lambda popup: popup.close())
                try:
                    async def inspect():
                        nonlocal site
                        response = await _navigate(page, url, config, state, emit)
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
                            queue.append(candidate)
                            queued.add(candidate_key)
                except Exception as exc:
                    state.errors.append({"url": url, "message": str(exc) or "페이지 제한시간을 초과했습니다."})
                    emit({"kind": "warning", "message": f"점검 누락: {url} - {exc or '페이지 제한시간 초과'}"})
                finally:
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
            if attempt == config.retries or any(r["url"] == url for r in state.blocked_requests):
                raise
            delay = min(5, 1 + attempt)
        state.retry_count += 1
        emit({"kind": "status", "message": f"일시 오류 재시도 {attempt + 1}/{config.retries}: {url}"})
        await asyncio.sleep(delay)


_FINGERPRINT = """() => {
    const body = document.body;
    const text = body?.textContent || '';
    return JSON.stringify([location.href, text.length, text.slice(0, 2000), text.slice(-2000),
      body?.scrollHeight, document.querySelectorAll('*').length,
      [...document.querySelectorAll('a[href]')].map(a=>a.href).join('|').slice(0,20000)]);
}"""


async def _inspect_dynamic(page, config, profile, rules, site, script, state, emit):
    links, seen = [], set()
    async def snapshot():
        if site in state.stopped_origins:
            raise RuntimeError("HTTP 429 수신으로 해당 origin 수집을 중단했습니다.")
        if origin(page.url) != site:
            raise RuntimeError("설정된 동작이 다른 사이트로 이동하여 점검을 중단했습니다.")
        fingerprint = await page.evaluate(_FINGERPRINT)
        if fingerprint not in seen:
            seen.add(fingerprint)
            state.states_scanned += 1
            links.extend(await _inspect_frame(page.main_frame, "", {}, page.url, script, state, emit, rules))
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


async def _inspect_frame(frame, prefix, inherited, page_url, script, state, emit, rules=None):
    data = await frame.evaluate(script, {})
    if data["truncated"] or data["links_truncated"]:
        state.errors.append({"url": page_url, "message": "요소·텍스트·링크 수집 한도 초과: 일부 콘텐츠가 누락되었습니다."})
    links = data["links"]
    for hit in classify_elements(data["elements"], inherited, rules):
        location = prefix + hit["location"]
        key = page_url, location, hit["technique"]
        if key in state.seen_findings:
            continue
        state.seen_findings.add(key)
        finding = {"id": f"f_{len(state.findings) + 1:05d}", "url": page_url, "is_violation": True,
                   "location": location, "evidence_text": hit["text"], "technique": hit["technique"]}
        state.findings.append(finding)
        state.evidence_details[finding["id"]] = {"analysis": analyze(hit["text"], rules),
            "style_reasons": hit.get("reasons", []), "computed_style": hit.get("computed_style", {}),
            "frame_flags": inherited, "action_sequence": list(state.actions)}
        emit({"kind": "finding", "finding": finding})
    for child in frame.child_frames:
        try:
            element = await child.frame_element()
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
