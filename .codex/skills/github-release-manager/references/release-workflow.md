# Release 워크플로 구현 기준

사용자 예시의 구조를 재사용하되 앱 이름 `a8a`, 경로, 환경변수와 빌드 명령은 저장소에서 확인한다. 예시에 첨부된 로컬 스크린샷 경로는 명령의 일부가 아니다.

## 공통

- 워크플로 이름은 `Release`, 기본 트리거는 `main`·`master` push다. 사용자 요청이나 기존 정책에 따라 변경한다.
- 기본 권한은 `contents: read`, 게시 job만 `contents: write`로 설정한다.
- 모든 job은 동일한 실행의 commit을 checkout한다. 게시할 태그도 같은 SHA를 가리켜야 한다.
- Node 22 및 사용자 예시의 `actions/checkout@v4`, `actions/setup-node@v4`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`를 참고하되, 적용 시 저장소 정책과 공식 지원 상황을 확인한다. 무관한 버전 업그레이드는 묶지 않는다.
- 앱이 하위 폴더에 있으면 `working-directory`, npm cache의 `cache-dependency-path`, artifact 경로를 각각 조정한다. `defaults.run`은 `uses` 단계 경로에 적용되지 않는다.
- 동시에 게시하지 않도록 워크플로 단위의 공통 concurrency group과 `cancel-in-progress: false`를 고려한다. concurrency는 모든 push를 보존하는 FIFO 큐가 아니므로 모든 커밋 배포가 필요한 요구에는 별도 설계가 필요하다.

## version

Node 설치 뒤 저장소의 실제 버전 원본을 읽는다. 예시의 추출 명령:

```bash
version=$(node -e "const fs=require('fs'); const text=fs.readFileSync('src/main/appVersion.ts','utf8'); const match=text.match(/APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]/); if(!match){throw new Error('APP_VERSION not found')} console.log(match[1])")
if ! printf '%s' "$version" | grep -Eq '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]{2}\.[0-9]{2}$'; then
  echo "Invalid APP_VERSION: $version" >&2
  exit 1
fi
echo "app_version=$version" >> "$GITHUB_OUTPUT"
```

이는 형식 검사다. 실제 날짜·시각 유효성 검사가 필요하면 별도로 구현한다. 주석의 문자열이나 여러 선언이 잘못 선택되지 않도록 실제 원본 구조를 확인한다.

step `id: version`과 job output `app_version: ${{ steps.version.outputs.app_version }}`을 연결한다. 후속 job은 `needs.version.outputs.app_version`을 사용한다.

## OS별 빌드

두 job 모두 `needs: version`이다. 버전과 `${{ github.repository }}`를 앱의 버전·업데이트 저장소 환경변수로 전달한다.

Windows는 `windows-latest`, PowerShell을 사용한다.

```powershell
npm ci
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm run version:stamp -- $env:A8A_APP_VERSION
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm run build:win
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

가능하면 각 명령을 독립된 step으로 둔다. 필수 산출물 예시:

- `dist/a8a-Setup-<version>.exe`
- `dist/a8a-Setup-<version>.exe.blockmap`
- `dist/a8a-Portable-<version>.exe`

각 파일에 `Test-Path -PathType Leaf`를 적용하고 `Get-FileHash -Algorithm SHA256`으로 소문자 해시를 구한다. `<hash>  <basename>`을 ASCII `<asset>.sha256`에 기록한다.

macOS는 `macos-latest`에서 `npm ci`, `npm run version:stamp -- "$A8A_APP_VERSION"`, `npm run build:mac`을 실행한다. 예시는 서명 없이 `CSC_IDENTITY_AUTO_DISCOVERY: "false"`를 사용하지만 이미 있는 서명·공증 설정을 제거하지 않는다.

산출물 이름 예시:

- `dist/a8a-Mac-<arch>-<version>.dmg`
- `dist/a8a-Mac-<arch>-<version>.dmg.blockmap`
- `dist/a8a-Mac-<arch>-<version>.zip`

