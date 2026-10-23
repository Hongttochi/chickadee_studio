"""Offline inference from hash-pinned, inert JSON trees exported from our GPU job.

No pickle loader, training runtime, network client or paid API is used here.
Model outputs prioritize evidence review; they do not replace observed findings.
"""
from collections import Counter
from array import array
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import re
import unicodedata
from .ad_context import commercial_support

DATA = Path(__file__).resolve().parent / 'data'


def prepare_models():
    """Load native inference libraries before a page's collection deadline starts."""
    from PIL import Image
    Image.preinit()
    model('text'); model('visual')
    visual_features(Image.new('RGB', (8, 8)))


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    text = re.sub(r'\[(?:redacted|삭제|마스킹)[^\]]*\]', ' ', text, flags=re.I)
    return ' '.join(text.split())


@lru_cache(maxsize=2)
def model(kind):
    if kind not in ('text', 'visual'): raise ValueError('지원하지 않는 로컬 모델')
    manifest = json.loads((DATA / 'ai-models.json').read_text(encoding='utf-8'))
    item = next(item for item in manifest['files'] if item['kind'] == kind)
    if item['path'] != kind + '.json': raise ValueError('AI 모델 경로 오류')
    data = (DATA / 'ai-models' / item['path']).read_bytes()
    if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('AI 모델 무결성 확인 실패')
    value = json.loads(data)
    if value['format'] != 1 or not 1 <= len(value['trees']) <= 300:
        raise ValueError('AI 모델 형식 오류')
    return value


def probability(forest, vector):
    vector = array('f', vector)
    if len(vector) != forest['dimensions'] or not all(math.isfinite(v) for v in vector):
        raise ValueError('AI 입력 특징 오류')
    total = 0.
    for tree in forest['trees']:
        node = 0
        for _ in range(len(tree['left'])):
            left = tree['left'][node]
            if left == -1:
                total += tree['positive'][node]; break
            node = left if float(vector[tree['feature'][node]]) <= tree['threshold'][node] else tree['right'][node]
        else: raise ValueError('AI 모델 트리 오류')
    return total / len(forest['trees'])


@lru_cache(maxsize=2048)
def text_analysis(text):
    forest = model('text')
    text = normalize(text[:4000])
    counts = Counter(text[i:i+n] for n in (2, 3, 4) for i in range(max(0, len(text)-n+1)))
    vocabulary = forest['vocabulary']
    hits = [(token, count, vocabulary[token]) for token, count in counts.items() if token in vocabulary]
    vector = [0.] * forest['dimensions']
    for _, count, index in hits: vector[index] = count * forest['idf'][index]
    norm = math.sqrt(sum(v*v for v in vector))
    if norm: vector = [v / norm for v in vector]
    score = probability(forest, vector) if norm else None
    priority = score is not None and score >= .65 and len(hits) >= 3
    return {'status': 'completed', 'model': '문자 TF-IDF · Random Forest', 'version': forest['version'],
            'score': round(score, 6) if score is not None else None, 'score_kind': 'uncalibrated_model_score',
            'label': 'ad_context' if priority else 'review' if hits else 'no_features',
            'matched_features': [token for token, _, index in sorted(hits, key=lambda h: vector[h[2]], reverse=True)[:6]],
            'feature_count': len(hits), 'review_priority': 'high' if priority else 'standard'}


