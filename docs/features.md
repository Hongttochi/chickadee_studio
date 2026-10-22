# 기능 안내와 실제 실행 화면

실제 Windows 앱에서 촬영한 화면입니다. 실제 사이트 검사와 로컬 OCR 검증 화면을 구분했습니다. 저장된 점수는 정확도나 위법 확률이 아닙니다.

## 녹화와 GIF

| 영상 | 내용 |
| --- | --- |
| [실제 사이트 검사](assets/demos/site-scan.webm) | 100페이지 검사 과정. 페이지 및 수집 한도에 따른 부분 결과 |
| [기능 전체 보기](assets/demos/features-details.webm) | 통계, Groq 의견, 저장, 근거 확대, 기록과 설정 |
| [긴 탐색 그래프](assets/demos/graphs-original.webm) | 전체 보기와 60개 확대 구간 |
| [한국어 OCR 검증](assets/demos/ocr-original.webm) | 로컬 검증 이미지에서 글자 추출과 줄 선택 |

![검토와 주요 기능](assets/demos/features.gif)

![이미지 OCR과 글자 영역](assets/demos/ocr.gif)

![탐색 그래프 확대와 이동](assets/demos/exploration.gif)

## 화면별 기능

### 검사 구성

진입 URL과 검사 조건을 설정합니다. 본문은 ML로 전달하고 이미지는 OCR을 거쳐 전달합니다.

![검사 구성](assets/demos/01-pipeline.png)

### 필수 기법 4종

로컬 검증 페이지에서 닮은꼴 문자, 자모 분해, 투명 문자와 화면 밖 문자를 확인합니다.

![필수 기법 4종](assets/demos/22-four-techniques.png)

### 원문과 탐지 근거

같은 항목의 원문, URL, 위치와 검토 상태를 확인합니다.

![원문과 탐지 근거](assets/demos/06-evidence.png)

### 촬영 화면 확대

검사 당시 화면을 확대합니다. 숨은 요소를 강제로 드러내지 않습니다.

![촬영 화면 확대](assets/demos/07-evidence-zoom.png)

### 이미지 OCR

한국어 검증 이미지의 추출 문구, 글자 박스와 인식 신뢰도를 확인합니다.

![이미지 OCR](assets/demos/23-ocr-boxes.png)

### OCR 줄 선택

줄을 선택하면 이미지의 해당 글자 영역을 강조합니다.

![OCR 줄 선택](assets/demos/24-ocr-line.png)

### 모델 처리 통계

ML 점수 분포와 OCR 처리 상태를 표시합니다. Laya는 미적용 상태를 그대로 표시합니다.

![모델 처리 통계](assets/demos/02-statistics.png)

### Groq 근거 검토

조회한 근거 ID와 광고 문맥 의견, 부족한 근거를 확인합니다.

![Groq 근거 검토](assets/demos/03-groq-report.png)

### Groq 누적 사용량

요청과 토큰 한도를 확인합니다. 예시 검사는 5회와 6,165토큰을 사용했습니다.

![Groq 누적 사용량](assets/demos/04-budget.png)

### 전체 탐색 그래프

100페이지에서 관측한 371개 노드 전체를 표시합니다. START와 END 표시는 UI 안내용입니다.

![전체 탐색 그래프](assets/demos/20-full-graph-overview.png)

### 탐색 경로

방문한 페이지와 대기 중인 URL을 구분합니다.

![탐색 경로](assets/demos/11-navigation.png)

### 진행 기록

실제 실행한 수집, 차단과 분석 과정을 확인합니다.

![진행 기록](assets/demos/10-events.png)

### 검사 기록

저장된 원문과 화면, Groq 의견을 다시 엽니다.

![검사 기록](assets/demos/12-history.png)

### 환경과 검사 설정

CPU와 메모리에 맞는 실행 모드, 검사 범위와 저장 위치를 설정합니다.

![환경과 검사 설정](assets/demos/13-settings-general.png)

### AI 연결

키는 비밀번호 입력으로 처리합니다. 녹화에는 키 값을 넣지 않았습니다.

![AI 연결](assets/demos/14-settings-groq.png)

### 알림 설정

완료 알림과 채널별 리포트 설정 화면입니다. 이 촬영에서는 외부 메시지를 전송하지 않았습니다.

![알림 설정](assets/demos/15-settings-notifications.png)

### 예약 검사

일정에 맞춰 저장한 검사 구성을 실행합니다. 앱이 실행 중일 때 동작합니다.

![예약 검사](assets/demos/16-settings-schedule.png)

### 단축키

화면 이동과 자주 쓰는 명령의 단축키를 설정합니다.

![단축키](assets/demos/17-shortcuts.png)

### 업데이트

새 릴리스와 다운로드 상태를 확인합니다.

![업데이트](assets/demos/18-updates.png)

### 빠른 명령

화면 이동, 결과 불러오기와 내보내기 명령을 검색합니다.

