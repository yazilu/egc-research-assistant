@echo off
set "BACKEND_DIR=%~dp0"
echo started %date% %time% > "%BACKEND_DIR%backend-dev-launch.log"
set DATABASE_URL=postgresql://postgres:pg123456@localhost:5432/gsk
set ES_URL=http://localhost:1200
set "NLTK_DATA=%BACKEND_DIR%nltk_data"

cd /d "%BACKEND_DIR%app"
"%BACKEND_DIR%.venv\Scripts\python.exe" app_main.py > "%BACKEND_DIR%backend-dev.combined.log" 2>&1
