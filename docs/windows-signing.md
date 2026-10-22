# Windows 배포

Windows x64 ZIP의 `Chickadee.exe`는 Electron 공식 실행 파일을 이름만 바꾸어 사용합니다. 아이콘·버전 리소스를 편집하지 않으며, 앱 화면의 로고·이름은 앱 코드에서 지정합니다. 탐색기의 EXE 아이콘과 파일 속성은 Electron 원본입니다.

공식 배포 ZIP과 실행 파일의 SHA-256은 `desktop/vendor-runtime.json`에 고정합니다. 빌드와 배포 ZIP 검증에서 실행 파일이 원본과 일치하는지 확인합니다.

기본 패키지는 미서명입니다. 인증서 설치, Windows 보안 설정 변경이나 보호 기능 해제를 수행하지 않습니다. Windows의 실행 허용 여부는 해당 환경의 정책과 파일 평판에 따릅니다.

[빠른 실행](quickstart-windows.md) · [최신 릴리스](https://github.com/orqan137/chickadee_studio/releases/latest)
