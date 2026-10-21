"""Bounded, inert evidence snapshots and an observed exploration graph."""
from copy import deepcopy
from datetime import datetime
import base64
import hashlib
import json
import math
import re


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def comparable_style(style):
    if not isinstance(style, dict):
        return None
    # Viewport scrolling is not a content or hiding change.
    return {k: style.get(k) for k in ('color', 'background', 'effective_opacity', 'font_size',
             'display', 'visibility', 'position', 'document_rect', 'hiding_ancestors')}


class InspectionTrace:
    MAX_PACKETS = 1000
    MAX_STATES = 3000
    MAX_PACKET_BYTES = 6_000_000

    def __init__(self):
        self.nodes, self.edges, self.packets = {}, {}, {}
        self.last_state = {}
        self.active = None
        self.truncated = False
        self.packet_bytes = 0

    def page(self, url, status, emit, parent=None):
        key = 'p_' + fingerprint(url)[:20]
        self.nodes[key] = {**self.nodes.get(key, {}), 'id': key, 'kind': 'page', 'url': url,
                           'label': url, 'status': status}
        edge = None
        if parent:
            source = 'p_' + fingerprint(parent)[:20]
            if source in self.nodes and source != key:
                edge = {'id': source + ':' + key, 'source': source, 'target': key, 'label': '링크 발견'}
                self.edges[edge['id']] = edge
        emit({'kind': 'exploration', 'node': deepcopy(self.nodes[key]), 'edge': edge})
        return key

    def snapshot(self, url, signature, action, emit):
        if sum(n['kind'] == 'state' for n in self.nodes.values()) >= self.MAX_STATES:
            self.truncated = True
            self.active = None
            return
        page = self.page(url, 'inspecting', emit)
        key = 's_' + fingerprint([url, signature, len(self.nodes)])[:20]
        self.nodes[key] = {'id': key, 'kind': 'state', 'url': url, 'label': action,
                           'status': 'observed', 'packet_ids': [], 'observed_at': datetime.now().astimezone().isoformat()}
        source = self.last_state.get(url, page)
        edge = {'id': source + ':' + key, 'source': source, 'target': key, 'label': action}
        self.edges[edge['id']] = edge
        self.last_state[url] = self.active = key
        emit({'kind': 'exploration', 'node': deepcopy(self.nodes[key]), 'edge': edge})

    def capture(self, elements, url, frame_path, emit, inherited=None):
        inherited = inherited or {}
        frame_node = None
        if frame_path and self.active:
            frame_node = 'r_' + fingerprint([self.active, frame_path])[:20]
            self.nodes[frame_node] = {'id': frame_node, 'kind': 'frame', 'url': url,
                                     'label': 'iframe · ' + frame_path, 'status': 'observed', 'packet_ids': []}
            edge = {'id': self.active + ':' + frame_node, 'source': self.active, 'target': frame_node, 'label': 'frame 수집'}
            self.edges[edge['id']] = edge
            emit({'kind': 'exploration', 'node': deepcopy(self.nodes[frame_node]), 'edge': edge})
        by_location = {e['location']: e for e in elements}
        selected = {}
        for element in elements:
            scope = element.get('content_scope')
            if scope or element.get('direct_text', '').strip():
                selected[scope or element['location']] = by_location.get(scope, element)
        for location, element in selected.items():
            text = element['text'][:4000]
            style = element.get('computed_style')
            identity = fingerprint([url, frame_path, location])
            link_targets = element.get('link_targets', [])[:20]
            content_hash = fingerprint([text, comparable_style(style), link_targets, inherited])
            key = 'e_' + fingerprint([identity, content_hash])[:24]
            if key not in self.packets and len(self.packets) >= self.MAX_PACKETS:
                self.truncated = True
                continue
            if key not in self.packets:
                self.packets[key] = {
                    'id': key, 'identity': identity, 'url': url, 'frame_path': frame_path,
                    'location': location, 'text': text, 'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'link_targets': link_targets,
                    'content_sha256': content_hash, 'computed_style': deepcopy(style),
                    'transparent': element.get('transparent') or inherited.get('transparent', False) if style is not None else None,
                    'offscreen': element.get('offscreen') or inherited.get('offscreen', False) if style is not None else None,
                    'frame_flags': deepcopy(inherited),
                    'style_reasons': element.get('reasons', []), 'text_breaks': element.get('text_breaks', []),
                    'scope_quality': 'overlapping' if element.get('nested_content_scopes') else
                                     'semantic' if element.get('content_scope') else 'element',
                    'truncated': len(element['text']) > len(text),
                    'missing_evidence': ([] if style is not None else ['computed_style']) +
                                        (['isolated_scope_context'] if element.get('nested_content_scopes') else []),
                    'snapshot_id': self.active, 'observed_at': datetime.now().astimezone().isoformat(),
                    'source_kind': element.get('source_kind', 'dom_text'), 'image_id': element.get('image_id'),
                }
                size = len(json.dumps(self.packets[key], ensure_ascii=False).encode('utf-8'))
                if self.packet_bytes + size > self.MAX_PACKET_BYTES:
                    self.packets.pop(key)
                    self.truncated = True
                    continue
                self.packet_bytes += size
            # Keep latest observation order, including changes reverted to a
            # previously seen value, without duplicating identical packets.
            self.packets[key] = self.packets.pop(key)
            self.packets[key]['last_snapshot_id'] = self.active
            self.packets[key]['last_observed_at'] = datetime.now().astimezone().isoformat()
            if self.active and key not in self.nodes[self.active]['packet_ids']:
                self.nodes[self.active]['packet_ids'].append(key)
            if frame_node:
                self.nodes[frame_node]['packet_ids'].append(key)
        if self.active:
            emit({'kind': 'exploration', 'node': deepcopy(self.nodes[self.active]), 'edge': None})
        if frame_node:
            emit({'kind': 'exploration', 'node': deepcopy(self.nodes[frame_node]), 'edge': None})

    def export(self):
        return {'version': 1, 'nodes': list(self.nodes.values()), 'edges': list(self.edges.values()),
                'truncated': self.truncated, 'packet_limit': self.MAX_PACKETS, 'packet_byte_limit': self.MAX_PACKET_BYTES}


