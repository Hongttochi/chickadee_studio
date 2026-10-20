import asyncio
import base64
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest

from chickadee.bridge import DesktopBridge
from chickadee.demo import DemoSite
from chickadee.scanner import ScanConfig, scan
from chickadee.workflow import CONNECTIONS, compile_workflow


def workflow():
    return {'version': 1, 'edges': [{'source': a, 'target': b} for a, b in CONNECTIONS]}


class DesktopTests(unittest.TestCase):
    def test_graph_connections_control_real_analysis(self):
        value = workflow()
        value['edges'] = [e for e in value['edges'] if e['source'] != 'techniques']
        flags = compile_workflow(value)
        self.assertFalse(flags['detect_techniques'])
        self.assertTrue(flags['detect_candidates'])
        with DemoSite() as site:
            outcome = asyncio.run(scan(ScanConfig(site.url+'board?id=1', max_pages=1, settle_ms=0, interval_sec=0,
                                                  follow_links=False, detect_techniques=False)))
        self.assertEqual(outcome.report['status'], 'completed', outcome.report['errors'])
        self.assertEqual(len(outcome.report['pages_scanned']), 1)
        self.assertEqual(outcome.result['findings'], [])
        self.assertTrue(outcome.report['ad_candidates'])

    def test_broken_or_injected_graph_is_rejected(self):
        for edges in ([], [{'source': 'target', 'target': 'report'}], [{'source': 'exec', 'target': 'report'}]):
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
