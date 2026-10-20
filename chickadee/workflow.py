"""Validate the visual pipeline against stages supported by the real engine."""

CONNECTIONS = {('target', 'browser'), ('browser', 'collector'), ('collector', 'techniques'),
               ('collector', 'candidates'), ('techniques', 'report'), ('candidates', 'report')}


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
    if not {('target', 'browser'), ('browser', 'collector')} <= edges:
        raise ValueError('대상 URL → 브라우저 → 콘텐츠 수집을 연결하세요.')
    techniques = {('collector', 'techniques'), ('techniques', 'report')} <= edges
    candidates = {('collector', 'candidates'), ('candidates', 'report')} <= edges
    if not (techniques or candidates):
        raise ValueError('분석 단계 중 하나 이상을 결과 저장까지 연결하세요.')
    follow = workflow.get('follow_links', True)
    if type(follow) is not bool:
        raise ValueError('하위 링크 탐색 설정은 true/false여야 합니다.')
    return dict(detect_techniques=techniques, detect_candidates=candidates, follow_links=follow)
