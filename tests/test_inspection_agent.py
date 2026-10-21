"""Observed state/diff integration and bounded Grok protocol tests, offline."""
import asyncio
import os
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import patch

from chickadee.agent import EvidenceAgent, ENDPOINT, groq_request
from chickadee.bridge import DesktopBridge
from chickadee.detection import analyze, techniques
from chickadee.inspection import InspectionTrace, validate_inspection
from chickadee.scanner import ScanConfig, scan
from tests.test_desktop import workflow


def element(text='카지노 가입 보너스', **extra):
    return {'location': 'article#post', 'content_scope': 'article#post', 'text': text,
            'direct_text': text, 'computed_style': {'effective_opacity': 1},
            'transparent': False, 'offscreen': False, **extra}


def packet():
    trace = InspectionTrace()
    trace.capture([element()], 'https://example.invalid/', '', lambda _: None)
    return next(iter(trace.packets.values()))


def grok_stub(payload, _key, _timeout):
    if payload.get('tools'):
        evidence_id = payload['tools'][0]['function']['parameters']['properties']['evidence_id']['enum'][0]
        message = {'role': 'assistant', 'tool_calls': [
            {'id': 'read1', 'type': 'function', 'function': {'name': 'evidence_read', 'arguments': json.dumps({'evidence_id': evidence_id})}},
            {'id': 'read2', 'type': 'function', 'function': {'name': 'style_read', 'arguments': json.dumps({'evidence_id': evidence_id})}},
        ]}
        reason = 'tool_calls'
    else:
        value = json.loads(next(m['content'] for m in payload['messages'] if m['role'] == 'tool'))
        message = {'role': 'assistant', 'content': json.dumps({'assessment': 'ad_suspected',
            'evidence_ids': [value['evidence_id']], 'summary': '가입 유도 문맥입니다.',
            'missing_evidence': [], 'recommended_next_action': 'human_review'})}
        reason = 'stop'
    return {'choices': [{'message': message, 'finish_reason': reason}], 'usage': {'total_tokens': 250}}


