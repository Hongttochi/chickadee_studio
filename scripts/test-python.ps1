param([string]$LogDirectory = 'artifacts/python-tests')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    $env:PYTHONUTF8 = '1'
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $taskResults = @()
    # Fresh Windows event-loop/socket state for each module; every failure is kept.
    foreach ($taskFile in (Get-ChildItem -LiteralPath tests -Filter 'test_*.py' -File | Sort-Object Name)) {
        $taskModule = 'tests.' + $taskFile.BaseName
        $taskLog = Join-Path $LogDirectory ($taskModule + '.log')
        & .venv/Scripts/python.exe -m unittest $taskModule -v *> $taskLog
        $taskCode = $LASTEXITCODE
        $taskResults += [pscustomobject]@{ module=$taskModule; exit_code=$taskCode }
        Get-Content -LiteralPath $taskLog -Tail 6
    }
    $taskResults | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $LogDirectory 'summary.json') -Encoding UTF8
    $taskFailed = @($taskResults | Where-Object { $_.exit_code -ne 0 })
    if ($taskFailed.Count) { throw ('Python regression failed: ' + (($taskFailed | ForEach-Object { $_.module }) -join ', ')) }
} finally { Pop-Location }
