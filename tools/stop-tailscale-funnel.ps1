$ErrorActionPreference = "SilentlyContinue"

$tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tailscale -and (Test-Path "C:\Program Files\Tailscale\tailscale.exe")) {
  $tailscale = Get-Item "C:\Program Files\Tailscale\tailscale.exe"
}

if ($tailscale) {
  & $tailscale.Source funnel --https=443 off
}

Get-NetTCPConnection -LocalPort 8080 |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ }

Write-Host "Stopped Tailscale Funnel and local gateway."
