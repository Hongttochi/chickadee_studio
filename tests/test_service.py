import asyncio
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
import tkinter as tk
import unittest
from unittest.mock import patch

from chickadee.candidates import analyze_candidate
from chickadee.detection import analyze, techniques
from chickadee.exports import CSV_COLUMNS
from chickadee.gui import Application
from chickadee.scanner import ScanConfig, ScanOutcome, scan

ROOT = Path(__file__).resolve().parents[1]


class ServiceTests(unittest.TestCase):
    def test_default_launch_allows_external_url_without_flags(self):
        from chickadee.__main__ import main
        for flags, expected in (([], True), (["--local-only"], False)):
            with self.subTest(flags=flags), patch("sys.argv", ["ChickadeeBot.exe", *flags]), patch("chickadee.gui.launch") as launch:
                self.assertEqual(main(), 0)
                self.assertEqual(launch.call_args.args[2], expected)

    def test_mixed_vowels_domain_separator_and_non_keyword_digits(self):
        self.assertEqual(techniques('ㅋrㅈi노 가입 보너스'), ['HOMOGLYPH'])
        self.assertEqual(techniques('카지노 접속주소 demo｡com'), ['HOMOGLYPH'])
        self.assertEqual(techniques('카지노 가입 보너스 𝟑+𝟐'), [])
        result = analyze('카\u00ad지노 가입 보너스')
        self.assertTrue(result['is_advertisement'])
        self.assertEqual(result['additional_patterns'][0]['pattern'], 'SOFT_HYPHEN_INSERTION')
        self.assertEqual(techniques('카\u00ad지노 가입 보너스'), [])

    def test_editorial_disclaimer_and_filename_contexts(self):
        self.assertEqual(techniques('책임도박과 예방 안내를 제공하며 ｃａｓｉｎｏ 가입하고 보너스 받으세요'), ['HOMOGLYPH'])
        self.assertEqual(techniques('ｃａｓｉｎｏ 가입하고 보너스 받으세요라는 광고를 비판하는 기사', True), [])
        self.assertFalse(analyze_candidate('카지노 가입을 권하는 글이 아닌 보호자의 질문입니다.'))
        self.assertEqual(techniques('카지노-임대.png'), [])

    def test_general_candidates_are_separate_from_required_techniques(self):
        cases = {
            '카지노 가입하고 충전 보너스 받으세요.': 'GAMBLING',
            '신용 확인 없이 즉시 입금! 대출 상담 신청 https://loan.example.invalid': 'LOAN',
            '원금 보장 고수익 투자 모집 https://invest.example.invalid': 'INVESTMENT',
            '특별 할인 상품 주문하고 추천 수당 받으세요 https://shop.example.invalid': 'COMMERCIAL',
        }
        for text, category in cases.items():
            self.assertEqual(analyze_candidate(text)[0]['category'], category)
            self.assertEqual(techniques(text), [])
        for text in ('도서관 무료 부모교육 안내', '대출 광고를 누르지 마세요 https://warning.example.invalid',
                     '바카라 전자밸브 무료 배송', '카지노 실무개론'):
            self.assertEqual(analyze_candidate(text), [])

    def test_fixed_csv_columns_multiline_and_formula_safety(self):
        result = json.loads((ROOT/'examples/result.sample.json').read_text(encoding='utf-8'))
        text = '=HYPERLINK("https://example.invalid","x")\n쉼표, 따옴표 "원문"'
        result['findings'][0]['evidence_text'] = text
        outcome = ScanOutcome(result, {'status':'completed', 'pages_scanned':[], 'errors':[],
                                     'ad_candidates':[], 'evidence_details':{}})
        with tempfile.TemporaryDirectory() as folder:
            path = outcome.save(Path(folder))
            self.assertEqual(ScanOutcome.load(path).result['findings'][0]['evidence_text'], text)
            raw = path.with_suffix('.csv').read_bytes()
            self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
            with path.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, list(CSV_COLUMNS))
                rows = list(reader)
            self.assertEqual(rows[0]['evidence_text'], "'"+text)
            self.assertEqual(outcome.report['csv_sha256'], hashlib.sha256(raw).hexdigest())

    def test_candidate_csv_has_no_invented_technique_or_violation(self):
        result = json.loads((ROOT/'examples/result.empty.json').read_text(encoding='utf-8'))
        candidate = {'id':'c_00001','url':'https://example.invalid/', 'location':'article > p',
                     'evidence_text':'원금 보장 투자 모집', 'category':'INVESTMENT', 'review_required':True,
                     'matched_keywords':['투자'], 'reasons':['모집 권유']}
        outcome = ScanOutcome(result, {'status':'completed','pages_scanned':[],'errors':[], 'ad_candidates':[candidate]})
        with tempfile.TemporaryDirectory() as folder:
            path = outcome.save(Path(folder))
            loaded = ScanOutcome.load(path)
            self.assertEqual(len(loaded.report['ad_candidates']), 1)
            with path.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['record_kind'], 'ad_candidate')
            self.assertEqual(row['technique'], '')
            self.assertEqual(row['is_violation'], '')
            self.assertEqual(row['review_required'], 'true')

    def test_gui_search_candidate_filter_and_export(self):
        root = tk.Tk()
        root.withdraw()
        app = Application(root)
        try:
            self.assertTrue(app.allow_network)
            ScanConfig("http://113.198.66.73:18244/", allow_network=app.allow_network)
            result = json.loads((ROOT/'examples/result.sample.json').read_text(encoding='utf-8'))
            app.findings = result['findings']
            app.candidates = [{'id':'c_00001','url':'https://example.invalid/loan','location':'p',
                               'evidence_text':'대출 상담', 'category':'LOAN','reasons':['모집 권유']}]
            app.outcome = ScanOutcome(result, {'ad_candidates':app.candidates})
            app.set_filter('광고 의심')
            self.assertEqual(len(app.table.get_children()), 1)
            app.search.set('없는문구')
            self.assertFalse(app.table.get_children())
            app.search.set('대출')
            self.assertEqual(len(app.table.get_children()), 1)
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'내보내기.csv'
                with patch('chickadee.gui.filedialog.asksaveasfilename', return_value=str(path)):
                    app.export_csv()
                self.assertTrue(path.exists())
        finally:
            root.destroy()

    def test_css_only_dynamic_change_and_content_scope(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                if self.path == '/dynamic':
                    content = '''<p id="target">카지노 가입 보너스</p><button id="apply" type="button">더보기</button>
                    <script>document.querySelector('#apply').onclick=function(){this.disabled=true;document.querySelector('#target').style.opacity=0}</script>'''
                elif self.path == '/post':
                    content = '<aside style="opacity:0">카지노 가입 보너스</aside><article class="post-detail"><small>정서·행동 등 발달 분야</small><h3>동네 도서관 무료 부모교육 안내</h3><p>공공 교육 프로그램입니다.</p></article><article class="post-detail"><h3>투자 정보</h3><p>원금 보장 고수익 투자 모집 https://invest.example.invalid</p></article>'
                else:
                    content = '<aside style="opacity:0">카지노 가입 보너스</aside><a href="/post">글</a>'
                raw = ('<!doctype html><meta charset="utf-8"><body>'+content+'</body>').encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with tempfile.TemporaryDirectory() as folder:
                profile = Path(folder)/'profile.json'
                profile.write_text(json.dumps({'controls':['#apply'],'max_actions':1,'scroll_steps':0}),encoding='utf-8')
                outcome = asyncio.run(scan(ScanConfig(base+'/dynamic',profile_path=profile,settle_ms=20)))
                self.assertEqual(outcome.report['status'],'completed',outcome.report)
                self.assertEqual([f['technique'] for f in outcome.result['findings']],['TRANSPARENT'])
                self.assertFalse(outcome.report['ad_candidates'])
                profile.write_text(json.dumps({'content_selector':'.post-detail','scroll_steps':0}),encoding='utf-8')
                outcome = asyncio.run(scan(ScanConfig(base+'/',profile_path=profile,settle_ms=20,interval_sec=0)))
                self.assertEqual(outcome.report['status'],'completed',outcome.report)
                self.assertEqual(len(outcome.report['pages_scanned']),2)
                self.assertEqual(outcome.result['findings'],[])
                self.assertEqual(len(outcome.report['ad_candidates']),1)
                self.assertEqual(outcome.report['ad_candidates'][0]['category'],'INVESTMENT')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
