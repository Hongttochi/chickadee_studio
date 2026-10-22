<div align="center">

<img src="desktop/assets/app-mark.png" width="104" alt="Chickadee" />

# Chickadee Studio

**웹사이트의 수상한 문구를 찾고, 근거를 보고, 검토를 남기세요.**

브라우저 수집 · 한국어 이미지 OCR · 탐지 근거 · AI 검토

[![Latest release](https://img.shields.io/github/v/release/orqan137/chickadee_studio?style=flat&color=526d82)](https://github.com/orqan137/chickadee_studio/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/orqan137/chickadee_studio/release.yml?branch=main&label=build&style=flat)](https://github.com/orqan137/chickadee_studio/actions/workflows/release.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-526d82?style=flat)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-x64-526d82?style=flat)](docs/quickstart-windows.md)
[![Electron](https://img.shields.io/badge/Electron-47848f?style=flat&logo=electron&logoColor=white)](desktop/package.json)
[![Python](https://img.shields.io/badge/Python-3.12-47779e?style=flat&logo=python&logoColor=white)](requirements.txt)

[**다운로드**](https://github.com/orqan137/chickadee_studio/releases/latest) · [사용 가이드](docs/desktop.md) · [버그 제보](https://github.com/orqan137/chickadee_studio/issues) · [기여하기](CONTRIBUTING.md)

**한국어** · [English](README.en.md)

</div>

![Chickadee Studio의 고정 검사 파이프라인](docs/assets/screenshots/workflow.png)

<p align="center"><sub>실제 앱에서 내장 데모를 실행한 화면입니다. 스크린샷은 0.10.5 기준이며, 실사이트 탐지 정확도를 나타내는 자료는 아닙니다.</sub></p>

## Chickadee는 무엇인가요?

Chickadee Studio는 공공 웹사이트와 게시판의 광고 의심 문구, 위장 문자, 숨겨진 텍스트를 점검하는 오픈소스 데스크톱 도구입니다. Chromium으로 페이지를 읽고 DOM·CSS·이미지 속 글자를 분석합니다. 발견한 항목은 원문, 위치, 스크린샷과 함께 사람이 검토할 수 있습니다.

**기본 검사·PaddleOCR·로컬 AI는 외부 API 키 없이 실행됩니다.** 외부 AI 검토는 별도 설정 후 사용자가 시작할 때 실행합니다. 탐지 결과는 검토를 돕는 단서이며 최종 판정은 직접 확인해야 합니다.

## 시작하기

1. [최신 Windows 릴리스](https://github.com/orqan137/chickadee_studio/releases/latest)에서 `Chickadee-Studio-<버전>-win-x64.zip`을 내려받습니다.
2. **전체 압축을 풀고** `Chickadee.exe`를 실행합니다. 앱·Python 검사 엔진·Chromium·모델이 포함되어 있습니다.
3. **검사 대상** 노드에서 주소를 입력하고 상단 **검사 실행**을 누릅니다.
4. **탐지 내역**에서 항목을 선택해 근거를 확인하고 검토 상태를 저장합니다.

처음에는 **검사 실행 옆 펼침 메뉴 → 데모 검사**로 둘러보세요. 인터넷 없이 사용할 수 있습니다.

> 배포 파일은 **미서명 Windows x64 ZIP**입니다. 동봉된 파일과 폴더를 함께 유지하세요. macOS는 소스 실행을 지원하며, 별도 배포 파일은 제공하지 않습니다.

[Windows 빠른 시작](docs/quickstart-windows.md) · [설정과 사용법](docs/desktop.md) · [릴리스 변경 사항](https://github.com/orqan137/chickadee_studio/releases)

## 주요 기능

| | 기능 |
| --- | --- |
| **브라우저 검사** | 같은 사이트의 링크·게시글을 탐색하고, DOM·계산된 CSS·스크롤로 나타난 내용을 수집합니다. |
| **이미지 OCR** | PaddleOCR로 한국어 이미지 글자를 읽습니다. 판독 실패·생략은 탐지 없음과 구분합니다. |
| **근거 중심 검토** | 원문·DOM 위치·이미지 근거·스크린샷을 확인하고, 검토 확인·제외·메모를 저장합니다. |
| **로그인 이어가기** | 로그인 화면을 감지하면 대기합니다. 별도 창에서 로그인한 뒤 원래 페이지의 검사를 재개합니다. |
| **검사 분석** | START부터 수집 경로를 살펴보고, 선택적으로 외부 AI 검토와 리포트 저장을 사용합니다. |
| **작업 자동화** | 탐색 속도·예약 검사를 설정하고, 데스크톱 또는 Slack·Discord 웹훅으로 완료 알림을 받습니다. |
| **결과 보관** | JSON·CSV와 검사 기록을 저장하고, 이전 결과를 다시 열어 검토를 이어갑니다. |

## 화면 둘러보기

### 탐지 내역과 근거

![원문·스크린샷·검토 상태를 함께 확인하는 탐지 내역](desktop/assets/guide/review.png)

목록에서 항목을 선택하면 오른쪽에 근거가 열립니다. 필수 탐지와 광고 의심을 구분하고, 원문을 확인한 뒤 검토 상태를 남깁니다.

### 검사 분석

![START부터 수집 경로를 확인하는 검사 분석](desktop/assets/guide/analysis.png)

실제로 관측한 페이지와 수집 동작을 그래프로 확인합니다. 외부 AI 검토는 별도 탭에서 시작하며, 원본 탐지 결과와 사람의 검토 상태를 덮어쓰지 않습니다.

<details>
<summary><strong>검사 구성 · OCR · HTTP 통신 보기</strong></summary>

**검사 대상 입력**

![검사 대상 URL 입력](desktop/assets/guide/start.png)

**이미지 OCR 설정**

![PaddleOCR 노드 설정](desktop/assets/guide/ocr.png)

**HTTP 통신 기록**

![응답 상태와 요청 메서드를 구분한 HTTP 기록](docs/assets/screenshots/http.png)

</details>

<details>
<summary><strong>설정 · 예약 · 알림 보기</strong></summary>

**일반 설정**

![탐색 범위와 실행 환경 설정](desktop/assets/guide/general.png)

**예약 검사**

![예약 검사 작성 화면](desktop/assets/guide/schedules.png)

**완료 알림**

![데스크톱과 Slack·Discord 알림 설정](desktop/assets/guide/notifications.png)

**AI 연결**

![외부 AI 연결 설정](desktop/assets/guide/ai.png)

**업데이트**

![현재 버전과 업데이트 확인](desktop/assets/guide/updates.png)

**단축키**

![앱 단축키 설정](docs/assets/screenshots/shortcuts.png)

</details>

<details>
<summary><strong>검사 기록 · 탐색 경로 · AI 검토 보기</strong></summary>

![저장된 검사 기록](desktop/assets/guide/history.png)

![페이지 탐색 경로](docs/assets/screenshots/navigation.png)

![AI 검토 시작 화면 — 외부 API 미실행 상태](docs/assets/screenshots/ai-review.png)

</details>

## 탐지 범위

| 유형 | 코드 | 확인하는 내용 |
| --- | --- | --- |
| 닮은꼴 글자 위장 | `HOMOGLYPH` | 전각·키릴·일부 그리스 문자·숫자 등의 혼합 표기 |
| 자모 분해 | `JAMO` | 분리된 한글 자모와 태그 사이에 나뉜 문구 |
| 투명 텍스트 | `TRANSPARENT` | 투명색·요소 및 조상 opacity·단색 배경과 같은 글자색 |
| 화면 밖 은닉 | `OFFSCREEN` | 음수 좌표·작은 글자·잘린 영역·숨김 요소 |

위장·은닉이 없는 도박·대출·투자·구매 유도는 **광고 의심 후보**로 별도 분류합니다. 차단·인증 필요·처리 한도·오류로 읽지 못한 내용은 정상 검사 완료와 구분합니다.

로그인은 쿠키 기반 인증을 지원합니다. 팝업·브라우저 저장소 기반 인증이나 비표준 로그인 주소는 자동 처리되지 않을 수 있습니다. 개인 Chrome 프로필은 사용하지 않으며, 로그인 쿠키는 이번 검사에서만 메모리로 유지합니다.

[탐색 범위와 제한](docs/performance.md) · [AI 검토와 전송 정보](docs/inspection-agent.md) · [결과 파일 형식](docs/result-format.md)

## 소스에서 실행

개발 기준은 **Python 3.12 · Node.js 24**입니다. Windows 배포 파일 사용자는 설치할 필요가 없습니다.

```sh
git clone https://github.com/orqan137/chickadee_studio.git
cd chickadee_studio
```

<details>
<summary><strong>macOS</strong></summary>

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

Electron과 Python 가상환경의 CPU 아키텍처를 맞춰 사용하세요. `npm start`는 Chickadee 이름의 개발용 앱을 준비합니다.

</details>

<details>
<summary><strong>Windows PowerShell</strong></summary>

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

패키징은 저장소 루트에서 `./scripts/build-desktop.ps1`로 실행합니다. 출력 경로는 `artifacts/electron-<버전>/win-unpacked/`입니다.

</details>

## 기여하기

버그 수정, 탐지 규칙 개선, 문서·번역, UI 개선에 참여할 수 있습니다.

- [이슈](https://github.com/orqan137/chickadee_studio/issues)에 재현 절차와 기대 동작을 적어 주세요.
- 변경 범위를 작게 유지하고, 관련 테스트 결과를 PR에 포함해 주세요.
- 스크린샷을 바꿀 때는 실제 앱 화면을 사용하고 개인정보·API 키를 제외해 주세요.

개발·테스트·화면 재촬영 방법은 [기여 가이드](CONTRIBUTING.md)를 참고하세요.

## 문서와 구조

| 사용자 | 개발자 |
| --- | --- |
| [Windows 빠른 시작](docs/quickstart-windows.md) | [기여 가이드](CONTRIBUTING.md) |
| [데스크톱 사용 가이드](docs/desktop.md) | [아키텍처](docs/architecture.md) |
| [검사 분석·AI 검토](docs/inspection-agent.md) | [검증 기록](docs/validation.md) |
| [결과 파일 형식](docs/result-format.md) | [외부 구성요소](docs/third-party-notices.md) |
| [CLI·호환 UI 매뉴얼](docs/manual.md) | [연구 자료](research/README.md) |

```text
chickadee/       Python 검사 엔진 · OCR · 탐지 규칙
desktop/        Electron 앱 · React UI · 데스크톱 테스트
  tests/        실제 앱 검증 · 문서 화면 촬영
scripts/        모델 준비 · 빌드 · 릴리스 검증
tests/          Python 회귀 테스트 · 로컬 테스트 사이트
docs/           사용법 · 설계 · 릴리스 노트
```

## 라이선스

[Apache License 2.0](LICENSE). 외부 구성요소와 모델에는 각 라이선스가 적용됩니다. [서드파티 고지](docs/third-party-notices.md)를 확인하세요.
