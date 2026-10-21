# Windows 패키지

사용자 요청에 따라 서명 서비스 신청·승인 대기와 서명 필수 배포 조건을 제거했습니다. 자동 테스트를 통과한 미서명 ZIP을 배포합니다. 서비스 계정이나 담당자 연락처는 필요하지 않습니다.

`windows-signatures.json`은 빌드 파일의 서명 상태를 읽어 기록하는 진단 자료입니다. 서명 여부 때문에 배포를 보류하지 않으며 인증서를 설치하거나 PC 보안 설정을 변경하지 않습니다.

Windows의 코드 무결성 정책이나 Smart App Control이 미서명 실행 파일을 차단하는 경우, 앱 자체에서 이 OS 차단을 삭제할 수는 없습니다. 미서명 배포는 해당 PC에서의 실행 허용을 보장하지 않습니다. [Microsoft 코드 서명 안내](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control)
