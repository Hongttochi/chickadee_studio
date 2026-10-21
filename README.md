<div align="center">

<img width="500" height="180" alt="치카디 미니멀 테크 로고" src="https://github.com/user-attachments/assets/00fe0c7d-f628-4bf1-bf8a-f10b9b3c4f0c" />

# Chickadee Studio

**한국어** · [English](README.en.md)

**웹사이트를 검사하고, 발견한 문구와 근거를 한곳에서 검토하세요.**

공공 웹사이트의 광고 의심 요소를 찾는 데스크톱 검사 도구입니다.<br />
주소 입력부터 브라우저 검사, 근거 확인, JSON·CSV 저장까지 연결합니다.

[![Release](https://img.shields.io/github/v/release/orqan137/chickadee_studio?include_prereleases&style=flat&color=506b83&label=release)](https://github.com/orqan137/chickadee_studio/releases)
[![Release workflow](https://img.shields.io/github/actions/workflow/status/orqan137/chickadee_studio/release.yml?branch=main&style=flat&label=build)](https://github.com/orqan137/chickadee_studio/actions/workflows/release.yml)
[![Windows x64](https://img.shields.io/badge/Windows-x64-506b83?style=flat)](docs/quickstart-windows.md)
[![Electron](https://img.shields.io/badge/Electron-44-47848f?style=flat&logo=electron&logoColor=white)](desktop/package.json)
[![Python](https://img.shields.io/badge/Python-3.12-47779e?style=flat&logo=python&logoColor=white)](requirements.txt)

[**Windows 다운로드**](https://github.com/orqan137/chickadee_studio/releases/tag/v0.10.3) · [빠른 시작](docs/quickstart-windows.md) · [사용 설명서](docs/manual.md) · [릴리스 노트](docs/releases/0.10.3.md)

</div>

<br />

[![검사 대상과 단계별 처리 흐름을 보여주는 Chickadee 검사 구성 화면](desktop/assets/guide/start.png)](desktop/assets/guide/start.png)

<p align="center"><sub>검사 대상 노드를 선택해 URL을 입력합니다. 이미지를 누르면 원본 크기로 볼 수 있습니다.</sub></p>

## 바로 시작하기

**Windows 배포 파일에는 앱·Python 검사 엔진·Chromium이 모두 포함됩니다.** Python, Node.js, Docker를 따로 설치할 필요가 없습니다.

1. [**0.10.3 Windows ZIP**](https://github.com/orqan137/chickadee_studio/releases/download/v0.10.3/Chickadee-Studio-0.10.3-win-x64.zip)을 내려받아 전체 압축을 풉니다.
2. `Chickadee-0.10.3/Chickadee.exe`를 실행합니다.
3. **검사 대상** 노드를 누르고 오른쪽 URL 입력란에 주소를 입력합니다.
4. 상단 **검사 실행**을 누릅니다. 먼저 둘러보려면 옆의 펼침 메뉴에서 **데모 검사**를 선택하세요.

로컬 데모는 인터넷 없이 실행할 수 있습니다. 처음에는 앱의 **설정 → 사용 가이드** 또는 [상세 사용 가이드](docs/desktop.md)에서 검사 구성·OCR·검토·예약·알림을 화면 예시와 함께 확인하세요.

> 현재 다운로드는 **Windows x64**입니다. `Chickadee.exe`와 `resources` 등 동봉 파일을 같은 폴더에 유지하세요. macOS는 소스 실행을 지원하며 별도 배포 파일은 제공하지 않습니다.

## 화면으로 살펴보기

### 발견한 문구에서 검토까지

[![데모 탐지 목록과 오른쪽 원문·근거 패널](desktop/assets/guide/review.png)](desktop/assets/guide/review.png)

- **탐지 내역**에서 필수 탐지·광고 의심을 나누고, 문구·URL·검토 상태로 좁혀봅니다.
- 행을 누르면 **발견한 문구와 탐지 이유**가 오른쪽에 나타납니다.
- **검토 확인·제외**를 선택하고 메모를 남깁니다. 저장한 검토 상태는 결과를 다시 열어도 유지됩니다.
- **페이지 · 기술 정보**를 펼치면 URL과 DOM 위치를 확인하고 복사할 수 있습니다.

### 이전 검사 다시 열기

<details>
<summary><strong>검사 기록 화면 보기</strong></summary>

[![이전 검사 대상, 상태, 페이지 수와 완료 시간을 표시하는 검사 기록](desktop/assets/guide/history.png)](desktop/assets/guide/history.png)

검사 기록의 행을 누르면 해당 결과가 열립니다. 별도로 보관한 `result.json`은 **결과 불러오기**로 확인하고, 파일 위치는 상단 **결과 폴더**에서 엽니다.

</details>

스크린샷은 내장 데모를 검사한 앱 실행 화면입니다.

## 주요 기능

| 기능 | 할 수 있는 일 |
| --- | --- |
| 노드 기반 검사 구성 | 대상 → 콘텐츠 수집·이미지 OCR → 필수 탐지·광고 분류 → 중복 정리 → 결과 출력. 검사 순서는 고정되며 OCR 사용 여부만 별도로 설정 |
| 한국어 이미지 OCR | 게시글·배경 이미지의 글자 인식과 필수 탐지·광고 문맥 분석. 처리 실패·판독 불가를 별도로 표시하고 원본·글자 위치·신뢰도 보존 |
| 검사 제어 | 페이지 경계에서 일시정지·재개, 중단 후 일부 결과 저장, 특정 페이지 재검사 |
| 실제 브라우저 미리보기 | Chromium 화면·현재 URL·진행 단계를 접이식 패널에서 확인 |
| 탐색 경로와 진행 기록 | 방문·대기 주소, HTTP 응답, 링크 발견, 처리 단계와 오류 확인 |
| 검토 작업 | 미검토·검토 확인·제외, 최대 2,000자 메모, 최대 500건 일괄 처리 |
| 저장과 복원 | JSON·CSV·보고서, 마지막 검사 화면과 최근 30개 실행 기록 보관 |
| 빠른 조작 | 앱 드롭다운, 키보드 메뉴 이동, 빠른 명령, 설정·노드 위치 기억 |

기본 검사와 이미지 OCR은 외부 API 키나 GPU 없이 동작합니다. 같은 페이지에서 유형과 문구가 같은 본문·OCR 결과는 합치되, 각 위치와 이미지 근거는 보존합니다. 다른 페이지나 서로 다른 문구는 병합하지 않습니다.

### 검사 분석 · 0.10.0

- **탐색 그래프**: 실제 관찰한 페이지, 스크롤·읽기 동작과 iframe 탐색을 확인합니다.
- **AI 검토**: 전체 수집 영역을 순서대로 분석하고, 근거 부족 시 같은 사이트의 관측 링크를 최대 2개 추가 탐색해 재판정합니다. 사용자가 분석을 시작해야 실행하며, 기존 누적 6회/24,000토큰 한도를 유지합니다. 원본 탐지 결과와 사람의 검토 상태는 변경하지 않습니다.
- **근거 화면**: 탐지 당시 화면을 촬영해 근거 패널·검사 기록에서 확대하며 원본 JPEG도 결과 폴더의 `evidence/`에 저장합니다. 이미지는 Groq에 전송하지 않습니다.

- **로컬 AI 분석 · 0.10.1**: 학습한 문자 문맥·피싱 화면 모델이 API 키 없이 동작합니다. 근거 패널과 AI 검토에서 모델 분류·일치 특징·화면 분석을 확인하고 검사 기록에 보존합니다. Groq 추가 검토에도 같은 로컬 분석을 전달합니다.

[검사 분석과 AI 검토 사용법](docs/inspection-agent.md)

외부로 전달되는 근거와 마스킹 범위, 설정 방법은 [검사 분석 안내](docs/inspection-agent.md)를 확인하세요.

## 무엇을 탐지하나요?

| 필수 유형 | 코드 | 예시 |
| --- | --- | --- |
| 닮은꼴 글자 위장 | `HOMOGLYPH` | 전각·키릴·일부 그리스 문자·숫자, 혼합 표기 |
| 자모 분해 | `JAMO` | 호환·결합 자모, 여러 인라인 태그에 나뉜 문구 |
| 투명 텍스트 | `TRANSPARENT` | 투명색, 요소·조상 opacity, 단색 배경과 같은 글자색 |
| 화면 밖 은닉 | `OFFSCREEN` | 음수 좌표, 0~1px 글자, 작은 상자와 overflow, 숨김 요소 |

실제 Chromium의 DOM과 계산된 CSS를 검사합니다. 위장·은닉이 없는 도박·대출·투자·구매 유도는 **별도 광고 의심 후보**로 분류하며 필수 유형 코드를 임의로 붙이지 않습니다. 원문과 탐지 근거를 함께 확인하세요.

<details>
<summary><strong>탐색 범위와 처리 방식</strong></summary>

- 같은 사이트의 링크와 게시글 쿼리를 탐색하며 게시판·상세 글을 우선 방문합니다.
- 지연 로딩, 제한된 스크롤, 사이트 설정의 읽기용 컨트롤과 허용 origin 안의 중첩 iframe을 처리합니다.
- 외부 프레임의 출처는 설정에서 명시해야 하며 차단·누락은 보고서에 남습니다.
- 네트워크 오류·5xx 재시도, 페이지 간 간격, 시간·페이지 한도를 적용합니다. 429 수신 시 해당 origin의 재시도와 새 요청을 중단합니다.
- 사용자 Chrome 프로필·탭을 사용하지 않고, 검사 대상 HTML을 Electron 표시 창에 직접 삽입하지 않습니다.
- 탐지 규칙과 사이트 설정은 JSON으로 교체합니다. 설정 파일의 코드를 실행하지 않습니다.

[탐색 처리 방식](docs/performance.md) · [실제 테스트 결과](examples/test-site-2026-10-20/)

</details>

## 결과 파일

기본 위치는 `문서/Chickadee/results/실행별폴더`이며 **검사 설정**에서 바꿀 수 있습니다.

| 파일 | 내용 |
| --- | --- |
| `result.json` | `meta`와 `findings` — 필수 4종 결과. 탐지 0건은 빈 배열로 저장 |
| `scan-report.json` | 검사 상태, 방문 페이지, 오류·한도, 광고 의심 후보, 결과 파일 해시 |
| `result.csv` | 필수 기법·광고 의심 후보를 고정 17개 칼럼으로 저장 |

중단·실패·일부 결과는 정상 완료와 구분됩니다. 검토 정보는 원본 탐지 근거를 덮어쓰지 않습니다. [CSV 칼럼 정의](docs/result-format.md) · [결과 스키마](schemas/result.schema.json)

## 개발 환경

Python 3.12와 Node.js 24를 기준으로 합니다. 아래는 **소스 개발용** 절차입니다. Windows 배포 파일 사용자는 이 과정을 건너뛰세요.

<details>
<summary><strong>Windows에서 소스 실행</strong></summary>

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/prepare_ocr_models.py
$env:PLAYWRIGHT_BROWSERS_PATH = '0'
.\.venv\Scripts\python.exe -m playwright install chromium --only-shell
cd desktop
npm ci
npm run build
npm start
```

Windows 앱·검사 엔진 패키징은 저장소 루트의 `scripts/build-desktop.ps1`을 사용합니다. 출력은 `artifacts/electron-0.10.0/win-unpacked/Chickadee.exe`이며 폴더 전체를 배포합니다.

</details>

<details>
<summary><strong>macOS에서 소스 실행</strong></summary>

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/prepare_ocr_models.py
PLAYWRIGHT_BROWSERS_PATH=0 .venv/bin/python -m playwright install chromium --only-shell
cd desktop
npm ci
npm run build
npm start
```

`npm start`는 `artifacts/dev-app/`에 Chickadee 이름의 개발 번들을 준비합니다. Electron과 Python 가상환경의 CPU 아키텍처를 맞춰 사용하세요. macOS 배포·공증 패키지는 제공하지 않습니다.

</details>

<details>
<summary><strong>테스트와 CLI</strong></summary>

```powershell
# 저장소 루트에서 Python 회귀 검사
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# CLI 데모 검사
.\.venv\Scripts\python.exe -m chickadee --demo --cli --output-dir artifacts/demo

# 데스크톱 단위 검사
cd desktop
npm test
```

macOS에서는 Python 실행 경로를 `.venv/bin/python`으로 바꿉니다. 기존 Tkinter 호환 화면과 CLI 사용법은 [매뉴얼](docs/manual.md), 데스크톱 빌드는 [개발·배포 절차](docs/desktop.md)를 참고하세요.

</details>

## 문서

| 시작과 사용 | 개발과 검증 | 조사와 연구 |
| --- | --- | --- |
| [Windows 빠른 실행](docs/quickstart-windows.md) | [데스크톱 개발·배포](docs/desktop.md) | [조사 자료 원본](research/README.md) |
| [사용 매뉴얼](docs/manual.md) | [아키텍처](docs/architecture.md) | [Dots 자료 반영](docs/research-integration.md) |
| [결과 파일 형식](docs/result-format.md) | [검증 기록](docs/validation.md) | [v4 조사 정리](docs/research-v4.md) |
| [릴리스 노트](docs/releases/0.10.3.md) | [디자인 기준](DESIGN.md) | [ML·에이전트 설계](docs/ml-agent-generalization.md) |
| [개발 계획](docs/development-plan.md) | [에이전트 규격](docs/agent-extension.md) | [ML 오프라인 대조](research/ml-review/2026-10-21/) |
| [요구사항](docs/requirements.md) | [외부 구성요소](docs/third-party-notices.md) | [모의 웹 명세](examples/mock-site-spec.json) |
| [제출 체크리스트](docs/submission-checklist.md) | [결과 예시](examples/result.sample.json) | [모의 웹 내용](examples/mock-site-content.json) |

<details>
<summary><strong>아키텍처 그림 보기</strong></summary>

![Chickadee 구조와 실행 경계](docs/assets/architecture-gpt.png)

[편집 가능한 원본](docs/assets/architecture.drawio)

</details>

## 라이선스

원본 코드는 [Apache-2.0](LICENSE)으로 배포합니다. 외부 구성요소의 라이선스는 각각 유지됩니다.
