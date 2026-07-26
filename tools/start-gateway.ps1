param(
  [int]$Port = 8080,
  [string]$BackendOrigin = "http://127.0.0.1:8000",
  [string]$GatewayUser = "",
  [string]$GatewayPassword = "",
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path (Join-Path $scriptDir "..")
$frontendDir = Join-Path $rootDir "frontend"
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

$nodeExe = Resolve-NodeExe

if (-not $SkipBuild) {
  Push-Location $frontendDir
  try {
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCommand) {
      npm run build
    } else {
      & $nodeExe ".\node_modules\typescript\bin\tsc" -b
      & $nodeExe ".\node_modules\vite\bin\vite.js" build
    }
  }
  finally {
    Pop-Location
  }
}

$env:GATEWAY_HOST = "127.0.0.1"
$env:GATEWAY_PORT = "$Port"
$env:BACKEND_ORIGIN = $BackendOrigin
$env:API_PREFIX = "/ai-search"
$env:STATIC_DIR = Join-Path $frontendDir "dist"
$env:GATEWAY_USER = $GatewayUser
$env:GATEWAY_PASSWORD = $GatewayPassword

Write-Host "Starting EGC gateway at http://127.0.0.1:$Port"
Write-Host "Keep this terminal open while the site is shared."
& $nodeExe $gatewayScript
