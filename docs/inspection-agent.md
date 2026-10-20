# 탐색 그래프·변경 비교·Groq 근거 조사

2026-10-21 개발 소스에 구현한 기능이다. 0.6.3까지의 기존 배포 ZIP에 소스 변경이 소급 적용되는 것은 아니다. 새 패키지를 만들 때 `scripts/build-desktop.ps1`의 엔진·렌더러를 함께 빌드한다.

## 화면

왼쪽 **검사 분석**에서 세 기능을 사용한다. 기존 디자인 파일은 수정하지 않았다. 구현은 `desktop/src/InspectionInsights.jsx`, 데이터 변환은 `inspection-model.mjs`, 영역에 한정된 배치는 `inspection.css`로 분리했다. 다른 화면 디자인에 옮길 때 컴포넌트와 preload API를 유지하면 된다.

- **탐색 그래프**: 발견한 페이지, 실제 DOM 수집 상태, 스크롤·읽기 버튼 뒤의 상태, iframe 수집을 관측된 연결로 표시한다. 노드를 누르면 수집 근거를 확인한다. 검사 구성의 단계 연결 그래프와는 별개다. 새 화면을 연 상태에서 검사하면 실시간으로 갱신한다.
- **변경 비교**: 같은 시작 URL의 직전 검사와 자동 비교한다. 다른 이전 기록을 직접 선택할 수도 있다. 같은 URL·frame 경로·selector의 최종 관측을 기준으로 원문·링크 목적지·스타일 변화를 비교한다. 스크롤에 따른 viewport 좌표 이동은 변경 신호에서 제외한다.
- **Groq 검토**: 키와 모델·사용량 한도를 적용하고, 수집 영역을 선택해 **Groq 분석**을 누른다. 자동 호출은 없다. API 키는 앱 세션의 메모리에만 보관하며 기록·설정 파일·저장소에 쓰지 않는다. 이미 설정한 세션에서는 키를 다시 입력하지 않고 한도를 낮출 수 있다.

`신규 관측`은 처음 확인된 영역, `미관측`은 이번에 확인되지 않은 영역이다. 미관측을 삭제 확정으로 해석하지 않는다. selector가 바뀌면 신규·미관측 두 항목으로 나올 수 있다. 일부 검사·수집 한도 도달도 비교 화면에 표시한다. 이전 버전 기록에 영역 근거가 없으면 비교할 수 없다.

## 수집과 문자 분석

광고로 판정되지 않은 영역도 근거 패킷으로 보존한다. 현재 영역 경계는 기존 `content_scope`의 게시글·댓글 마크업과 직접 텍스트 요소를 사용한다. 의미 영역을 찾지 못한 경우 `scope_quality=element`로 기록한다. 사이트 종류를 자동으로 이해하는 학습 모델은 아직 포함하지 않는다.

패킷에는 원문(최대 4,000자), URL·selector·frame 경로, 관측 시각·snapshot ID, 원문 SHA-256, 관측한 computed style·숨김 근거·링크 문자열을 저장한다. 미수집 스타일은 null이다. iframe의 숨김 플래그도 별도로 보존한다. 동일한 근거를 여러 상태에서 재사용하며 최종 관측 순서를 유지하므로 값이 변경됐다가 복구된 경우도 최종 값으로 비교한다.

영역은 실행당 최대 1,000개·본문 패킷 합계 약 6MB, DOM 상태는 최대 3,000개로 제한하고 초과 시 `truncated`를 남긴다. 그래프 화면은 최대 240개 노드만 표시한다. 원문·스크롤·페이지 한도는 기존 검사 제한도 함께 적용한다.

Unicode 공식 confusables 데이터의 **18.0.0, 1,351개 제한 매핑**을 로컬에 고정했다. 비ASCII 단일 글자에서 ASCII 글자로의 매핑만 사용하고, 기존 한글·자모 처리를 유지한다. ASCII끼리의 과도한 치환은 하지 않는다. 원문 위치를 보존하며 광고 문맥 조건과 정상 예외도 유지한다. 보이지 않는 형식 문자 삽입과 혼합 문자 체계는 보조 패턴으로 기록한다. 형식 문자만 있다는 이유로 HOMOGLYPH를 만들지는 않는다. 이는 UTS #39 전체 구현이나 모든 언어의 위장 탐지 완성을 의미하지 않는다.

데이터 출처·원본 SHA-256·필터는 `chickadee/data/confusables-ascii.json`, 라이선스는 같은 폴더 `LICENSE-UNICODE.txt`에 있다. 실행 중 Unicode 서버에 접속하지 않는다.

## Groq 실행과 비용

제공자는 **Groq 하나**이고 요청 주소는 `https://api.groq.com/openai/v1/chat/completions`로 고정한다. 다른 제공자·유료 검색 API·Groq 내장 검색·코드 실행 도구는 호출하지 않는다. 기본 모델은 해당 계정의 실제 목록에서 확인한 `openai/gpt-oss-20b`다. 모델 이름에 `openai`가 포함되어 있지만 API 요청·인증·과금 경로는 Groq다.

1. 모델이 등록된 `evidence_read`, `style_read`, `text_analyze` 중 필요한 조회를 선택한다.
2. 앱이 선택한 근거 ID와 도구 인자를 검증하고 **이미 수집된 근거만** 조회한다. 임의 URL·파일·명령 실행, 다른 실행의 근거 접근, 기존 탐지·사람 검토 수정은 허용하지 않는다.
3. 별도 모델 호출에서 JSON 의견을 받는다. JSON Schema와 실제 조회한 근거 ID를 검증한다. 짧거나 잘린 문구·본문을 읽지 않은 의견은 보류로 처리한다.