class InspectionTests(unittest.TestCase):
    def test_unicode_source_spans_and_normal_controls(self):
        for text in ('caꜱino join now', 'cɑsino join now', 'caѕinο join now'):
            result = analyze(text)
            self.assertIn('HOMOGLYPH', techniques(text))
            self.assertEqual(result['matches'][0]['source_span'], [0, 6])
            self.assertEqual(text[slice(*result['matches'][0]['source_span'])], text[:6])
        zero_width = analyze('ca\u200bsino join now')
        self.assertEqual(zero_width['matches'][0]['source_span'], [0, 7])
        self.assertIn('FORMAT_CHARACTER_INSERTION', [p['pattern'] for p in zero_width['additional_patterns']])
        for text in ('timeslot free', 'cɑsino 실무개론', 'Greek alphabet ɑ beta', 'caѕinο 예방 안내'):
            self.assertFalse(analyze(text)['is_advertisement'])

    def test_reverted_snapshots_scroll_and_unknown_are_preserved(self):
        trace = InspectionTrace()
        emit = lambda _: None
        for opacity in (1, 0, 1):
            trace.capture([element(computed_style={'effective_opacity': opacity})], 'https://example.invalid/', '', emit)
        self.assertEqual(len(trace.packets), 2)
        self.assertEqual(list(trace.packets.values())[-1]['computed_style']['effective_opacity'], 1)
        trace.capture([element(computed_style=None)], 'https://example.invalid/unknown', '', emit)
        self.assertIsNone(list(trace.packets.values())[-1]['transparent'])
        a, b = InspectionTrace(), InspectionTrace()
        a.capture([element(computed_style={'rect': {'y': 100}, 'scroll': {'y': 0}})], 'https://example.invalid/', '', emit)
        b.capture([element(computed_style={'rect': {'y': -100}, 'scroll': {'y': 200}})], 'https://example.invalid/', '', emit)
        self.assertEqual(next(iter(a.packets.values()))['content_sha256'], next(iter(b.packets.values()))['content_sha256'])

    def test_packet_limits_and_corrupt_report_rejection(self):
        trace = InspectionTrace(); trace.MAX_PACKETS = 1
        trace.capture([element()], 'https://example.invalid/', '', lambda _: None)
        trace.capture([element('새로운 원문')], 'https://example.invalid/', '', lambda _: None)
        self.assertTrue(trace.truncated)
        self.assertEqual(len(trace.packets), 1)
        for report in ({'evidence_packets': 'invalid'}, {'evidence_packets': [packet(), packet()]},
                       {'exploration': {'nodes': [{'id': 'n', 'kind': 'state', 'url': '', 'label': '', 'status': 'observed', 'packet_ids': [['invalid']]}], 'edges': []}}):
            with self.subTest(report=report), self.assertRaises(ValueError): validate_inspection(report)

    def test_frame_hiding_is_observed_in_its_graph_branch(self):
        trace = InspectionTrace()
        trace.snapshot('https://example.invalid/', 'state1', '초기 수집', lambda _: None)
        trace.capture([element()], 'https://example.invalid/', 'iframe#widget >>> ', lambda _: None, {'transparent': True})
        value = next(iter(trace.packets.values()))
        self.assertTrue(value['transparent'])
        self.assertTrue(any(node['kind'] == 'frame' for node in trace.export()['nodes']))
        validate_inspection({'evidence_packets': list(trace.packets.values()), 'exploration': trace.export()})

    def test_real_browser_graph_and_bridge_reload(self):
        revision = [0]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                content = ('<a href="/post">게시글</a>' if self.path == '/' else
                           f'<article id="post" style="opacity:{1 if revision[0] == 0 else 0}"><p>카지노 가입 보너스 {revision[0]}</p><a href="https://example.invalid/{revision[0]}">주소</a></article>')
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(content.encode('utf-8'))
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/'
            with tempfile.TemporaryDirectory() as folder:
                bridge = DesktopBridge(folder, lambda _: None)
                options = {'url': url, 'workflow': workflow(), 'max_pages': 2, 'settle_ms': 0, 'interval_sec': 0, 'preview': False}
                bridge.command('start', options); bridge.worker.join(30)
                self.assertEqual(bridge.outcome.report['status'], 'completed')
                revision[0] = 1
                bridge.command('start', options); bridge.worker.join(30)
                self.assertEqual(bridge.outcome.report['status'], 'completed')
                insight = bridge.command('inspection', {'run_id': bridge.run_id})
                self.assertTrue(insight['graph']['edges'])
                self.assertTrue(any(n['kind'] == 'state' for n in insight['graph']['nodes']))
                path = Path(bridge.output_path); original = path.read_bytes()
                with patch('chickadee.agent.groq_request', side_effect=grok_stub):
                    bridge.command('agent-configure', {'api_key': 'test_key_not_real'})
                    bridge.command('agent-run', {'run_id': bridge.run_id, 'evidence_id': next(p['id'] for p in insight['packets'] if '카지노' in p['text'])})
                    bridge.agent_worker.join(5)
                self.assertEqual(len(bridge.agent_data['assessments']), 1)
                self.assertEqual(path.read_bytes(), original)
                self.assertNotIn('test_key_not_real', path.with_name('agent.json').read_text(encoding='utf-8'))
                bridge.command('load', {'path': str(path)})
                loaded = bridge.command('inspection', {'run_id': bridge.run_id})
                self.assertNotIn('comparison', loaded)
                self.assertFalse(path.with_name('comparison.json').exists())
                self.assertEqual(loaded['agent']['ledger']['calls'], 2)
                self.assertTrue(loaded['agent']['assessments'])
        finally:
            server.shutdown(); server.server_close(); thread.join(3)


