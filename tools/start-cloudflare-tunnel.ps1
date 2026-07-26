param(
  [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Join-Path $scriptDir "docker-compose.tunnel.yml"

$env:TUNNEL_ORIGIN = "http://host.docker.internal:$Port"

docker compose -f $composeFile up -d
Start-Sleep -Seconds 5

$logs = docker compose -f $composeFile logs --tail=120 cloudflared
$matches = [regex]::Matches($logs, "https://[-a-zA-Z0-9.]+\.trycloudflare\.com")

if ($matches.Count -gt 0) {
  $url = $matches[$matches.Count - 1].Value
  Write-Host "Cloudflare Tunnel is ready:"
  Write-Host $url
  Write-Host "Share this URL with your users."
} else {
  Write-Host "Tunnel started. Run this command to find the public URL:"
  Write-Host "docker compose -f tools/docker-compose.tunnel.yml logs -f cloudflared"
}
