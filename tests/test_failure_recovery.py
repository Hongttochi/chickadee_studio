"""Fatal failures terminate visibly; partial crawls and diagnostics are preserved."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from chickadee.scanner import ScanConfig, scan, _fetch_route, _State
from chickadee.bridge import DesktopBridge
from tests.test_desktop import workflow


class FailureTests(unittest.TestCase):
    def test_transient_read_failure_retries_once_without_following_redirects(self):
        async def check():
            response=object();route=SimpleNamespace(fetch=AsyncMock(side_effect=[OSError('connect EFAULT'),response]))
            state=_State();events=[];config=ScanConfig('http://127.0.0.1/')
            result=await _fetch_route(route,config,state,events.append,config.entry_url)
            self.assertIs(result,response)
            self.assertEqual(route.fetch.await_count,2)
            self.assertEqual(state.retry_count,1)
            for call in route.fetch.call_args_list:
                self.assertEqual(call.kwargs['max_redirects'],0)
            route.fetch=AsyncMock(side_effect=OSError('permanent failure'))
            with self.assertRaises(OSError):
                await _fetch_route(route,config,state,events.append,config.entry_url)
            self.assertEqual(route.fetch.await_count,1)
        asyncio.run(check())

    def test_exception_after_a_page_preserves_partial_status_and_error(self):
        async def interrupted(config,state,*args):
            state.pages.append(config.entry_url)
            raise RuntimeError('fixture browser disconnected')
        with patch('chickadee.scanner._crawl',side_effect=interrupted):
            outcome=asyncio.run(scan(ScanConfig('http://127.0.0.1/')))
        self.assertEqual(outcome.report['status'],'partial')
        self.assertEqual(len(outcome.report['pages_scanned']),1)
        self.assertIn('disconnected',outcome.report['errors'][0]['message'])

    def test_fatal_failure_is_not_left_running_and_writes_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            events=[];bridge=DesktopBridge(temp,events.append)
            with patch('chickadee.bridge.scan',side_effect=RuntimeError('fixture engine failure')):
                bridge.command('start',{'url':'http://127.0.0.1/','workflow':workflow(),'output_root':temp})
                bridge.worker.join(15)
            self.assertFalse(bridge.running)
            self.assertEqual(bridge.command('state',{})['status'],'failed')
            report=next(Path(temp).rglob('failure.json'))
            self.assertEqual(json.loads(report.read_text('utf-8'))['error_type'],'RuntimeError')
            self.assertIn('fixture engine failure',report.with_suffix('.log').read_text('utf-8'))
            timeline=report.with_name('events.jsonl').read_text('utf-8').splitlines()
            self.assertEqual(json.loads(timeline[-1])['kind'],'error')
