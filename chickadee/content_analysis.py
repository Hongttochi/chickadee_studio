"""Direct text/image analysis; offline computation, no filesystem or URL inputs."""
import asyncio
from datetime import datetime
import hashlib

from .candidates import analyze_candidate
from .detection import analyze
from .image_ocr import OCRSession, inline_image, recognized_text
from .local_ai import prepare_models, text_analysis, visual_analysis


def inputs(params):
    if not isinstance(params, dict) or set(params) - {'text', 'image_data_url'}:
        raise ValueError('text 또는 image_data_url만 입력하세요.')
    text, image = params.get('text', ''), params.get('image_data_url')
    if not isinstance(text, str) or len(text) > 4000:
        raise ValueError('입력 텍스트는 4,000자 이하여야 합니다.')
    if image is not None and (not isinstance(image, str) or not image or len(image) > 900000):
        raise ValueError('이미지는 900,000자 이하의 PNG/JPEG/WebP/GIF data URL이어야 합니다.')
    if not text.strip() and image is None: raise ValueError('분석할 텍스트 또는 이미지가 필요합니다.')
    return text, inline_image(image)[0] if image is not None else None


def text_result(text, kind):
    try: local = dict(text_analysis(text))
    except Exception: local = {'status': 'unavailable', 'message': '로컬 문자 모델을 불러오지 못했습니다.'}
    return {'source_kind': kind, 'text': text, 'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'unicode_analysis': analyze(text), 'ad_candidates': analyze_candidate(text),
            'local_ai': {'text': local}, 'original_unicode_observed': kind == 'provided_text'}


async def analyze_content(text, pixels, runtime, stop, progress=lambda _: None):
    """Keep typed text and OCR observations separate, even when submitted together."""
    worker = OCRSession()
    async def work():
        sources, errors = [], []
        progress('models')
        try: await asyncio.to_thread(prepare_models)
        except Exception: errors.append('로컬 AI 모델 준비 실패')
        if text.strip(): sources.append(await asyncio.to_thread(text_result, text, 'provided_text'))
        image = None
        if pixels is not None:
            progress('image')
            image = {'image_sha256': hashlib.sha256(pixels).hexdigest(), 'input_scope': 'provided_image'}
            try:
                image['local_ai'] = {'visual': await asyncio.to_thread(visual_analysis, pixels)}
            except Exception:
                image['local_ai'] = {'visual': {'status': 'unavailable', 'message': '지원하지 않거나 손상된 이미지입니다.'}}
                errors.append('이미지 특징 분석 실패')
            if not runtime['features']['ocr_enabled']:
                image['ocr'] = {'status': 'skipped', 'reason': 'economy' if runtime['effective_mode'] == 'economy' else 'unavailable'}
            else:
                progress('ocr')
                try: result = await worker.recognize(pixels)
                except Exception: result = {'status': 'failed', 'message': 'OCR 프로세스 처리 실패'}
                image['ocr'] = result
                if result['status'] == 'completed':
                    observation = recognized_text(result)
                    image['ocr'].update(observation)
                    source = await asyncio.to_thread(text_result, observation['text'], 'image_ocr')
                    source['truncated'] = observation['text_truncated']
                    source['ocr'] = {k: v for k, v in observation.items() if k != 'text'}
                    source['local_ai'].update(image['local_ai'])
                    sources.append(source)
                else: errors.append('PaddleOCR 이미지 문자 인식 실패')
        if any(source['local_ai']['text']['status'] != 'completed' for source in sources): errors.append('로컬 문자 모델 분석 미완료')
        return {'status': 'partial' if errors or image and image['ocr']['status'] != 'completed' else 'completed',
                'sources': sources, 'image': image, 'errors': errors, 'runtime_environment': runtime,
                'finished_at': datetime.now().astimezone().isoformat(), 'paid_requests': 0,
                'candidate_count': sum(len(source['ad_candidates']) for source in sources)}
    task = asyncio.create_task(work())
    try:
        async with asyncio.timeout(60):
            while not task.done():
                if stop.is_set(): raise asyncio.CancelledError()
                await asyncio.wait({task}, timeout=.1)
            return await task
    finally:
        if not task.done(): task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await worker.close()
