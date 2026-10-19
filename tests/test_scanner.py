import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from playwright.async_api import async_playwright

from chickadee.demo import DemoSite
from chickadee.scanner import ScanConfig, _State, _inspect_frame, scan

ROOT = Path(__file__).resolve().parent.parent


class ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = DemoSite().start()
        cls.outcome = asyncio.run(scan(ScanConfig(cls.site.url, settle_ms=100)))

    @classmethod
    def tearDownClass(cls):
        cls.site.close()

    def test_full_demo_and_query_navigation(self):
        outcome = self.outcome
        self.assertEqual(outcome.report["status"], "completed", outcome.report)
        self.assertEqual(len(outcome.report["pages_scanned"]), 4)
        self.assertEqual(len(outcome.result["findings"]), 14)
        self.assertEqual(Counter(f["technique"] for f in outcome.result["findings"]),
                         {"HOMOGLYPH": 2, "JAMO": 4, "TRANSPARENT": 5, "OFFSCREEN": 3})
        nested = [f for f in outcome.result["findings"] if " >>> " in f["location"]]
        self.assertEqual(len(nested), 2)
        self.assertTrue(all(f["location"].count(" >>> ") == 2 for f in nested))
        self.assertFalse(any("/empty" in f["url"] for f in outcome.result["findings"]))

    def test_schema_encoding_and_identity(self):
        validator = Draft202012Validator(json.loads((ROOT / "schemas/result.schema.json").read_text(encoding="utf-8")), format_checker=FormatChecker())
        validator.validate(self.outcome.result)
        with tempfile.TemporaryDirectory(prefix="chickadee 한글 ") as folder:
            path = self.outcome.save(Path(folder))
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            report = json.loads(path.with_name("scan-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["result_sha256"], hashlib.sha256(raw).hexdigest())
        ids = [f["id"] for f in self.outcome.result["findings"]]
        keys = [(f["url"], f["location"], f["technique"]) for f in self.outcome.result["findings"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(keys), len(set(keys)))

    def test_selectors_point_to_exact_original_evidence(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    page = await browser.new_page()
                    current = None
                    for finding in self.outcome.result["findings"]:
                        if current != finding["url"]:
                            await page.goto(finding["url"])
                            current = finding["url"]
                        frame = page.main_frame
                        parts = finding["location"].split(" >>> ")
                        for part in parts[:-1]:
                            selector, encoded = part.rsplit("[src=", 1)
                            self.assertEqual(await frame.locator(selector).count(), 1)
                            element = await frame.locator(selector).element_handle()
                            self.assertEqual(await element.evaluate("el => el.src"), json.loads(encoded[:-1]))
                            frame = await element.content_frame()
                        self.assertEqual(await frame.locator(parts[-1]).count(), 1, finding)
                        self.assertEqual(await frame.locator(parts[-1]).text_content(), finding["evidence_text"])
                finally:
                    await browser.close()
        asyncio.run(check())

    def test_empty_page(self):
        outcome = asyncio.run(scan(ScanConfig(self.site.url + "empty", settle_ms=0)))
        self.assertEqual(outcome.report["status"], "completed")
        self.assertEqual(outcome.result["findings"], [])

    def test_page_limit_is_partial(self):
        outcome = asyncio.run(scan(ScanConfig(self.site.url, max_pages=1, settle_ms=0)))
        self.assertEqual(outcome.report["status"], "partial")
        self.assertEqual(outcome.report["pages_remaining"], 3)

    def test_cancel_and_deadline_are_explicit(self):
        stop = Event()
        stop.set()
        cancelled = asyncio.run(scan(ScanConfig(self.site.url), stop))
        self.assertEqual(cancelled.report["status"], "cancelled")
        timed = asyncio.run(scan(ScanConfig(self.site.url, timeout_sec=0.01)))
        self.assertEqual(timed.report["status"], "partial")
        self.assertTrue(timed.report["errors"])

    def test_cancel_after_a_finding_preserves_partial_results(self):
        stop = Event()
        def emit(event):
            if event["kind"] == "finding":
                stop.set()
        outcome = asyncio.run(scan(ScanConfig(self.site.url, settle_ms=100), stop, emit))
        self.assertEqual(outcome.report["status"], "cancelled")
        self.assertGreater(len(outcome.result["findings"]), 0)
        with tempfile.TemporaryDirectory() as folder:
            outcome.save(Path(folder))
            report = json.loads((Path(folder) / "scan-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "cancelled")

    def test_page_timeout_is_reported(self):
        outcome = asyncio.run(scan(ScanConfig(self.site.url, page_timeout_sec=0.1, settle_ms=500)))
        self.assertEqual(outcome.report["status"], "failed")
        self.assertTrue(outcome.report["errors"])

    def test_missing_page_reports_failure(self):
        outcome = asyncio.run(scan(ScanConfig(self.site.url + "missing", settle_ms=0)))
        self.assertEqual(outcome.report["status"], "failed")
        self.assertIn("404", outcome.report["errors"][0]["message"])

    def test_dynamic_styles_inherited_and_frame_state(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    page = await browser.new_page()
                    await page.set_content('''<body><div style="display:none"><p class="hidden">카지노 가입 보너스 지급</p></div>
                        <p style="position:absolute;top:-9999px">슬롯 무료 체험</p>
                        <p class="normal">일반 안내문</p>
                        <iframe style="opacity:0" srcdoc="<p>카지노 가입 보너스</p>"></iframe></body>''')
                    state = _State()
                    await _inspect_frame(page.main_frame, "", {}, "https://example.com/", (ROOT / "chickadee/extract.js").read_text(encoding="utf-8"), state, lambda _: None)
                    self.assertEqual(Counter(f["technique"] for f in state.findings), {"OFFSCREEN": 2, "TRANSPARENT": 1})
                    self.assertTrue(any(" >>> " in f["location"] for f in state.findings))
                finally:
                    await browser.close()
        asyncio.run(check())

    def test_visible_child_and_script_source_are_not_hidden_ads(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    page = await browser.new_page()
                    await page.set_content('''<body>
                        <div style="color:white;background:white"><p style="color:black">카지노 가입 보너스 지급</p></div>
                        <div style="display:none">일반 안내문<script type="application/json">"카지노 가입 보너스 지급"</script></div>
                        </body>''')
                    state = _State()
                    await _inspect_frame(page.main_frame, "", {}, "https://example.com/", (ROOT / "chickadee/extract.js").read_text(encoding="utf-8"), state, lambda _: None)
                    self.assertEqual(state.findings, [])
                finally:
                    await browser.close()
        asyncio.run(check())

    def test_direct_body_text_and_output_failure(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    page = await browser.new_page()
                    await page.set_content('<body style="opacity:0">카지노 가입 보너스</body>')
                    state = _State()
                    await _inspect_frame(page.main_frame, "", {}, "https://example.com/", (ROOT / "chickadee/extract.js").read_text(encoding="utf-8"), state, lambda _: None)
                    self.assertEqual(len(state.findings), 1)
                    self.assertEqual(state.findings[0]["technique"], "TRANSPARENT")
                finally:
                    await browser.close()
        asyncio.run(check())
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaises(OSError):
                self.outcome.save(Path(file.name))

    def test_cross_origin_frame(self):
        async def check():
            with DemoSite() as other:
                async with async_playwright() as pw:
                    browser = await pw.chromium.launch()
                    try:
                        page = await browser.new_page()
                        await page.goto(self.site.url + "empty")
                        await page.evaluate("url => {const f=document.createElement('iframe');f.src=url;document.body.append(f)}", other.url + "frame/inner")
                        await page.wait_for_timeout(300)
                        state = _State()
                        await _inspect_frame(page.main_frame, "", {}, page.url, (ROOT / "chickadee/extract.js").read_text(encoding="utf-8"), state, lambda _: None)
                        self.assertEqual(Counter(f["technique"] for f in state.findings), {"JAMO": 1, "TRANSPARENT": 1})
                        self.assertTrue(all(other.url in f["location"] for f in state.findings))
                    finally:
                        await browser.close()
        asyncio.run(check())
