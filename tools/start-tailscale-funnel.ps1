param(
  [string]$GatewayUser = "egc",
  [string]$GatewayPassword = "xzc123456",
  [int]$Port = 8080,
  [string]$Hostname = "egc-agent"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path (Join-Path $scriptDir "..")
$gatewayOut = Join-Path $scriptDir "gateway.out.log"
$gatewayErr = Join-Path $scriptDir "gateway.err.log"
$gatewayScript = Join-Path $scriptDir "tunnel-gateway.mjs"

function Resolve-NodeExe {
  $candidates = @()
  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if ($nodeCommand) {
    $candidates += $nodeCommand.Source
  }
  if ($env:USERPROFILE) {
    $candidates += Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
  }
  $candidates += "C:\Program Files\nodejs\node.exe"

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      try {
        & $candidate --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
          return $candidate
        }
      }
      catch {
        continue
      }
    }
  }

  throw "Node.js was not found. Install Node.js or add node.exe to PATH."
}

function Resolve-TailscaleExe {
  $candidates = @()
  $tailscaleCommand = Get-Command tailscale -ErrorAction SilentlyContinue
  if ($tailscaleCommand) {
    $candidates += $tailscaleCommand.Source
  }
  $candidates += "C:\Program Files\Tailscale\tailscale.exe"

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      return $candidate
    }
  }

  throw "Tailscale was not found. Install Tailscale first."
}

$nodeExe = Resolve-NodeExe
$tailscaleExe = Resolve-TailscaleExe

Push-Location (Join-Path $rootDir "frontend")
try {
  & $nodeExe ".\node_modules\typescript\bin\tsc" -b
  & $nodeExe ".\node_modules\vite\bin\vite.js" build
}
finally {
  Pop-Location
}

$gateway = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  Select-Object -First 1

if ($gateway) {
  Write-Host "Gateway already appears to be listening on port $Port."
} else {
  if (Test-Path $gatewayOut) { Clear-Content $gatewayOut }
  if (Test-Path $gatewayErr) { Clear-Content $gatewayErr }

  $env:GATEWAY_HOST = "127.0.0.1"
  $env:GATEWAY_PORT = "$Port"
  $env:BACKEND_ORIGIN = "http://127.0.0.1:8000"
  $env:API_PREFIX = "/ai-search"
  $env:STATIC_DIR = Join-Path $rootDir "frontend\dist"
  $env:GATEWAY_USER = $GatewayUser
  $env:GATEWAY_PASSWORD = $GatewayPassword

  $process = Start-Process `
    -FilePath $nodeExe `
    -ArgumentList @("`"$gatewayScript`"") `
    -WorkingDirectory $rootDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $gatewayOut `
    -RedirectStandardError $gatewayErr `
    -PassThru

  Write-Host "Gateway started on http://127.0.0.1:$Port"
  Write-Host "Gateway PID: $($process.Id)"
}

& $tailscaleExe set --hostname=$Hostname
& $tailscaleExe funnel --yes --bg $Port

Write-Host "Tailscale Funnel is enabled."
Write-Host "Run this command to see the public URL:"
Write-Host "`"$tailscaleExe`" funnel status"
