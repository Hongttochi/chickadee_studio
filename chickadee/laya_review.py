"""Bounded offline Laya review, isolated from the scanner and its public I/O."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_ITEMS = 12


def configuration():
    """Read only the user's explicit local-model configuration, never credentials."""
    value = {}
    config = os.environ.get('CHICKADEE_LAYA_CONFIG')
    if config:
        path = Path(config)
        if not path.is_absolute():
            raise ValueError('Laya 설정 파일 오류')
        if path.exists():
            if path.stat().st_size > 16_384:
                raise ValueError('Laya 설정 파일 크기 오류')
            value = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value.get('format') != 1:
                raise ValueError('Laya 설정 형식 오류')
    folder = os.environ.get('CHICKADEE_LAYA_MODEL_DIR') or value.get('model_dir')
    executable = os.environ.get('CHICKADEE_LAYA_PYTHON') or value.get('python')
    if folder:
        if not isinstance(folder, str): raise ValueError('Laya 모델 경로 오류')
        folder = str(Path(folder).resolve())
    if executable and (not isinstance(executable, str) or not Path(executable).is_absolute() or not Path(executable).is_file()):
        raise ValueError('Laya 실행 환경 오류')
    return folder, executable


def unavailable(reason='model_not_validated'):
    messages = {'model_not_validated': '검증한 Laya 모델을 적용하지 않았습니다.',
        'insufficient_scope': '문맥 검토에 필요한 원문 범위가 부족합니다.',
        'budget_or_cancelled': '검토 한도 또는 사용자 중단으로 처리하지 않았습니다.',
        'time_budget': '남은 검사 시간이 없어 검토를 생략했습니다.',
        'insufficient_memory': 'Laya 검토에 필요한 메모리가 부족합니다.',
        'runtime_unavailable': '로컬 Laya 실행 환경을 찾지 못했습니다.',
        'timeout': 'Laya 검토 제한시간을 초과했습니다.'}
    return {'status': 'unavailable', 'model': 'Laya', 'reason': reason,
            'message': messages.get(reason, 'Laya 검토를 완료하지 못했습니다.'), 'paid_requests': 0}


class LayaSession:
    def __init__(self, timeout_seconds=45):
        self.process = None
        self.stderr_task = None
        self.timeout_seconds = min(45, max(0, timeout_seconds))

    async def analyze(self, texts):
        if not texts or len(texts) > MAX_ITEMS or any(not isinstance(t, str) or not 0 < len(t) <= 4000 for t in texts):
            raise ValueError('Laya 입력 크기 오류')
        if not self.timeout_seconds:
            return [unavailable('time_budget') for _ in texts]
        try:
            folder, executable = configuration()
        except (OSError, ValueError, TypeError):
            return [unavailable('runtime_unavailable') for _ in texts]
        if not folder:
            return [unavailable() for _ in texts]
        from .runtime import memory_info, GIB
        available = memory_info()['available_bytes']
        if available is not None and available < 3 * GIB:
            return [unavailable('insufficient_memory') for _ in texts]
        if executable:
            if not Path(executable).is_absolute() or not Path(executable).is_file():
                return [unavailable('runtime_unavailable') for _ in texts]
            # The external Python cannot import modules embedded in a frozen engine.
            args = [executable, str(Path(__file__).with_name('laya_worker.py'))]
        else:
            args = [sys.executable, '--laya-worker'] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'chickadee.laya_worker']
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'HF_HUB_OFFLINE': '1',
               'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false', 'USE_TF': '0',
               'CHICKADEE_LAYA_MODEL_DIR': folder}
        try:
            self.process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=100_000,
                cwd=str(ROOT), env=env,
                **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
            async def drain():
                while await self.process.stderr.read(4096): pass
            self.stderr_task = asyncio.create_task(drain())
            self.process.stdin.write((json.dumps({'texts': texts}, ensure_ascii=True)+'\n').encode())
            await self.process.stdin.drain()
            line = await asyncio.wait_for(self.process.stdout.readline(), self.timeout_seconds)
            results = json.loads(line)['results']
            from .inspection import validate_local_ai
            if len(results) != len(texts): raise ValueError('Laya 결과 개수 오류')
            for item in results: validate_local_ai({'laya': item})
            return results
        except asyncio.TimeoutError:
            return [unavailable('timeout') for _ in texts]
        except (OSError, ValueError, KeyError, TypeError):
            return [unavailable('inference_failed') for _ in texts]
        finally:
            await self.close()

    async def close(self):
        if self.process:
            if self.process.returncode is None: self.process.kill()
            await self.process.wait()
            if self.stderr_task: await self.stderr_task
            self.process = None


