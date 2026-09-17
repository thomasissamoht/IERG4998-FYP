$ErrorActionPreference = "Stop"

$tunnelName = "bib-manager"
$hostname = "bib.tomisthebest.win"
$configDirectory = Join-Path $HOME ".cloudflared"
$configPath = Join-Path $configDirectory "config.yml"
$cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = if ($cloudflaredCommand) { $cloudflaredCommand.Source } else { "C:\Program Files (x86)\cloudflared\cloudflared.exe" }
if (-not (Test-Path $cloudflaredPath)) {
  throw "cloudflared was not found. Reopen PowerShell or reinstall Cloudflare Tunnel."
}

Write-Host "Opening Cloudflare login..."
& $cloudflaredPath tunnel login

$tunnelJson = & $cloudflaredPath tunnel list --output json | ConvertFrom-Json
$tunnel = @($tunnelJson) | Where-Object { $_.name -eq $tunnelName } | Select-Object -First 1
if (-not $tunnel) {
    Write-Host "Creating named tunnel '$tunnelName'..."
  & $cloudflaredPath tunnel create $tunnelName
  $tunnelJson = & $cloudflaredPath tunnel list --output json | ConvertFrom-Json
    $tunnel = @($tunnelJson) | Where-Object { $_.name -eq $tunnelName } | Select-Object -First 1
}

if (-not $tunnel -or -not $tunnel.id) {
    throw "Could not find the '$tunnelName' tunnel after creation. Run: cloudflared tunnel list"
}

$tunnelId = $tunnel.id
$credentialsPath = Join-Path $configDirectory "$tunnelId.json"
if (-not (Test-Path $credentialsPath)) {
    throw "Tunnel credentials were not found at $credentialsPath"
}

Write-Host "Routing $hostname to the tunnel..."
& $cloudflaredPath tunnel route dns $tunnelName $hostname

New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
@"
tunnel: $tunnelId
credentials-file: $credentialsPath
ingress:
  - hostname: $hostname
    service: http://localhost:8501
  - service: http_status:404
"@ | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Tunnel configured successfully."
Write-Host "Config: $configPath"
Write-Host "Next: run .\start_bib_public.ps1"
