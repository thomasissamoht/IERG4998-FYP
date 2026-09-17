$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $HOME ".cloudflared\config.yml"
$streamlitPath = Join-Path $projectRoot "venv\Scripts\streamlit.exe"
$cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = if ($cloudflaredCommand) { $cloudflaredCommand.Source } else { "C:\Program Files (x86)\cloudflared\cloudflared.exe" }

if (-not (Test-Path $configPath)) {
    throw "Tunnel is not configured. Run .\setup_cloudflare_tunnel.ps1 first."
}
if (-not (Test-Path $streamlitPath)) {
    throw "The project virtual environment was not found at $streamlitPath"
}
if (-not (Test-Path $cloudflaredPath)) {
    throw "cloudflared was not found. Reopen PowerShell or reinstall Cloudflare Tunnel."
}

$env:BIB_PUBLIC_BASE_URL = "https://bib.tomisthebest.win/app/static"

Write-Host "Starting Streamlit on http://localhost:8501 ..."
$streamlit = Start-Process -FilePath $streamlitPath -ArgumentList "run", "bib_streamlit.py", "--server.headless", "true" -WorkingDirectory $projectRoot -PassThru

try {
    Write-Host "Starting Cloudflare Tunnel for https://bib.tomisthebest.win ..."
    & $cloudflaredPath tunnel run bib-manager
}
finally {
    if ($streamlit -and -not $streamlit.HasExited) {
        Stop-Process -Id $streamlit.Id -Force
    }
}