async def review_sources(sources, *, stop=None, emit=lambda _: None, timeout_seconds=45):
    """One review per unique evidence text, bounded; never remove deterministic findings."""
    emit({'kind': 'phase', 'stage': 'laya', 'action': 'prepare', 'message': 'Laya 적용 상태를 확인합니다.'})
    selected, seen = [], set()
    for source in sources:
        text = source.get('text', '')
        key = text[:4000]
        if text.strip() and key not in seen and source.get('scope_quality') != 'overlapping' and len(selected) < MAX_ITEMS:
            selected.append(source); seen.add(key)
    session = LayaSession(timeout_seconds)
    async def work():
        if not selected: return []
        return await session.analyze([s['text'][:4000] for s in selected])
    task = asyncio.create_task(work())
    try:
        while not task.done():
            if stop and stop.is_set():
                task.cancel()
                break
            await asyncio.wait({task}, timeout=.1)
        results = await task if not task.cancelled() else []
    except asyncio.CancelledError:
        results = []
        if not (stop and stop.is_set()): raise
    except Exception:
        results = [unavailable('inference_failed') for _ in selected]
    finally:
        if not task.done(): task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await session.close()
    by_text = {s['text'][:4000]: r for s, r in zip(selected, results)}
    for source in sources:
        source.setdefault('local_ai', {})['laya'] = by_text.get(source.get('text','')[:4000], unavailable('budget_or_cancelled'))
    completed = sum(r['status'] == 'completed' for r in results)
    omitted = sum(s['local_ai']['laya']['status'] != 'completed' for s in sources)
    summary = {'status': 'completed' if completed and not omitted else 'partial' if completed else 'unavailable',
               'analyzed': completed, 'unique_selected': len(selected), 'item_limit': MAX_ITEMS,
               'omitted': omitted, 'paid_requests': 0}
    emit({'kind': 'phase', 'stage': 'laya', 'action': 'complete' if completed else 'skipped',
          'message': f'Laya {completed}개 문맥 검토' if completed else 'Laya 미적용 · 기존 탐지 결과 유지'})
    return summary


async def enrich_laya(report, *, stop=None, emit=lambda _: None, timeout_seconds=45):
    packets = report.get('evidence_packets', [])
    evidence = [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]
    keys = {(r.get('url'), r.get('scope_location', r.get('location'))) for r in evidence}
    def relevant(packet):
        if packet.get('scope_quality') == 'overlapping' or not packet.get('text','').strip(): return False
        if (packet.get('url'), packet.get('location')) in keys: return True
        if packet.get('scope_quality') == 'semantic' or packet.get('source_kind') == 'image_ocr':
            return len(packet['text'].strip()) >= 8
        if len(packet['text'].strip()) < 12: return False
        signal = packet.get('local_ai', {}).get('text', {})
        return signal.get('feature_count', 0) > 0
    # Preserve original evidence order; use existing ML only for routing uncertain fragments.
    def priority(packet):
        score = packet.get('local_ai', {}).get('text', {}).get('score')
        return packet.get('scope_quality') == 'overlapping', abs((.5 if score is None else score)-.5)
    selected = sorted([p for p in packets if relevant(p)], key=priority)
    summary = await review_sources(selected, stop=stop, emit=emit, timeout_seconds=timeout_seconds)
    for packet in packets:
        if not relevant(packet): packet.setdefault('local_ai', {})['laya'] = unavailable('insufficient_scope')
    summary['omitted'] = sum(p['local_ai']['laya']['status'] != 'completed' for p in packets)
    if summary['status'] == 'completed' and summary['omitted']: summary['status'] = 'partial'
    images = {i['id']: i for i in report.get('ocr_images', [])}
    for packet in packets:
        if packet.get('image_id') in images: images[packet['image_id']]['local_ai'] = packet['local_ai']
    for row in [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]:
        match = next((p for p in reversed(packets) if p['url'] == row.get('url') and
                      p['location'] == row.get('scope_location', row.get('location'))), None)
        if match: row['local_ai'] = match['local_ai']
    report.setdefault('local_ai', {})['laya'] = summary
    return summary
