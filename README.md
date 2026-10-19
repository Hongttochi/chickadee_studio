## Chickadee Bot

<img width="300" height="300" alt="image" src="https://github.com/user-attachments/assets/2fe3aa9a-222b-4c1e-bb5a-b83734a70462" />

공공 웹사이트에서 문자로 위장하거나 CSS로 숨긴 불법광고 의심 요소를 찾는 점검 도구입니다. URL을 시작으로 하위 페이지·동적 댓글·설정한 읽기 버튼·iframe을 탐색하고, 판정 근거와 평가용 `result.json`을 제공합니다.

**0.2.0의 기본 실행은 로컬(loopback) 전용입니다.** 실제 사이트 검사는 별도 VM에서 `--network`로 실행하고, 사용자 PC에서는 **결과 불러오기**로 JSON만 확인하는 경로를 권장합니다. 프로그램은 VM을 생성하거나 VM 격리를 검증하지 않으며, 브라우저를 실행하는 환경의 보안을 보장하지 않습니다.

행정안전부·한국지능정보사회진흥원의 **2026 공공 웹사이트 불법광고 탐지 도구 개발 공모전**을 목표로 개발하고 있습니다. 현재 필수 4종의 규칙 기반 탐지·화면·파일 출력을 구현했으며, 최종 제출본 수준의 탐지 성능 검증은 남아 있습니다.

## 구현한 기능

| 필수 탐지 유형 | 코드 | 처리하는 사례 |
| --- | --- | --- |
| 닮은꼴 글자 위장 | `HOMOGLYPH` | 전각·키릴·일부 그리스 문자와 숫자로 위장한 문구 |
| 자모 분해 | `JAMO` | 호환·결합 자모, 여러 인라인 태그에 분리된 문구 |
| 투명 텍스트 | `TRANSPARENT` | 투명색, 요소·조상 opacity, 단색 배경과 같은 글자색 |
| 화면 밖 은닉 | `OFFSCREEN` | 음수 좌표, 0~1px 글자, display:none·visibility:hidden |

- 실제 Chromium 렌더링의 DOM·계산된 CSS를 검사합니다. 사용자의 Chrome 프로필·탭은 사용하지 않습니다.
- 같은 사이트의 링크·게시글 쿼리를 탐색하고, 지연 로딩·제한된 스크롤·설정한 읽기용 컨트롤을 처리합니다.
- 허용 origin 안의 중첩 iframe을 검사합니다. 외부 출처는 사이트 설정에서 명시해야 하며 차단·누락은 보고서에 남깁니다.
- 네트워크 일시 오류·429·5xx 재시도, 페이지 간 간격, 시간·페이지·동작 한도를 적용합니다.
- 키워드 안에서 실제로 변형된 문자를 추적합니다. 관계없는 전각·자모 문자가 있다고 위장으로 판정하지 않습니다.
- 탐지 규칙·사이트 설정을 JSON으로 교체할 수 있습니다. 규칙·설정 파일의 코드는 실행하지 않습니다.
- 원문·URL·유형·요소 위치를 화면에서 조회하고 유형별로 필터링합니다.
- `result.json`을 UTF-8(BOM 없음)으로 저장합니다. 중첩 기법은 기법별로 나누고 동일 검출을 중복 저장하지 않습니다.
- 중단·시간/페이지 한도·수집 오류를 화면과 `scan-report.json`에 표시합니다.
- 결과를 다시 불러와 필터링하고, 키워드 일치·CSS 속성·프레임·읽기 동작 근거를 확인할 수 있습니다.
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

## 실제 사이트 검사: 별도 VM

아래 명령은 개인 계정·비밀정보·호스트 공유 폴더를 연결하지 않은 별도 검사 환경에서 실행합니다. `--network`는 외부 URL 허용 스위치이며 VM 여부를 판별하지 않습니다. 이 PC에서 실제 광고 페이지를 열어 검증하지 않았습니다.

```powershell
# 별도 VM에서 실행. 정책브리핑은 검증 후보이며 실제 탐지 성능을 보증하지 않습니다.
.\.venv\Scripts\python.exe -m chickadee --scan 'https://www.korea.kr/' --network --profile profiles/public-site.json --max-pages 3 --timeout 120 --interval 2 --output-dir artifacts/scan
```

VM에서 `result.json`, `scan-report.json`만 가져온 뒤 화면의 **결과 불러오기**를 사용합니다. 이 기능은 출처 사이트에 접속하거나 HTML을 실행하지 않습니다. 자세한 [사용 절차와 실행 제한](docs/manual.md)을 확인하세요.

## 아키텍처

![Chickadee Bot 아키텍처](docs/assets/architecture-gpt.png)

[구조·실행 경계 설명](docs/architecture.md) · [편집 가능한 원본](docs/assets/architecture.drawio)

## 문서와 구조

| 경로 | 내용 |
| --- | --- |
| `chickadee/` | 탐지 규칙, 브라우저 탐색, 화면, CLI, 로컬 데모 |
| `tests/` | 실제 Chromium 통합 검사와 화면·출력 검사 |
| [실행·빌드·사용설명서](docs/manual.md) | 설치, 배포, 저장 경로, 오류·제한 |
| [0.2.0 검증 기록](docs/validation.md) | 통과한 테스트·배포 확인과 미검증 항목 |
| [요구사항](docs/requirements.md) | 모집요강과 필수 스키마·평가 조건 |
| [개발 계획](docs/development-plan.md) | 구현 상태와 다음 작업 |
| [제출 체크리스트](docs/submission-checklist.md) | 신청 서류·실행 파일·최종 검증 |
| [결과 스키마](schemas/result.schema.json) | 자체 개발용 검증 규칙, 공식 배포 파일 아님 |
| [검출 예시](examples/result.sample.json) / [0건 예시](examples/result.empty.json) | 형식 설명용 가상 데이터 |
| [외부 구성요소](docs/third-party-notices.md) | 사용 도구와 라이선스 확인 경로 |

## 현재 한계

규칙 기반 도구로 오탐과 누락이 있으며 법적 판단을 대신하지 않습니다. 읽기 버튼은 사이트별 선택자 설정이 필요하고, POST 기반 댓글 API·로그인·이미지 OCR·모든 CSS 은닉 기법·무한 스크롤 전체 수집·Shadow DOM은 지원하지 않습니다. 자체 테스트의 14건 검출은 실제 사이트나 비공개 평가셋의 정확도를 뜻하지 않습니다. 사용자 PC 보호 요청에 따라 실제 의심 사이트의 브라우저 검증은 실행하지 않았습니다.

접수 마감은 제공된 모집요강 기준 **2026년 10월 23일 18:00**입니다. Windows 11 실행 파일, 전체 소스코드, 실행·빌드 매뉴얼, 사용설명서와 신청 서류를 함께 준비해야 하며 최종 일정·운영 조건은 주최 측 공지를 확인해야 합니다. 근거는 「공공 웹사이트 불법광고 탐지 도구 개발 공모전 모집요강」(2026년 9월)이며 PDF 원문과 개인정보 서류는 저장소에 포함하지 않았습니다.
