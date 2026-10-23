import asyncio
import base64
import io
import unittest
from unittest.mock import AsyncMock, patch

from chickadee.authentication import active_timeout
from chickadee.image_ocr import OCRSession
from chickadee.scanner import _State, _inspect_images, _ocr_summary, ScanConfig, origin


class OCRBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_unreadable_warning_identifies_the_image(self):
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (32, 32), 'white').save(buffer, format='PNG')
        source = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        state = _State()
        state.ocr = AsyncMock()
        state.ocr.recognize.return_value = {
            'status': 'completed', 'lines': [], 'image_format': 'PNG',
            'width': 32, 'height': 32, 'preview_data_url': '',
        }
        events = []
        await _inspect_images(None, [{'source_url': source, 'location': 'span.service-icon',
                                     'source_type': 'img'}], '', 'http://localhost/', state, events.append, None)
        warning = next(e for e in events if e['kind'] == 'warning')
        self.assertEqual(warning['image_id'], state.ocr_images[0]['id'])
        self.assertEqual(warning['location'], 'span.service-icon')
        self.assertIn('span.service-icon', warning['message'])
        self.assertEqual(warning['source_url'], '(inline)')

    async def test_local_ocr_has_its_own_budget_without_disabling_page_timeout(self):
        session = OCRSession()
        async def read(_):
            await asyncio.sleep(.16)
            return {'status': 'completed'}
        session._recognize = AsyncMock(side_effect=read)
        result = await active_timeout(session.recognize(b'image'), .07, None,
                                      excluded_seconds=lambda: session.elapsed_seconds)
        self.assertEqual(result['status'], 'completed')
        self.assertGreaterEqual(session.elapsed_seconds, .15)
        elapsed = session.elapsed_seconds
        await asyncio.sleep(.02)
        self.assertAlmostEqual(session.elapsed_seconds, elapsed, places=4)
        with self.assertRaises(asyncio.TimeoutError):
            await active_timeout(asyncio.sleep(.3), .05, None,
                                 excluded_seconds=lambda: session.elapsed_seconds)

    async def test_cancelled_ocr_time_is_accounted_and_cancellation_propagates(self):
        session = OCRSession()
        session._recognize = AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):
            await session.recognize(b'image')
        self.assertIsNone(session._since)

    async def test_collection_limit_is_skipped_once_instead_of_ocr_failure(self):
        state = _State(image_origins={origin('http://127.0.0.1:8765')}, image_requests=2000)
        images = [{'location': 'img#one', 'source_url': 'http://127.0.0.1:8765/a.png', 'source_type': 'img'},
                  {'location': 'img#two', 'source_url': 'http://127.0.0.1:8765/b.png', 'source_type': 'img'}]
        events = []
        with patch('chickadee.scanner.fetch_image') as fetch:
            await _inspect_images(None, images, '', 'http://127.0.0.1:8765/', state, events.append, None)
            fetch.assert_not_called()
        summary = _ocr_summary(state, ScanConfig('http://127.0.0.1:8765/'))
        self.assertEqual((summary['failed'], summary['skipped'], summary['status']), (0, 2, 'partial'))
        self.assertEqual(len([e for e in events if e['kind'] == 'warning']), 1)


if __name__ == '__main__':
    unittest.main()