![빠른 명령](assets/demos/19-command-palette.png)

### 저장한 리포트

네트워크 요청 없이 스크린샷을 포함한 HTML을 열었습니다. 브라우저 인쇄로 PDF를 저장할 수 있습니다.

![저장한 리포트](assets/demos/26-standalone-report.png)

## 긴 그래프의 전체 구간

371개 관측 노드와 안내용 START, END를 포함해 촬영했습니다. 저장한 원문이나 그래프의 관측 내용을 추가 생성하지 않았습니다. 구간은 겹치도록 이동하며 촬영했습니다.

<details>
<summary>60개 확대 구간 펼치기</summary>

![graph-tile-001](assets/demos/graph-tile-001.png)

![graph-tile-002](assets/demos/graph-tile-002.png)

![graph-tile-003](assets/demos/graph-tile-003.png)

![graph-tile-004](assets/demos/graph-tile-004.png)

![graph-tile-005](assets/demos/graph-tile-005.png)

![graph-tile-006](assets/demos/graph-tile-006.png)

![graph-tile-007](assets/demos/graph-tile-007.png)

![graph-tile-008](assets/demos/graph-tile-008.png)

![graph-tile-009](assets/demos/graph-tile-009.png)

![graph-tile-010](assets/demos/graph-tile-010.png)

![graph-tile-011](assets/demos/graph-tile-011.png)

![graph-tile-012](assets/demos/graph-tile-012.png)

![graph-tile-013](assets/demos/graph-tile-013.png)

![graph-tile-014](assets/demos/graph-tile-014.png)

![graph-tile-015](assets/demos/graph-tile-015.png)

![graph-tile-016](assets/demos/graph-tile-016.png)

![graph-tile-017](assets/demos/graph-tile-017.png)

![graph-tile-018](assets/demos/graph-tile-018.png)

![graph-tile-019](assets/demos/graph-tile-019.png)

![graph-tile-020](assets/demos/graph-tile-020.png)

![graph-tile-021](assets/demos/graph-tile-021.png)

![graph-tile-022](assets/demos/graph-tile-022.png)

![graph-tile-023](assets/demos/graph-tile-023.png)

![graph-tile-024](assets/demos/graph-tile-024.png)

![graph-tile-025](assets/demos/graph-tile-025.png)

![graph-tile-026](assets/demos/graph-tile-026.png)

![graph-tile-027](assets/demos/graph-tile-027.png)

![graph-tile-028](assets/demos/graph-tile-028.png)

![graph-tile-029](assets/demos/graph-tile-029.png)

![graph-tile-030](assets/demos/graph-tile-030.png)

![graph-tile-031](assets/demos/graph-tile-031.png)

![graph-tile-032](assets/demos/graph-tile-032.png)

![graph-tile-033](assets/demos/graph-tile-033.png)

![graph-tile-034](assets/demos/graph-tile-034.png)

![graph-tile-035](assets/demos/graph-tile-035.png)

![graph-tile-036](assets/demos/graph-tile-036.png)

![graph-tile-037](assets/demos/graph-tile-037.png)

![graph-tile-038](assets/demos/graph-tile-038.png)

![graph-tile-039](assets/demos/graph-tile-039.png)

![graph-tile-040](assets/demos/graph-tile-040.png)

![graph-tile-041](assets/demos/graph-tile-041.png)

![graph-tile-042](assets/demos/graph-tile-042.png)

![graph-tile-043](assets/demos/graph-tile-043.png)

![graph-tile-044](assets/demos/graph-tile-044.png)

![graph-tile-045](assets/demos/graph-tile-045.png)

![graph-tile-046](assets/demos/graph-tile-046.png)

![graph-tile-047](assets/demos/graph-tile-047.png)

![graph-tile-048](assets/demos/graph-tile-048.png)

![graph-tile-049](assets/demos/graph-tile-049.png)

![graph-tile-050](assets/demos/graph-tile-050.png)

![graph-tile-051](assets/demos/graph-tile-051.png)

![graph-tile-052](assets/demos/graph-tile-052.png)

![graph-tile-053](assets/demos/graph-tile-053.png)

![graph-tile-054](assets/demos/graph-tile-054.png)

![graph-tile-055](assets/demos/graph-tile-055.png)

![graph-tile-056](assets/demos/graph-tile-056.png)

![graph-tile-057](assets/demos/graph-tile-057.png)

![graph-tile-058](assets/demos/graph-tile-058.png)

![graph-tile-059](assets/demos/graph-tile-059.png)

![graph-tile-060](assets/demos/graph-tile-060.png)

</details>

## 리포트 파일

[스크린샷이 포함된 HTML 예시](assets/demos/sample-report.html)와 [모델 평가 수치](assets/evaluation/metrics.json)를 확인할 수 있습니다. 검사 실행마다 결과 폴더에 HTML과 Markdown을 함께 저장합니다.