실제 설정에 있는 아키텍처마다 필수 파일을 명시해 검사한다. glob 하나가 매칭된다는 이유로 모든 아키텍처가 생성됐다고 간주하지 않는다. blockmap은 빌더가 생성하도록 설정된 경우 필수로 검증하고 업로드한다.

macOS 체크섬은 `dist` 안에서 basename을 사용해 작성한다.

```bash
cd dist
shasum -a 256 "$asset_name" > "$asset_name.sha256"
```

`dist/`가 체크섬 내부에 포함되면 사용자가 같은 폴더에 다운로드한 뒤 검증하기 어렵다. 최소한 DMG와 ZIP의 체크섬을 제공하고, blockmap을 배포하면 그 체크섬도 함께 제공할 수 있다.

artifact 이름은 `windows-release-assets`, `macos-release-assets`로 분리하고 `if-no-files-found: error`를 설정한다. 빌드 명령의 자동 publish는 비활성화하여 게시 job과 중복 배포되지 않게 한다.

자동 업데이트를 사용하는 앱은 updater 구현을 확인한다. 필요한 `latest.yml`, `latest-mac.yml`, ZIP blockmap 등 메타데이터가 있으면 해당 파일도 업로드한다. 설치 파일만 있다고 자동 업데이트가 완성된 것으로 판단하지 않는다.

## publish-release

`version`, `windows-build`, `macos-build`에 모두 의존한다. 릴리스 노트를 checkout하고 이 실행의 두 release artifact만 `release-assets` 아래로 다운로드한다. 게시 전에 다음을 검사한다.

1. 필요한 모든 OS·아키텍처의 파일과 체크섬이 존재한다.
2. SHA256 파일이 가리키는 basename이 실제 다운로드 파일과 일치하고 해시가 맞는다.
3. 릴리스 asset 이름이 중복되지 않으며 릴리스 노트가 존재하고 비어 있지 않다.
4. 같은 태그의 기존 릴리스·태그 상태를 조회한다. 인증·네트워크 오류를 “태그가 없음”으로 처리하지 않는다. 기존 태그가 다른 SHA라면 중단한다.

`GH_TOKEN: ${{ github.token }}`, `GH_REPO: ${{ github.repository }}`, `A8A_APP_VERSION: ${{ needs.version.outputs.app_version }}`를 전달한다. 아래는 검사가 끝난 신규 릴리스용 PowerShell 게시 단계다.

```powershell
$ErrorActionPreference = "Stop"
$version = $env:A8A_APP_VERSION
$tag = "v$version"
$assets = @(Get-ChildItem -Path release-assets -Recurse -File |
  Select-Object -ExpandProperty FullName)
if ($assets.Count -eq 0) { throw "No release assets found." }
gh release create $tag @assets --repo $env:GH_REPO --target $env:GITHUB_SHA --latest --title $version --notes-file build/release-notes.md
if ($LASTEXITCODE -ne 0) { throw "Release creation failed." }
```

`--target`은 새 태그 생성 시 빌드한 SHA를 지정한다. 이미 존재하는 태그를 바꾸는 옵션이 아니므로 기존 태그 검사는 별도로 필요하다. 기존 릴리스가 있다면 상태를 보고하고 신규 생성은 멈춘다. 사용자가 복구를 요청한 경우에만 기존 파일·커밋을 비교한 뒤 허용된 범위의 복구를 수행한다.

사용자 예시는 `--latest`로 정식 최신 릴리스를 게시한다. 과거 버전 재배포나 prerelease 요청에는 채널·latest 정책을 맞춰 조정한다.

## 공식 참고 자료

- [gh release create](https://cli.github.com/manual/gh_release_create): 태그 생성, target, 노트, asset 게시 옵션.
- [Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): 실행 동시성 및 대기 실행 처리.
