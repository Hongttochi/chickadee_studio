# Chickadee Studio 0.5.0

Electron Windows 앱과 Python 검사 프로그램을 함께 배포합니다. 사용자에게 Node.js·Python·Docker 설치를 요구하지 않습니다. 디자인 기준과 참고 제품은 [DESIGN.md](../DESIGN.md)에 기록합니다.

## 검사 구성

지원 노드 여섯 개를 연결합니다. 대상 → 브라우저 → 콘텐츠 수집은 필수 경로입니다. 이후 필수 탐지와 광고 분류 중 하나 이상을 결과 출력까지 연결합니다. 포트 드래그로 연결하고, 연결선 선택 후 Delete/Backspace로 해제합니다.

분석 경로를 해제하면 해당 분석을 실행하지 않습니다. 콘텐츠 수집의 하위 링크 탐색을 끄면 입력 페이지만 검사합니다. 구성은 저장·JSON 내보내기·불러오기를 지원합니다. 임의 코드를 실행하는 범용 워크플로 엔진은 아닙니다.

## 실시간 검사

현재 URL·HTTP 응답·DOM/CSS 추출·스크롤·읽기 버튼·분석·저장 단계를 표시합니다. 방문 출처와 대기 URL도 기록합니다. 활성 노드와 연결선은 실제 이벤트로 강조하며 퍼센트를 임의 생성하지 않습니다.

화면은 실제 Chromium의 JPEG 스크린샷입니다. 콘텐츠 변경 스냅샷에서 갱신하며 연속 영상은 아닙니다. 대상 HTML·스크립트를 앱의 표시 창에 넣지 않습니다. 미리보기는 설정에서 끌 수 있고, 생성 실패 시 본문 검사는 계속합니다.

## 출력과 이력

기본 출력은 운영체제 문서 폴더 아래 `Chickadee/results/YYYYMMDD-HHMMSS-식별자`입니다. 설정에서 변경할 수 있습니다.

| 파일 | 내용 |
| --- | --- |
| result.json | 필수 기법 4종 결과 |
| result.csv | 필수 탐지·광고 의심, 고정 17개 칼럼 |
| scan-report.json | 상태·한도·방문/대기·근거·노드 구성·해시 |
| events.jsonl | 진행 단계·HTTP 응답·발견 경로·판정 이벤트 |
| last-preview.jpg / last-preview.json | 마지막 화면과 실제 촬영 URL |

최근 30개 실행은 앱 데이터 폴더의 history.json에 보관합니다. 결과 불러오기에서 result.json을 고르고 나머지 파일을 같은 폴더에 두면 근거·경로·기록을 함께 읽습니다. UI는 최근 2,000개 이벤트, 저장 로그는 최대 100,000개입니다. 마지막 화면만 보관하며 모든 스크린샷을 동영상처럼 저장하지 않습니다.

일반 광고 후보는 화면에서 **광고 의심**으로 표시합니다. 법적 불법성이나 필수 은닉 기법의 확정과 구분합니다. 중단·일부 결과·실패도 별도 상태입니다. 내부 분류 코드와 17개 CSV 칼럼은 유지합니다.

## 실행 구조

렌더러는 로컬 파일만 표시하고 Node.js 접근을 끕니다. 제한된 main/preload IPC가 자식 프로세스와 stdin/stdout JSONL로 통신합니다. 별도 웹 서버·원격 API·로그인·API 키는 사용하지 않습니다.

검사 Chromium은 임시 컨텍스트와 sandbox를 사용하며 동일 origin·GET/HEAD·다운로드/서비스워커 제한을 유지합니다. 이미지·미디어·폰트 요청은 차단하므로 일반 브라우저와 외관이 다를 수 있습니다. 이 정책은 OS 격리나 취약점 부재를 보장하지 않습니다.

## 개발과 배포

루트의 Python 3.12 가상환경에 requirements-dev.txt를 설치하고 Chromium headless shell을 준비합니다. desktop에서 Node.js 24로 npm ci, npm run build, npm start를 실행합니다. scripts/build-desktop.ps1은 Python 프로그램과 Electron 앱을 함께 빌드합니다.

scripts/engine.spec은 실제 사용하는 headless shell을 포함하고 중복된 headed Chromium은 제외합니다. artifacts/electron-0.5.0/win-unpacked 전체를 배포합니다. exe 한 파일만 배포하면 안 됩니다.

빌드 후 루트에서 `.venv/Scripts/python.exe scripts/package-desktop.py`를 실행하면 사용법·프런트엔드 라이선스와 함께 ZIP·SHA-256 파일을 만듭니다. ZIP을 다시 읽어 각 파일의 CRC도 검사합니다.

검증은 루트의 unittest discover, desktop의 npm test와 npm run smoke를 사용합니다. CHICKADEE_PACKAGED_EXE에 실행 파일 절대 경로를 지정하면 배포본으로 통합 검사합니다. 별도 테스트 폴더에서 실제 데모·화면·CSV·연결선 해제와 재연결을 확인합니다.
