"""JSON-lines desktop protocol over private child-process stdio; no HTTP server."""
import argparse
import asyncio
import base64
from datetime import datetime
import json
from pathlib import Path
import sys
from threading import Event, Lock, Thread
import uuid
from collections import deque

from . import __version__
from .demo import DemoSite
from .exports import atomic_write
from .scanner import ScanConfig, ScanOutcome, scan
from .workflow import compile_workflow
from .control import ScanControl
from .reviews import ReviewStore
from .tools import capabilities, resolve_tool


class DesktopBridge:
    def __init__(self, data_dir, send):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.send = send
        self.worker = None
        self.busy = Event()
        self.stop = Event()
        self.outcome = None
        self.output_path = None
        self.control = ScanControl()
        self.run_id = None
        self.sequence = 0
        self.recent_events = deque(maxlen=2000)
        self.live_records = {}
        self.reviews = None
        self.phase = None
        self.stopping = False
        self.last_status = 'idle'
        self._event_lock = Lock()
        self.history_path = self.data_dir/'history.json'
        try:
            self.history = json.loads(self.history_path.read_text(encoding='utf-8'))[:30]
        except (OSError, ValueError, TypeError):
            self.history = []

    @property
    def running(self):
        return self.busy.is_set()

    def emit(self, event):
        with self._event_lock:
            self.sequence += 1
            value = {**event, 'timestamp': datetime.now().astimezone().isoformat(),
                     'run_id': self.run_id, 'sequence': self.sequence, 'protocol_version': 1}
            if event['kind'] != 'preview':
                self.recent_events.append(value)
            if event['kind'] == 'phase':
                self.phase = event['stage']
        self.send({'event': value})
        return value

    def command(self, method, params):
        if not isinstance(params, dict):
            raise ValueError('명령 인자가 올바르지 않습니다.')
        if method == 'capabilities':
            return capabilities()
        if method == 'tool-call':
            arguments = params.get('arguments', {})
            target = resolve_tool(params.get('name'), arguments)
            if 'run_id' in arguments and arguments['run_id'] != self.run_id:
                raise ValueError('현재 검사 실행 ID와 일치하지 않습니다.')
            return self.command(target, {**arguments, **({'actor': 'agent'} if target == 'review' else {})})
        if method == 'validate-workflow':
            return compile_workflow(params.get('workflow'))
        if method == 'state':
            state = ('stopping' if self.stopping else 'paused' if self.control.paused.is_set() else
                     'pausing' if self.control.requested.is_set() else 'running') if self.running else self.last_status
            return {'version': __version__, 'running': self.running, 'history': self.history,
                    'run_id': self.run_id, 'status': state, 'phase': self.phase, 'sequence': self.sequence,
                    'paused_sec': round(self.control.paused_seconds, 3), 'protocol_version': 1}
        if method in ('pause', 'resume'):
            if not self.running or self.stopping:
                raise ValueError('진행 중인 검사가 없습니다.')
            if method == 'pause':
                self.control.pause()
            else:
                self.control.resume()
            return {'status': 'pausing' if method == 'pause' else 'running', 'run_id': self.run_id}
        if method == 'stop':
            self.stopping = self.running
            self.stop.set()
            return {'stopping': self.running}
        if method in ('findings', 'events'):
            offset, limit = params.get('offset', 0), params.get('limit', 100)
            after = params.get('after_sequence', 0)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500 or type(after) is not int or after < 0:
                raise ValueError('조회 범위가 올바르지 않습니다.')
            if method == 'events':
                with self._event_lock:
                    available = list(self.recent_events)
                rows = [event for event in available if event['sequence'] > after][:limit]
                return {'run_id': self.run_id, 'items': rows, 'next_sequence': rows[-1]['sequence'] if rows else after,
                        'truncated': bool(available and after < available[0]['sequence'] - 1)}
            records = [*self.outcome.result['findings'], *self.outcome.report.get('ad_candidates', [])] if self.outcome else list(self.live_records.values())
            details = self.outcome.report.get('evidence_details', {}) if self.outcome else {}
            items = [{**record, 'detail': details.get(record['id'], record.get('_detail', {})),
                      'review': self.reviews.data['items'].get(record['id']) if self.reviews else None} for record in records[offset:offset+limit]]
            return {'run_id': self.run_id, 'items': items, 'total': len(records), 'next_offset': offset + len(items)}
        if method == 'review':
            if self.running or self.reviews is None:
                raise ValueError('검사가 끝난 뒤 검토 상태를 저장하세요.')
            value = self.reviews.update(params.get('ids'), params.get('status'), params.get('note'),
                                        params.get('expected_revision'), params.get('actor', 'human'))
            self.emit({'kind': 'review_updated', 'ids': params['ids'], 'status': params['status'], 'revision': value['revision']})
            return value
        if method == 'start':
            if self.running:
                raise ValueError('이미 검사 중입니다.')
            flags = compile_workflow(params.get('workflow'))
            profile = params.get('profile', 'default')
            if profile not in ('default', 'test', 'public'):
                raise ValueError('지원하지 않는 사이트 설정입니다.')
            # Frozen resources are collected beside chickadee/ under _internal.
            root = Path(__file__).resolve().parent.parent
            profile_path = root/'profiles'/('inuri-test.json' if profile == 'test' else 'public-site.json') if profile != 'default' else None
            config = ScanConfig(params.get('url', ''), max_pages=params.get('max_pages', 100),
                                timeout_sec=params.get('timeout_sec', 300), settle_ms=params.get('settle_ms', 350),
                                interval_sec=params.get('interval_sec', .5), allow_network=True,
                                profile_path=profile_path, capture_previews=params.get('preview', True), **flags)
            output_root = Path(params['output_root']) if params.get('output_root') else self.data_dir/'scans'
            folder = output_root/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
            self.stop = Event()
            self.outcome = None
            self.output_path = None
            self.reviews = None
            self.control = ScanControl()
            self.stopping = False
            self.run_id = folder.name
            self.sequence = 0
            self.recent_events.clear()
            self.live_records.clear()
            self.phase = None
            self.last_status = 'running'
            self.busy = Event()
            self.busy.set()
            self.worker = Thread(target=self._run, args=(config, folder, bool(params.get('demo')), params['workflow']), daemon=True)
            self.worker.start()
            return {'started': True, 'folder': str(folder), 'run_id': self.run_id}
        if method == 'load':
            if self.running:
                raise ValueError('검사를 중단한 다음 결과를 불러오세요.')
            loaded = ScanOutcome.load(Path(params['path']))
            loaded_path = str(Path(params['path']).resolve())
            loaded_reviews = ReviewStore(loaded_path, loaded)
            folder = Path(params['path']).parent
            events = []
            log = folder/'events.jsonl'
            if log.exists() and log.stat().st_size <= 30_000_000:
                try:
                    events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line][-2000:]
                    events = [event for event in events if isinstance(event, dict) and isinstance(event.get('kind'), str)
                              and type(event.get('sequence', 1)) is int and event.get('sequence', 1) > 0]
                except (ValueError, OSError):
                    events = []
            preview = None
            image = folder/'last-preview.jpg'
            if image.exists() and image.stat().st_size < 1_000_000:
                try:
                    metadata = json.loads((folder/'last-preview.json').read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    metadata = {}
                preview = {'url': metadata.get('url', ''), 'title': metadata.get('title', ''),
                           'timestamp': metadata.get('timestamp'),
                           'data_url': 'data:image/jpeg;base64,' + base64.b64encode(image.read_bytes()).decode('ascii')}
            self.outcome, self.output_path, self.reviews = loaded, loaded_path, loaded_reviews
            self.last_status = loaded.report['status']
            self.run_id = loaded.report.get('run_id') or Path(loaded_path).parent.name
            self.phase = None
            self.control = ScanControl()
            with self._event_lock:
                self.recent_events.clear()
                self.recent_events.extend({**event, 'sequence': event.get('sequence', index+1), 'run_id': self.run_id}
                                          for index, event in enumerate(events))
                self.sequence = max((event['sequence'] for event in self.recent_events), default=0)
            return {'result': self.outcome.result, 'report': self.outcome.report, 'path': self.output_path,
                    'events': events, 'preview': preview, 'reviews': self.reviews.data, 'run_id': self.run_id}
        if method == 'export':
            if self.outcome is None or self.running:
                raise ValueError('완료된 결과가 없습니다.')
            self.outcome.save_csv(Path(params['path']))
            return {'path': params['path']}
        raise ValueError('지원하지 않는 명령입니다.')

    def _run(self, config, folder, demo, workflow):
        site = None
        busy = self.busy
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if demo:
                from dataclasses import replace
                site = DemoSite().start()
                config = replace(config, entry_url=site.url, profile_path=None)
            events = []
            def observe(event):
                if event['kind'] == 'preview':
                    atomic_write(folder/'last-preview.jpg', base64.b64decode(event['data_url'].split(',', 1)[1]))
                    atomic_write(folder/'last-preview.json', json.dumps({'url': event['url'], 'title': event.get('title', ''),
                        'timestamp': datetime.now().astimezone().isoformat()}, ensure_ascii=False).encode('utf-8'))
                if event['kind'] in ('finding', 'candidate'):
                    record = event.get('finding') or event['candidate']
                    self.live_records[record['id']] = {**record, '_detail': event.get('detail')}
                value = self.emit(event)
                # Persist a complete process timeline without huge image payloads.
                if event['kind'] != 'preview' and len(events) < 100000:
                    events.append(value)
            observe({'kind': 'started', 'url': config.entry_url, 'folder': str(folder)})
            # Initialize the event loop before constructing the coroutine so an
            # OS startup failure does not leak an unawaited scan coroutine.
            with asyncio.Runner() as runner:
                runner.get_loop()
                self.outcome = runner.run(scan(config, self.stop, observe, self.control))
            observe({'kind': 'phase', 'stage': 'report', 'action': 'save', 'message': 'JSON·CSV·탐색 보고서와 실행 기록을 저장합니다.'})
            self.outcome.report['workflow'] = workflow
            self.outcome.report['run_id'] = self.run_id
            self.outcome.report['desktop_options'] = {'demo': demo, 'preview': config.capture_previews}
            path = self.outcome.save(folder)
            self.output_path = str(path)
            self.reviews = ReviewStore(path, self.outcome)
            entry = {'id': folder.name, 'url': config.entry_url, 'status': self.outcome.report['status'],
                     'findings': len(self.outcome.result['findings']), 'candidates': self.outcome.report['candidate_count'],
                     'pages': len(self.outcome.report['pages_scanned']), 'path': str(path),
                     'finished_at': self.outcome.result['meta']['finished_at']}
            self.history = [entry, *self.history][:30]
            atomic_write(self.history_path, json.dumps(self.history, ensure_ascii=False, indent=2).encode('utf-8'))
            if site:
                site.close()
                site = None
            # Release busy state before notifying clients, so an immediate next
            # command can review or start another run without a cleanup race.
            events.append({'kind': 'done', 'report': {'status': self.outcome.report['status']},
                           'path': str(path), 'timestamp': datetime.now().astimezone().isoformat(),
                           'run_id': self.run_id, 'sequence': self.sequence + 1, 'protocol_version': 1})
            atomic_write(folder/'events.jsonl', ''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events).encode('utf-8'))
            busy.clear()
            self.stopping = False
            self.last_status = self.outcome.report['status']
            self.emit({'kind': 'done', 'result': self.outcome.result, 'report': self.outcome.report,
                       'path': str(path), 'history': self.history, 'reviews': self.reviews.data})
        except Exception as exc:
            busy.clear()
            self.last_status = 'failed'
            self.emit({'kind': 'error', 'message': str(exc)})
        finally:
            if site:
                site.close()
            busy.clear()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stdin.reconfigure(encoding='utf-8')
    lock = Lock()
    def send(message):
        with lock:
            print(json.dumps(message, ensure_ascii=False, allow_nan=False), flush=True)
    bridge = DesktopBridge(args.data_dir, send)
    for line in sys.stdin:
        request = {}
        try:
            if len(line) > 1_000_000:
                raise ValueError('명령이 너무 큽니다.')
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError('잘못된 요청입니다.')
            result = bridge.command(request.get('method'), request.get('params', {}))
            send({'id': request.get('id'), 'result': result})
        except Exception as exc:
            send({'id': request.get('id') if isinstance(request, dict) else None, 'error': str(exc)})
    bridge.stop.set()
    if bridge.worker:
        bridge.worker.join(timeout=8)


if __name__ == '__main__':
    main()
