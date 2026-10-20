# 구현 구조와 실행 경계

![GPT로 생성한 아키텍처](assets/architecture-gpt.png)

현재 코드는 0.5.0이며, 그림은 이전 버전의 개념도입니다. Electron 화면 → 제한된 IPC → Python JSONL 브리지 → Playwright Chromium → 탐지·저장 순서로 실행합니다. 외부 사이트를 직접 검사하거나 저장된 결과를 불러올 수 있습니다. 그림의 VM은 사용자가 별도로 구성하는 실행 환경입니다. 프로그램에 VM 생성·자동 격리·원격 VM 접속 기능이 들어 있다는 뜻이 아닙니다.

| 구성 | 구현 | 역할 |
| --- | --- | --- |
| Windows 화면 | `desktop/src`, `desktop/electron` | React Flow 구성, 실제 페이지 이미지·단계·진단, 제한된 IPC |
| 검사 브리지 | `bridge.py`, `workflow.py` | JSONL 자식 프로세스, 그래프 검증, 단계 선택, 실행별 저장과 기록 |
| 호환 화면 / CLI | `chickadee/gui.py`, `__main__.py` | Tkinter 입력, 중단, 결과 불러오기, 유형·원문·근거 조회 |
| 탐색 제어 | `scanner.py` | 게시판·상세 글 우선순위 큐, 재시도, 한도, 지연 로딩·스크롤·읽기 동작, 페이지별 진단 |
| 요청 정책 | `scanner.py` | 외부 URL 기본 허용·선택적 --local-only, origin 허용 목록, GET/HEAD, 자원·WebSocket 차단 |
| DOM 수집 | `extract.js`, `_inspect_frame` | 원문, 선택자, CSS·좌표, 중첩 iframe 경로 |
| 규칙 분석 | `detection.py`, `rules.json` | 키워드의 원문 문자 추적, 필수 기법 4종, 예방 안내 제외 |
| 사이트 설정 | `profiles.py`, `profiles/` | 경로 범위·읽기 선택자·리소스 origin, 실행 코드 없는 JSON |
| 후보 분석 | `candidates.py` | 일반 광고 검토 후보, 목록·상세 후보 통합 |
| 결과 처리 | `ScanOutcome`, `exports.py` | 표준 JSON, 17개 칼럼 CSV, 원자적 교체, 보고서 해시·불러오기 |

GUI·CLI는 외부 URL을 기본 허용합니다. 로컬 전용으로 제한하려면 `--local-only`를 지정합니다. Python 내부 API의 `ScanConfig`는 명시적인 `allow_network=True`를 요구합니다. 결과 조회는 원본 URL을 열거나 HTML을 렌더링하지 않습니다. Windows 앱에 Docker나 VM은 필요하지 않습니다.

브라우저 내장 sandbox를 켜고 임시 컨텍스트를 사용하지만, 이 정책이 브라우저 취약점이나 모든 통신·부수 효과를 통제하는 OS 보안 경계는 아닙니다. 계정·개인 데이터·호스트 공유 자원을 검사 환경에 연결하지 않는 운영 구성이 별도로 필요합니다.

외부 AI API, 학습된 불법성 분류 모델, 원격 서버나 DB는 사용하지 않습니다. 규칙 기반 의심 항목이며 실제 사이트 정확도와 비공개 평가셋 성능은 별도 검증 대상입니다. 이번 검증은 사용자 제공 모의 게시판과 합성 fixture를 대상으로 했습니다.

주 이미지에는 GPT 이미지 생성 도구를 사용했습니다. [생성 프롬프트](assets/architecture-prompt.txt)와 [편집 가능한 구조 원본](assets/architecture.drawio)을 함께 보관합니다. 그림보다 코드·이 문서의 동작 조건을 기준으로 판단합니다.
