# Chickadee Bot

공공 웹사이트에서 문자로 위장하거나 CSS로 숨긴 불법광고 의심 요소를 찾는 **Windows 데스크톱 데모**입니다. URL 하나를 입력하면 하위 페이지와 iframe을 탐색하고, 결과 화면과 평가용 `result.json`을 제공합니다.

행정안전부·한국지능정보사회진흥원의 **2026 공공 웹사이트 불법광고 탐지 도구 개발 공모전**을 목표로 개발하고 있습니다. 현재 필수 4종의 규칙 기반 탐지·화면·파일 출력을 구현했으며, 최종 제출본 수준의 탐지 성능 검증은 남아 있습니다.

## 구현한 기능

| 필수 탐지 유형 | 코드 | 처리하는 사례 |
| --- | --- | --- |
| 닮은꼴 글자 위장 | `HOMOGLYPH` | 전각·키릴·일부 그리스 문자와 숫자로 위장한 문구 |
| 자모 분해 | `JAMO` | 호환·결합 자모, 여러 인라인 태그에 분리된 문구 |
| 투명 텍스트 | `TRANSPARENT` | 투명색, 요소·조상 opacity, 단색 배경과 같은 글자색 |
| 화면 밖 은닉 | `OFFSCREEN` | 음수 좌표, 0~1px 글자, display:none·visibility:hidden |

- 실제 Chromium 렌더링의 DOM·계산된 CSS를 검사합니다. 사용자의 Chrome 프로필·탭은 사용하지 않습니다.
- 같은 사이트의 일반 링크를 순회하며 게시글 쿼리를 보존합니다. 외부 출처와 중첩 iframe도 검사합니다.
- 원문·URL·유형·요소 위치를 화면에서 조회하고 유형별로 필터링합니다.
- `result.json`을 UTF-8(BOM 없음)으로 저장합니다. 중첩 기법은 기법별로 나누고 동일 검출을 중복 저장하지 않습니다.
- 중단·시간/페이지 한도·수집 오류를 화면과 `scan-report.json`에 표시합니다.
- 로컬 데모 사이트를 내장합니다. 외부 API·API 키·GPU 없이 작동합니다.

## 바로 실행

빌드된 Windows 패키지가 있으면 **`ChickadeeBot` 폴더 전체**를 해제하고 `ChickadeeBot.exe`를 실행합니다. **로컬 데모 준비 → 탐지 시작**을 누르면 예상 14건과 원문·위치를 확인할 수 있습니다.

소스 실행은 Windows 11 x64, Python 3.12 기준입니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH = '0'
.\.venv\Scripts\python.exe -m playwright install chromium --only-shell
.\.venv\Scripts\python.exe -m chickadee --demo
```

CLI 데모와 테스트:

```powershell
.\.venv\Scripts\python.exe -m chickadee --demo --cli --output-dir artifacts/demo
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Windows 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

생성 위치는 `dist/ChickadeeBot/ChickadeeBot.exe`입니다. 브라우저와 런타임이 포함된 `_internal` 폴더도 함께 배포해야 합니다. 소스코드만 clone한 경우 설치·빌드 절차가 필요합니다.

## 결과 파일

기본 저장 위치는 배포본에서는 실행 파일 폴더, 소스 실행에서는 저장소 최상위입니다. 화면에서 폴더를 바꾸거나 CLI에서 `--output-dir`를 지정할 수 있습니다.

| 파일 | 내용 |
| --- | --- |
| `result.json` | `meta`와 `findings`, 필수 4종 평가용 결과. 0건도 빈 배열 저장 |
| `scan-report.json` | 완료·일부 결과·중단·실패 상태, 점검 페이지, 오류·한도, 결과 파일 해시 |

새 실행 종료 시 이전 파일을 교체합니다. **일부 결과나 실패를 0건 정상 완료로 해석하지 마세요.** 추가 유형은 미구현이며 `result_extra.json`은 생성하지 않습니다.

## 문서와 구조

| 경로 | 내용 |
| --- | --- |
| `chickadee/` | 탐지 규칙, 브라우저 탐색, 화면, CLI, 로컬 데모 |
| `tests/` | 실제 Chromium 통합 검사와 화면·출력 검사 |
| [실행·빌드·사용설명서](docs/manual.md) | 설치, 배포, 저장 경로, 오류·제한 |
| [요구사항](docs/requirements.md) | 모집요강과 필수 스키마·평가 조건 |
| [개발 계획](docs/development-plan.md) | 구현 상태와 다음 작업 |
| [제출 체크리스트](docs/submission-checklist.md) | 신청 서류·실행 파일·최종 검증 |
| [결과 스키마](schemas/result.schema.json) | 자체 개발용 검증 규칙, 공식 배포 파일 아님 |
| [검출 예시](examples/result.sample.json) / [0건 예시](examples/result.empty.json) | 형식 설명용 가상 데이터 |
| [외부 구성요소](docs/third-party-notices.md) | 사용 도구와 라이선스 확인 경로 |

## 현재 한계

광고 키워드·문자·CSS 규칙을 결합한 데모이므로 오탐과 누락이 있습니다. 접근성용 숨김 텍스트·예방 안내 등 정상 사례를 대조하지만 법적 판단을 대신하지 않습니다. 이미지 OCR, 모든 CSS 은닉 기법, 로그인, 버튼 전용 탐색, 무한 스크롤 전체 수집, Shadow DOM은 지원하지 않습니다. 자체 데모의 14건 검출은 실제 사이트나 비공개 평가셋의 정확도를 뜻하지 않습니다.

접수 마감은 제공된 모집요강 기준 **2026년 10월 23일 18:00**입니다. Windows 11 실행 파일, 전체 소스코드, 실행·빌드 매뉴얼, 사용설명서와 신청 서류를 함께 준비해야 하며 최종 일정·운영 조건은 주최 측 공지를 확인해야 합니다. 근거는 「공공 웹사이트 불법광고 탐지 도구 개발 공모전 모집요강」(2026년 9월)이며 PDF 원문과 개인정보 서류는 저장소에 포함하지 않았습니다.
