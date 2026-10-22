param([switch]$SkipInstall, [switch]$SkipEngine, [switch]$RequireSigned)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskVersion = (Get-Content -LiteralPath (Join-Path $taskRoot 'desktop/package.json') -Raw | ConvertFrom-Json).version
Push-Location $taskRoot
try {
    $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install requirements-dev.txt into .venv first.' }
    $env:PLAYWRIGHT_BROWSERS_PATH = '0'
    if (-not $SkipEngine) {
        & $taskPython scripts/prepare_ocr_models.py
        if ($LASTEXITCODE -ne 0) { throw 'OCR model preparation failed.' }
        & $taskPython -m playwright install chromium --only-shell
        if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
        # Extended-length paths avoid MAX_PATH during bundled Chromium copies.
        # This does not require changing Windows policy or machine settings.
        $taskEngineDist = "\\?\$taskRoot\artifacts\engine-$taskVersion"
        $taskEngineWork = "\\?\$taskRoot\artifacts\engine-build-$taskVersion"
        & $taskPython -m PyInstaller --noconfirm --distpath $taskEngineDist --workpath $taskEngineWork scripts/engine.spec
        if ($LASTEXITCODE -ne 0) { throw 'Engine build failed.' }
        if (-not (Test-Path -LiteralPath "artifacts/engine-$taskVersion/ChickadeeEngine/ChickadeeEngine.exe")) { throw 'Engine executable is missing.' }
    }
    Push-Location desktop
    try {
        if (-not $SkipInstall) {
            npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Desktop dependency installation failed.' }
        }
        $env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
        if ($RequireSigned) { npm.cmd run package -- --config.win.signAndEditExecutable=true --config.forceCodeSigning=true }
        else { npm.cmd run package }
        if ($LASTEXITCODE -ne 0) { throw 'Desktop package build failed.' }
    } finally { Pop-Location }
    if (-not (Test-Path -LiteralPath "artifacts/electron-$taskVersion/win-unpacked/Chickadee.exe")) { throw 'Desktop executable is missing: inspect the build log and free disk space.' }
    if (-not (Test-Path -LiteralPath "artifacts/electron-$taskVersion/win-unpacked/resources/engine/ChickadeeEngine.exe")) { throw 'Bundled scan engine is missing.' }
    if (-not $RequireSigned) {
        $taskRuntime = Get-Content -LiteralPath 'desktop/vendor-runtime.json' -Raw | ConvertFrom-Json
        $taskInstalledVersion = (Get-Content -LiteralPath 'desktop/node_modules/electron/package.json' -Raw | ConvertFrom-Json).version
        $taskVendorExe = Join-Path $taskRoot 'desktop/node_modules/electron/dist/electron.exe'
        if (-not (Test-Path -LiteralPath $taskVendorExe)) {
            # electron-builder can download Electron without installing its npm
            # binary. Obtain the pinned upstream EXE independently in that case.
            $taskVendorDirectory = Join-Path $taskRoot "artifacts/vendor-runtime/$($taskRuntime.version)"
            New-Item -ItemType Directory -Path $taskVendorDirectory -Force | Out-Null
            $taskVendorArchive = Join-Path $taskVendorDirectory 'electron.zip'
            if (-not (Test-Path -LiteralPath $taskVendorArchive)) {
                Invoke-WebRequest -Uri $taskRuntime.source_url -OutFile $taskVendorArchive
            }
            if ((Get-FileHash -LiteralPath $taskVendorArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRuntime.archive_sha256) { throw 'Official Electron archive SHA256 mismatch.' }
            $taskVendorExe = Join-Path $taskVendorDirectory 'electron.exe'
            $taskArchive = [IO.Compression.ZipFile]::OpenRead($taskVendorArchive)
            try {
                $taskEntry = $taskArchive.GetEntry('electron.exe')
                if ($null -eq $taskEntry) { throw 'Official Electron archive has no executable.' }
                [IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntry, $taskVendorExe, $true)
            } finally { $taskArchive.Dispose() }
        }
        $taskVendorHash = (Get-FileHash -LiteralPath $taskVendorExe -Algorithm SHA256).Hash.ToLowerInvariant()
        $taskAppHash = (Get-FileHash -LiteralPath "artifacts/electron-$taskVersion/win-unpacked/Chickadee.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($taskInstalledVersion -ne $taskRuntime.version -or $taskVendorHash -ne $taskRuntime.executable_sha256) {
            throw 'The installed Electron runtime differs from the pinned official release.'
        }
        # Keep electron-builder's embedded ASAR integrity resource. Only its
        # verified output for this app version may receive the character icon.
        $taskAsarHash = (Get-FileHash -LiteralPath "artifacts/electron-$taskVersion/win-unpacked/resources/app.asar" -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($taskRuntime.app_version -ne $taskVersion -or $taskAsarHash -ne $taskRuntime.app_asar_sha256 -or $taskAppHash -ne $taskRuntime.builder_executable_sha256) {
            throw 'The packaged app differs from the pinned ASAR-integrity build. Verify and update vendor-runtime.json for this version.'
        }
        $taskIcon = Join-Path $taskRoot 'desktop/assets/app.ico'
        $taskEditor = Join-Path $taskRoot "desktop/node_modules/$($taskRuntime.icon_editor)"
        if ((Get-FileHash -LiteralPath $taskIcon -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRuntime.icon_sha256 -or
            (Get-FileHash -LiteralPath $taskEditor -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRuntime.icon_editor_sha256) {
            throw 'The app icon or icon editor differs from the pinned build inputs.'
        }
        $taskApp = Join-Path $taskRoot "artifacts/electron-$taskVersion/win-unpacked/Chickadee.exe"
        $taskVendorInfo = (Get-Item -LiteralPath $taskVendorExe).VersionInfo
        & $taskEditor $taskApp --set-icon $taskIcon
        if ($LASTEXITCODE -ne 0) { throw 'App icon update failed.' }
        $taskAppInfo = (Get-Item -LiteralPath $taskApp).VersionInfo
        foreach ($taskField in @('CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','OriginalFilename','ProductName','ProductVersion')) {
            if ($taskAppInfo.$taskField -cne $taskVendorInfo.$taskField) { throw "Upstream runtime metadata changed: $taskField" }
        }
        $taskAppHash = (Get-FileHash -LiteralPath $taskApp -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($taskAppHash -ne $taskRuntime.packaged_executable_sha256) { throw 'The executable differs from the verified icon-only runtime.' }
        Write-Output "Chickadee icon applied; upstream runtime metadata retained: $taskAppHash"
    }
    & (Join-Path $PSScriptRoot 'verify-windows-signatures.ps1') -AppDirectory "artifacts/electron-$taskVersion/win-unpacked" -AllNative:$RequireSigned -RequireTrusted:$RequireSigned
    Write-Output "Built artifacts/electron-$taskVersion/win-unpacked/Chickadee.exe. Distribute the complete win-unpacked folder."
} finally { Pop-Location }
