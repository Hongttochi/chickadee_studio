"""Research-derived regressions; original snippets are never executed.

Rendered cases below are SYNTHETIC, written here with no external resources,
links or scripts. IDs identify inspiration, not validation of a live source.
"""
import asyncio
import json
from pathlib import Path
import unittest

from playwright.async_api import async_playwright

from chickadee.detection import analyze, techniques
from chickadee.scanner import _State, _inspect_frame
from scripts.validate_research import DATA, validate

EXTRACT = (Path(__file__).resolve().parents[1] / "chickadee/extract.js").read_text(encoding="utf-8")


class ResearchTests(unittest.TestCase):
    def test_imported_corpus_integrity_and_observation_boundaries(self):
        result = validate()
        self.assertEqual(result["total_records"], 43)
        self.assertEqual(result["original_files_sha256_verified"], 8)
        self.assertEqual(result["origin_counts"], {"observed": 38, "reported": 5})
        self.assertEqual(result["direct_ad_techniques"].get("TRANSPARENT", 0), 0)

    def test_normal_evidence_is_not_advertising_even_with_hidden_style(self):
        # Text-level check only: not an evaluation of those original DOMs.
        for line in (DATA / "negatives.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            with self.subTest(id=row["id"]):
                self.assertFalse(analyze(row["evidence_text"])["is_advertisement"])
                self.assertEqual(techniques(row["evidence_text"], True, True), [])

    def test_mixed_hangul_latin_and_partial_spaced_jamo(self):
        cases = {
            "ㅋr지노 가입 보너스": ["HOMOGLYPH"],
            "ㅂr카라 가입 보너스": ["HOMOGLYPH"],
            "ㅍ ㅏ워볼 가입 보너스": ["JAMO"],
            "미니ㄱ ㅔ임 임대": ["JAMO"],
            "ㅍ ㅏ워볼, 미니ㄱ ㅔ임, ㅋr지노 임대": ["HOMOGLYPH", "JAMO"],
            "ㅋr지노 실무 교재": [],
            "r 무료 안내": [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(techniques(text), expected)
        match = analyze("ㅋr지노 가입 보너스")["matches"][0]
        self.assertEqual(match["source_span"], [0, 4])

    def test_domain_feature_requires_same_local_promotional_context(self):
        for suffix in ("CΟΜ", "сом"):
            text = "카지노 가입 보너스 demo." + suffix
            result = analyze(text)
            self.assertEqual(techniques(text), ["HOMOGLYPH"])
            feature = result["contextual_homoglyphs"][0]
            self.assertEqual(text[slice(*feature["source_span"])], suffix)
            self.assertFalse(any(m["homoglyph"] for m in result["matches"]))
            self.assertEqual(techniques(suffix), [])
            self.assertEqual(techniques("그리스 문자 교육 " + suffix), [])
            self.assertEqual(techniques("카지노 가입 보너스\n별도 문장 " + suffix), [])
            self.assertEqual(techniques("카지노 가입 보너스 demo." + suffix + " 사칭 주의"), [])

    def test_topic_only_and_critical_quotations_are_not_ads(self):
        for text in ("바카라 전자밸브 무료 배송", "카지노 기구 검사", "카지노 가입 보너스로 현혹하는 광고를 취재했다"):
            # The valve case includes a generic commercial term: a real
            # product exclusion is required, not just promotion gating.
            with self.subTest(text=text):
                self.assertFalse(analyze(text)["is_advertisement"])

    def test_synthetic_dom_visibility_and_scroll_regressions(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(chromium_sandbox=True)
                try:
                    page = await browser.new_page(viewport={"width": 1000, "height": 600})
                    # All CSS/HTML is authored here. No imported HTML is parsed.
                    await page.set_content('''<body>
                        <p id="visible">카지노 가입 보너스</p>
                        <div style="opacity:0.003"><p id="low">casino free bonus</p></div>
                        <div style="width:1px;height:1px;overflow:hidden"><p id="box">slot gacor</p></div>
                        <div style="height:0;overflow:hidden"><p id="zero">Toto 4D</p></div>
                        <p id="negative" style="position:absolute;left:-9999px;top:-9999px">slot777</p>
                        <p id="escaped">&lt;a style="display:none;color:transparent"&gt;slot gacor&lt;/a&gt;</p>
                        <textarea style="display:none">카지노 가입 보너스</textarea>
                        <div style="height:2200px"></div>
                        <iframe id="frame" srcdoc="&lt;p&gt;카지노 가입 보너스&lt;/p&gt;"></iframe>
                        <div style="height:1500px"></div></body>''')
                    data = await page.evaluate(EXTRACT, {})
                    def item(name):
                        return next(e for e in reversed(data["elements"]) if e['text'] == name)
                    low = item('casino free bonus')
                    self.assertTrue(low['transparent'])
                    self.assertAlmostEqual(low['computed_style']['effective_opacity'], .003)
                    box = item('slot gacor')
                    self.assertTrue(box['offscreen'])
                    self.assertNotEqual(box['computed_style']['font_size'], '1px')
                    self.assertIn('요소/조상 0~1px 상자와 overflow:hidden/clip', box['reasons'])
                    self.assertTrue(item('Toto 4D')['offscreen'])
                    escaped = next(e for e in data['elements'] if e['text'].startswith('<a style='))
                    self.assertFalse(escaped['transparent'] or escaped['offscreen'])
                    self.assertFalse(any('textarea' in e['location'] for e in data['elements']))
                    state = _State()
                    await _inspect_frame(page.main_frame, '', {}, 'http://127.0.0.1/', EXTRACT, state, lambda _: None)
                    baseline = {(f['location'], f['technique']) for f in state.findings}
                    self.assertEqual(len(baseline), 4)
                    # After scrolling, both the paragraph and iframe are above
                    # the viewport but still in normal document flow.
                    await page.evaluate('scrollTo(0, 10000)')
                    self.assertGreater(await page.evaluate('scrollY'), 600)
                    state = _State()
                    await _inspect_frame(page.main_frame, '', {}, 'http://127.0.0.1/', EXTRACT, state, lambda _: None)
                    self.assertEqual({(f['location'], f['technique']) for f in state.findings}, baseline)
                finally:
                    await browser.close()
        asyncio.run(check())
