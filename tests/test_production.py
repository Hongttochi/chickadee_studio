"""Production-path regressions. All servers/resources are owned loopback fixtures."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
import tkinter as tk
import unittest
from unittest.mock import patch

from chickadee.detection import Rules, techniques
from chickadee.gui import Application
from chickadee.profiles import SiteProfile
from chickadee.scanner import ScanConfig, ScanOutcome, scan

ROOT = Path(__file__).resolve().parent.parent


class Fixture:
    def __init__(self):
        self.counts = {}
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                fixture.counts["writes"] = fixture.counts.get("writes", 0) + 1
                self.send_response(200)
                self.end_headers()

            def do_GET(self):
                fixture.counts[self.path] = fixture.counts.get(self.path, 0) + 1
                status = 200
                if self.path == "/retry" and fixture.counts[self.path] == 1:
                    status, content = 503, "temporary failure"
                elif self.path == "/rate":
                    content = '<a href="/limited">first</a><a href="/after-limit">second</a>'
                elif self.path == "/limited":
                    status, content = 429, "rate limited"
                elif self.path == "/ajax429":
                    content = "<script>fetch('/limited').then(()=>fetch('/after-limit')).catch(()=>{});</script>"
                elif self.path == "/retry":
                    content = "<p>ㅋㅏㅈㅣㄴㅗ 가입 보너스</p>"
                elif self.path == "/comments":
                    content = '<p style="opacity:0">카지노 가입 보너스</p>'
                elif self.path == "/more":
                    content = '<p>ｃａｓｉｎｏ 가입 보너스</p>'
                elif self.path == "/dynamic":
                    content = '''<div id="comments"></div><div id="additional"></div>
                        <button type="button" id="more">댓글 더보기</button>
                        <script>setTimeout(()=>fetch('/comments').then(r=>r.text()).then(t=>document.querySelector('#comments').innerHTML=t),70);
                        document.querySelector('#more').onclick=async function(){this.disabled=true;
                        document.querySelector('#additional').innerHTML=await (await fetch('/more')).text()};</script>'''
                elif self.path == "/paging":
                    content = '''<div id="content"><p>ｃａｓｉｎｏ 가입 보너스</p></div><button id="next" type="button">다음</button>
                        <script>document.querySelector('#next').onclick=function(){this.disabled=true;
                        history.pushState({},'', '?page=2');document.querySelector('#content').innerHTML='<p>ㅋㅏㅈㅣㄴㅗ 가입 보너스</p>'};</script>'''
                elif self.path == "/form":
                    content = '<form action="/write" method="post"><button id="submit">등록</button></form>'
                elif self.path.startswith("/blocked"):
                    content = f'''<iframe src="{fixture.other_url}"></iframe>
                        <script>fetch('/write',{{method:'POST',body:'fixture'}}).catch(()=>{{}});
                        new WebSocket('{fixture.other_url.replace('http:', 'ws:')}socket');</script>'''
                else:
                    content = '<p>정상 안내</p>'
                raw = ('<!doctype html><html><meta charset="utf-8"><body>' + content + '</body></html>').encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                if status == 503:
                    self.send_header('Retry-After', '0.5')
                if status == 429:
                    self.send_header('Retry-After', '3600')
                self.end_headers()
                self.wfile.write(raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.url = f'http://127.0.0.1:{self.server.server_port}/'
        self.other_url = self.url

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class ProductionTests(unittest.TestCase):
    def test_local_mode_rejects_remote_url_before_browser_start(self):
        with self.assertRaisesRegex(ValueError, '로컬 전용'):
            ScanConfig('https://example.com/')
        self.assertTrue(ScanConfig('https://example.com/', allow_network=True).allow_network)

    def test_unrelated_jamo_and_fullwidth_do_not_label_a_plain_keyword(self):
        self.assertEqual(techniques('카지노 가입 보너스 １２３ ㄱ'), [])
        self.assertEqual(techniques('카지노 가입 보너스 １２３ ㄱ', True), ['TRANSPARENT'])
        self.assertEqual(techniques('timeslot 예약 안내', True), [])
        self.assertEqual(techniques('예방 안내입니다. ｃａｓｉｎｏ 가입 보너스'), ['HOMOGLYPH'])

    def test_external_rule_file(self):
        with tempfile.TemporaryDirectory() as folder:
            rules_file = Path(folder) / 'rules.json'
            rules_file.write_text(json.dumps({'version':'custom', 'keywords':['가상광고'], 'promotion':['가입'], 'prevention':['예방']}), encoding='utf-8')
            rules = Rules.load(rules_file)
            self.assertEqual(techniques('가상광고 가입', True, rules=rules), ['TRANSPARENT'])
            self.assertEqual(techniques('가상광고 예방', True, rules=rules), [])

    def test_delayed_comments_and_configured_read_control(self):
        with Fixture() as site, tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / 'profile.json'
            profile.write_text(json.dumps({'controls':['#more'], 'max_actions':2, 'scroll_steps':1}), encoding='utf-8')
            outcome = asyncio.run(scan(ScanConfig(site.url+'dynamic', settle_ms=150, interval_sec=0, profile_path=profile)))
            self.assertEqual(outcome.report['status'], 'completed', outcome.report)
            self.assertEqual({f['technique'] for f in outcome.result['findings']}, {'TRANSPARENT','HOMOGLYPH'})
            self.assertEqual(len(outcome.report['actions']), 1)
            self.assertGreaterEqual(outcome.report['states_scanned'], 2)
            for evidence in outcome.report['evidence_details'].values():
                self.assertTrue(evidence['analysis']['matches'])
                self.assertIn('rect', evidence['computed_style'])

    def test_javascript_pagination_keeps_each_url(self):
        with Fixture() as site, tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / 'profile.json'
            profile.write_text(json.dumps({'controls':['#next'], 'scroll_steps':0}), encoding='utf-8')
            outcome = asyncio.run(scan(ScanConfig(site.url+'paging', settle_ms=50, profile_path=profile)))
            self.assertEqual(outcome.report['status'], 'completed', outcome.report)
            self.assertEqual({f['url'] for f in outcome.result['findings']}, {site.url+'paging', site.url+'paging?page=2'})

    def test_retry_http_503(self):
        with Fixture() as site:
            outcome = asyncio.run(scan(ScanConfig(site.url+'retry', settle_ms=0)))
            self.assertEqual(outcome.report['status'], 'completed', outcome.report)
            self.assertEqual(outcome.report['retry_count'], 1)
            self.assertEqual(site.counts['/retry'], 2)
            self.assertEqual(outcome.result['findings'][0]['technique'], 'JAMO')

    def test_unlisted_origin_post_and_websocket_do_not_reach_servers(self):
        with Fixture() as site, Fixture() as other:
            site.other_url = other.url
            outcome = asyncio.run(scan(ScanConfig(site.url+'blocked', settle_ms=100)))
            self.assertEqual(outcome.report['status'], 'partial', outcome.report)
            self.assertEqual(other.counts, {})
            self.assertEqual(site.counts.get('writes', 0), 0)
            self.assertTrue(any(r['method']=='POST' for r in outcome.report['blocked_requests']))
            self.assertTrue(any(r['type']=='document' for r in outcome.report['blocked_requests']))

    def test_429_stops_origin_without_retry_or_following_queued_pages(self):
        with Fixture() as site:
            outcome = asyncio.run(scan(ScanConfig(site.url+'rate', settle_ms=0, interval_sec=0, retries=3)))
            self.assertEqual(outcome.report['status'], 'partial', outcome.report)
            self.assertEqual(outcome.report['retry_count'], 0)
            self.assertEqual(site.counts.get('/limited'), 1)
            self.assertNotIn('/after-limit', site.counts)
            self.assertEqual(outcome.report['pages_remaining'], 1)
            self.assertEqual(outcome.report['stopped_origins'][site.url.rstrip('/')]['retry_after'], '3600')
            self.assertFalse(any('최대 페이지' in e['message'] for e in outcome.report['errors']))
            with tempfile.TemporaryDirectory() as folder:
                path = outcome.save(Path(folder))
                self.assertEqual(ScanOutcome.load(path).report['stopped_origins'], outcome.report['stopped_origins'])

    def test_ajax_429_blocks_subsequent_requests_to_origin(self):
        with Fixture() as site:
            outcome = asyncio.run(scan(ScanConfig(site.url+'ajax429', settle_ms=200, interval_sec=0)))
            self.assertNotEqual(outcome.report['status'], 'completed', outcome.report)
            self.assertEqual(site.counts.get('/limited'), 1)
            self.assertNotIn('/after-limit', site.counts)
            self.assertTrue(outcome.report['stopped_origins'])

    def test_form_submission_control_is_rejected(self):
        with Fixture() as site, tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / 'profile.json'
            profile.write_text(json.dumps({'controls':['#submit'], 'scroll_steps':0}), encoding='utf-8')
            outcome = asyncio.run(scan(ScanConfig(site.url+'form', settle_ms=0, profile_path=profile)))
            self.assertNotEqual(outcome.report['status'], 'completed')
            self.assertEqual(site.counts.get('writes', 0), 0)
            self.assertTrue(any('폼 제출' in e['message'] for e in outcome.report['errors']))

    def test_profile_is_data_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            for data in [{'execute':'arbitrary code'}, {'max_actions':999}, {'allowed_resource_origins':['file:///secret']}]:
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    SiteProfile.load(path)

    def test_result_import_and_tamper_detection(self):
        result = json.loads((ROOT/'examples/result.sample.json').read_text(encoding='utf-8'))
        outcome = ScanOutcome(result, {'status':'completed', 'pages_scanned':[], 'errors':[]})
        with tempfile.TemporaryDirectory() as folder:
            path = outcome.save(Path(folder))
            self.assertEqual(ScanOutcome.load(path).result, result)
            path.write_text(path.read_text(encoding='utf-8')+' ', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '해시'):
                ScanOutcome.load(path)

    def test_gui_import_does_not_launch_scanner(self):
        root = tk.Tk()
        root.withdraw()
        app = Application(root)
        try:
            with patch('chickadee.gui.filedialog.askopenfilename', return_value=str(ROOT/'examples/result.sample.json')), patch('chickadee.gui.scan', side_effect=AssertionError('must not run')):
                app.open_result()
            self.assertEqual(len(app.findings), 4)
            self.assertIsNone(app.worker)
            self.assertIsNone(app.demo_site)
        finally:
            root.destroy()
