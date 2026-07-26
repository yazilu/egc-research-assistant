@echo off
set "FRONTEND_DIR=%~dp0"
echo started %date% %time% > "%FRONTEND_DIR%frontend-dev-launch.log"
where node >nul 2>&1
if errorlevel 1 if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" set "PATH=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;%PATH%"
where node >nul 2>&1
if errorlevel 1 (
    echo Node.js was not found. Install Node.js or configure PATH. > "%FRONTEND_DIR%frontend-dev.combined.log"
    exit /b 1
)

cd /d "%FRONTEND_DIR%"
call "%FRONTEND_DIR%node_modules\.bin\vite.cmd" --host localhost --port 5181 > "%FRONTEND_DIR%frontend-dev.combined.log" 2>&1
