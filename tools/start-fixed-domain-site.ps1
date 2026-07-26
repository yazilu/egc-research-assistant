param(
  [string]$GatewayUser = "egc",
  [string]$GatewayPassword = "xzc123456",
  [int]$Port = 8080,
  [string]$Token = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path (Join-Path $scriptDir "..")
$nodeExe = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$gatewayScript = Join-Path $scriptDir "tunnel-gateway.mjs"
$gatewayOut = Join-Path $scriptDir "gateway.out.log"
$gatewayErr = Join-Path $scriptDir "gateway.err.log"

if (-not (Test-Path $nodeExe)) {
  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if (-not $nodeCommand) {
    throw "Node.js was not found. Install Node.js or add node.exe to PATH."
  }
  $nodeExe = $nodeCommand.Source
}

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

Push-Location (Join-Path $rootDir "frontend")
try {
  & $nodeExe ".\node_modules\typescript\bin\tsc" -b
  & $nodeExe ".\node_modules\vite\bin\vite.js" build
}
finally {
  Pop-Location
}

$existingGateway = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  Select-Object -First 1

if ($existingGateway) {
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

  $gateway = Start-Process `
    -FilePath $nodeExe `
    -ArgumentList @("`"$gatewayScript`"") `
    -WorkingDirectory $rootDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $gatewayOut `
    -RedirectStandardError $gatewayErr `
    -PassThru

  Write-Host "Gateway started on http://127.0.0.1:$Port"
  Write-Host "Gateway PID: $($gateway.Id)"
}

powershell -ExecutionPolicy Bypass -File (Join-Path $scriptDir "start-cloudflare-named-tunnel.ps1") -Token $Token -Background

Write-Host "Fixed-domain local site startup complete."
