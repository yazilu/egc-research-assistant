param(
  [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cloudflared = Join-Path $scriptDir "bin\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
  throw "cloudflared.exe not found at $cloudflared"
}

& $cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$Port"
