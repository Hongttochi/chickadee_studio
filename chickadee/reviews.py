"""Human/agent review sidecar; never changes detector evidence or evaluation JSON."""
from datetime import datetime
import json
from pathlib import Path

from .exports import atomic_write

STATES = {'unreviewed', 'confirmed', 'dismissed'}


class ReviewStore:
    def __init__(self, result_path, outcome):
        self.path = Path(result_path).with_name('review.json')
        self.ids = {r['id'] for r in [*outcome.result['findings'], *outcome.report.get('ad_candidates', [])]}
        self.digest = outcome.report.get('result_sha256')
        if not self.digest:
            import hashlib
            self.digest = hashlib.sha256(Path(result_path).read_bytes()).hexdigest()
        self.data = {'version': 1, 'result_sha256': self.digest, 'revision': 0, 'items': {}, 'audit': []}
        if self.path.exists():
            if self.path.stat().st_size > 5_000_000:
                raise ValueError('검토 파일은 5MB 이하여야 합니다.')
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value.get('version') != 1 or value.get('result_sha256') != self.digest:
                raise ValueError('검토 기록과 검사 결과가 일치하지 않습니다.')
            items, audit = value.get('items'), value.get('audit')
            if type(value.get('revision')) is not int or value['revision'] < 0 or not isinstance(items, dict) or not isinstance(audit, list) or len(audit) > 5000:
                raise ValueError('검토 기록 형식이 올바르지 않습니다.')
            for key, item in items.items():
                if key not in self.ids or not isinstance(item, dict) or item.get('status') not in STATES or not isinstance(item.get('note', ''), str) or len(item.get('note', '')) > 2000:
                    raise ValueError('검토 항목이 올바르지 않습니다.')
            self.data = value

    def update(self, ids, status, note=None, expected_revision=None, actor='human'):
        if not isinstance(ids, list) or not 1 <= len(ids) <= 500 or not all(isinstance(key, str) and key in self.ids for key in ids):
            raise ValueError('현재 결과의 항목을 1~500개 선택하세요.')
        if status not in STATES or actor not in ('human', 'agent'):
            raise ValueError('지원하지 않는 검토 상태입니다.')
        if note is not None and (not isinstance(note, str) or len(note) > 2000):
            raise ValueError('검토 메모는 2000자 이하여야 합니다.')
        if type(expected_revision) is not int or expected_revision != self.data['revision']:
            raise ValueError('검토 기록이 변경되었습니다. 결과를 다시 불러온 뒤 저장하세요.')
        now = datetime.now().astimezone().isoformat()
        items = dict(self.data['items'])
        changes = []
        for key in dict.fromkeys(ids):
            previous = items.get(key, {})
            items[key] = {'status': status, 'note': previous.get('note', '') if note is None else note,
                          'actor': actor, 'updated_at': now}
            changes.append({'id': key, 'from': previous.get('status', 'unreviewed'), 'to': status})
        audit = [*self.data['audit'], {'actor': actor, 'at': now, 'changes': changes}][-5000:]
        value = {**self.data, 'revision': self.data['revision'] + 1, 'items': items, 'audit': audit}
        payload = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
        if len(payload) > 5_000_000:
            raise ValueError('검토 기록 크기 한도에 도달했습니다.')
        atomic_write(self.path, payload)
        self.data = value
        return self.data
