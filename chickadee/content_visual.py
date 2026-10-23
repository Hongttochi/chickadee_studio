"""Offline photo classification, independent of whether OCR found any text."""
import asyncio
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

DATA = Path(__file__).resolve().parent/'data/ai-models/content'
TOPICS = ('sexual_content', 'gambling', 'drugs')
LABELS = {'sexual_content': ('ADULT', '성인물 이미지'), 'gambling': ('GAMBLING', '도박 이미지'),
          'drugs': ('DRUGS', '마약 관련 이미지')}


def model_contract(folder=DATA):
    path = Path(folder)/'manifest.json'
    if not path.is_file(): return None
    if path.stat().st_size > 100_000: raise ValueError('사진 모델 설정 크기 오류')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not value.get('approved_for_app'): return None
    if (value.get('architecture') != 'resnet18' or value.get('num_outputs') != 3
            or tuple(value.get('topics', [])) != TOPICS or value.get('input_shape') != [1,3,224,224]
            or value.get('preprocessing') != 'RGB aspect-preserving pad; ImageNet mean/std'
            or not isinstance(value.get('validation'), dict) or value['validation'].get('passed') is not True):
        raise ValueError('검증된 사진 모델 설정이 필요합니다.')
    for topic in TOPICS:
        threshold = value.get('thresholds', {}).get(topic)
        if type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError('사진 모델 임계값 오류')
    weights = path.with_name('model.pdparams')
    if not weights.is_file() or not 1_000_000 <= weights.stat().st_size <= 100_000_000:
        raise ValueError('사진 모델 파일 누락·크기 오류')
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    if digest != value.get('sha256'): raise ValueError('사진 모델 무결성 오류')
    return value


def validate_analysis(value):
    if not isinstance(value,dict) or value.get('status') != 'completed': raise ValueError('사진 분석 미완료')
    if set(value.get('scores',{})) != set(TOPICS) or set(value.get('thresholds',{})) != set(TOPICS):
        raise ValueError('사진 분석 출력 오류')
    for topic in TOPICS:
        score, threshold = value['scores'][topic], value['thresholds'][topic]
        if (type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1
                or type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0<threshold<1):
            raise ValueError('사진 분석 점수 오류')
    for field in ('image_sha256','model_sha256'):
        digest=value.get(field)
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('사진 분석 해시 오류')
    if not isinstance(value.get('model'),str) or len(value['model'])>200:raise ValueError('사진 모델 정보 오류')
    return value


def image_candidates(image, analysis):
    validate_analysis(analysis)
    if image.get('interface_image'):
        return []
    from .candidates import analyze_candidate
    from .image_ocr import recognized_text
    text = image.get('text') or recognized_text(image)['text']
    text_categories = {hit['category'] for hit in analyze_candidate(text)}
    # Typed text evidence is already surfaced by the text classifier. A photo
    # score alone does not establish advertising or a harmful topic.
    if text_categories:
        return []
    topics = [topic for topic in TOPICS if analysis['scores'][topic] >= analysis['thresholds'][topic]]
    if not topics:
        return []
    return [{'url':image['url'], 'location':image['location'], 'scope_location':image['location'],
             'category':'IMAGE_REVIEW', 'source_kind':'image_visual', 'image_id':image['id'],
             'evidence_text':text or '문자 근거 없는 이미지 · 검토 필요',
             'visual_topics':topics, 'matched_keywords':[], 'review_required':True,
             'reasons':['사진 모델의 단독 신호로 남긴 이미지 검토 항목입니다.',
                        '광고 여부와 도박·성인·마약 주제는 확인되지 않았습니다.'],
             'local_ai':{'content_visual':analysis}}]


