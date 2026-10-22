import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest

from chickadee.scanner import ScanConfig, navigation_priority, readonly_navigation, scan


class NavigationTests(unittest.TestCase):
    def test_write_and_destructive_endpoints_are_not_followed(self):
        for url in ('https://example.invalid/board/write.do', 'https://example.invalid/logout',
                    'https://example.invalid/board?mode=delete', 'https://example.invalid/board?act=update'):
            self.assertFalse(readonly_navigation(url))
        self.assertTrue(readonly_navigation('https://example.invalid/board/view.do?board_idx=7'))

    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                if self.path == '/':
                    body = ''.join(f'<a href="/menu{i}">메뉴</a>' for i in range(6))
                    body += '<a href="/board/index.do">게시판</a><a href="http://[">잘못된 주소</a>'
                elif self.path == '/board/index.do':
                    body = '<article><a href="/board/view.do?board_idx=7">카지노 가입 보너스</a></article>'
                    body += '<button data-url="/board/view.do?board_idx=8">다음 글</button>'
                    body += '''<button onclick="location.href='/board/view.do?board_idx=9'; return false;">다른 글</button>'''
                    body += '''<button onclick="location.href='/write'+userId">실행 금지</button>'''
                    body += '''<button onclick="fetch('/write')">실행 금지</button>'''
                elif self.path.startswith('/board/view.do?'):
                    body = '<article><p>카지노 가입하고 충전 보너스 받으세요.</p></article>'
                else:
                    body = '<p>일반 안내</p>'
                raw = ('<!doctype html><meta charset="utf-8"><body>'+body+'</body>').encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_content_first_with_small_page_budget(self):
        outcome = asyncio.run(scan(ScanConfig(self.base, max_pages=3, settle_ms=10, interval_sec=0)))
        self.assertEqual([u.removeprefix(self.base) for u in outcome.report['pages_scanned']],
                         ['/', '/board/index.do', '/board/view.do?board_idx=7'])
        diagnostics = outcome.report['page_diagnostics']
        self.assertEqual(len(diagnostics), 3)
        self.assertEqual(diagnostics[1]['links_discovered'], 3)
        self.assertTrue(all(p['elements_examined'] > 0 for p in diagnostics))
        self.assertEqual(len(outcome.report['ad_candidates']), 1)
        self.assertIn('summary_observations', outcome.report['ad_candidates'][0])

    def test_literal_endpoint_discovery_and_summary_dedup(self):
        outcome = asyncio.run(scan(ScanConfig(self.base, max_pages=20, settle_ms=10, interval_sec=0)))
        self.assertEqual(outcome.report['status'], 'completed', outcome.report['errors'])
        candidates = outcome.report['ad_candidates']
        self.assertEqual(len(candidates), 3)
        self.assertEqual({c['url'].split('=')[-1] for c in candidates}, {'7', '8', '9'})
        self.assertFalse(any('/write' in u for u in outcome.report['pages_scanned']))
        self.assertGreater(navigation_priority(self.base+'/login/'), navigation_priority(self.base+'/board/'))