def visual_features(image):
    from PIL import Image
    # Preserve the training float32 operations using the stdlib array type.
    # Avoid importing a large BLAS runtime in the desktop scan thread.
    def f32(value): return array('f', [value])[0]
    pixels = image.convert('RGB').resize((64, 64), Image.Resampling.BILINEAR).tobytes()
    histogram = [0.] * 48
    grey = []
    for i in range(0, len(pixels), 3):
        channels = pixels[i:i+3]
        for c, value in enumerate(channels): histogram[c*16 + min(15, value*16//255)] += 1/4096
        r, g, b = [f32(value/255) for value in channels]
        grey.append(f32(f32(f32(r+g)+b)/3))
    magnitudes, bins = [], []
    pi = f32(math.pi)
    for y in range(64):
        for x in range(64):
            gx = f32(grey[y*64+min(63,x+1)] - grey[y*64+max(0,x-1)])
            gy = f32(grey[min(63,y+1)*64+x] - grey[max(0,y-1)*64+x])
            if 0 < x < 63: gx = f32(gx/2)
            if 0 < y < 63: gy = f32(gy/2)
            magnitudes.append(f32(math.hypot(gx, gy)))
            angle = f32(f32(math.atan2(gy, gx)) % pi)
            bins.append(min(8, int(f32(f32(angle*9)/pi))))
    gradient = []
    for y in range(0, 64, 8):
        for x in range(0, 64, 8):
            weights = [0.] * 9
            for row in range(y, y+8):
                for col in range(x, x+8):
                    i = row*64+col; weights[bins[i]] += magnitudes[i]
            norm = math.sqrt(sum(v*v for v in weights)) + 1e-6
            gradient.extend(v/norm for v in weights)
    return array('f', [*histogram, *gradient])


def visual_analysis(pixels):
    from PIL import Image
    forest = model('visual')
    with Image.open(io.BytesIO(pixels)) as image:
        if image.width * image.height > 8_000_000: raise ValueError('AI 화면 크기 한도')
        score = probability(forest, visual_features(image))
    return {'status': 'completed', 'model': '화면 특징 · Random Forest', 'version': forest['version'],
            'score': round(score, 6), 'score_kind': 'uncalibrated_model_score',
            'label': 'phishing_pattern' if score >= .5 else 'review',
            'review_priority': 'high' if score >= .5 else 'standard'}


def has_review_context(source):
    text = source.get('text', '')
    return (source.get('source_kind') != 'image_ocr' or
            (len(text.strip()) >= 8 and sum(c.isalnum() for c in text) >= 4))


def analysis_packets(report):
    """Review retained OCR even when the bounded exploration trace is full.

    Supplemental scopes reference image observations; they do not expand or
    mutate the persisted exploration graph and its packet limit.
    """
    packets = list(report.get('evidence_packets', []))
    image_ids = {p.get('image_id') for p in packets if p.get('source_kind') == 'image_ocr'}
    for image in report.get('ocr_images', []):
        if image.get('id') in image_ids:
            continue
        from .image_ocr import recognized_text
        text = image.get('text') or recognized_text(image)['text']
        if not text.strip():
            continue
        packets.append({'url': image['url'], 'location': image['location'], 'text': text[:4000],
                        'source_kind': 'image_ocr', 'image_id': image['id'], 'scope_quality': 'element',
                        'source_role': image.get('source_role'),
                        'local_ai': image.setdefault('local_ai', {})})
        image_ids.add(image['id'])
    return packets


def add_model_candidates(report, kind):
    """Surface positive model observations as review rows, preserving typed hits."""
    from .detection import is_editorial_context
    rows = report.setdefault('ad_candidates', [])
    number = max((int(r['id'][2:]) for r in rows if r.get('id', '').startswith('c_') and r['id'][2:].isdigit()), default=0) + 1
    existing = {(r.get('url'), r.get('scope_location', r.get('location')))
                for r in [*rows, *report.get('evidence_details', {}).values()]
                if r.get('category') != 'IMAGE_REVIEW'}
    for packet in analysis_packets(report):
        signal = packet.get('local_ai', {}).get(kind, {})
        key = packet['url'], packet['location']
        if (signal.get('status') != 'completed' or signal.get('label') != 'ad_context'
                or signal.get('review_priority') != 'high' or key in existing
                or not has_review_context(packet)
                or not commercial_support(packet['text'])
                or packet.get('scope_quality') == 'overlapping' or is_editorial_context(packet['text'])):
            continue
        snapshot = packet.get('last_snapshot_id') or packet.get('snapshot_id')
        neutral = next((r for r in rows if r.get('category') == 'IMAGE_REVIEW' and
                        (r.get('url'), r.get('scope_location', r.get('location'))) == key), None)
        if neutral:
            rows.remove(neutral)
        rows.append({'id': neutral['id'] if neutral else f'c_{number:05d}', 'url': packet['url'], 'location': packet['location'],
                     'scope_location': packet['location'], 'evidence_text': packet['text'],
                     'category': 'AI_CONTEXT', 'review_required': True, 'matched_keywords': [],
                     'reasons': ['문맥 모델에서 광고·상업적 홍보 신호를 확인했습니다. 일반 광고를 포함한 검토 후보입니다.'],
                     'source_kind': packet.get('source_kind', 'dom_text'), 'image_id': packet.get('image_id'),
                     'source_role': packet.get('source_role'),
                     'screenshot_id': snapshot, 'local_ai': packet['local_ai'],
                     'observed_at': packet.get('observed_at')})
        existing.add(key)
        number += 1


def enrich_report(report, *, candidates=True):
    """Attach reproducible ML observations to packets and existing evidence rows."""
    packets = analysis_packets(report)
    analyzed, priority = 0, 0
    images = {image['id']: image for image in report.get('ocr_images', [])}
    screens = report.get('screenshots', {})
    used_ids = {row['id'] for row in report.get('ad_candidates', [])}
    candidate_number = max((int(value[2:]) for value in used_ids if value.startswith('c_') and value[2:].isdigit()), default=0) + 1
    for packet in packets:
        try: text = dict(text_analysis(packet['text']))
        except Exception:
            text = {'status': 'unavailable', 'message': '로컬 문자 모델을 불러오지 못했습니다.'}
        snapshot = packet.get('last_snapshot_id') or packet.get('snapshot_id')
        packet['local_ai'] = {'text': text}
        visual = screens.get(snapshot, {}).get('local_ai', {}).get('visual')
        if visual: packet['local_ai']['visual'] = visual
        if packet.get('image_id') in images: images[packet['image_id']]['local_ai'] = packet['local_ai']
        analyzed += text.get('status') == 'completed'
        priority += text.get('review_priority') == 'high'
        if (candidates and text.get('review_priority') == 'high' and has_review_context(packet)
                and commercial_support(packet['text']) and packet.get('scope_quality') != 'overlapping'
                and not any(c.get('url') == packet['url'] and c.get('scope_location', c.get('location')) == packet['location']
                            for c in [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()])):
            from .detection import is_editorial_context
            if not is_editorial_context(packet['text']):
                report.setdefault('ad_candidates', []).append({
                    'id': f"c_{candidate_number:05d}", 'url': packet['url'],
                    'location': packet['location'], 'scope_location': packet['location'], 'evidence_text': packet['text'],
                    'category': 'AI_CONTEXT', 'review_required': True, 'matched_keywords': [],
                    'reasons': ['학습한 문자 문맥 모델에서 광고 유사 문맥을 분류했습니다.'],
                    'source_kind': packet.get('source_kind', 'dom_text'), 'image_id': packet.get('image_id'),
                    'source_role': packet.get('source_role'),
                    'screenshot_id': snapshot, 'local_ai': packet['local_ai'], 'observed_at': packet.get('observed_at')})
                candidate_number += 1
    for row in [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]:
        match = next((p for p in reversed(packets) if p['url'] == row.get('url') and
                      p['location'] == row.get('scope_location', row.get('location'))), None)
        if match: row['local_ai'] = match['local_ai']
    report['local_ai'] = {'status': 'completed' if analyzed == len(packets) else 'partial',
                          'text_analyzed': analyzed, 'text_priority': priority,
                          'visual_analyzed': sum(s.get('local_ai', {}).get('visual', {}).get('status') == 'completed' for s in screens.values()),
                          'paid_requests': 0, 'version': 'jpushare-v2'}
