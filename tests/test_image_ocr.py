"""Real official PaddleOCR inference and bounded loopback collection; no AI API."""
import asyncio
import base64
from copy import deepcopy
import hashlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import AsyncMock, patch

from chickadee.image_ocr import OCRSession, fetch_image, inline_image
from chickadee.async_runtime import event_loop_runner
from chickadee.inspection import validate_ocr_images
from chickadee.scanner import ScanConfig, ScanOutcome, _State, _fetch_image_bounded, _inspect_images, origin, scan

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/ocr'


class ImageOCRTests(unittest.TestCase):
    def test_transparent_korean_banner_is_read_instead_of_black_on_black(self):
        from PIL import Image
        with Image.open(FIXTURES/'promotion.png') as original:
            image=original.convert('RGBA')
            image.putdata([(0,0,0,0) if min(pixel[:3])>240 else pixel for pixel in image.getdata()])
            buffer=io.BytesIO();image.save(buffer,format='PNG')
        async def scenario():
            session=OCRSession()
            try:
                value=await session.recognize(buffer.getvalue())
                self.assertEqual(value['status'],'completed',value)
                self.assertTrue(any('카지노' in line['text'] and line['confidence']>=.55 for line in value['lines']),value['lines'])
            finally:await session.close()
        asyncio.run(scenario())

    def test_repeated_logos_do_not_consume_unique_image_budget(self):
        async def scenario():
            state = _State(); state.ocr_max_images = 2
            sample = deepcopy(next(i for i in self.outcome.report['ocr_images'] if i['status'] == 'completed' and i.get('text')))
            sample['preview_data_url'] = 'data:image/png;base64,AA=='
            state.ocr = AsyncMock()
            state.ocr.recognize.return_value = sample
            inline = 'data:image/png;base64,' + base64.b64encode(self.ad).decode()
            images = [{'location': f'img#logo{i}', 'source_url': inline, 'source_type': 'img'} for i in range(5)]
            second = 'data:image/png;base64,' + base64.b64encode((FIXTURES/'benign.png').read_bytes()).decode()
            images += [{'location': 'img#new', 'source_url': second, 'source_type': 'img'}]
            await _inspect_images(None, images, '', self.url, state, lambda _: None, None)
            self.assertEqual(state.ocr.recognize.await_count, 2)
            self.assertEqual(len(state.ocr_cache), 2)
            self.assertEqual(len(state.ocr_images), 6)
            self.assertEqual(state.ocr_skipped, 0)
        with event_loop_runner() as runner:
            runner.run(scenario())

    @classmethod
    def setUpClass(cls):
        cls.external_requests = []
        class Sink(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.external_requests.append(self.path)
                self.send_response(200); self.end_headers()
            def log_message(self, *_args): pass
        cls.sink = ThreadingHTTPServer(('127.0.0.1', 0), Sink)
        sink_url = f'http://127.0.0.1:{cls.sink.server_port}/external.png'
        cls.ad = (FIXTURES / 'promotion.png').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/rate.png':
                    self.send_response(429); self.send_header('Retry-After', '60'); self.end_headers(); return
                if self.path == '/large.png':
                    self.send_response(200); self.send_header('Content-Type', 'image/png'); self.send_header('Content-Length', '2000001'); self.end_headers(); return
                if self.path == '/redirect.png':
                    self.send_response(302); self.send_header('Location', sink_url); self.end_headers(); return
                if self.path.endswith('.png'):
                    name = 'benign.png' if self.path == '/benign.png' else 'promotion.png'
                    data = (FIXTURES / name).read_bytes()
                    self.send_response(200); self.send_header('Content-Type', 'image/png'); self.end_headers(); self.wfile.write(data); return
                if self.path == '/frame':
                    text = '<img src="/promotion.png" id="framed">'
                else:
                    inline = 'data:image/png;base64,' + base64.b64encode(cls.ad).decode()
                    text = f'''<article><img id="ad" src="/promotion.png"><img id="benign" src="/benign.png">
                        <div id="background" style="width:900px;height:240px;background-image:url(/promotion.png)"></div>
                        <img id="inline" src="{inline}"><img id="external" src="{sink_url}">
                        <img id="redirect" src="/redirect.png"><iframe src="/frame"></iframe></article>'''
                data = ('<!doctype html><meta charset="utf-8">' + text).encode()
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(data)
            def log_message(self, *_args): pass
        cls.site = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        for server in (cls.site, cls.sink):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.site.server_port}/'
        cls.outcome = asyncio.run(scan(ScanConfig(cls.url, max_pages=1, timeout_sec=90,
            page_timeout_sec=60, settle_ms=0, interval_sec=0, follow_links=False)))

    @classmethod
    def tearDownClass(cls):
        for server in (cls.site, cls.sink):
            server.shutdown(); server.server_close()

    def test_real_korean_image_only_detection_and_boxes(self):
        report = self.outcome.report
        images = [image for image in report['ocr_images'] if image['status'] == 'completed']
        self.assertGreaterEqual(len(images), 5, report['errors'])
        ads = [c for c in report['ad_candidates'] if c.get('source_kind') == 'image_ocr']
        self.assertGreaterEqual(len(ads), 4)
        self.assertTrue(any(' >>> ' in c['location'] for c in ads))
        self.assertTrue(any(i['source_type'] == 'background' for i in images))
        self.assertTrue(any(i['source_url'] == '(inline)' for i in images))
        benign_ids = {i['id'] for i in images if i['source_url'].endswith('/benign.png')}
        self.assertTrue(benign_ids)
        self.assertFalse(any(c['image_id'] in benign_ids for c in ads))
        self.assertEqual(self.outcome.result['findings'], [])
        ad_image = next(i for i in images if i['source_url'].endswith('/promotion.png'))
        self.assertIn('카지노', ad_image['text'])
        self.assertTrue(all(line['confidence'] > .55 and len(line['box']) == 4 for line in ad_image['lines']))
        self.assertTrue(any(p.get('source_kind') == 'image_ocr' for p in report['evidence_packets']))
        validate_ocr_images(report['ocr_images'])

    def test_external_images_and_redirects_never_reach_sink(self):
        self.assertEqual(self.external_requests, [])
        failed = [i for i in self.outcome.report['ocr_images'] if i['status'] == 'failed']
        self.assertTrue(any(i['source_url'].endswith('/external.png') for i in failed))
        with self.assertRaises(Exception): fetch_image(self.url + 'redirect.png')
        self.assertEqual(self.external_requests, [])

    def test_save_reload_integrity_and_untrusted_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.outcome.save(Path(folder))
            loaded = ScanOutcome.load(path)
            image = next(i for i in loaded.report['ocr_images'] if i['status'] == 'completed')
            self.assertEqual(hashlib.sha256((Path(folder) / image['relative_path']).read_bytes()).hexdigest(), image['image_sha256'])
            self.assertIn('카지노', image['text'])
        for replacement in ([[float('nan'), 0]] * 4, [[-1, 0]] * 4, 'invalid'):
            altered = deepcopy(self.outcome.report['ocr_images'])
            next(i for i in altered if i['status'] == 'completed')['lines'][0]['box'] = replacement
            with self.assertRaises(ValueError): validate_ocr_images(altered)

    def test_cancelled_reply_cannot_become_next_images_evidence(self):
        async def scenario():
            session = OCRSession()
            try:
                await session.recognize((FIXTURES/'benign.png').read_bytes())
                pending = asyncio.create_task(session.recognize(self.ad))
                await asyncio.sleep(.02)
                pending.cancel()
                with self.assertRaises(asyncio.CancelledError): await pending
                self.assertIsNone(session.process)
                result = await session.recognize((FIXTURES/'benign.png').read_bytes())
                text = '\n'.join(line['text'] for line in result['lines'])
                self.assertEqual(result['status'], 'completed')
                self.assertNotIn('카지노', text)
                self.assertIn('도서관', text)
            finally:
                await session.close()
        asyncio.run(scenario())

    def test_worker_rejects_nonimages_recovers_and_closes(self):
        async def check():
            worker = OCRSession()
            try:
                bad = await worker.recognize(b'<svg>bad</svg>')
                self.assertEqual(bad['status'], 'failed')
                good = await worker.recognize(self.ad)
                self.assertEqual(good['status'], 'completed', good)
                process = worker.process
            finally:
                await worker.close()
            self.assertIsNotNone(process.returncode)
        asyncio.run(check())
        with self.assertRaises(ValueError): inline_image('data:image/svg+xml;base64,PHN2Zz4=')

    def test_rate_limit_stops_further_images_and_rejects_large_files(self):
        async def check():
            state = _State(image_origins={origin(self.url)})
            with self.assertRaises(Exception): await _fetch_image_bounded(self.url + 'rate.png', state)
            self.assertEqual(state.stopped_origins[origin(self.url)]['retry_after'], '60')
            with self.assertRaisesRegex(ValueError, '429'): await _fetch_image_bounded(self.url + 'promotion.png', state)
            self.assertEqual(state.image_requests, 1)
        asyncio.run(check())
        with self.assertRaisesRegex(ValueError, '크기'): fetch_image(self.url + 'large.png')