도구 조회 단계와 JSON 응답 단계는 별도 요청이다. 현재 에이전트는 저장된 영역을 조사하는 구현이며, 브라우저를 다시 열어 DOM을 재검사하거나 새로운 사이트를 스스로 탐색하지 않는다. 현재 페이지 재관측 도구·ML 후보 확장·OCR은 후속 범위다.

한 번의 분석은 모델 요청 **2회**, 도구 조회 최대 **4개**, 출력 요청당 최대 **512토큰**, 전체 **30초**, 단일 HTTP 대기 최대 **10초**다. 취소는 요청 전후에 확인하므로 이미 전송된 요청의 비용을 취소하지는 못한다. 실패·429·형식 오류 때 자동 재시도나 제공자 전환은 없다.

기본 누적 한도는 **검사 실행당 6회 / 24,000토큰**이다. 토큰은 요청 전에 UTF-8 크기로 보수적으로 예약하고, 정상 응답의 제공자 사용량으로 정산한다. 응답 실패·사용량 누락은 예약을 유지한다. 호출 여유가 2회 미만이면 새 분석을 시작하지 않는다. 사용량과 설정 한도는 `agent.json`에 요청 전에 저장하며 같은 기록을 다시 열어도 이어진다. 이미 저장한 실행 한도는 낮출 수 있지만 높이지 않는다. 새 검사는 별도 한도를 사용한다.

이는 앱 내 호출·토큰 제어이며 계정 전체의 달러 한도는 아니다. 모델별 가격, 다른 앱에서 쓰는 같은 키와 새 검사들의 합산 비용까지 제한하려면 [Groq Spend Limits](https://console.groq.com/docs/spend-limits)도 설정한다.

Groq에는 선택한 영역의 초기 발췌와 요청한 도구 결과만 전송한다. 본문 조회는 최대 1,600자다. URL·이메일·전화번호·키 모양 문자열을 마스킹하며 쿠키·인증 헤더·HTML 원본·전체 화면 이미지를 보내지 않는다. 자유 서술 개인정보까지 모두 제거하는 기능은 아니다. 페이지의 지시문은 데이터로 취급하며 도구 권한도 별도로 제한한다. [Groq 데이터 정책](https://console.groq.com/docs/your-data)을 참고한다.

## 저장과 로컬 API

필수 `result.json`과 17칼럼 CSV는 변경하지 않는다. `scan-report.json`에 `exploration`과 `evidence_packets`가 추가된다. `comparison.json`은 변경 비교, `agent.json`은 근거 조사 의견·사용량·최근 실행 동작을 보관한다. sidecar는 원본 결과 SHA-256에 연결한다. AI 의견은 사람의 `review.json`을 덮어쓰지 않는다.

기존 stdio bridge에 다음 명령을 추가했다. 별도 HTTP 포트는 열지 않는다.

| 명령 | 인자 | 반환·효과 |
| --- | --- | --- |
| `inspection` | `run_id` | 그래프·영역·변경 비교·에이전트 상태 |
| `compare` | `run_id`, `baseline_id` | 같은 시작 URL의 이전 기록과 비교·저장 |
| `agent-configure` | `api_key` 선택, `model`, `token_limit`, `call_limit` | 세션 설정. 키 생략 시 기존 세션 키 또는 `GROQ_API_KEY` |
| `agent-run` | `run_id`, `evidence_id` | 백그라운드 근거 조사 시작 |
| `agent-status` | 없음 | 설정 여부·실행 상태·누적 사용량·의견 |
| `agent-stop` | 없음 | 에이전트 취소 요청 |

`inspection.read`, `inspection.compare`, `agent.status`는 기존 로컬 tool-call 계약에도 등록했다. 비용 발생 명령과 인증 설정은 근거 조사 모델에 노출하지 않는다. `agent_connected`는 세션 설정 여부이며 `agent_available=true`, `providers=["groq"]`로 구현 가용성을 표시한다.

## 검증과 재실행

로컬 fixture로 두 차례 실제 Chromium 검사, 링크·문구·opacity 변경, 자동 비교와 재불러오기, 원본 결과 불변을 시험한다. 에이전트는 결정론적 응답으로 잘못된 도구·다른 근거 ID·환각 ID·예산·취소를 검증한다. 화면 시험은 로컬 렌더러와 실제 Python bridge를 연결한다. 네이티브 Electron 패키지 실행 검증과는 별개다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd desktop
npm run build
npm test
$env:PLAYWRIGHT_BROWSERS_PATH = '..\.venv\Lib\site-packages\playwright\driver\package\.local-browsers'
node tests/inspection-smoke.cjs
```

유료 실서버 검증은 자동 테스트에 포함하지 않는다. 필요할 때만 다음 명령을 직접 실행한다. 합성 문구만 사용하고 출력 파일에 사용량을 보존해 재실행 시 기존 한도를 이어 적용한다.

```powershell
.\.venv\Scripts\python.exe scripts/verify_groq_agent.py --output artifacts/groq-live-check.json
# 또는 --env-file <사용자가 지정한 dotenv 경로>. GROQ_API_KEY만 읽고 실행·복사하지 않는다.
```

2026-10-21 실제 Groq에서 합성 광고 문구 1건의 도구 호출·JSON 판정을 확인했다. 추가 합성 주입 사례는 누적 호출 한도에 도달해 최종 판정을 완료하지 않았다. 이를 프롬프트 주입 방어 성능 입증으로 해석하지 않는다. 작은 합성 사례의 성공은 실제 사이트 정확도 보장이 아니다.
