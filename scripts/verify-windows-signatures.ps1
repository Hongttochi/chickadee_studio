param(
    [Parameter(Mandatory=$true)][string]$AppDirectory,
    [switch]$AllNative,
    [switch]$RequireTrusted
)
$ErrorActionPreference = 'Stop'
# Read-only Windows trust verification. Never creates certificates or changes policy.
$taskApp = (Resolve-Path -LiteralPath $AppDirectory).Path
$taskEntries = @('Chickadee.exe', 'resources/engine/ChickadeeEngine.exe')
foreach ($taskEntry in $taskEntries) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskApp $taskEntry))) { throw "Missing application entry point: $taskEntry" }
}
$taskFiles = if ($AllNative) {
    @(Get-ChildItem -LiteralPath $taskApp -File -Recurse | Where-Object { $_.Extension -in @('.exe','.dll','.pyd','.node') })
} else { @($taskEntries | ForEach-Object { Get-Item -LiteralPath (Join-Path $taskApp $_) }) }
$taskResults = @($taskFiles | ForEach-Object {
    $taskSignature = Get-AuthenticodeSignature -LiteralPath $_.FullName
    $taskEKUs = @($taskSignature.SignerCertificate.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' } | ForEach-Object { $_.EnhancedKeyUsages } | ForEach-Object { $_.Value })
    $taskValid = $taskSignature.Status -eq 'Valid' -and $taskEKUs -contains '1.3.6.1.5.5.7.3.3'
    [pscustomobject]@{
        path = $_.FullName.Substring($taskApp.TrimEnd('\').Length + 1).Replace('\','/')
        status = [string]$taskSignature.Status
        trusted = [bool]$taskValid
        publisher = if ($taskSignature.SignerCertificate) { $taskSignature.SignerCertificate.Subject } else { $null }
        thumbprint = if ($taskSignature.SignerCertificate) { $taskSignature.SignerCertificate.Thumbprint } else { $null }
        timestamped = $null -ne $taskSignature.TimeStamperCertificate
    }
})
$taskTrusted = @($taskResults | Where-Object { -not $_.trusted }).Count -eq 0
$taskReport = [pscustomobject]@{
    checked_at = [DateTimeOffset]::Now.ToString('o')
    trusted = $taskTrusted
    all_native_checked = [bool]$AllNative
    files = $taskResults
}
$taskReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskApp 'windows-signatures.json') -Encoding UTF8
if ($RequireTrusted -and -not $taskTrusted) { throw 'Trusted Windows code signatures are missing or invalid. Security settings were not changed.' }
Write-Output ("Windows signature check: trusted={0}; native files checked={1}" -f $taskTrusted, $taskFiles.Count)