def validate_inspection(report):
    """Legacy reports are accepted; malformed new feature data is rejected."""
    validate_screenshots(report.get('screenshots', {}))
    validate_ocr_images(report.get('ocr_images', []))
    for row in [*report.get('ad_candidates', []), *report.get('evidence_details', {}).values()]:
        validate_local_ai(row.get('local_ai'))
    packets = report.get('evidence_packets', [])
    if not isinstance(packets, list) or len(packets) > InspectionTrace.MAX_PACKETS:
        raise ValueError('수집 영역 목록 형식 오류')
    seen = set()
    for packet in packets:
        if not isinstance(packet, dict) or not all(isinstance(packet.get(k), str) and packet[k]
                for k in ('id', 'identity', 'url', 'location', 'text', 'text_sha256', 'content_sha256')):
            raise ValueError('수집 영역 필수 필드 오류')
        if packet['id'] in seen or len(packet['text']) > 4000 or not isinstance(packet.get('computed_style'), (dict, type(None))):
            raise ValueError('수집 영역 중복·크기·스타일 오류')
        if not isinstance(packet.get('link_targets', []), list) or not all(isinstance(url, str) for url in packet.get('link_targets', [])):
            raise ValueError('영역 링크 형식 오류')
        seen.add(packet['id'])
        validate_local_ai(packet.get('local_ai'))
    graph = report.get('exploration', {'nodes': [], 'edges': []})
    if not isinstance(graph, dict) or any(not isinstance(graph.get(k), list) for k in ('nodes', 'edges')):
        raise ValueError('탐색 그래프 형식 오류')
    if len(graph['nodes']) > 50000 or len(graph['edges']) > 100000:
        raise ValueError('탐색 그래프 크기 한도')
    nodes = set()
    for node in graph['nodes']:
        if not isinstance(node, dict) or not all(isinstance(node.get(k), str) for k in ('id', 'kind', 'url', 'label', 'status')):
            raise ValueError('탐색 노드 형식 오류')
        packet_ids = node.get('packet_ids', [])
        if node['id'] in nodes or not isinstance(packet_ids, list) or not all(isinstance(p, str) for p in packet_ids) or not set(packet_ids) <= seen:
            raise ValueError('탐색 노드 근거 ID 오류')
        nodes.add(node['id'])
    for edge in graph['edges']:
        if not isinstance(edge, dict) or not all(isinstance(edge.get(k), str) for k in ('id', 'source', 'target')) or edge['source'] not in nodes or edge['target'] not in nodes:
            raise ValueError('탐색 연결 형식 오류')


