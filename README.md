<div align="center">

<img src="desktop/assets/app-mark.png" width="104" alt="Chickadee" />

# Chickadee Studio

**공공 웹사이트의 위장·은닉 광고를 탐지하고, 원문과 위치를 근거로 검토하는 데스크톱 도구**

[![Latest release](https://img.shields.io/github/v/release/orqan137/chickadee_studio?style=flat&color=526d82)](https://github.com/orqan137/chickadee_studio/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/orqan137/chickadee_studio/release.yml?branch=main&label=build&style=flat)](https://github.com/orqan137/chickadee_studio/actions/workflows/release.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-526d82?style=flat)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-x64-526d82?style=flat)](docs/quickstart-windows.md)

[**Windows 다운로드**](https://github.com/orqan137/chickadee_studio/releases/latest) · [사용설명서](docs/quickstart-windows.md) · [결과 규격](docs/result-format.md) · [English](README.en.md)

</div>

![Chickadee Studio 검사 구성 화면](docs/assets/screenshots/workflow.png)

## 주요 탐지 기능

「공공 웹사이트 불법광고 탐지 도구 개발 공모전」의 주요 탐지 유형 4종을 기준으로 광고 문구의 위장·은닉 여부를 확인합니다.

| 유형 | 결과 코드 | 탐지 근거 |
| --- | --- | --- |
| 닮은꼴 글자 위장 | `HOMOGLYPH` | 키릴·전각 문자, 유사 문자·숫자 등을 섞은 표기 |
| 자모 분해 | `JAMO` | 한글 음절을 분리한 자모, 태그 사이에 나뉜 문구 |
| 투명 텍스트 | `TRANSPARENT` | `color:transparent`, 요소·조상의 투명도, 배경과 같은 글자색 |
| 화면 밖 은닉 | `OFFSCREEN` | 음수 좌표, 0~1px 글자, 잘린 영역, `display:none` 등 |

Chromium으로 페이지를 렌더링해 원문·DOM·계산된 CSS·좌표를 확인합니다. 광고 문맥과 위장·은닉 근거를 함께 사용하며, 추가 광고 문맥은 필수 4종과 분리해 기록합니다.

## 바로 실행하기

1. [최신 릴리스](https://github.com/orqan137/chickadee_studio/releases/latest)의 `Chickadee-Studio-<버전>-win-x64.zip`을 받습니다.
2. ZIP **전체를 새 폴더에 압축 해제**하고 `Chickadee.exe`를 실행합니다. 동봉된 `resources` 폴더를 함께 유지합니다.
3. **검사 대상**에 진입 URL 하나를 입력하고 **검사 실행**을 누릅니다.
4. **탐지 내역**에서 원문·위치·근거 이미지를 확인하고 검토 상태와 메모를 저장합니다.
5. **결과 폴더**에서 `result.json`과 추가 결과·CSV를 확인합니다.

Windows x64 실행본에는 Python 검사 엔진, Chromium, 한국어 OCR·로컬 ML 모델이 포함됩니다. Python·Node.js·Docker·GPU를 별도로 설치할 필요가 없습니다. **검사 실행 옆 펼침 메뉴 → 데모 검사**로 인터넷 없이 기능을 확인할 수 있습니다.

## 모집요강 대응

| 요구 항목 | 구현 내용 | 상세 안내 |
| --- | --- | --- |
| 진입 URL 1개 입력 | 같은 사이트의 하위 페이지·게시글·댓글 및 iframe 내부 요소 탐색 | [탐색 설정](docs/desktop.md) |
| 주요 탐지 유형 4종 | 유형별 원문·URL·CSS 위치·판정 근거 기록 | [요구사항](docs/requirements.md) |
| 결과 안내·관리 화면 | 탐지 목록, 근거 패널, 검토 상태·메모, 검색·필터, 검사 기록 | [화면 사용법](docs/desktop.md) |
| 적격평가용 결과 | UTF-8(BOM 없음) `result.json`, `meta`·`findings` 구조 | [결과 규격](docs/result-format.md) |
| 추가 유형 결과 | `result_extra.json`에 `ETC`·`extra_finding`으로 분리 | [추가 결과](docs/result-format.md) |
| Windows 11·일반 PC | CPU·RAM 기반 로컬 검사와 한국어 OCR | [실행 안내](docs/quickstart-windows.md) |
| 개발 산출물 | 소스코드, 빌드 절차, 사용설명서, 버전별 실행본 | [빌드](#소스에서-실행) · [릴리스](https://github.com/orqan137/chickadee_studio/releases) |
| 외부 AI 설정 | Groq 서비스·모델·환경변수 명시, 외부 파일로 키 교체 | [AI 설정](docs/inspection-agent.md) |

## 검사 흐름과 근거

본문은 ML 문맥 분석으로 전달하고, **이미지가 있을 때만 PaddleOCR로 글자를 추출한 뒤 ML로 전달**합니다. 이미지가 없으면 OCR 단계에 `이미지 없음`을 표시합니다. 이미지 근거에서는 원본, 인식 문구, 글자 위치와 신뢰도를 함께 확인할 수 있습니다.

![탐지 원문과 검토 기능](desktop/assets/guide/review.png)

검사 중인 페이지의 미리보기와 진행 기록, 실제 방문 경로를 확인할 수 있습니다. 로그인 필요 시 별도 창에서 인증한 뒤 검사를 이어가며, 저장한 결과는 사이트를 다시 방문하지 않고 열 수 있습니다.

![탐색 흐름과 검사 분석](desktop/assets/guide/analysis.png)

## 결과 파일

기본 저장 위치는 **`문서/Chickadee/results/<실행별 폴더>/`**입니다. 저장 위치를 바꾸면 해당 폴더 아래에 실행별로 생성됩니다. 실제 위치는 앱의 **결과 폴더**에서 확인합니다.

| 파일 | 내용 |
| --- | --- |
| `result.json` | 필수 4종 결과. 모든 페이지의 항목을 `findings` 배열 하나에 저장 |
| `result_extra.json` | 추가 광고 문맥 관측값. 검토 후보의 불법성을 자동 확정하지 않음 |
| `result.csv` | 필수 탐지·광고 의심 항목을 고정 17개 칼럼으로 내보내기 |
| `scan-report.json` | 검사 상태, 수집 범위, 오류, OCR·문맥 분석과 근거 정보 |
| `review.json` | 검토 상태와 메모 |

`result.json`의 검출 단위는 `(url, location, technique)`입니다. 같은 요소에 기법이 둘이면 별도 항목으로 기록하고, 원문은 정규화 전 그대로 보존합니다. iframe 위치는 `iframe[src="절대주소"] >>> 내부 선택자` 형식으로 기록합니다. 결과가 없을 때도 `findings: []`를 생성합니다.

<details>
<summary><strong>result.json 구조 예시</strong></summary>

```json
{
  "meta": {
    "topic": "TOPIC",
    "entry_url": "https://example.org/board",
    "started_at": "2026-10-23T10:00:00+09:00",
    "finished_at": "2026-10-23T10:00:12.500+09:00",
    "elapsed_sec": 12.5
  },
  "findings": [
    {
      "id": "f_00001",
      "url": "https://example.org/board/view?id=1",
      "is_violation": true,
      "location": "article.post > p:nth-of-type(1)",
      "evidence_text": "ｃａｓｉｎｏ 가입 보너스 지급",
      "technique": "HOMOGLYPH"
    }
  ]
}
```

필드와 인코딩은 [JSON Schema](schemas/result.schema.json) 및 [결과 규격](docs/result-format.md)을 참고하세요. 파일별 생성 위치와 실행 방법은 [사용설명서 첫 장](docs/quickstart-windows.md)에 있습니다.

</details>

## 선택 AI 검토

기본 검사·OCR·ML은 API 키 없이 로컬에서 동작합니다. 추가 근거 검토는 사용자가 Groq 키를 설정하고 실행할 때 사용합니다.

| 설정 | 값 |
| --- | --- |
| 서비스 | Groq |
| 기본 모델 | `openai/gpt-oss-20b` |
| 외부 파일의 키 이름 | `GROQ_API_KEY` |
| 기본 누적 한도 | 검사당 6회·24,000토큰 |

앱 AI 설정에서 키를 입력하거나 `Chickadee.exe --groq-env-file "외부 설정 파일 경로"`로 읽습니다. 키 교체에 재빌드가 필요하지 않습니다. [설정 예시](.env.example) · [에이전트 설정·사용량](docs/inspection-agent.md)

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

## 문서

[사용설명서](docs/quickstart-windows.md) · [상세 기능](docs/desktop.md) · [모집요강 요구사항](docs/requirements.md) · [제출 체크리스트](docs/submission-checklist.md) · [아키텍처](docs/architecture.md) · [검증](docs/validation.md) · [기여 안내](CONTRIBUTING.md)

## 라이선스

[Apache License 2.0](LICENSE). 외부 구성요소·모델의 라이선스와 고지는 [외부 구성요소 안내](docs/third-party-notices.md)에 정리되어 있습니다.
