import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest

from chickadee.async_runtime import event_loop_runner
from chickadee.scanner import ScanConfig, image_document_key, scan


class ImageCollectionTests(unittest.TestCase):
    def test_repeated_icons_do_not_hide_later_images_or_queue_image_downloads(self):
        image=Path('tests/fixtures/ocr/benign.png').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path == '/':
                    data=b'<a href="/image-20">Download</a><a href="/board/view.do?board_idx=1">Post</a>';mime='text/html'
                elif self.path.startswith('/image'):
                    data=image;mime='image/png'
                else:
                    body='<nav>'+('<img width="24" height="24" src="/image-icon">'*30)+'</nav><article>'
                    body+=''.join(f'<img width="300" height="100" src="/image-{i}?inline=1">' for i in range(21))
                    body+='</article><a href="/image-20">첨부파일</a>'
                    data=('<!doctype html><meta charset="utf-8">'+body).encode();mime='text/html; charset=utf-8'
                self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with event_loop_runner() as runner:
                outcome=runner.run(scan(ScanConfig(f'http://127.0.0.1:{server.server_port}/',max_pages=10,
                    settle_ms=0,interval_sec=0)))
            self.assertEqual(len(outcome.report['pages_scanned']),2)
            self.assertEqual(outcome.report['pages_remaining'],0)
            self.assertEqual(outcome.report['status'],'completed')
            self.assertEqual(outcome.report['ocr_summary']['skipped'],0)
            self.assertEqual(len(outcome.report['ocr_images'][0]['occurrences']),51)
            self.assertFalse(any('Download is starting' in x['message'] for x in outcome.report['errors']))
            self.assertFalse(any('이미지 수집 한도' in x['message'] for x in outcome.report['errors']))
        finally:server.shutdown();server.server_close();thread.join()

    def test_html_preview_query_is_not_confused_with_a_known_image(self):
        self.assertEqual(image_document_key('https://example.test/file?inline=1'),image_document_key('https://example.test/file?download=1'))
        self.assertNotEqual(image_document_key('https://example.test/file?format=html'),image_document_key('https://example.test/file?inline=1'))
