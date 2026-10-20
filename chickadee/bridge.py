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

from . import __version__
from .demo import DemoSite
from .exports import atomic_write
from .scanner import ScanConfig, ScanOutcome, scan
from .workflow import compile_workflow


class DesktopBridge:
    def __init__(self, data_dir, send):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.send = send
        self.worker = None
        self.stop = Event()
        self.outcome = None
        self.output_path = None
        self.history_path = self.data_dir/'history.json'
        try:
            self.history = json.loads(self.history_path.read_text(encoding='utf-8'))[:30]
        except (OSError, ValueError, TypeError):
            self.history = []

    @property
    def running(self):
        return self.worker is not None and self.worker.is_alive()

    def emit(self, event):
        self.send({'event': {**event, 'timestamp': datetime.now().astimezone().isoformat()}})

    def command(self, method, params):
        if not isinstance(params, dict):
            raise ValueError('명령 인자가 올바르지 않습니다.')
        if method == 'state':
            return {'version': __version__, 'running': self.running, 'history': self.history}
        if method == 'stop':
            self.stop.set()
            return {'stopping': self.running}
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
            self.worker = Thread(target=self._run, args=(config, folder, bool(params.get('demo')), params['workflow']), daemon=True)
            self.worker.start()
            return {'started': True, 'folder': str(folder)}
        if method == 'load':
            if self.running:
                raise ValueError('검사를 중단한 다음 결과를 불러오세요.')
            self.outcome = ScanOutcome.load(Path(params['path']))
            self.output_path = str(Path(params['path']).resolve())
            folder = Path(params['path']).parent
            events = []
            log = folder/'events.jsonl'
            if log.exists() and log.stat().st_size <= 30_000_000:
                try:
                    events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line][-2000:]
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
            return {'result': self.outcome.result, 'report': self.outcome.report, 'path': self.output_path,
                    'events': events, 'preview': preview}
        if method == 'export':
            if self.outcome is None or self.running:
                raise ValueError('완료된 결과가 없습니다.')
            self.outcome.save_csv(Path(params['path']))
            return {'path': params['path']}
        raise ValueError('지원하지 않는 명령입니다.')

    def _run(self, config, folder, demo, workflow):
        site = None
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
                # Persist a complete process timeline without huge image payloads.
                if event['kind'] != 'preview' and len(events) < 100000:
                    events.append({**event, 'timestamp': datetime.now().astimezone().isoformat()})
                self.emit(event)
            observe({'kind': 'started', 'url': config.entry_url, 'folder': str(folder)})
            self.outcome = asyncio.run(scan(config, self.stop, observe))
            observe({'kind': 'phase', 'stage': 'report', 'action': 'save', 'message': 'JSON·CSV·탐색 보고서와 실행 기록을 저장합니다.'})
            self.outcome.report['workflow'] = workflow
            path = self.outcome.save(folder)
            self.output_path = str(path)
            entry = {'id': folder.name, 'url': config.entry_url, 'status': self.outcome.report['status'],
                     'findings': len(self.outcome.result['findings']), 'candidates': self.outcome.report['candidate_count'],
                     'pages': len(self.outcome.report['pages_scanned']), 'path': str(path),
                     'finished_at': self.outcome.result['meta']['finished_at']}
            self.history = [entry, *self.history][:30]
            atomic_write(self.history_path, json.dumps(self.history, ensure_ascii=False, indent=2).encode('utf-8'))
            events.append({'kind': 'done', 'report': {'status': self.outcome.report['status']},
                           'path': str(path), 'timestamp': datetime.now().astimezone().isoformat()})
            atomic_write(folder/'events.jsonl', ''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events).encode('utf-8'))
            self.emit({'kind': 'done', 'result': self.outcome.result, 'report': self.outcome.report, 'path': str(path), 'history': self.history})
        except Exception as exc:
            self.emit({'kind': 'error', 'message': str(exc)})
        finally:
            if site:
                site.close()


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
