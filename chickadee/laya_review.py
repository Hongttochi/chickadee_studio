"""Bounded offline Laya review, isolated from the scanner and its public I/O."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MAX_ITEMS = 12  # Per request; the scan can process successive batches.
MAX_SECONDS = 120


def configuration():
    """Read only the user's explicit local-model configuration, never credentials."""
    if os.environ.get('CHICKADEE_LAYA_WORKER') and os.environ.get('CHICKADEE_LAYA_MODEL_DIR'):
        # A portable release must not depend on a stale developer Python setting.
        return str(Path(os.environ['CHICKADEE_LAYA_MODEL_DIR']).resolve()), None
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


def analysis_reserve(total_seconds):
    """Leave time for a shipped model instead of letting crawling consume its entire budget."""
    try:
        folder, _ = configuration()
        return min(MAX_SECONDS, total_seconds*.4) if folder and (Path(folder)/'manifest.json').is_file() else 0
    except (OSError, ValueError, TypeError):
        return 0


class LayaSession:
    def __init__(self, timeout_seconds=MAX_SECONDS):
        self.process = None
        self.stderr_task = None
        self.timeout_seconds = min(MAX_SECONDS, max(0, timeout_seconds))

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
        # Measured bundled CPU peak: 2.78 GiB working set, about 2.04 GiB
        # additional available memory. Keep a reserve and monitor it while loading.
        if available is not None and available < 2.75 * GIB:
            return [unavailable('insufficient_memory') for _ in texts]
        bundled_worker = os.environ.get('CHICKADEE_LAYA_WORKER')
        if bundled_worker:
            if not Path(bundled_worker).is_absolute() or not Path(bundled_worker).is_file():
                return [unavailable('runtime_unavailable') for _ in texts]
            args = [bundled_worker]
        elif executable:
            if not Path(executable).is_absolute() or not Path(executable).is_file():
                return [unavailable('runtime_unavailable') for _ in texts]
            # The external Python cannot import modules embedded in a frozen engine.
            args = [executable, str(Path(__file__).with_name('laya_worker.py'))]
        else:
            args = [sys.executable, '--laya-worker'] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'chickadee.laya_worker']
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'HF_HUB_OFFLINE': '1',
               'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false', 'USE_TF': '0',
               'CHICKADEE_LAYA_MODEL_DIR': folder}
        reply = None
        reusable = False
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
            reply = asyncio.create_task(self.process.stdout.readline())
            deadline = time.monotonic() + self.timeout_seconds
            while not reply.done():
                free = memory_info()['available_bytes']
                if free is not None and free < .5 * GIB:
                    return [unavailable('insufficient_memory') for _ in texts]
                if time.monotonic() >= deadline:
                    raise asyncio.TimeoutError()
                await asyncio.wait({reply}, timeout=.25)
            line = await reply
            results = json.loads(line)['results']
            from .inspection import validate_local_ai
            if len(results) != len(texts): raise ValueError('Laya 결과 개수 오류')
            for item in results: validate_local_ai({'laya': item})
            reusable = any(item['status'] == 'completed' for item in results)
            return results
        except asyncio.TimeoutError:
            return [unavailable('timeout') for _ in texts]
        except (OSError, ValueError, KeyError, TypeError):
            return [unavailable('inference_failed') for _ in texts]
        finally:
            if reply is not None and not reply.done():
                reply.cancel()
                await asyncio.gather(reply, return_exceptions=True)
            if not reusable: await self.close()

    async def close(self):
        if self.process:
            if self.process.returncode is None: self.process.kill()
            await self.process.wait()
            if self.stderr_task: await self.stderr_task
            self.process = None


