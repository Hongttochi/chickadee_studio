# 이미지·텍스트 직접 분석

`content.analyze`는 사이트 검사 없이 텍스트와 이미지를 직접 분석하는 로컬 백엔드 도구입니다. PaddleOCR, 문자 탐지 규칙, 광고 문맥 분류 모델, 이미지 특징 분류 모델을 사용하며 Groq 요청은 발생하지 않습니다.

## 호출

기존 stdio JSON-lines 백엔드에서 다음과 같이 시작합니다. `text`와 `image_data_url`은 하나 이상 필요하며 함께 보낼 수도 있습니다.

```json
{"id":1,"method":"content-analyze","params":{"text":"caѕino 가입 보너스"}}
```

응답의 `result.analysis_id`로 진행 상태와 결과를 조회합니다. ID는 매번 생성되는 32자리 소문자 16진수입니다.

```json
{"id":2,"method":"content-analyze","params":{"analysis_id":"응답에서 받은 실제 ID"}}
```

같은 조회 인자에 `"cancel":true`를 추가하면 실행 중인 분석을 취소합니다. `tool-call`에서 `name: "content.analyze"`, `arguments: {...}`로도 동일하게 호출할 수 있습니다. Electron preload는 하나의 `window.chickadee.analyzeContent({...})` 메서드를 제공합니다.

```javascript
const job = await window.chickadee.analyzeContent({
  text: '도서관 이용 안내',
  image_data_url: imageDataUrl,
});
// content_analysis 이벤트의 완료 상태를 받거나 analysis_id로 조회
const state = await window.chickadee.analyzeContent({ analysis_id: job.analysis_id });
```

텍스트는 4,000자, 이미지 data URL은 900,000자까지입니다. 이미지는 PNG/JPEG/WebP/GIF의 base64 data URL만 받습니다. 파일 경로·웹 이미지 URL을 백엔드에서 열지 않습니다. 기존 stdio 한 줄 크기 한도 안에서 처리합니다.

## 반환 데이터

작업 상태는 `running`, `completed`, `partial`, `failed`, `cancelled`입니다. 시작 응답은 `started`입니다. 완성된 분석은 `result` 안에 있습니다.

| 필드 | 내용 |
| --- | --- |
| `sources[]` | 직접 입력 `provided_text`와 OCR `image_ocr`를 분리한 원문·출처 |
| `sources[].unicode_analysis` | 문자 변형 탐지 결과 |
| `sources[].ad_candidates` | 광고 문맥 규칙의 검토 항목 |
| `sources[].local_ai.text` | 무료 문자 분류 모델의 관측값 |
| `sources[].local_ai.laya` | 독립 검증을 통과해 설치한 Laya의 로컬 문맥 검토. 미설치·검증 대기는 `unavailable` |
| `sources[].original_unicode_observed` | 입력 텍스트는 true, 이미지 OCR은 false |
| `image.local_ai.visual` | 제출한 이미지 자체의 분류 관측값 |
| `image.ocr` | 인식 상태·문구·좌표·인식 신뢰도 |
| `sources[].ocr` | 신뢰도 기준·채택/제외 줄 수·평균 신뢰도·문구 잘림 여부 |
| `runtime_environment` | 이 작업에 적용한 실행 모드와 기능 상태 |
| `paid_requests` | 항상 0 |

직접 입력과 OCR을 섞어 하나의 광고 문맥으로 판단하지 않습니다. OCR에서 복원한 글자는 이미지에 사용된 원래 유니코드 코드포인트의 증거로 취급하지 않습니다. 이미지 분류는 검토 신호이며 피싱 확정 결과가 아닙니다.

전체 작업 시간은 60초로 제한합니다. OCR 실패 시 입력 텍스트의 결과는 유지하고 `partial`로 반환합니다. 신뢰할 수 있는 문구를 읽지 못했을 때도 `recognition_status: "unreadable"`과 `partial`을 반환합니다. 절약 모드에서는 이미지 분류를 유지하고 OCR은 `skipped`와 `reason: "economy"`를 반환합니다. 진행 이벤트는 ID·상태·단계만 전달하고 이미지나 원문을 로그에 넣지 않습니다.

분석은 백그라운드에서 하나씩 실행합니다. 사이트 검사·에이전트·OCR 환경 검사와 동시 시작하지 않으며 일반 상태 조회는 계속 응답합니다. 마지막 작업의 결과만 메모리에 유지하고 새 작업은 이를 교체합니다. 직접 입력 원본·결과를 검사 기록에 자동 저장하지 않습니다.

## 웹 검사와 공통 처리

