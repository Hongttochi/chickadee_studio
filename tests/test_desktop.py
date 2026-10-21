import asyncio
import base64
import json
from pathlib import Path
import tempfile
import time
from threading import Event
import unittest

from chickadee.bridge import DesktopBridge
from chickadee.demo import DemoSite
from chickadee.scanner import ScanConfig, scan
from chickadee.workflow import CONNECTIONS, compile_workflow


def workflow():
    return {'version': 1, 'edges': [{'source': a, 'target': b} for a, b in CONNECTIONS]}


class DesktopTests(unittest.TestCase):
    def test_pause_waits_at_page_boundary_and_resumes_without_losing_queue(self):
        with tempfile.TemporaryDirectory() as temporary:
            messages = []
            bridge = DesktopBridge(temporary, messages.append)
            bridge.command('start', {'url': 'http://127.0.0.1/', 'demo': True, 'max_pages': 20,
                                    'preview': False, 'settle_ms': 0, 'interval_sec': .1, 'workflow': workflow()})
            bridge.command('pause', {})
            self.assertTrue(bridge.control.paused.wait(10), messages[-3:])
            before = len([m for m in messages if m['event']['kind'] == 'page_complete'])
            time.sleep(.25)
            self.assertEqual(before, len([m for m in messages if m['event']['kind'] == 'page_complete']))
            self.assertEqual(bridge.command('state', {})['status'], 'paused')
            bridge.command('resume', {})
            bridge.worker.join(30)
            self.assertFalse(bridge.running)
            self.assertEqual(len(bridge.outcome.result['findings']), 14)
            self.assertGreaterEqual(bridge.outcome.report['paused_sec'], .2)
            self.assertEqual(len(bridge.outcome.report['pages_scanned']), 4)

    def test_stopping_paused_scan_saves_cancelled_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            bridge = DesktopBridge(temporary, lambda event: None)
            bridge.command('start', {'url': 'http://127.0.0.1/', 'demo': True, 'preview': False, 'workflow': workflow()})
            bridge.command('pause', {})
            self.assertTrue(bridge.control.paused.wait(10))
            bridge.command('stop', {})
            bridge.worker.join(15)
            self.assertFalse(bridge.running)
            self.assertEqual(bridge.outcome.report['status'], 'cancelled')
            self.assertTrue(Path(bridge.output_path).is_file())

    def test_review_sidecar_preserves_raw_evidence_and_rejects_stale_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            bridge = DesktopBridge(temporary, lambda event: None)
            bridge.command('start', {'url': 'http://127.0.0.1/', 'demo': True, 'max_pages': 4,
                                    'preview': False, 'settle_ms': 0, 'interval_sec': 0, 'workflow': workflow()})
            bridge.worker.join(30)
            path = Path(bridge.output_path)
            original = path.read_bytes()
            record = bridge.outcome.result['findings'][0]
            review = bridge.command('review', {'ids': [record['id']], 'status': 'confirmed', 'note': '원문 확인', 'expected_revision': 0})
            self.assertEqual(review['revision'], 1)
            self.assertEqual(path.read_bytes(), original)
            for params in ({'ids': ['missing'], 'status': 'dismissed', 'expected_revision': 1},
                           {'ids': [record['id']], 'status': 'dismissed', 'expected_revision': 0}):
                with self.assertRaises(ValueError):
                    bridge.command('review', params)
            loaded = bridge.command('load', {'path': str(path)})
            self.assertEqual(loaded['reviews']['items'][record['id']]['note'], '원문 확인')
            self.assertEqual(loaded['reviews']['items'][record['id']]['status'], 'confirmed')
            items = bridge.command('tool-call', {'name': 'scan.findings', 'arguments': {'run_id': bridge.run_id, 'limit': 1}})
            self.assertEqual(len(items['items']), 1)
            self.assertEqual(items['items'][0]['review']['status'], 'confirmed')
            events = bridge.command('tool-call', {'name': 'scan.events', 'arguments': {'run_id': bridge.run_id}})['items']
            self.assertTrue(all(isinstance(event['sequence'], int) for event in events))
            self.assertTrue(all(event['kind'] != 'preview' for event in events))

    def test_agent_contract_rejects_unknown_tools_paths_and_wrong_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            bridge = DesktopBridge(temporary, lambda event: None)
            caps = bridge.command('capabilities', {})
            self.assertFalse(caps['agent_connected'])
            self.assertTrue(any(tool['name'] == 'review.update' for tool in caps['tools']))
            for name, arguments in [('exec', {}), ('scan.stop', {'run_id': 'stale'}),
                                    ('scan.start', {'url': 'http://127.0.0.1/', 'workflow': workflow(), 'output_root': 'C:/'}),
                                    ('review.update', {'run_id': 'x', 'ids': [], 'status': 'confirmed', 'expected_revision': 0})]:
                with self.assertRaises(ValueError):
                    bridge.command('tool-call', {'name': name, 'arguments': arguments})

    def test_saved_connections_cannot_disable_fixed_analysis(self):
        value = workflow()
        value['edges'] = [e for e in value['edges'] if e['source'] != 'techniques']
        flags = compile_workflow(value)
        self.assertTrue(flags['detect_techniques'])
        self.assertTrue(flags['detect_candidates'])
        with DemoSite() as site:
            outcome = asyncio.run(scan(ScanConfig(site.url+'board?id=1', max_pages=1, settle_ms=0, interval_sec=0,
                                                  follow_links=False, detect_techniques=False)))
        self.assertEqual(outcome.report['status'], 'completed', outcome.report['errors'])
        self.assertEqual(len(outcome.report['pages_scanned']), 1)
        self.assertEqual(outcome.result['findings'], [])
        self.assertTrue(outcome.report['ad_candidates'])

    def test_broken_or_injected_graph_is_rejected(self):
        for edges in ([{'source': 'target', 'target': 'report'}], [{'source': 'exec', 'target': 'report'}]):
            with self.assertRaises(ValueError):
                compile_workflow({'edges': edges})

    def test_live_phases_preview_and_bridge_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            messages=[]
            bridge=DesktopBridge(temporary, messages.append)
            ack=bridge.command('start', {'url':'http://127.0.0.1/','demo':True,'max_pages':1,
                                        'settle_ms':0,'interval_sec':0,'workflow':workflow()})
            self.assertTrue(ack['started'])
            bridge.worker.join(timeout=30)
            self.assertFalse(bridge.running)
            events=[message['event'] for message in messages]
            done=next(event for event in events if event['kind']=='done')
            self.assertEqual(done['report']['status'],'partial')
            self.assertTrue(any(event.get('stage')=='collector' for event in events))
            preview=next(event for event in events if event['kind']=='preview')
            self.assertTrue(base64.b64decode(preview['data_url'].split(',')[1]).startswith(b'\xff\xd8'))
            folder=Path(done['path']).parent
            self.assertTrue((folder/'events.jsonl').exists())
            loaded=bridge.command('load', {'path':done['path']})
            self.assertTrue(loaded['events'])
            self.assertTrue(loaded['preview'])
            self.assertEqual(len(bridge.command('state', {})['history']),1)