class WholeReportTests(unittest.TestCase):
    def test_all_packets_and_partial_failure(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as folder:
                bridge = DesktopBridge(folder, lambda _: None)
                bridge.agent_data['report'] = {'total': 3, 'completed': 0, 'status': 'running', 'assessments': []}
                values = [{'id': str(i)} for i in range(3)]
                answers = [{'summary': 'first'}, None] if fail else [{'summary': str(i)} for i in range(3)]
                with patch.object(bridge, '_run_agent', side_effect=answers) as run, patch.object(bridge, '_save_agent'):
                    bridge._run_agent_report({}, values)
                report = bridge.agent_data['report']
                self.assertEqual(report['completed'], 1 if fail else 3)
                self.assertEqual(report['status'], 'partial' if fail else 'completed')
                self.assertEqual(run.call_count, 2 if fail else 3)
                self.assertEqual(len(report['assessments']), report['completed'])

    def test_cancel_does_not_review_remaining_packets(self):
        with tempfile.TemporaryDirectory() as folder:
            bridge = DesktopBridge(folder, lambda _: None)
            bridge.agent_data['report'] = {'total': 2, 'completed': 0, 'status': 'running', 'assessments': []}
            bridge.agent_stop.set()
            with patch.object(bridge, '_run_agent') as run, patch.object(bridge, '_save_agent'):
                bridge._run_agent_report({}, [{'id': 'a'}, {'id': 'b'}])
            run.assert_not_called()
            self.assertEqual(bridge.agent_data['report']['status'], 'stopped')


class AgentTests(unittest.TestCase):
    def config(self, **extra):
        return {'api_key': 'test_key_not_real', **extra}

    def test_tools_final_schema_redaction_and_immutable_evidence(self):
        value = packet(); value['text'] += ' https://example.invalid/?token=secret x@example.invalid 010-1234-5678'
        original = deepcopy(value)
        calls = []
        def transport(payload, key, timeout):
            calls.append(deepcopy(payload))
            return grok_stub(payload, key, timeout)
        agent = EvidenceAgent(self.config(), transport=transport)
        result = agent.investigate(value)
        self.assertEqual(result['assessment'], 'ad_suspected')
        self.assertEqual(agent.ledger['calls'], 2)
        self.assertEqual(value, original)
        self.assertNotIn('token=secret', json.dumps(calls))
        self.assertNotIn('010-1234-5678', json.dumps(calls))
        self.assertNotIn('x@example.invalid', json.dumps(calls))
        self.assertIn('tools', calls[0]); self.assertNotIn('response_format', calls[0])
        self.assertNotIn('tools', calls[1]); self.assertIn('response_format', calls[1])

    def test_budget_before_network_cancel_and_failure_reservation(self):
        called = []
        def failed(*args): called.append(1); raise ValueError('simulated failure')
        tiny = EvidenceAgent(self.config(token_limit=1000), transport=failed)
        with self.assertRaisesRegex(ValueError, '한도'): tiny.investigate(packet())
        self.assertEqual(called, [])
        stopped = Event(); stopped.set()
        with self.assertRaisesRegex(ValueError, '취소'):
            EvidenceAgent(self.config(), transport=failed, stop=stopped).investigate(packet())
        self.assertEqual(called, [])
        agent = EvidenceAgent(self.config(), transport=failed)
        with self.assertRaises(ValueError): agent.investigate(packet())
        self.assertEqual(agent.ledger['calls'], 1)
        self.assertGreater(agent.ledger['charged_tokens'], 0)
        resumed = EvidenceAgent(self.config(token_limit=60000), agent.ledger, transport=failed)
        self.assertEqual(resumed.ledger['token_limit'], 24000)

    def test_unknown_tool_wrong_scope_and_hallucinated_evidence_rejected(self):
        for kind in ('unknown_tool', 'wrong_scope', 'hallucinated'):
            def bad(payload, key, timeout):
                result = grok_stub(payload, key, timeout)
                message = result['choices'][0]['message']
                if payload.get('tools'):
                    if kind == 'unknown_tool': message['tool_calls'][0]['function']['name'] = 'exec'
                    if kind == 'wrong_scope': message['tool_calls'][0]['function']['arguments'] = '{"evidence_id":"another_run"}'
                elif kind == 'hallucinated':
                    content = json.loads(message['content']); content['evidence_ids'] = ['invented']; message['content'] = json.dumps(content)
                return result
            with self.subTest(kind=kind), self.assertRaises(Exception):
                EvidenceAgent(self.config(), transport=bad).investigate(packet())

    def test_short_fragment_abstains_and_null_css_remains_unknown(self):
        value = packet(); value['text'] = 'CΟΜ'; value['computed_style'] = None
        result = EvidenceAgent(self.config(), transport=grok_stub).investigate(value)
        self.assertEqual(result['assessment'], 'uncertain')
        self.assertEqual(result['recommended_next_action'], 'collect_more_evidence')
        value = packet(); value['scope_quality'] = 'overlapping'
        self.assertEqual(EvidenceAgent(self.config(), transport=grok_stub).investigate(value)['assessment'], 'uncertain')

    def test_fixed_grok_endpoint_and_provider_error_not_echoed(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _limit): return b'{"choices":[]}'
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        opener = Opener()
        with patch('chickadee.agent.urllib.request.build_opener', return_value=opener):
            groq_request({'model': 'example'}, 'test_key_not_real', 1)
        self.assertEqual(opener.request.full_url, ENDPOINT)
        self.assertEqual(opener.request.get_method(), 'POST')
        with patch('chickadee.agent.urllib.request.build_opener', side_effect=OSError('secret')):
            with self.assertRaises(OSError): groq_request({}, 'test_key_not_real', 1)

class GroqOnlyTests(unittest.TestCase):
    def test_desktop_requires_user_key_and_forgets_it_on_restart(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'GROQ_API_KEY': 'gsk_ambient123456789'}):
            bridge = DesktopBridge(folder, lambda _: None)
            self.assertFalse(bridge.command('agent-status', {})['configured'])
            with self.assertRaisesRegex(ValueError, 'API 키를 입력'):
                bridge.command('agent-configure', {})
            bridge.command('agent-configure', {'api_key': 'gsk_userinput123456789'})
            self.assertTrue(bridge.command('agent-status', {})['configured'])
            bridge.command('agent-configure', {'token_limit': 1000, 'call_limit': 1})
            self.assertEqual(bridge.agent_config['api_key'], 'gsk_userinput123456789')
            self.assertFalse(DesktopBridge(folder, lambda _: None).command('agent-status', {})['configured'])
            for file in Path(folder).rglob('*.json'):
                self.assertNotIn('gsk_userinput123456789', file.read_text(encoding='utf-8'))

    def test_groq_endpoint_key_source_and_other_provider_rejection(self):
        from chickadee.agent import settings, DEFAULT_MODEL, redact
        self.assertEqual(ENDPOINT, 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(DEFAULT_MODEL, 'openai/gpt-oss-20b')
        with patch.dict(os.environ, {'XAI_API_KEY': 'xai-testkey123456789', 'GROQ_API_KEY': 'gsk_oldkey123456789'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'API 키를 입력'):
                settings({})
            self.assertEqual(settings({'api_key': 'gsk_userkey123456789'})['api_key'], 'gsk_userkey123456789')
        with patch.dict(os.environ, {'XAI_API_KEY': 'xai-testkey123456789'}, clear=True):
            with self.assertRaises(ValueError): settings({})
        with self.assertRaises(ValueError): settings({'api_key': 'xai-testkey123456789'})
        self.assertNotIn('xai-testkey123456789', redact('key xai-testkey123456789'))