이미지는 `OCR → ML → Laya` 순서로 처리하며 직접 입력한 문자는 OCR을 거치지 않습니다. 입력 인자·결과 조회 방식·`result.json`과 CSV 칼럼은 유지합니다. Laya 신호는 근거의 `local_ai.laya`에 추가하고 원문·기존 규칙 탐지·사람의 검토 결과를 덮어쓰지 않습니다. Groq와 별개이며 키·API·인터넷 접속을 사용하지 않습니다.

Laya는 원문이 같은 영역을 중복 추론하지 않고, 사이트 검사당 최대 12개 문맥을 검토합니다. ML에서 판단 경계에 가까운 문맥을 먼저 검토합니다. 생략·미설치·실행 오류·취소는 정상 판정으로 간주하지 않습니다. 노드 캔버스에는 기존 OCR·ML 단계와 Laya 노드 하나를 사용하며 기존 사용자 배치는 유지합니다. 불러온 과거 결과에 Laya 관측값을 소급해 붙이지 않습니다.

### 로컬 Laya 연결

[한국어 문맥 모델 팩](https://github.com/orqan137/chickadee_studio/releases/tag/laya-ko-v1)은 Laya Multilingual 전체 모델을 한국어 자료로 학습한 가중치입니다. 원문만으로 판단 가능한 자료와 출처 문맥이 필요한 자료를 구분해 독립 검증했으며, 실제 앱에서 문맥 8개의 처리를 확인했습니다. 결과와 해시는 [공개 평가 수치](assets/evaluation/metrics.json)에 있습니다.

모델 팩에서 `laya-config.zip`, `best.safetensors`, `model.safetensors`, `SHA256SUMS.txt`를 내려받습니다. 설정 ZIP을 `laya` 폴더에 압축 해제한 뒤 `best.safetensors`는 그 폴더에, `model.safetensors`는 `base/` 아래에 넣습니다. 전체 모델과 설정에는 약 1.9GB의 공간이 필요하며 실행 환경 설치 공간은 별도입니다.

소스 개발 환경에서 다음과 같이 로컬 CPU 실행 환경을 준비하고 등록합니다.

```powershell
py -3.12 -m venv .venv-laya
.\.venv-laya\Scripts\python.exe -m pip install -r requirements-laya.txt
.\.venv\Scripts\python.exe scripts/activate_laya.py --bundle 'C:\모델\laya' --python .\.venv-laya\Scripts\python.exe
```

등록 후 앱을 다시 실행하면 사용자 설정 폴더의 `laya.json`에서 모델과 실행 환경을 읽습니다. Windows의 기본 위치는 `%APPDATA%/Chickadee/laya.json`입니다. 설정에는 모델 경로와 Python 경로만 저장합니다. API 키와 원문은 포함하지 않습니다.

추론용 묶음은 `manifest.json`, `base/`, `best.safetensors`로 구성됩니다. 파일 크기와 SHA-256, 평가한 가중치의 해시와 보정 온도를 확인하고 경로 이탈이나 목록에 없는 모델 파일을 거부합니다. 가중치는 safetensors 형식입니다. 실행 시 사용 가능한 메모리가 3GB 미만이면 Laya를 건너뛰고 OCR과 RF 결과를 보존합니다.

환경변수로 지정하려면 `CHICKADEE_LAYA_MODEL_DIR`에 모델 폴더를, `CHICKADEE_LAYA_PYTHON`에 Python 실행 파일의 절대 경로를 설정합니다. 별도 설정 파일은 `CHICKADEE_LAYA_CONFIG`로 지정할 수 있습니다. 가중치와 실행 환경을 자동으로 다운로드하지 않으며, API 호출 없이 PC에서 실행합니다.

기존 사이트 검사와 직접 분석 모두 OCR 신뢰도 0.55 이상인 줄을 사용하며 4,000자에서 잘렸는지 기록합니다. 사이트 검사 근거에는 이미지 SHA-256과 OCR 엔진·모델·신뢰도 정보를 보존합니다.

에이전트가 같은 사이트를 추가 탐색한 경우에도 OCR 이미지 원본과 관측값을 `agent.json` 및 해당 실행의 근거 폴더에 보존합니다. 이미지 ID는 조회 시 `agent_0_...` 등으로 분리하여 최초 검사의 이미지와 충돌하지 않게 합니다. 다시 열 때 파일 경로·해시·메타데이터를 검증합니다. 최초 `result.json`, CSV, 검사 보고서는 수정하지 않습니다. Groq의 기존 호출·토큰·방문 한도도 그대로 적용합니다.
