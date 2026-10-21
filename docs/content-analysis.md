# 이미지·텍스트 직접 분석

`content.analyze`는 사이트 검사 없이 텍스트와 이미지를 직접 분석하는 로컬 도구입니다. 화면의 버튼·배치는 변경하지 않습니다. PaddleOCR, 문자 탐지 규칙, 광고 문맥 분류 모델, 이미지 특징 분류 모델을 사용하며 Groq 요청은 발생하지 않습니다.

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

기존 사이트 검사와 직접 분석 모두 OCR 신뢰도 0.55 이상인 줄을 사용하며 4,000자에서 잘렸는지 기록합니다. 사이트 검사 근거에는 이미지 SHA-256과 OCR 엔진·모델·신뢰도 정보를 보존합니다.

에이전트가 같은 사이트를 추가 탐색한 경우에도 OCR 이미지 원본과 관측값을 `agent.json` 및 해당 실행의 근거 폴더에 보존합니다. 이미지 ID는 조회 시 `agent_0_...` 등으로 분리하여 최초 검사의 이미지와 충돌하지 않게 합니다. 다시 열 때 파일 경로·해시·메타데이터를 검증합니다. 최초 `result.json`, CSV, 검사 보고서는 수정하지 않습니다. Groq의 기존 호출·토큰·방문 한도도 그대로 적용합니다.
