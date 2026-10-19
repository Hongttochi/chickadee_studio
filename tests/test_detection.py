import unittest

from chickadee.detection import techniques
from chickadee.scanner import ScanConfig, normalize_url, visit_key


class DetectionTests(unittest.TestCase):
    def test_obfuscated_promotions(self):
        cases = [
            ("ｃａｓｉｎｏ 가입 보너스", ["HOMOGLYPH"]),
            ("саsіnо 가입 보너스", ["HOMOGLYPH"]),
            ("cas1n0 bonus", ["HOMOGLYPH"]),
            ("cas１n０ bonus", ["HOMOGLYPH"]),
            ("ㅋㅏㅈㅣㄴㅗ 가입 보너스", ["JAMO"]),
            ("카지노 가입 보너스", ["JAMO"]),
            ("ㅅㅡㄹㄹㅗㅅ 무료", ["JAMO"]),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(techniques(text), expected)

    def test_styles_and_stacked_techniques(self):
        self.assertEqual(techniques("ㅋㅏㅈㅣㄴㅗ 가입 보너스", True, True), ["JAMO", "TRANSPARENT", "OFFSCREEN"])
        self.assertEqual(techniques("카지노 가입 보너스", True), ["TRANSPARENT"])
        self.assertEqual(techniques("슬롯 무료 체험 바로가기", False, True), ["OFFSCREEN"])

    def test_normal_controls(self):
        for text in ["본문 바로가기", "민원 신청 안내", "도박 예방: 카지노 광고를 발견하면 신고하세요", "카지노 가입 보너스 지급 피해 주의"]:
            with self.subTest(text=text):
                self.assertEqual(techniques(text, True, True), [])
        self.assertEqual(techniques("카지노 가입 보너스 30%"), [])

    def test_url_identity_keeps_query_values(self):
        self.assertEqual(visit_key("https://example.com/?id=1&x=2#top"), visit_key("https://example.com/?x=2&id=1"))
        self.assertNotEqual(visit_key("https://example.com/?id=1"), visit_key("https://example.com/?id=2"))
        self.assertNotEqual(visit_key("https://example.com/"), visit_key("http://example.com/"))
        self.assertEqual(normalize_url(" https://example.com#top "), "https://example.com/")

    def test_invalid_inputs(self):
        for url in ["file:///secret", "javascript:alert(1)", "https://", "https://user:password@example.com", "https://example.com:bad"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)
        for options in [{"max_pages": 0}, {"timeout_sec": 1801}, {"settle_ms": -1}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                ScanConfig("https://example.com", **options)
