param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

$candidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Host "Inno Setup compiler (ISCC.exe) not found."
    Write-Host "Install Inno Setup from https://jrsoftware.org/isinfo.php"
    exit 1
}

Write-Host "Using ISCC: $iscc"
& $iscc "/DMyAppVersion=$Version" "installer\BibTeXManager.iss"
exit $LASTEXITCODE