def validate_local_ai(value):
    if value is None: return
    if not isinstance(value, dict) or set(value) - {'text', 'visual'}: raise ValueError('AI 분석 형식 오류')
    for signal in value.values():
        if not isinstance(signal, dict) or signal.get('status') not in ('completed', 'unavailable'):
            raise ValueError('AI 분석 상태 오류')
        score = signal.get('score')
        if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('AI 모델 점수 오류')
        if signal.get('status') == 'completed':
            if signal.get('label') not in ('ad_context', 'phishing_pattern', 'review', 'no_features'):
                raise ValueError('AI 분류 오류')
            if not all(isinstance(signal.get(k), str) and len(signal[k]) < 200 for k in ('model', 'version', 'score_kind')):
                raise ValueError('AI 모델 정보 오류')
        features = signal.get('matched_features', [])
        if not isinstance(features, list) or len(features) > 6 or any(not isinstance(s, str) or len(s) > 4 for s in features):
            raise ValueError('AI 일치 특징 오류')


def validate_screenshots(screenshots):
    if not isinstance(screenshots, dict) or len(screenshots) > 24:
        raise ValueError('근거 화면 목록 형식 오류')
    size = 0
    for value in screenshots.values():
        if isinstance(value, dict): validate_local_ai(value.get('local_ai'))
        if not isinstance(value, dict) or not isinstance(value.get('data_url'), str) or not value['data_url'].startswith('data:image/jpeg;base64,'):
            raise ValueError('근거 화면은 내장 JPEG만 허용합니다.')
        try:
            pixels = base64.b64decode(value['data_url'].split(',', 1)[1], validate=True)
        except ValueError:
            raise ValueError('근거 화면 인코딩 오류') from None
        size += len(pixels)
        if len(pixels) > 200_000 or not pixels.startswith(b'\xff\xd8\xff') or hashlib.sha256(pixels).hexdigest() != value.get('sha256'):
            raise ValueError('근거 화면 크기·해시 오류')
    if size > 3_000_000:
        raise ValueError('근거 화면 총 크기 초과')


def validate_ocr_images(images):
    if not isinstance(images, list) or len(images) > 50:
        raise ValueError('OCR 이미지 목록 형식 오류')
    ids, preview_size = set(), 0
    for item in images:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in ids:
            raise ValueError('OCR 이미지 ID 오류')
        ids.add(item['id'])
        if item.get('status') not in ('completed', 'failed'):
            raise ValueError('OCR 처리 상태 오류')
        lines = item.get('lines', [])
        if not isinstance(lines, list) or len(lines) > 80:
            raise ValueError('OCR 문구 목록 오류')
        if item['status'] != 'completed':
            continue
        w, h = item.get('width'), item.get('height')
        if type(w) is not int or type(h) is not int or min(w, h) < 8 or w * h > 8_000_000:
            raise ValueError('OCR 이미지 크기 오류')
        digest = item.get('image_sha256', '')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('OCR 원본 해시 오류')
        if not re.fullmatch(r'evidence/images/' + digest + r'\.(png|jpg|webp|gif)', item.get('relative_path', '')):
            raise ValueError('OCR 원본 경로 오류')
        for line in lines:
            if not isinstance(line, dict) or not isinstance(line.get('text'), str) or len(line['text']) > 1000:
                raise ValueError('OCR 문구 오류')
            confidence, box = line.get('confidence'), line.get('box')
            if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError('OCR 신뢰도 오류')
            if not isinstance(box, list) or len(box) != 4 or any(
                not isinstance(point, list) or len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in point)
                or not (0 <= point[0] <= w and 0 <= point[1] <= h) for point in box):
                raise ValueError('OCR 좌표 오류')
        if 'preview_data_url' in item:
            validate_screenshots({'image': {'data_url': item['preview_data_url'], 'sha256': item.get('preview_sha256')}})
            preview_size += len(item['preview_data_url'])
    if preview_size > 3_000_000:
        raise ValueError('OCR 미리보기 총 크기 초과')