async def review_sources(sources, *, stop=None, emit=lambda _: None, timeout_seconds=MAX_SECONDS):
    """One review per unique evidence text, bounded; never remove deterministic findings."""
    emit({'kind': 'phase', 'stage': 'laya', 'action': 'prepare', 'message': 'Laya 적용 상태를 확인합니다.'})
    selected, seen = [], set()
    from .local_ai import has_review_context
    for source in sources:
        text = source.get('text', '')
        key = text[:4000]
        if text.strip() and has_review_context(source) and key not in seen and source.get('scope_quality') != 'overlapping':
            selected.append(source); seen.add(key)
    session = LayaSession(timeout_seconds)
    results = []
    async def work():
        deadline = time.monotonic() + session.timeout_seconds
        for start in range(0, len(selected), MAX_ITEMS):
            if stop and stop.is_set(): break
            remaining = deadline - time.monotonic()
            if remaining <= 0: break
            session.timeout_seconds = remaining
            batch = selected[start:start + MAX_ITEMS]
            replies = await session.analyze([s['text'][:4000] for s in batch])
            if len(replies) != len(batch): raise ValueError('Laya 결과 개수 오류')
            results.extend(replies)
            emit({'kind': 'phase', 'stage': 'laya', 'action': 'progress',
                  'message': f'Laya 문맥 검토 {len(results)}/{len(selected)}개'})
            # A missing model or exhausted worker should not be retried for
            # every remaining batch. Completed earlier batches remain usable.
            if all(r.get('status') != 'completed' for r in replies): break
        return results
    task = asyncio.create_task(work())
    try:
        while not task.done():
            if stop and stop.is_set():
                task.cancel()
                break
            await asyncio.wait({task}, timeout=.1)
        if not task.cancelled(): await task
    except asyncio.CancelledError:
        if not (stop and stop.is_set()): raise
    except Exception:
        results.extend(unavailable('inference_failed') for _ in selected[len(results):])
    finally:
        if not task.done(): task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await session.close()
    by_text = {s['text'][:4000]: r for s, r in zip(selected, results)}
    remaining_reason = 'budget_or_cancelled' if stop and stop.is_set() else 'time_budget'
    if results and all(r.get('status') != 'completed' for r in results[-MAX_ITEMS:]):
        remaining_reason = results[-1].get('reason', remaining_reason)
    for source in sources:
        source.setdefault('local_ai', {})['laya'] = (by_text.get(source.get('text','')[:4000], unavailable(remaining_reason))
            if has_review_context(source) else unavailable('insufficient_scope'))
    completed = sum(r['status'] == 'completed' for r in results)
    omitted = sum(s['local_ai']['laya']['status'] != 'completed' for s in sources)
    summary = {'status': 'completed' if completed and not omitted else 'partial' if completed else 'unavailable',
               'analyzed': completed, 'unique_selected': len(selected), 'batch_size': MAX_ITEMS,
               'omitted': omitted, 'paid_requests': 0}
    if not completed and results:
        summary['reason'] = results[0].get('reason', 'inference_failed')
    emit({'kind': 'phase', 'stage': 'laya', 'action': 'complete' if completed else 'skipped',
          'message': f'Laya {completed}개 문맥 검토 · 미검토 {omitted}개' if completed else 'Laya 미적용 · 기존 탐지 결과 유지'})
    return summary


async def enrich_laya(report, *, stop=None, emit=lambda _: None, timeout_seconds=MAX_SECONDS, candidates=True):
    from .local_ai import analysis_packets, has_review_context
    packets = analysis_packets(report)
    evidence = [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]
    keys = {(r.get('url'), r.get('scope_location', r.get('location'))) for r in evidence}
    def relevant(packet):
        if not has_review_context(packet): return False
        if packet.get('scope_quality') == 'overlapping' or not packet.get('text','').strip(): return False
        if (packet.get('url'), packet.get('location')) in keys: return True
        if packet.get('scope_quality') == 'semantic' or packet.get('source_kind') == 'image_ocr':
            return len(packet['text'].strip()) >= 8
        if len(packet['text'].strip()) < 12: return False
        # Unknown RF vocabulary is a reason for independent review, not a veto.
        return len(packet['text'].strip()) >= 30
    # Fill detection gaps before spending the remaining budget on known rows.
    def priority(packet):
        score = packet.get('local_ai', {}).get('text', {}).get('score')
        return ((packet.get('url'), packet.get('location')) in keys,
                packet.get('source_kind') != 'image_ocr',
                packet.get('scope_quality') == 'overlapping', abs((.5 if score is None else score)-.5))
    selected = sorted([p for p in packets if relevant(p)], key=priority)
    summary = await review_sources(selected, stop=stop, emit=emit, timeout_seconds=timeout_seconds)
    for packet in packets:
        if not relevant(packet): packet.setdefault('local_ai', {})['laya'] = unavailable('insufficient_scope')
    summary['omitted'] = sum(p['local_ai']['laya']['status'] != 'completed' for p in packets)
    if summary['status'] == 'completed' and summary['omitted']: summary['status'] = 'partial'
    images = {i['id']: i for i in report.get('ocr_images', [])}
    for packet in packets:
        if packet.get('image_id') in images: images[packet['image_id']].setdefault('local_ai', {}).update(packet['local_ai'])
    for row in [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]:
        match = next((p for p in reversed(packets) if p['url'] == row.get('url') and
                      p['location'] == row.get('scope_location', row.get('location'))), None)
        if match: row.setdefault('local_ai', {}).update(match['local_ai'])
    report.setdefault('local_ai', {})['laya'] = summary
    if candidates:
        from .local_ai import add_model_candidates
        add_model_candidates(report, 'laya')
    return summary
