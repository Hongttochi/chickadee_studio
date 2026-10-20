"""Opt-in paid integration: real Groq -> real localhost Chromium follow-up.

At most four Groq requests / 24000 reserved tokens. Synthetic data only.
An existing output ledger is resumed; failed calls are never silently retried.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import tempfile
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chickadee.bridge import DesktopBridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = {'call_limit': 4, 'token_limit': 24000}
    if args.env_file:
        for line in args.env_file.read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'\s*(?:export\s+)?GROQ_API_KEY\s*=\s*(.*?)\s*$', line)
            if match:
                value = match.group(1)
                if value[:1] in ('"', "'") and value[-1:] == value[:1]: value = value[1:-1]
                else: value = value.split(' #', 1)[0].strip()
                config['api_key'] = value
    previous = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else {}
    if previous.get('completed'):
        print('Already completed. No paid requests sent.'); return 0
    requests = []
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            requests.append(self.path)
            body = ('<article id="post">요약<a href="/posts/1">상세</a></article>' if self.path == '/' else
                    '<article id="post">게시글 상세: caѕino 가입하고 충전 보너스를 받으세요. 신규 회원 가입 혜택 안내입니다.</article>')
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(body.encode('utf-8'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with tempfile.TemporaryDirectory() as folder:
            bridge = DesktopBridge(folder, lambda _: None)
            from chickadee.scanner import ScanConfig, scan
            from chickadee.reviews import ReviewStore
            import asyncio
            url = f'http://127.0.0.1:{server.server_port}/'
            bridge.outcome = asyncio.run(scan(ScanConfig(url, max_pages=1, settle_ms=0, follow_links=False)))
            bridge.output_path = str(bridge.outcome.save(Path(folder)))
            bridge.run_id = Path(folder).name
            bridge.reviews = ReviewStore(bridge.output_path, bridge.outcome)
            if previous.get('ledger'): bridge.agent_data['ledger'] = previous['ledger']
            source = bridge.outcome.report['evidence_packets'][0]
            bridge.command('agent-configure', config)
            # Persist the sanitized ledger after EVERY reservation, even if the
            # process is interrupted before the final integration result.
            original_save = bridge._save_agent
            def save():
                original_save()
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps({'ledger': bridge.agent_data['ledger'], 'completed': False}, indent=2) + '\n', encoding='utf-8')
            bridge._save_agent = save
            bridge.command('agent-run', {'run_id': bridge.run_id, 'evidence_id': source['id']})
            bridge.agent_worker.join(40)
            bridge.agent_stop.set()
            status = bridge.command('agent-status', {})
            results = status['assessments']
            completed = bool(results and results[0].get('exploration_status') == 'completed' and status['explorations'])
            proof = {'scope': 'Real Groq tool selection + real Chromium on owned synthetic localhost pages; no real-site accuracy claim.',
                     'provider': 'groq', 'completed': completed, 'ledger': status['ledger'],
                     'local_paths_requested': requests,
                     'assessments': [{k: a.get(k) for k in ('assessment', 'exploration_status', 'reads', 'missing_evidence', 'model')} for a in results],
                     'collected_pages': len(status['explorations']),
                     'screenshots_captured': sum(len(v.get('screenshots', {})) for v in status['explorations']),
                     'events': [{k: e[k] for k in ('kind', 'action', 'tool', 'message') if k in e} for e in status['events']]}
            args.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(proof, ensure_ascii=True))
            return 0 if completed else 1
    finally:
        server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__': raise SystemExit(main())
