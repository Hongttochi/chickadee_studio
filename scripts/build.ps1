param([switch]$SkipBrowserInstall)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv and install requirements-dev.txt first. See docs/manual.md.'
}
Push-Location $taskRoot
try {
    $env:PLAYWRIGHT_BROWSERS_PATH = '0'
    if (-not $SkipBrowserInstall) {
        & $taskPython -m playwright install chromium --only-shell
        if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
    }
    & $taskPython -m PyInstaller --noconfirm --clean --onedir --windowed --name ChickadeeBot --add-data 'chickadee/extract.js;chickadee' --add-data 'chickadee/rules.json;chickadee' --add-data 'schemas/result.schema.json;schemas' --add-data 'chickadee/demo_site;chickadee/demo_site' run.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    Copy-Item -LiteralPath 'docs\manual.md' -Destination 'dist\ChickadeeBot\MANUAL.md'
    Copy-Item -LiteralPath 'docs\third-party-notices.md' -Destination 'dist\ChickadeeBot\THIRD-PARTY-NOTICES.md'
    Copy-Item -LiteralPath 'README.md' -Destination 'dist\ChickadeeBot\README.md'
    Copy-Item -LiteralPath 'docs' -Destination 'dist\ChickadeeBot\docs' -Recurse
    Copy-Item -LiteralPath 'profiles' -Destination 'dist\ChickadeeBot\profiles' -Recurse
    Write-Output 'Built dist\ChickadeeBot\ChickadeeBot.exe. Distribute the whole ChickadeeBot folder.'
} finally {
    Pop-Location
}
