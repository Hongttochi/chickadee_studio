import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from chickadee.authentication import LoginCoordinator
from chickadee.control import ScanControl
from chickadee.scanner import ScanConfig, scan

class LoginTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_is_private_and_rejects_stale_or_foreign_cookie(self):
        auth=LoginCoordinator(); events=[]
        task=asyncio.create_task(auth.wait('https://example.org/login','https://example.org/private',[{'value':'secret'}],events.append))
        await asyncio.sleep(.01)
        request=auth.state()['request_id']
        self.assertNotIn('secret',json.dumps(events))
        with self.assertRaises(ValueError): auth.complete('old',[],True)
        with self.assertRaises(ValueError): auth.complete(request,[{'domain':'other.org','name':'sid','value':'x','path':'/'}])
        auth.complete(request,skip=True)
        self.assertTrue((await task)['skip'])
        self.assertIsNone(auth.state()); self.assertEqual(auth.cookies,[])

    async def test_cancel_releases_wait_and_session(self):
        auth = LoginCoordinator(); events = []
        task = asyncio.create_task(auth.wait('https://example.org/login', 'https://example.org', [{'value': 'secret'}], events.append))
        await asyncio.sleep(.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertIsNone(auth.state())
        self.assertEqual(auth.cookies, [])
        self.assertEqual(events[-1]['kind'], 'login_finished')

    async def test_login_resume_retries_protected_page_and_excludes_wait(self):
        await self.run_site(skip=False)

    async def test_skipped_login_is_not_a_clean_scan(self):
        await self.run_site(skip=True)

    async def run_site(self,skip):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                if self.path=='/private' and 'sid=authenticated' not in self.headers.get('Cookie',''):
                    self.send_response(302);self.send_header('Location','/login');self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
                self.wfile.write(b'<form><input type="password"></form>' if self.path=='/login' else b'<article>Public content</article>')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        control=ScanControl(); events=[]; workers=[]
        def emit(event):
            events.append(event)
            if event['kind']=='login_required':
                async def finish():
                    await asyncio.sleep(2.2)
                    control.login.complete(event['request_id'],[{'name':'sid','value':'authenticated','domain':'127.0.0.1','path':'/'}],skip)
                workers.append(asyncio.create_task(finish()))
        try:
            with patch('chickadee.scanner.prepare_models'), patch('chickadee.scanner.enrich_report',side_effect=lambda report,**kwargs:report.update(local_ai={})):
                outcome=await scan(ScanConfig(f'http://127.0.0.1:{server.server_port}/private',interactive_login=True,
                    timeout_sec=10,page_timeout_sec=3,settle_ms=0,ocr_enabled=False,capture_previews=False),emit=emit,control=control)
            self.assertGreaterEqual(outcome.report['paused_sec'],2)
            # Assert the accounting directly; a two-second total budget can
            # expire during a cold Chromium startup before any login is seen.
            self.assertAlmostEqual(outcome.result['meta']['elapsed_sec'] - outcome.report['paused_sec'],
                                   outcome.report['active_elapsed_sec'], delta=.15)
            if skip:
                self.assertNotEqual(outcome.report['status'],'completed')
                self.assertEqual(outcome.report['page_diagnostics'][0]['status'],'authentication_required')
                self.assertEqual(outcome.report['pages_scanned'],[])
            else:
                self.assertEqual(outcome.report['status'],'completed',outcome.report['errors'])
                self.assertTrue(outcome.report['pages_scanned'][0].endswith('/private'))
            self.assertNotIn('authenticated',json.dumps(events))
        finally:
            await asyncio.gather(*workers,return_exceptions=True)
            server.shutdown();server.server_close();thread.join()

    async def test_redirect_during_read_action_resumes_original_page(self):
        from chickadee.profiles import SiteProfile
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                if self.path == '/gate':
                    self.send_response(302)
                    self.send_header('Location', 'http://localhost:9/member/login.php')
                    self.end_headers(); return
                authenticated = 'sid=authenticated' in self.headers.get('Cookie', '')
                if self.path == '/favicon.ico':
                    import io
                    from PIL import Image
                    icon = io.BytesIO(); Image.new('RGBA', (16, 16), '#4488aa').save(icon, format='PNG')
                    self.send_response(200); self.send_header('Content-Type', 'image/png'); self.end_headers()
                    self.wfile.write(icon.getvalue()); return
                body = '<title>Parent portal</title><article>Collected content</article>'
                if not authenticated:
                    body += '<button id="more" onclick="location.href=\'/gate\'">More</button>'
                self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers()
                self.wfile.write(body.encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        control = ScanControl(); events = []
        def emit(event):
            events.append(event)
            if event['kind'] == 'login_required':
                control.login.complete(event['request_id'], [{'name':'sid','value':'authenticated','domain':'127.0.0.1','path':'/'}])
        try:
            with patch('chickadee.scanner.prepare_models'), patch('chickadee.scanner.enrich_report', side_effect=lambda report, **kw: report.update(local_ai={})), patch('chickadee.scanner.SiteProfile.load', return_value=SiteProfile(controls=('#more',), scroll_steps=0)):
                result = await scan(ScanConfig(f'http://127.0.0.1:{server.server_port}/private', interactive_login=True,
                    page_timeout_sec=10, settle_ms=100, ocr_enabled=False, capture_previews=False), emit=emit, control=control)
            self.assertEqual(result.report['status'], 'completed', result.report['errors'])
            prompts = [e for e in events if e['kind'] == 'login_required']
            self.assertEqual(len(prompts), 1)
            self.assertEqual(prompts[0]['title'], 'Parent portal')
            self.assertTrue(prompts[0]['favicon'].startswith('data:image/png;base64,'))
            self.assertEqual(prompts[0]['url'], 'http://localhost:9/member/login.php')
            self.assertTrue(prompts[0]['requested_url'].endswith('/private'))
            self.assertFalse(any(e['kind'] == 'request_blocked' for e in events))
            self.assertTrue(all(url.endswith('/private') for url in result.report['pages_scanned']))
        finally:
            server.shutdown(); server.server_close(); thread.join()
