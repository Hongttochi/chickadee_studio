# Windows code signing

현재 상태: **무료 서명 신청 준비, 인증서·서명 서비스 승인 미등록**. 서명이 완료되었다거나 이 PC에서 최종 Electron 실행이 통과했다는 의미가 아닙니다.

## Code signing policy

신뢰할 수 있는 Windows Authenticode 서명과 실제 네이티브 앱 테스트를 통과한 파일만 정식 GitHub Release로 게시합니다. 자체 서명 인증서를 신뢰 저장소에 넣거나 Windows 정책·Defender·Smart App Control을 변경하지 않습니다. 무료 서비스 승인 전에는 자동 유료 서비스 대체 호출을 하지 않습니다.

무료 경로는 [SignPath Foundation](https://signpath.org/apply) 신청입니다. [조건](https://signpath.org/terms)에 따라 공개 라이선스, 프로젝트 심사, GitHub 빌드 출처 검증, 릴리스별 담당자 승인이 필요합니다. 채택 여부와 처리 기간은 재단이 결정합니다. 이 문서는 신청 준비이며 아직 SignPath 제공 프로젝트로 등록되었다는 표시는 아닙니다.

## 신청 초안

| 항목 | 내용 |
| --- | --- |
| 프로젝트 | Chickadee Studio |
| 저장소·소스 | https://github.com/orqan137/chickadee_studio |
| 라이선스 | Apache-2.0, 루트 LICENSE·NOTICE |
| 배포·설명 | README.md와 GitHub Releases |
| 기능 | 공공 웹사이트의 위장·은닉 광고 기법을 수집한 근거와 함께 검토하는 Windows 앱. 한국어 이미지 OCR, 무료 문자·화면 분류 모델, 사용자 입력 Groq API 키를 이용한 추가 검토 지원 |
| 네트워크·개인정보 | 운영자가 지정한 사이트를 검사합니다. 운영자가 입력한 Groq 키로 AI 검토를 실행할 때 선택된 근거 문맥을 Groq에 전송하며 키는 세션 메모리에만 보관합니다. 자동 업데이트 확인·사용자가 설정한 알림 채널은 각각 GitHub·지정 채널에 연결합니다. 조사 데이터·학습 원본·키는 배포하지 않습니다. |
| 제출·유지관리 책임 | 저장소 소유자 orqan137. 실제 신청 연락처와 최종 서명 승인자는 소유자가 서비스 신청에서 지정해야 합니다. 팀원 2단계 인증도 확인해야 합니다. |
| 아직 하지 않은 일 | 서비스 가입·약관 동의·연락처 제출·재단 심사 신청·인증서 발급·실제 서명. 이 항목은 코드만으로 대체할 수 없습니다. |

서비스가 프로젝트를 승인하면, 제공받은 조직·프로젝트·서명 정책으로 다음 GitHub 설정을 등록합니다. 개인키나 API 토큰을 저장소 파일·이슈·채팅에 넣지 않습니다.

| GitHub 설정 | 값 |
| --- | --- |
| Secret `SIGNPATH_API_TOKEN` | 승인된 서비스의 서명 요청 권한 토큰 |
| Variable `SIGNPATH_ORGANIZATION_ID` | 승인 후 받은 조직 ID |
| Variable `SIGNPATH_PROJECT_SLUG` | 승인된 프로젝트 slug |
| Variable `SIGNPATH_SIGNING_POLICY_SLUG` | 무료 프로덕션 인증서와 사람의 승인 절차가 연결된 정책 slug |
| Variable `SIGNPATH_ENABLED` | 위 등록과 무료 서비스 승인 완료 후에만 `true` |

SignPath 쪽 Artifact Configuration은 `actions/upload-artifact`가 만든 ZIP의 내부 앱 파일을 대상으로 구성해야 합니다. Windows 네이티브 파일(EXE·DLL·PYD·NODE)과 원본 라이선스·제품 메타데이터를 검토하고 재단이 허용하는 서명 범위를 확정해야 합니다. 해당 설정·인증서가 없는 상태에서 테스트 인증서나 다른 서비스를 자동 대체하지 않습니다.

## 연결된 빌드 흐름

1. GitHub-hosted Windows runner에서 소스·모델·화면 검사 후 앱을 빌드합니다.
2. 서비스가 활성화되어 있으면 원본 빌드 폴더를 GitHub Artifact로 올리고 고정 커밋의 공식 SignPath Action으로 서명 승인을 요청합니다.
3. 반환 파일은 목록이 일치하고 모든 비실행 파일(앱 코드·디자인·모델 포함)의 바이트가 원본과 같아야 수용합니다.
4. Windows의 `Get-AuthenticodeSignature`로 네이티브 파일들의 신뢰 체인과 코드 서명 용도를 확인한 뒤 앱을 실행합니다. 이 과정은 OS 보안 설정을 수정하지 않습니다.
5. 실제 Electron 검사·기록·OCR·실행 환경 테스트가 통과하면 ZIP·SHA-256을 생성합니다. 전체 서명 검증이 통과한 경우에만 정식 릴리스를 게시합니다.

서비스가 등록되지 않으면 미서명 테스트 빌드와 로그는 Actions Artifact로 보관하고 정식 릴리스는 보류합니다. 이 테스트 빌드의 SHA-256·ZIP 무결성 검증은 Windows 게시자 신뢰 검증을 대신하지 않습니다.

관련 구현: `.github/workflows/release.yml`, `scripts/verify-windows-signatures.ps1`, `scripts/accept_signed_app.py`. 실제 서버 서명 왕복은 서비스 등록 전이므로 아직 검증하지 못했습니다.
