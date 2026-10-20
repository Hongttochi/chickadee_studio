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

격리 실행은 [Playwright Docker 안내](https://playwright.dev/python/docs/docker)를 참고했습니다. `deploy/seccomp_profile.json`은 microsoft/playwright v1.64.0의 Apache-2.0 배포 파일을 바탕으로 합니다. 원본 SHA-256은 `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`입니다. capability를 모두 제거한 컨테이너에서 Chromium의 자체 user namespace sandbox가 동작하도록 `chroot` syscall 허용 규칙을 추가했습니다. 컨테이너 사용자는 비관리자이며 privileged·host IPC·Docker socket·호스트 폴더 연결을 사용하지 않습니다. 원문과 변경 사항은 패키지의 `deploy` 폴더·이 문서에 보존합니다.
