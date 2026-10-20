"""Bounded, inert evidence snapshots and an observed exploration graph."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json


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
                    'scope_quality': 'semantic' if element.get('content_scope') else 'element',
                    'truncated': len(element['text']) > len(text),
                    'missing_evidence': ([] if style is not None else ['computed_style']),
                    'snapshot_id': self.active, 'observed_at': datetime.now().astimezone().isoformat(),
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


def compare_reports(previous, current):
    """Same URL/frame/selector identity; absence is not proof of removal."""
    def latest(report):
        return {p['identity']: p for p in report.get('evidence_packets', [])}
    before, after = latest(previous), latest(current)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        a, b = before.get(key), after.get(key)
        status = ('newly_observed' if a is None else 'not_observed' if b is None else
                  'changed' if a['content_sha256'] != b['content_sha256'] else 'unchanged')
        changes.append({'identity': key, 'status': status, 'before': a, 'after': b})
    counts = {status: sum(c['status'] == status for c in changes)
              for status in ('newly_observed', 'changed', 'not_observed', 'unchanged')}
    complete = previous.get('status') == current.get('status') == 'completed' and not any(
        r.get('exploration', {}).get('truncated') for r in (previous, current))
    return {'version': 1, 'matching': 'exact URL + frame path + selector; changed selectors may appear as two entries',
            'coverage_complete': complete, 'counts': counts, 'changes': changes,
            'warning': '미관측은 삭제 확정이 아닙니다. 탐색 범위·상태·선택자가 달라질 수 있습니다.'}
