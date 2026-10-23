"""Real model parity, saved evidence validation, and free/paid signal separation."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chickadee import local_ai
from chickadee.agent import EvidenceAgent
from chickadee.inspection import validate_local_ai
from tests.test_inspection_agent import packet, grok_stub

ROOT = Path(__file__).resolve().parents[1]


class LocalAITests(unittest.TestCase):
    def test_test_site_disclosure_is_not_repeated_as_an_ai_advertisement(self):
        item=packet();item['text']='본 사이트는 행정안전부 주최 공공 웹사이트 불법광고 탐지 도구 개발 공모전 참가를 위해 제작한 테스트 사이트입니다.'
        report={'evidence_packets':[item],'ad_candidates':[]}
        signal={**local_ai.text_analysis(item['text']),'review_priority':'high'}
        with patch.object(local_ai,'text_analysis',return_value=signal):local_ai.enrich_report(report)
        self.assertEqual(report['ad_candidates'],[])
        self.assertIn('text',item['local_ai'])
    def test_candidate_ids_remain_unique_after_summary_dedup_leaves_gaps(self):
        item = packet()
        report = {'evidence_packets': [item], 'ad_candidates': [
            {'id': 'c_00001', 'url': 'https://example.invalid/other', 'location': 'a'},
            {'id': 'c_00003', 'url': 'https://example.invalid/other', 'location': 'b'}]}
        signal = {**local_ai.text_analysis(item['text']), 'review_priority': 'high'}
        with patch.object(local_ai, 'text_analysis', return_value=signal): local_ai.enrich_report(report)
        ids = [c['id'] for c in report['ad_candidates']]
        self.assertEqual(ids, ['c_00001', 'c_00003', 'c_00004'])
        self.assertEqual(len(ids), len(set(ids)))
    def test_exported_trees_match_original_sklearn_predictions(self):
        expected = json.loads((ROOT / 'tests/fixtures/local-ai-predictions.json').read_text(encoding='utf-8'))
        for item in expected['texts']:
            self.assertAlmostEqual(local_ai.text_analysis(item['text'])['score'], item['score'], places=6)
        for item in expected['images']:
            result = local_ai.visual_analysis((ROOT / 'tests/fixtures/ocr' / item['file']).read_bytes())
            self.assertAlmostEqual(result['score'], item['score'], places=6)
            self.assertNotIn('safe', result.values())

    def test_unknown_text_is_unknown_not_a_safety_score(self):
        result = local_ai.text_analysis('🦜🧪🦉')
        self.assertIsNone(result['score'])
        self.assertEqual(result['label'], 'no_features')
        self.assertEqual(local_ai.normalize('ＣＡ\u200bSINO  가입'), 'casino 가입')

    def test_corrupt_model_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); (folder / 'ai-models').mkdir()
            (folder / 'ai-models.json').write_bytes((local_ai.DATA / 'ai-models.json').read_bytes())
            (folder / 'ai-models/text.json').write_text('{}')
            local_ai.model.cache_clear()
            try:
                with patch.object(local_ai, 'DATA', folder), self.assertRaisesRegex(ValueError, '무결성'):
                    local_ai.model('text')
            finally: local_ai.model.cache_clear()

    def test_report_priority_saved_without_overwriting_observed_findings(self):
        item = packet()
        report = {'evidence_packets': [item], 'ad_candidates': [], 'evidence_details': {}, 'screenshots': {}}
        signal = {**local_ai.text_analysis(item['text']), 'review_priority': 'high', 'label': 'ad_context'}
        original_hash = item['content_sha256']
        with patch.object(local_ai, 'text_analysis', return_value=signal): local_ai.enrich_report(report)
        self.assertEqual(report['ad_candidates'][0]['category'], 'AI_CONTEXT')
        self.assertTrue(report['ad_candidates'][0]['review_required'])
        self.assertEqual(item['content_sha256'], original_hash)
        self.assertEqual(report['local_ai']['paid_requests'], 0)
        self.assertNotIn('findings', report)
        self.assertNotIn('local_ai', signal)
        local_ai.enrich_report(report, candidates=False)
        self.assertEqual(len(report['ad_candidates']), 1)

    def test_bad_saved_scores_rejected(self):
        signal = local_ai.text_analysis('casino join bonus')
        validate_local_ai({'text': signal})
        for score in (float('nan'), float('inf'), -1, 1.01, True, '100'):
            with self.subTest(score=score), self.assertRaises(ValueError):
                validate_local_ai({'text': {**signal, 'score': score}})

    def test_groq_receives_local_model_tool_and_keeps_budget(self):
        item = packet(); item['local_ai'] = {'text': local_ai.text_analysis(item['text'])}
        calls = []
        def transport(payload, key, timeout):
            calls.append(deepcopy(payload))
            response = grok_stub(payload, key, timeout)
            if payload.get('tools'):
                response['choices'][0]['message']['tool_calls'].append({'id': 'ml', 'type': 'function', 'function': {
                    'name': 'local_ai_read', 'arguments': json.dumps({'evidence_id': item['id']})}})
            return response
        result = EvidenceAgent({'api_key': 'test_key_not_real', 'call_limit': 2}, transport=transport).investigate(item)
        self.assertEqual(result['provider'], 'groq')
        self.assertEqual(result['ledger']['calls'], 2)
        self.assertIn('local_ai_read', [r['tool'] for r in result['reads']])
        tool = json.loads(next(m['content'] for m in calls[-1]['messages'] if m.get('tool_call_id') == 'ml'))
        self.assertEqual(tool['local_ai']['text']['score_kind'], 'uncalibrated_model_score')
        self.assertNotIn('matched_features', tool['local_ai']['text'])
        evidence = json.loads(next(m['content'] for m in calls[-1]['messages'] if m.get('tool_call_id') == 'read1'))
        self.assertEqual(evidence['local_ai']['text']['score'], item['local_ai']['text']['score'])
