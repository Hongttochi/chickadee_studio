# 사용 구성요소와 배포 참고

이 저장소에서 생성한 코드를 제외한 구성요소의 라이선스는 각 프로젝트를 따릅니다. 프로젝트 전체의 라이선스는 아직 정하지 않았습니다.

| 구성요소 | 용도 | 공식 출처 |
| --- | --- | --- |
| Python / Tcl·Tk | 실행 환경, Tkinter 화면 | https://www.python.org/psf/license/ / https://www.tcl-lang.org/software/tcltk/license.html |
| Playwright | 브라우저 제어 | https://github.com/microsoft/playwright-python/blob/main/LICENSE |
| Chromium Headless Shell | 렌더링 엔진 | https://www.chromium.org/chromium-projects/ |
| PyInstaller | Windows 패키징 | https://pyinstaller.org/en/stable/license.html |
| jsonschema | 출력·불러오기 형식 검증 | https://github.com/python-jsonschema/jsonschema |

Playwright가 동봉하는 Node.js·브라우저 및 의존성의 라이선스·고지 파일도 배포본 내부에 유지해야 합니다. 실행 폴더의 `_internal`을 임의로 삭제하지 마세요. 이 목록은 최종 제출 시 필요한 전체 의존성·라이선스 검토를 대신하지 않습니다.

구현 참고: [Playwright 설치](https://playwright.dev/python/docs/library), [프레임 API](https://playwright.dev/python/docs/api/class-frame), [PyInstaller 연동](https://playwright.dev/python/docs/library#pyinstaller).
