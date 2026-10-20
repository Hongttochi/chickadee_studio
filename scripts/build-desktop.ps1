param([switch]$SkipInstall, [switch]$SkipEngine)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install requirements-dev.txt into .venv first.' }
    $env:PLAYWRIGHT_BROWSERS_PATH = '0'
    if (-not $SkipEngine) {
        & $taskPython -m playwright install chromium --only-shell
        if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
        & $taskPython -m PyInstaller --noconfirm --clean --distpath artifacts\engine-0.5.0 --workpath artifacts\engine-build-0.5.0 scripts\engine.spec
        if ($LASTEXITCODE -ne 0) { throw 'Engine build failed.' }
        if (-not (Test-Path -LiteralPath 'artifacts\engine-0.5.0\ChickadeeEngine\ChickadeeEngine.exe')) { throw 'Engine executable is missing.' }
    }
    Push-Location desktop
    try {
        if (-not $SkipInstall) {
            npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Desktop dependency installation failed.' }
        }
        $env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
        npm.cmd run package
        if ($LASTEXITCODE -ne 0) { throw 'Desktop package build failed.' }
    } finally { Pop-Location }
    if (-not (Test-Path -LiteralPath 'artifacts\electron-0.5.0\win-unpacked\Chickadee.exe')) { throw 'Desktop executable is missing: inspect the build log and free disk space.' }
    if (-not (Test-Path -LiteralPath 'artifacts\electron-0.5.0\win-unpacked\resources\engine\ChickadeeEngine.exe')) { throw 'Bundled scan engine is missing.' }
    Write-Output 'Built artifacts\electron-0.5.0\win-unpacked\Chickadee.exe. Distribute the complete win-unpacked folder.'
} finally { Pop-Location }
