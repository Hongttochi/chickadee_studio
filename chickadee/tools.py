"""Versioned local tool contract shared by desktop and future agent adapters."""
from copy import deepcopy
from jsonschema import Draft202012Validator


def schema(properties=None, required=()):
    return {'type': 'object', 'properties': properties or {}, 'required': list(required), 'additionalProperties': False}


RUN = {'run_id': {'type': 'string', 'minLength': 1, 'maxLength': 100}}
REVIEW = {**RUN, 'ids': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 500},
          'status': {'enum': ['unreviewed', 'confirmed', 'dismissed']},
          'note': {'type': 'string', 'maxLength': 2000}, 'expected_revision': {'type': 'integer', 'minimum': 0}}
CATALOG = [
    {'name': 'runtime.info', 'method': 'runtime-info', 'effect': 'read',
     'description': '현재 실행 환경과 사용 가능한 분석 기능을 조회합니다.', 'input_schema': schema()},
    {'name': 'runtime.configure', 'method': 'runtime-configure', 'effect': 'local_write',
     'description': '다음 검사에 사용할 자동·표준·절약 모드를 저장합니다.',
     'input_schema': schema({'mode': {'enum': ['auto', 'standard', 'economy']}}, ['mode'])},
    {'name': 'inspection.read', 'method': 'inspection', 'effect': 'read',
     'description': '현재 실행의 탐색 그래프·수집 영역·AI 검토를 조회합니다.', 'input_schema': schema(RUN, ['run_id'])},
    {'name': 'agent.status', 'method': 'agent-status', 'effect': 'read',
     'description': 'Groq 설정 여부·누적 사용량·검토 제안을 조회합니다.', 'input_schema': schema()},
    {'name': 'scan.start', 'method': 'start', 'effect': 'network_read',
     'description': '지정한 사이트와 한도에서 읽기 전용 검사를 시작합니다.',
     'input_schema': schema({'url': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
                             'max_pages': {'type': 'integer', 'minimum': 1, 'maximum': 10000},
                             'timeout_sec': {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1800},
                             'profile': {'enum': ['default', 'test', 'public']},
                             'preview': {'type': 'boolean'}, 'demo': {'type': 'boolean'},
                             'workflow': {'type': 'object'}}, ['url', 'workflow'])},
    {'name': 'scan.status', 'method': 'state', 'effect': 'read', 'description': '현재 실행 ID와 실제 실행 상태를 읽습니다.', 'input_schema': schema()},
    *[{'name': 'scan.' + name, 'method': name, 'effect': 'control', 'description': description,
       'input_schema': schema(RUN, ['run_id'])} for name, description in
      [('pause', '현재 페이지가 끝나면 일시정지합니다.'), ('resume', '정지한 검사를 이어갑니다.'), ('stop', '실행을 중단하고 수집한 결과를 저장합니다.')]],
    {'name': 'scan.findings', 'method': 'findings', 'effect': 'read', 'description': '현재 실행의 원문·근거·검토 상태를 페이지 단위로 읽습니다.',
     'input_schema': schema({**RUN, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}}, ['run_id'])},
    {'name': 'scan.events', 'method': 'events', 'effect': 'read', 'description': '순번 이후의 최근 실행 이벤트를 읽습니다. 화면 이미지 페이로드는 제외합니다.',
     'input_schema': schema({**RUN, 'after_sequence': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}}, ['run_id'])},
    {'name': 'review.update', 'method': 'review', 'effect': 'local_write', 'description': '완료된 결과에 검토 상태와 메모를 기록합니다. 탐지 원문은 변경하지 않습니다.',
     'input_schema': schema(REVIEW, ['run_id', 'ids', 'status', 'expected_revision'])},
    {'name': 'workflow.validate', 'method': 'validate-workflow', 'effect': 'read', 'description': '지원하는 노드 연결과 실제 실행 단계를 검증합니다.',
     'input_schema': schema({'workflow': {'type': 'object'}}, ['workflow'])},
]


def capabilities():
    return {'protocol_version': 1, 'transport': 'stdio-jsonl', 'agent_connected': False,
            'tools': [{k: deepcopy(v) for k, v in tool.items() if k != 'method'} for tool in CATALOG]}


def resolve_tool(name, arguments):
    tool = next((item for item in CATALOG if item['name'] == name), None)
    if tool is None:
        raise ValueError('지원하지 않는 도구입니다.')
    errors = sorted(Draft202012Validator(tool['input_schema']).iter_errors(arguments), key=lambda error: str(list(error.path)))
    if errors:
        raise ValueError('도구 입력 형식 오류: ' + errors[0].message)
    return tool['method']
