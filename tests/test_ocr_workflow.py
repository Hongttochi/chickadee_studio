import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from chickadee.workflow import compile_workflow
from chickadee.scanner import _inspect_frame


class OCRWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_ocr_does_not_invoke_reader(self):
        frame = SimpleNamespace(evaluate=AsyncMock(return_value={
            'elements': [], 'images': [{'source_url': 'https://example.org/image.png'}],
            'links': [], 'truncated': False, 'links_truncated': False,
        }), child_frames=[])
        state = SimpleNamespace(trace=SimpleNamespace(capture=Mock()), page_diagnostics=[])
        with patch('chickadee.scanner._inspect_images', new_callable=AsyncMock) as reader:
            await _inspect_frame(frame, '', {}, 'https://example.org', '', state, Mock(),
                                 detect_techniques=False, ocr_enabled=False)
            reader.assert_not_awaited()

    async def test_workflow_ocr_switch_independent_of_old_connections(self):
        pairs = [('target', 'browser'), ('browser', 'collector'), ('collector', 'candidates'),
                 ('candidates', 'report'), ('collector', 'ocr'), ('ocr', 'candidates')]
        flow = {'nodes': [{'id': 'ocr'}], 'edges': [{'source': a, 'target': b} for a, b in pairs]}
        self.assertTrue(compile_workflow(flow)['ocr_enabled'])
        flow['ocr_enabled'] = False
        self.assertFalse(compile_workflow(flow)['ocr_enabled'])
        flow['ocr_enabled'] = True
        flow['edges'].pop()
        self.assertTrue(compile_workflow(flow)['ocr_enabled'])

    async def test_ocr_enters_both_classifiers_and_keeps_evidence(self):
        from chickadee.scanner import _State
        state = _State()
        state.trace.capture = Mock()
        frame = SimpleNamespace(evaluate=AsyncMock(return_value={
            'elements': [], 'images': [{}], 'links': [], 'truncated': False, 'links_truncated': False,
        }), child_frames=[], page=object())
        image = {'node_id': 'ocr:1', 'parent_id': None, 'location': 'img.ad',
                 'text': '카지노 가입 보너스', 'direct_text': '카지노 가입 보너스',
                 'transparent': True, 'offscreen': False, 'source_kind': 'image_ocr', 'image_id': 'im_1'}
        with patch('chickadee.scanner._inspect_images', new_callable=AsyncMock, return_value=[image]), \
             patch('chickadee.scanner._evidence_screenshot', new_callable=AsyncMock, return_value=None):
            await _inspect_frame(frame, '', {}, 'https://example.org', '', state, Mock())
        self.assertEqual(state.findings[0]['technique'], 'TRANSPARENT')
        self.assertEqual(state.evidence_details[state.findings[0]['id']]['image_id'], 'im_1')

    async def test_exact_cross_source_merge_preserves_both_locations(self):
        from chickadee.scanner import _State
        state = _State()
        state.trace.capture = Mock()
        text = '카지노 가입 보너스'
        dom = {'node_id': 1, 'parent_id': None, 'location': 'p.ad', 'text': text, 'direct_text': text,
               'transparent': False, 'offscreen': False}
        image = {**dom, 'node_id': 'ocr:1', 'location': 'img.ad', 'source_kind': 'image_ocr', 'image_id': 'im_1'}
        frame = SimpleNamespace(evaluate=AsyncMock(return_value={'elements': [dom], 'images': [{}],
            'links': [], 'truncated': False, 'links_truncated': False}), child_frames=[], page=object())
        with patch('chickadee.scanner._inspect_images', new_callable=AsyncMock, return_value=[image]), \
             patch('chickadee.scanner._evidence_screenshot', new_callable=AsyncMock, return_value=None):
            await _inspect_frame(frame, '', {}, 'https://example.org', '', state, Mock())
        self.assertEqual(len(state.ad_candidates), 1)
        self.assertEqual(state.merged_observations, 1)
        self.assertEqual({s['location'] for s in state.ad_candidates[0]['evidence_sources']}, {'p.ad', 'img.ad'})

    async def test_different_text_or_page_is_not_merged_and_failure_is_partial(self):
        from chickadee.scanner import _cross_source_match, _ocr_summary, _State, ScanConfig
        record = {'id': 'c_1', 'url': 'http://localhost/', 'category': 'GAMBLING', 'evidence_text': 'casino 1',
                  'evidence_sources': [{'source_kind': 'dom_text'}]}
        for changes in ({'url': 'http://localhost/other'}, {'evidence_text': 'casino 2'}):
            self.assertIsNone(_cross_source_match([record], {**record, **changes, 'source_kind': 'image_ocr'}))
        state = _State(ocr_images=[{'status': 'failed'}, {'status': 'completed', 'recognition_status': 'unreadable'}])
        summary = _ocr_summary(state, ScanConfig('http://localhost/'))
        self.assertEqual(summary['status'], 'partial')
        self.assertEqual((summary['failed'], summary['unreadable']), (1, 1))

    async def test_fixed_pipeline_ignores_saved_disconnections(self):
        pairs = [('target', 'browser'), ('browser', 'collector'), ('collector', 'techniques'),
                 ('collector', 'candidates'), ('collector', 'ocr'), ('ocr', 'techniques'),
                 ('ocr', 'candidates'), ('techniques', 'dedup'), ('candidates', 'dedup'), ('dedup', 'report')]
        flow = {'version': 2, 'nodes': [{'id': 'ocr'}, {'id': 'dedup'}],
                'edges': [{'source': a, 'target': b} for a, b in pairs]}
        flags = compile_workflow(flow)
        self.assertTrue(flags['ocr_techniques'])
        self.assertTrue(flags['ocr_candidates'])
        flow['edges'] = [e for e in flow['edges'] if (e['source'], e['target']) != ('ocr', 'candidates')]
        flags = compile_workflow(flow)
        self.assertTrue(flags['ocr_enabled'])
        self.assertTrue(flags['ocr_candidates'])
        flow['edges'] = [e for e in flow['edges'] if e['source'] != 'dedup']
        self.assertTrue(compile_workflow(flow)['detect_techniques'])
