param(
  [string]$Token = "",
  [switch]$Background
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Join-Path $scriptDir "docker-compose.tunnel-token.yml"
$cloudflared = Join-Path $scriptDir "bin\cloudflared.exe"
$outLog = Join-Path $scriptDir "cloudflared.out.log"
$errLog = Join-Path $scriptDir "cloudflared.err.log"

if (-not $Token -and $env:CLOUDFLARE_TUNNEL_TOKEN) {
  $Token = $env:CLOUDFLARE_TUNNEL_TOKEN
}

if (-not $Token) {
  $secureToken = Read-Host "Paste Cloudflare tunnel token" -AsSecureString
  $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
  try {
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
  }
  finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
  }
}

$env:CLOUDFLARE_TUNNEL_TOKEN = $Token

if (Test-Path $cloudflared) {
  if ($Background) {
    if (Test-Path $outLog) { Clear-Content $outLog }
    if (Test-Path $errLog) { Clear-Content $errLog }

    $process = Start-Process `
      -FilePath $cloudflared `
      -ArgumentList @("tunnel", "--no-autoupdate", "run", "--token", $Token) `
      -WindowStyle Hidden `
      -RedirectStandardOutput $outLog `
      -RedirectStandardError $errLog `
      -PassThru

    Write-Host "Named Cloudflare Tunnel connector started in the background."
    Write-Host "PID: $($process.Id)"
    Write-Host "Logs: $errLog"
  } else {
    Write-Host "Starting named Cloudflare Tunnel connector."
    Write-Host "Keep this terminal open while the site is shared."
    & $cloudflared tunnel --no-autoupdate run --token $Token
  }

  Write-Host "In Cloudflare Zero Trust, set the public hostname service to:"
  Write-Host "http://127.0.0.1:8080"
  exit
}

docker compose -f $composeFile up -d

Write-Host "Named Cloudflare Tunnel connector started with Docker."
Write-Host "In Cloudflare Zero Trust, set the public hostname service to:"
Write-Host "http://host.docker.internal:8080"
