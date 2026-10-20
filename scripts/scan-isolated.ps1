param(
    [string]$Url = 'http://113.198.66.73:18244/parents/board/index.do?menu_idx=8&manage_idx=106',
    [string]$Distro = 'Ubuntu-24.04',
    [string]$OutputDir = '',
    [string]$SourceRoot = '',
    [string]$Profile = 'profiles/inuri-test.json',
    [int]$MaxPages = 100,
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
if (-not $SourceRoot) { $SourceRoot = Split-Path -Parent $PSScriptRoot }
$taskRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
if (-not $OutputDir) { $OutputDir = Join-Path $taskRoot 'artifacts\isolated-test' }
$taskOutput = [System.IO.Path]::GetFullPath($OutputDir)
$taskUri = [uri]$Url
if ($taskUri.Scheme -notin @('http', 'https') -or -not $taskUri.Host -or $taskUri.UserInfo) { throw 'Use an HTTP(S) URL without credentials.' }
if ($MaxPages -lt 1 -or $MaxPages -gt 1000) { throw 'MaxPages must be 1..1000.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'deploy\Dockerfile'))) { throw 'Isolated source files are missing.' }
$taskLinuxRoot = (& wsl.exe -d $Distro --exec wslpath -a -u $taskRoot).Trim()
if ($LASTEXITCODE -ne 0 -or -not $taskLinuxRoot) { throw 'WSL distribution is unavailable.' }
& wsl.exe -d $Distro --exec docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running inside WSL.' }
if (-not $SkipBuild) {
    & wsl.exe -d $Distro --exec docker build -f "$taskLinuxRoot/deploy/Dockerfile" -t chickadee-scan:0.4.2 $taskLinuxRoot
    if ($LASTEXITCODE -ne 0) { throw 'Isolated image build failed.' }
}
$taskName = 'chickadee-scan-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$taskVolume = $taskName + '-output'
$taskCreated = $false
$taskExitCode = 1
try {
    $taskCreate = @('create', '--name', $taskName, '--label', 'app=chickadee-isolated-scan', '--init',
        '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
        "--security-opt=seccomp=$taskLinuxRoot/deploy/seccomp_profile.json", '--memory=1536m', '--cpus=2',
        '--pids-limit=256', '--shm-size=256m', '--tmpfs=/tmp:rw,nosuid,nodev,size=256m',
        "--mount=type=volume,source=$taskVolume,target=/results",
        'chickadee-scan:0.4.2', '--scan', $Url, '--network', '--verbose', '--profile', $Profile,
        '--max-pages', "$MaxPages", '--timeout', '300', '--page-timeout', '20',
        '--settle-ms', '200', '--interval', '0.2', '--output-dir', '/results')
    & wsl.exe -d $Distro --exec docker @taskCreate
    if ($LASTEXITCODE -ne 0) { throw 'Container creation failed.' }
    $taskCreated = $true
    & wsl.exe -d $Distro --exec docker start -a $taskName
    $taskExitCode = $LASTEXITCODE
    New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
    $taskLinuxOutput = (& wsl.exe -d $Distro --exec wslpath -a -u $taskOutput).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Output path conversion failed.' }
    # No host folder or Docker socket is mounted in the browser container.
    # Copy only these three inert output files after the process has exited.
    foreach ($taskFile in @('result.json', 'scan-report.json', 'result.csv')) {
        & wsl.exe -d $Distro --exec docker cp "${taskName}:/results/$taskFile" "$taskLinuxOutput/$taskFile"
        if ($LASTEXITCODE -ne 0) { throw "Missing output: $taskFile" }
    }
    Write-Output "Results: $taskOutput"
    Write-Output "Scanner exit code: $taskExitCode (0 complete, 2 partial/cancelled, 1 failed)."
} finally {
    if ($taskCreated) {
        & wsl.exe -d $Distro --exec docker rm -f $taskName | Out-Null
        & wsl.exe -d $Distro --exec docker volume rm $taskVolume | Out-Null
    }
}
exit $taskExitCode
