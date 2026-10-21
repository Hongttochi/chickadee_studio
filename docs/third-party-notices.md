# 사용 구성요소와 배포 참고

이 저장소에서 생성한 코드를 제외한 구성요소의 라이선스는 각 프로젝트를 따릅니다. 프로젝트 전체의 라이선스는 아직 정하지 않았습니다.

| 구성요소 | 용도 | 공식 출처 |
| --- | --- | --- |
| Python / Tcl·Tk | 실행 환경, Tkinter 화면 | https://www.python.org/psf/license/ / https://www.tcl-lang.org/software/tcltk/license.html |
| Playwright | 브라우저 제어 | https://github.com/microsoft/playwright-python/blob/main/LICENSE |
| Chromium Headless Shell | 렌더링 엔진 | https://www.chromium.org/chromium-projects/ |
| PyInstaller | Windows 패키징 | https://pyinstaller.org/en/stable/license.html |
| jsonschema | 출력·불러오기 형식 검증 | https://github.com/python-jsonschema/jsonschema |
| PaddleOCR / PaddlePaddle | PP-OCRv5 모바일 탐지·한국어 인식 모델, 로컬 CPU 추론 | https://github.com/PaddlePaddle/PaddleOCR / https://github.com/PaddlePaddle/Paddle |
| OpenCV / NumPy / Pillow / pyclipper / PyYAML | OCR 전처리·좌표·이미지 처리·모델 설정 | 배포본의 licenses/OCR-Third-Party.txt |
| Electron | Windows 앱 셸 | https://github.com/electron/electron/blob/main/LICENSE |
| React | 화면 구성 | https://github.com/facebook/react/blob/main/LICENSE |
| React Flow | 노드·포트·연결 편집 | https://github.com/xyflow/xyflow/blob/main/LICENSE |
| Lucide | 기능 아이콘 | https://github.com/lucide-icons/lucide/blob/main/LICENSE |
| Pretendard | 로컬 글꼴, SIL Open Font License | https://github.com/orioncactus/pretendard/blob/main/LICENSE |
| Unicode confusables | 제한된 닮은꼴 문자 매핑, Unicode License V3 | https://www.unicode.org/reports/tr39/ |

Unicode 데이터는 `chickadee/data/confusables-ascii.json`에 버전·원본 SHA-256·필터와 함께 고정하며, 원문 라이선스는 `chickadee/data/LICENSE-UNICODE.txt`에 보존합니다. 이 폴더도 검사 엔진 패키지에 포함합니다.

PaddleOCR 공식 모델은 [PP-OCRv5 모바일 탐지](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det)와 [한국어 인식](https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec)을 사용합니다. Apache-2.0 모델의 revision·파일별 SHA-256은 `chickadee/data/ocr-models.json`에 고정합니다. DB 탐지·CTC 인식 전후처리를 연결한 자체 어댑터에서 PaddlePaddle CPU 추론을 수행하며 PaddleX 파이프라인의 자동 다운로드를 사용하지 않습니다. 원문 라이선스와 패키지 고지는 `desktop/licenses/OCR-Third-Party.txt`에 보관합니다.

Playwright가 동봉하는 Node.js·브라우저 및 의존성의 라이선스·고지 파일도 배포본 내부에 유지해야 합니다. Electron 배포본의 `resources`, Chromium 라이선스 파일과 검사 프로그램의 `_internal`을 유지합니다. Pretendard 라이선스는 `desktop/licenses/Pretendard-OFL.txt`에 보관합니다. 이 목록은 최종 제출 시 필요한 전체 의존성·라이선스 검토를 대신하지 않습니다.

원래 README 로고는 `desktop/assets/logo-original.png`에 보존했습니다. `app-mark.png`는 사용자 요청에 따라 해당 이미지를 참조해 GPT 이미지 도구로 생성한 새·돋보기 부분의 변형입니다. ICO는 같은 이미지의 Windows 아이콘 형식 변환본입니다.

구현 참고: [Playwright 설치](https://playwright.dev/python/docs/library), [프레임 API](https://playwright.dev/python/docs/api/class-frame), [PyInstaller 연동](https://playwright.dev/python/docs/library#pyinstaller).

격리 실행은 [Playwright Docker 안내](https://playwright.dev/python/docs/docker)를 참고했습니다. `deploy/seccomp_profile.json`은 microsoft/playwright v1.64.0의 Apache-2.0 배포 파일을 바탕으로 합니다. 원본 SHA-256은 `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`입니다. capability를 모두 제거한 컨테이너에서 Chromium의 자체 user namespace sandbox가 동작하도록 `chroot` syscall 허용 규칙을 추가했습니다. 컨테이너 사용자는 비관리자이며 privileged·host IPC·Docker socket·호스트 폴더 연결을 사용하지 않습니다. 원문과 변경 사항은 패키지의 `deploy` 폴더·이 문서에 보존합니다.