class ContentSession:
    def __init__(self): self.process=None; self.stderr=None

    async def recognize(self,data,timeout=25):
        if len(data)>2_000_000: raise ValueError('사진 파일 크기 한도')
        if self.process is None:
            args=[sys.executable,'--content-worker'] if getattr(sys,'frozen',False) else [sys.executable,'-m','chickadee.content_worker']
            self.process=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,limit=50_000,
                cwd=str(Path(__file__).resolve().parents[1]),env={**os.environ,'PYTHONIOENCODING':'utf-8','CPU_NUM':'2'},
                **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
            async def drain():
                while await self.process.stderr.read(4096): pass
            self.stderr=asyncio.create_task(drain())
        try:
            self.process.stdin.write((json.dumps({'image':base64.b64encode(data).decode('ascii')})+'\n').encode())
            await self.process.stdin.drain()
            reply=await asyncio.wait_for(self.process.stdout.readline(),timeout)
            result=validate_analysis(json.loads(reply))
            if result['image_sha256']!=hashlib.sha256(data).hexdigest():raise ValueError('사진 분석 응답 불일치')
            return result
        except BaseException:
            await self.close(); raise

    async def close(self):
        if self.process:
            if self.process.returncode is None:self.process.kill()
            await self.process.wait()
            if self.stderr:await self.stderr
            self.process=None


async def enrich_content_images(report, assets, *, candidates=True, timeout_seconds=45, stop=None):
    images=report.get('ocr_images',[])
    summary={'status':'unavailable','analyzed':0,'flagged':0,'failed':0,'paid_requests':0}
    report['content_visual']=summary
    if not images: summary.update(status='skipped',reason='no_images');return
    try: contract=await asyncio.to_thread(model_contract)
    except Exception: summary.update(reason='invalid_model');return
    if contract is None: summary.update(reason='validated_model_not_installed');return
    worker=ContentSession(); cache={};deadline=time.monotonic()+max(0,timeout_seconds)
    rows=report.setdefault('ad_candidates',[])
    number=max((int(r['id'][2:]) for r in rows if r.get('id','').startswith('c_') and r['id'][2:].isdigit()),default=0)+1
    summary['status']='completed'
    try:
        for image in images:
            if stop is not None and stop.is_set():summary['status']='cancelled';break
            if time.monotonic()>=deadline:summary['status']='partial';break
            path=image.get('relative_path');data=assets.get(path)
            if not data:continue
            digest=hashlib.sha256(data).hexdigest()
            if digest!=image.get('image_sha256'):summary['failed']+=1;summary['status']='partial';continue
            try:
                if digest not in cache:
                    cache[digest]=await worker.recognize(data,timeout=min(25,max(.01,deadline-time.monotonic())))
                    summary['analyzed']+=1
                analysis=cache[digest]
                image.setdefault('local_ai',{})['content_visual']=analysis
                signals=image_candidates(image,analysis)
                summary['flagged']+=bool(signals)
                if candidates:
                    for row in signals:
                        if any(r.get('source_kind') == 'image_visual' and
                               r.get('local_ai', {}).get('content_visual', {}).get('image_sha256') == digest for r in rows):
                            continue
                        match=next((r for r in rows if r['url']==row['url'] and r.get('image_id')==row['image_id'] and r['category']==row['category']),None)
                        if match:match.setdefault('local_ai',{})['content_visual']=analysis
                        else:rows.append({'id':f'c_{number:05d}',**row});number+=1
            except (ValueError,OSError,asyncio.TimeoutError):
                summary['failed']+=1;summary['status']='partial'
    finally:await worker.close()


async def analyze_photo(data,timeout_seconds=25):
    try:contract=await asyncio.to_thread(model_contract)
    except Exception:return {'status':'unavailable','message':'사진 모델 검증 실패'}
    if contract is None:return {'status':'unavailable','message':'검증된 사진 모델 미설치'}
    worker=ContentSession()
    try:return await worker.recognize(data,timeout_seconds)
    except (ValueError,OSError,asyncio.TimeoutError):return {'status':'unavailable','message':'사진 분류 처리 실패'}
    finally:await worker.close()
