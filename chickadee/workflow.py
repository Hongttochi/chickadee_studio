"""Validate the visual pipeline against stages supported by the real engine."""

CONNECTIONS = {('target', 'browser'), ('browser', 'collector'), ('collector', 'techniques'),
               ('collector', 'candidates'), ('techniques', 'report'), ('candidates', 'report'), ('collector', 'ocr'), ('ocr', 'candidates'), ('ocr', 'techniques'), ('techniques', 'dedup'), ('candidates', 'dedup'), ('dedup', 'report')}


def compile_workflow(workflow):
    if not isinstance(workflow, dict) or not isinstance(workflow.get('edges'), list) or len(workflow['edges']) > 12:
        raise ValueError('워크플로 연결 형식이 올바르지 않습니다.')
    edges = set()
    for edge in workflow['edges']:
        if not isinstance(edge, dict):
            raise ValueError('잘못된 연결입니다.')
        pair = edge.get('source'), edge.get('target')
        if pair not in CONNECTIONS:
            raise ValueError('지원하지 않는 단계 연결입니다.')
        edges.add(pair)
    follow = workflow.get('follow_links', True)
    if type(follow) is not bool:
        raise ValueError('하위 링크 탐색 설정은 true/false여야 합니다.')
    ocr = workflow.get('ocr_enabled', True)
    if type(ocr) is not bool:
        raise ValueError('OCR 설정은 true/false여야 합니다.')
    # Connections are display-only. Legacy disconnected graphs cannot disable
    # required analysis, including when launched by a saved schedule.
    return dict(ocr_techniques=True, ocr_candidates=True, ocr_enabled=ocr,
                detect_techniques=True, detect_candidates=True, follow_links=follow)
