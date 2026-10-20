# Windows 빠른 실행

1. ZIP 파일을 전부 압축 해제합니다.
2. `ChickadeeBot.exe`를 더블클릭합니다. `_internal` 폴더를 같은 위치에 둡니다.
3. 검사할 URL을 입력하고 **점검 시작**을 누릅니다. 외부 사이트도 기본으로 허용됩니다.
4. 결과는 실행 파일 옆 `results` 폴더의 `result.json`, `result.csv`, `scan-report.json`으로 저장됩니다.

Python·Docker·VM 설치나 별도 옵션은 필요하지 않습니다.

`RUN_TEST_SITE.cmd`를 실행하면 사용자 테스트 게시판 주소와 사이트 설정이 미리 입력됩니다. **점검 시작**을 누르면 검사합니다. `RUN_DEMO.cmd`는 로컬 데모를 준비합니다.

로컬 주소만 검사하려면 선택적으로 `--local-only` 옵션을 사용합니다.

[저장 형식](result-format.md) · [매뉴얼](manual.md)
