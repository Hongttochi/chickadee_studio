import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Event
import time
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from . import __version__
from .detection import classify_elements

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


def output_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ScanConfig:
    entry_url: str
    max_pages: int = 50
    timeout_sec: float = 300
    page_timeout_sec: float = 15
    settle_ms: int = 500

    def __post_init__(self):
        normalize_url(self.entry_url)
        if not 1 <= self.max_pages <= 10000:
            raise ValueError("최대 페이지 수는 1~10000 사이여야 합니다.")
        if not 0 < self.timeout_sec <= 1800 or not 0 < self.page_timeout_sec <= 120:
            raise ValueError("전체 제한시간은 0초 초과~1800초, 페이지 제한은 0초 초과~120초여야 합니다.")
        if not 0 <= self.settle_ms <= 5000:
            raise ValueError("렌더링 대기는 0~5000ms 사이여야 합니다.")


@dataclass
class ScanOutcome:
    result: dict
    report: dict

    def save(self, folder: Path) -> Path:
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


@dataclass
class _State:
    findings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    seen_findings: set = field(default_factory=set)
    remaining: int = 0


async def scan(config: ScanConfig, stop: Event | None = None, emit=None) -> ScanOutcome:
    stop = stop or Event()
    emit = emit or (lambda event: None)
    started = datetime.now().astimezone()
    clock = time.monotonic()
    state = _State()
    status = "completed"
    emit({"kind": "status", "message": "브라우저를 준비하고 있습니다."})
    worker = asyncio.create_task(_crawl(config, state, emit))
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
              "limits": {"max_pages": config.max_pages, "timeout_sec": config.timeout_sec,
                         "page_timeout_sec": config.page_timeout_sec, "settle_ms": config.settle_ms}}
    return ScanOutcome(result, report)


async def _crawl(config: ScanConfig, state: _State, emit):
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
            browser = await pw.chromium.launch(headless=True)
        except Exception as exc:
            raise RuntimeError("Chromium을 시작하지 못했습니다. 소스 실행 시 python -m playwright install chromium을 PLAYWRIGHT_BROWSERS_PATH=0 설정 후 실행하세요. " + str(exc)) from exc
        try:
            context = await browser.new_context(viewport={"width": 1366, "height": 900},
                                                accept_downloads=False, service_workers="block")
            queue = deque([normalize_url(config.entry_url)])
            queued = {visit_key(queue[0])}
            visited = set()
            site = origin(queue[0])
            attempts = 0
            while queue and attempts < config.max_pages:
                url = queue.popleft()
                key = visit_key(url)
                if key in visited:
                    continue
                visited.add(key)
                attempts += 1
                state.remaining = len(queue) + 1
                emit({"kind": "status", "message": f"{attempts}/{config.max_pages} 페이지 점검 중: {url}"})
                page = await context.new_page()
                page.on("dialog", lambda dialog: dialog.dismiss())
                try:
                    async def inspect():
                        nonlocal site
                        response = await page.goto(url, wait_until="domcontentloaded", timeout=int(config.page_timeout_sec * 1000))
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
                        # Trigger common lazy content without clicking forms.
                        await page.evaluate("window.scrollTo(0, document.body?.scrollHeight || 0)")
                        await page.wait_for_timeout(config.settle_ms)
                        await page.evaluate("window.scrollTo(0, 0)")
                        await page.wait_for_timeout(config.settle_ms)
                        return await _inspect_frame(page.main_frame, "", {}, page.url, script, state, emit)
                    links = await asyncio.wait_for(inspect(), timeout=config.page_timeout_sec)
                    state.pages.append(page.url)
                    for link in links:
                        try:
                            candidate = normalize_url(link)
                            candidate_key = visit_key(candidate)
                        except ValueError:
                            continue
                        if origin(candidate) == site and candidate_key not in queued and candidate_key not in visited:
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
            if queue:
                state.errors.append({"url": config.entry_url, "message": "최대 페이지 수에 도달했습니다. 일부 결과입니다."})
        finally:
            await browser.close()
    finally:
        await pw.stop()


async def _inspect_frame(frame, prefix, inherited, page_url, script, state, emit):
    data = await frame.evaluate(script, {})
    if data["truncated"] or data["links_truncated"]:
        state.errors.append({"url": page_url, "message": "요소·텍스트·링크 수집 한도 초과: 일부 콘텐츠가 누락되었습니다."})
    links = data["links"]
    for hit in classify_elements(data["elements"], inherited):
        location = prefix + hit["location"]
        key = page_url, location, hit["technique"]
        if key in state.seen_findings:
            continue
        state.seen_findings.add(key)
        finding = {"id": f"f_{len(state.findings) + 1:05d}", "url": page_url, "is_violation": True,
                   "location": location, "evidence_text": hit["text"], "technique": hit["technique"]}
        state.findings.append(finding)
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
            links.extend(await _inspect_frame(child, prefix + frame_selector + " >>> ", flags, page_url, script, state, emit))
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
    let opacity = 1, hidden = false;
    for (let node = el; node; node = node.parentElement) {
        const s = getComputedStyle(node);
        opacity *= Number(s.opacity);
        hidden ||= s.display === 'none';
    }
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return {selector: parts.join(' > '), src: el.hasAttribute('src') ? el.src : null, transparent: opacity <= 0.01,
        offscreen: hidden || ['hidden', 'collapse'].includes(s.visibility) ||
        ((r.width > 0 || r.height > 0) && (r.right <= 0 || r.bottom <= 0))};
}"""
