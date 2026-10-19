# 실행·빌드 및 사용설명서

**결과 저장 위치:** 실행 파일로 실행하면 `ChickadeeBot.exe`가 있는 폴더의 `result.json`과 `scan-report.json`에 저장합니다. 소스 실행 기본값은 저장소 최상위 폴더입니다. 화면의 **저장 폴더** 또는 `--output-dir`로 변경할 수 있으며, 화면에도 실제 저장 폴더를 표시합니다. 두 파일은 새 실행 종료 시 교체됩니다. `result_extra.json`은 추가 유형 미구현으로 생성하지 않습니다.

## Windows 실행 파일 사용

1. `dist/ChickadeeBot` **폴더 전체**를 쓰기 가능한 폴더로 복사하거나 배포 압축 파일을 해제합니다. `_internal` 폴더도 필요합니다.
2. `ChickadeeBot.exe`를 실행합니다. Python 설치·API 키·GPU는 필요하지 않습니다. 브라우저 엔진은 패키지에 포함됩니다.
3. **로컬 데모 준비**를 누르고 **탐지 시작**을 누르면 가상 사이트를 점검합니다.
4. 실제 사이트는 `http://` 또는 `https://` URL을 입력하고 탐지 시작을 누릅니다.
5. 결과 행을 선택하면 원문·페이지 URL·요소 선택자를 확인할 수 있습니다. 오른쪽 유형 필터로 목록을 좁힐 수 있습니다.
6. 완료 상태와 저장 안내를 확인하고 `result.json`을 사용합니다. **일부 결과·중단·실패** 상태에서는 `scan-report.json`의 누락·오류를 확인하세요.

기본값은 최대 50페이지, 전체 300초, 페이지당 15초, 렌더링 대기 500ms씩 두 번입니다. 전체 제한시간은 최대 1800초입니다. 중단 시 수집된 결과를 저장합니다. 브라우저 정리와 디스크 쓰기에 추가 시간이 걸릴 수 있으며 `elapsed_sec`는 브라우저 준비·탐색·정리까지 측정합니다. 결과 파일을 쓰는 시간은 포함하지 않습니다.

## 소스에서 실행

검증 환경은 Windows 11 x64, Python 3.12입니다. 아래 명령은 저장소 폴더의 PowerShell에서 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH = '0'
.\.venv\Scripts\python.exe -m playwright install chromium --only-shell
.\.venv\Scripts\python.exe -m chickadee --demo
```

`py`가 없으면 설치된 Python 3.12 실행 파일의 경로로 첫 명령을 바꿉니다. 가상환경 활성화 스크립트 실행은 필요하지 않습니다. 브라우저 설치는 최초 한 번 필요하며 실행 중에는 사용자의 Chrome 프로필이나 탭을 사용하지 않습니다.

화면 없이 점검할 수도 있습니다.

```powershell
# 로컬 데모: 가상 사이트 시작 -> 점검 -> 결과 저장 -> 사이트 종료
.\.venv\Scripts\python.exe -m chickadee --demo --cli --output-dir artifacts/demo

# 실제 입력 URL 점검
.\.venv\Scripts\python.exe -m chickadee --scan 'https://example.go.kr/' --max-pages 50 --timeout 300 --output-dir artifacts/scan
```

CLI 종료 코드는 완료 `0`, 일부 결과·중단 `2`, 실패 `1`입니다. 배포 실행 파일도 같은 인자를 지원하지만 콘솔 창이 없는 빌드이므로 결과 파일·실행 보고서로 확인합니다. 입력 오류로 실행되지 않으면 새 결과 파일은 생성하지 않습니다.

## 출력 파일 해석

- `result.json`: 모집요강의 필수 4종 결과만 담습니다. UTF-8(BOM 없음), 최상위 `meta`, `findings` 구조입니다. 0건도 빈 배열을 저장합니다.
- `scan-report.json`: `completed`, `partial`, `cancelled`, `failed` 상태, 점검한 페이지, 남은 페이지 수, 누락·오류, 실행 제한과 출력 경로를 담습니다.
- 보고서의 `result_sha256`이 `result.json` 바이트의 SHA-256과 일치하면 같은 실행의 파일 쌍입니다. 쓰기 도중 장애가 나면 파일 쌍이 맞지 않을 수 있습니다.
- `is_violation: true`는 규칙에 걸린 의심 항목을 뜻합니다. 법적 판단을 대신하지 않습니다.
- iframe 선택자의 `src`는 모집요강에 따라 절대주소입니다. 상대주소 iframe을 재조회할 때는 실제 `src` 속성도 절대주소로 해석하여 비교해야 합니다.

폴더 쓰기 권한이 없거나 디스크가 가득 차면 화면에 저장 실패를 표시합니다. 이전 파일을 이번 실행 결과로 사용하지 마세요. 새 실행 전 파일은 자동 삭제하지 않으며 정상 또는 일부 결과를 저장할 때 교체합니다.

## 테스트와 Windows 빌드

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

결과는 `dist/ChickadeeBot/ChickadeeBot.exe`입니다. 빌드는 Windows에서 수행하며 전체 폴더를 전달해야 합니다. 최초 브라우저 설치·빌드에는 네트워크 연결이 필요합니다. PyInstaller는 설치된 Playwright의 브라우저 파일을 수집하므로 다른 브라우저까지 추가 설치한 개발 환경에서는 패키지가 커질 수 있습니다.

실행 파일 확인 예시:

```powershell
$taskRun = Start-Process -FilePath '.\dist\ChickadeeBot\ChickadeeBot.exe' -ArgumentList '--demo --cli --output-dir artifacts/frozen-demo' -WindowStyle Hidden -Wait -PassThru
$taskRun.ExitCode
Get-Content artifacts/frozen-demo/scan-report.json
```

## 데모의 범위와 한계

- 같은 origin(스킴·호스트·포트)의 일반 링크를 따라 탐색하며 쿼리 값이 다른 게시글을 구분합니다. 삽입된 iframe은 외부 origin도 검사하고 중첩 경로를 남깁니다.
- 브라우저에 실제로 로드된 게시글·댓글을 검사합니다. 로그인, 폼 제출, 버튼으로만 접근하는 페이지, 무한 스크롤 전체 수집은 지원하지 않습니다.
- 광고 키워드·안내문 제외 규칙과 Unicode/CSS 규칙을 결합합니다. 문맥에 따라 오탐·누락이 있으며 자체 테스트 통과가 비공개 평가 사이트의 성능을 보장하지 않습니다.
- `opacity`, 투명색, 단색 배경과 같은 글자색, `display:none`, `visibility:hidden`, 0~1px 글자, 음수 화면 밖 배치를 처리합니다. 복잡한 배경 이미지·그라데이션·가림·모든 CSS 변형을 판별하지는 않습니다.
- 이미지 OCR, CSS 생성 콘텐츠, Shadow DOM, 추가 유형 출력, AI 판정은 구현하지 않았습니다. 외부 AI 서비스·모델·환경변수는 없습니다.
- 요소·링크 20000개, 요소 텍스트 20000자 수집 한도가 있으며 초과 시 일부 결과로 보고합니다.
- 로컬 데모는 정상 대조군을 포함한 4페이지, 중첩 iframe을 사용하며 예상 검출은 14건입니다. 실제 사이트의 정확도 수치와는 구분해야 합니다.

공모전 최종 제출 전에는 개발 도구가 전혀 없는 별도 Windows 11 PC에서 재검증하고 신청 서류·최종 기획서를 함께 준비해야 합니다.
