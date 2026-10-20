param([switch]$SkipBrowserInstall, [string]$DistPath = 'dist')
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
    & $taskPython -m PyInstaller --noconfirm --clean --onedir --windowed --distpath $DistPath --name ChickadeeBot --add-data 'chickadee/extract.js;chickadee' --add-data 'chickadee/rules.json;chickadee' --add-data 'schemas/result.schema.json;schemas' --add-data 'chickadee/demo_site;chickadee/demo_site' run.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    $taskApp = Join-Path $DistPath 'ChickadeeBot'
    Copy-Item -LiteralPath 'docs\manual.md' -Destination (Join-Path $taskApp 'MANUAL.md')
    Copy-Item -LiteralPath 'docs\third-party-notices.md' -Destination (Join-Path $taskApp 'THIRD-PARTY-NOTICES.md')
    Copy-Item -LiteralPath 'README.md' -Destination (Join-Path $taskApp 'README.md')
    Copy-Item -LiteralPath 'docs' -Destination (Join-Path $taskApp 'docs') -Recurse
    Copy-Item -LiteralPath 'profiles' -Destination (Join-Path $taskApp 'profiles') -Recurse
    Copy-Item -Path 'scripts\windows\*.cmd' -Destination $taskApp
    Copy-Item -LiteralPath 'schemas\result-csv.columns.json' -Destination (Join-Path $taskApp 'docs\result-csv.columns.json')
    Write-Output "Built $taskApp\ChickadeeBot.exe. Distribute the whole ChickadeeBot folder."
} finally {
    Pop-Location
}
