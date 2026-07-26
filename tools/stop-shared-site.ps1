$ErrorActionPreference = "SilentlyContinue"

Get-Process cloudflared | Stop-Process

Get-NetTCPConnection -LocalPort 8080 |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ }

Write-Host "Stopped Cloudflare Tunnel and local gateway processes."
