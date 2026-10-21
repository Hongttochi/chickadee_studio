import asyncio
import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import AsyncMock, patch

from chickadee.bridge import DesktopBridge
from chickadee.content_analysis import analyze_content, inputs
from chickadee.image_ocr import recognized_text
from chickadee.inspection import InspectionTrace, validate_inspection
from chickadee.runtime import environment
from chickadee.tools import resolve_tool
from tests.test_desktop import workflow

PIXELS = (Path(__file__).parent/'fixtures/ocr/promotion.png').read_bytes()
IMAGE = 'data:image/png;base64,' + base64.b64encode(PIXELS).decode('ascii')


class ContentAnalysisTests(unittest.TestCase):
    def test_real_direct_image_and_text_models_ocr_and_source_separation(self):
        with tempfile.TemporaryDirectory() as folder, patch('chickadee.agent.groq_request') as paid:
            messages = []; bridge = DesktopBridge(folder, messages.append)
            bridge.command('runtime-configure', {'mode': 'standard'})
            job = bridge.command('tool-call', {'name': 'content.analyze', 'arguments': {'text': '도서관 이용 안내', 'image_data_url': IMAGE}})
            self.assertEqual(bridge.command('state', {})['status'], 'idle')
            bridge.content_worker.join(45); self.assertFalse(bridge.content_worker.is_alive())
            value = bridge.command('content-analyze', {'analysis_id': job['analysis_id']})
            self.assertEqual(value['status'], 'completed', value)
            result = value['result']; typed, ocr = result['sources']
            self.assertEqual(typed['source_kind'], 'provided_text')
            self.assertEqual(typed['ad_candidates'], [])
            self.assertIn('카지노', ocr['text'])
            self.assertTrue(ocr['ad_candidates']); self.assertFalse(ocr['original_unicode_observed'])
            self.assertEqual(ocr['ocr']['image_sha256'], result['image']['image_sha256'])
            self.assertEqual(ocr['ocr']['engine'], 'PaddleOCR')
            self.assertTrue(typed['original_unicode_observed'])
            self.assertEqual(result['image']['local_ai']['visual']['status'], 'completed')
            self.assertEqual(ocr['local_ai']['text']['status'], 'completed')
            self.assertEqual(result['paid_requests'], 0); paid.assert_not_called()
            self.assertIsNone(bridge.outcome); self.assertEqual(bridge.history, [])
            self.assertNotIn('도서관 이용 안내', json.dumps(messages, ensure_ascii=False))
            self.assertNotIn(IMAGE, json.dumps(messages))
            value['result']['sources'].clear()
            self.assertEqual(len(bridge.command('content-analyze', {'analysis_id': job['analysis_id']})['result']['sources']), 2)
            self.assertFalse(list(Path(folder).rglob('*.png')))

    def test_direct_text_keeps_observed_unicode_and_does_not_start_ocr(self):
        with patch('chickadee.content_analysis.OCRSession.recognize', new_callable=AsyncMock) as ocr:
            result = asyncio.run(analyze_content('caѕino 가입 보너스', None, environment('standard'), Event()))
            ocr.assert_not_called()
        self.assertTrue(result['sources'][0]['unicode_analysis']['matches'])
        self.assertEqual(result['sources'][0]['text'], 'caѕino 가입 보너스')

    def test_invalid_inputs_remote_sources_and_tool_shapes_are_rejected(self):
        for value in ({}, {'text': ' '}, {'text': 'x'*4001}, {'image_data_url': 'https://example.invalid/x.png'},
                      {'image_data_url': 'file:///C:/private.png'}, {'image_path': 'private.png'},
                      {'image_data_url': 'x'*900001}, {'text': 3}, {'text': 'x', 'api_key': 'ignored'}):
            with self.subTest(value=str(value)[:50]), self.assertRaises(ValueError): inputs(value)
        for value in ({'text': 'x', 'analysis_id': 'a'*32}, {'cancel': True}, {'image_path': 'private.png'}):
            with self.assertRaises(ValueError): resolve_tool('content.analyze', value)

    def test_economy_explicitly_skips_ocr_but_keeps_image_model(self):
        with patch('chickadee.content_analysis.OCRSession.recognize', new_callable=AsyncMock) as ocr:
            result = asyncio.run(analyze_content('', PIXELS, environment('economy'), Event()))
            ocr.assert_not_called()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['image']['ocr'], {'status': 'skipped', 'reason': 'economy'})
        self.assertEqual(result['image']['local_ai']['visual']['status'], 'completed')

    def test_ocr_failure_retains_typed_text_and_local_model(self):
        with patch('chickadee.content_analysis.OCRSession.recognize', new_callable=AsyncMock, side_effect=ValueError('worker down')):
            result = asyncio.run(analyze_content('도서관 이용 안내', PIXELS, environment('standard'), Event()))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['sources'][0]['text'], '도서관 이용 안내')
        self.assertEqual(result['image']['ocr']['status'], 'failed')

    def test_unreadable_image_is_partial_with_no_advertising_conclusion(self):
        value = {'status': 'completed', 'engine': 'PaddleOCR', 'model': 'fixture', 'lines': []}
        with patch('chickadee.content_analysis.OCRSession.recognize', new_callable=AsyncMock, return_value=value):
            result = asyncio.run(analyze_content('', PIXELS, environment('standard'), Event()))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['image']['ocr']['recognition_status'], 'unreadable')
        self.assertEqual(result['candidate_count'], 0)
        self.assertTrue(result['errors'])

    def test_background_request_is_responsive_and_cancellable(self):
        async def slow(text, pixels, runtime, stop, progress):
            while not stop.is_set(): await asyncio.sleep(.01)
            raise asyncio.CancelledError()
        with tempfile.TemporaryDirectory() as folder, patch('chickadee.bridge.analyze_content', side_effect=slow):
            bridge = DesktopBridge(folder, lambda _: None)
            job = bridge.command('content-analyze', {'text': 'test'})
            self.assertFalse(bridge.command('state', {})['running'])
            with self.assertRaises(ValueError): bridge.command('content-analyze', {'text': 'second'})
            with self.assertRaises(ValueError): bridge.command('start', {'url': 'http://127.0.0.1/', 'workflow': workflow()})
            with self.assertRaises(ValueError): bridge.command('runtime-test', {})
            with self.assertRaises(ValueError): bridge.command('content-analyze', {'analysis_id': 'wrong'})
            bridge.command('content-analyze', {'analysis_id': job['analysis_id'], 'cancel': True})
            bridge.content_worker.join(5)
            self.assertEqual(bridge.command('content-analyze', {'analysis_id': job['analysis_id']})['status'], 'cancelled')

    def test_ocr_confidence_and_truncation_survive_evidence_capture(self):
        source = {'lines': [{'text': '가'*1000, 'confidence': .9} for _ in range(5)] + [{'text': '낮은 신뢰도', 'confidence': .54}]}
        observation = recognized_text(source)
        self.assertEqual(len(observation['text']), 4000)
        self.assertTrue(observation['text_truncated']); self.assertEqual(observation['rejected_lines'], 1)
        trace = InspectionTrace()
        trace.capture([{'location': 'img#one', 'text': observation['text'], 'direct_text': observation['text'],
                        'source_kind': 'image_ocr', 'image_id': 'im_1', 'ocr': {'engine': 'PaddleOCR', 'model': 'fixture',
                        'image_sha256': 'a'*64, **{k:v for k,v in observation.items() if k != 'text'}}}], 'https://example.invalid/', '', lambda _: None)
        report = {'evidence_packets': list(trace.packets.values()), 'exploration': trace.export()}
        self.assertTrue(report['evidence_packets'][0]['truncated']); validate_inspection(report)
        bad = deepcopy(report); bad['evidence_packets'][0]['ocr']['mean_confidence'] = float('nan')
        with self.assertRaises(ValueError): validate_inspection(bad)
